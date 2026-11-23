# Apply Advisor integration to lnpl_erp_dev_v1 (Notice Agent pattern)
# Usage (school server example):
#   .\apply-to-erp.ps1 -ErpRoot "D:\lms_dev_repo\erp\lnpl_erp_dev_v1"
#   .\apply-to-erp.ps1 -ErpRoot "D:\path\to\lnpl_erp_dev_v1" -AdvisorRoles @("applicant","teacher")

param(
    [Parameter(Mandatory = $true)]
    [string]$ErpRoot,

    [string[]]$AdvisorRoles = @()
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not (Test-Path $ErpRoot)) {
    Write-Error "ERP root not found: $ErpRoot"
}

function Get-AllAllowedRolesFromAppJs {
    param([string]$AppJsPath)
    $raw = Get-Content $AppJsPath -Raw
    $found = New-Object System.Collections.Generic.HashSet[string]
    foreach ($m in [regex]::Matches($raw, 'allowedRoles=\{(\[[^\]]*\])\}')) {
        $inner = $m.Groups[1].Value
        foreach ($rm in [regex]::Matches($inner, '"([^"]+)"')) {
            [void]$found.Add($rm.Groups[1].Value)
        }
    }
    return @($found)
}

function Get-AdvisorRolesCandidate {
    param([string[]]$AllRoles)
    $pattern = '(?i)parent|teacher|applicant|guardian|lms|principal|schooladmin|admin'
    return @($AllRoles | Where-Object { $_ -match $pattern } | Sort-Object -Unique)
}

# --- 1. Copy AdvisorPage (Communication folder, same as GenerateNotice.js) ---
$commDest = Join-Path $ErpRoot "src\components\Communication"
New-Item -ItemType Directory -Force -Path $commDest | Out-Null
$canonical = Join-Path $ScriptDir "src\components\Communication\AdvisorPage.js"
if (-not (Test-Path $canonical)) {
    Write-Error "Canonical AdvisorPage not found: $canonical"
}
Copy-Item $canonical (Join-Path $commDest "AdvisorPage.js") -Force
Write-Host "Copied src/components/Communication/AdvisorPage.js"

# ChildConnect UI used by AdvisorPage.js (components, API client, scoped CSS)
$advisorUiSrc = Join-Path $ScriptDir "src\components\Communication\advisor"
if (-not (Test-Path $advisorUiSrc)) {
    Write-Error "ChildConnect UI folder not found: $advisorUiSrc"
}
Copy-Item $advisorUiSrc $commDest -Recurse -Force
Write-Host "Copied src/components/Communication/advisor/ (ChildConnect UI)"

# --- 2. Copy server proxy helper ---
$serverDest = Join-Path $ErpRoot "server"
if (-not (Test-Path $serverDest)) {
    $serverDest = Join-Path $ErpRoot "src\server"
}
New-Item -ItemType Directory -Force -Path $serverDest | Out-Null
$proxySrc = Join-Path $ScriptDir "server\registerAdvisorProxy.js"
Copy-Item $proxySrc (Join-Path $serverDest "registerAdvisorProxy.js") -Force
Write-Host "Copied server/registerAdvisorProxy.js — wire into ERP server next to notice-agent routes"

# --- 3. App.js: import + RoleRoute (after Generate Notice) ---
$appJs = Join-Path $ErpRoot "src\components\App.js"
if (-not (Test-Path $appJs)) {
    Write-Error "App.js not found at $appJs"
}

$appRaw = Get-Content $appJs -Raw
if ($appRaw -notmatch "AdvisorPage") {
    if ($appRaw -match 'import\s+GenerateNotice\s+from\s+"\./Communication/GenerateNotice\.js";') {
        $appRaw = $appRaw -replace '(import\s+GenerateNotice\s+from\s+"\./Communication/GenerateNotice\.js";)', "`$1`r`nimport AdvisorPage from `"./Communication/AdvisorPage.js`";"
    } elseif ($appRaw -match 'import\s+GenerateNotice') {
        $appRaw = $appRaw -replace '(import\s+GenerateNotice[^\r\n]+)', "`$1`r`nimport AdvisorPage from `"./Communication/AdvisorPage.js`";"
    } else {
        Write-Warning "GenerateNotice import not found; add manually: import AdvisorPage from `"./Communication/AdvisorPage.js`";"
    }

    $roles = @($AdvisorRoles)
    if ($roles.Count -eq 0) {
        $all = Get-AllAllowedRolesFromAppJs -AppJsPath $appJs
        $roles = Get-AdvisorRolesCandidate -AllRoles $all
    }
    if ($roles.Count -eq 0) {
        Write-Warning "Could not infer Advisor allowedRoles from App.js. Edit the route after apply and set allowedRoles for Parent/Teacher users."
        $roles = @("CONFIRM_ROLE_PARENT", "CONFIRM_ROLE_TEACHER")
    }
    $rolesJson = ($roles | ForEach-Object { "`"$_`"" }) -join ", "

    $routeBlock = @"
              <Route
                path="/advisor"
                element={
                  <RoleRoute
                    allowedRoles={[$rolesJson]}
                  >
                    <AdvisorPage />
                  </RoleRoute>
                }
              />
"@

    if ($appRaw -match 'path="/generate-notice"') {
        $appRaw = [regex]::Replace(
            $appRaw,
            '(<Route\s+path="/generate-notice"[\s\S]*?</Route>)',
            "`$1`r`n$routeBlock",
            1
        )
    } else {
        Write-Warning "/generate-notice route not found; add /advisor route manually (see patches/App.js.advisor-snippet.txt)"
    }

    Set-Content -Path $appJs -Value $appRaw -NoNewline
    Write-Host "Patched App.js (import + /advisor RoleRoute). Roles: [$rolesJson]"
} else {
    Write-Host "App.js already references AdvisorPage — skipped route patch"
}

# --- 4. Sidebar link (optional) ---
$dashJs = Join-Path $ErpRoot "src\components\Applicant\dashboard_applicant.js"
if ((Test-Path $dashJs) -and ((Get-Content $dashJs -Raw) -notmatch '"/advisor"')) {
    $dashLines = Get-Content $dashJs
    $newDash = @()
    foreach ($line in $dashLines) {
        $newDash += $line
        if ($line -match 'Lesson Planning|generate-notice|Generate Notice') {
            $newDash += '        { to: "/advisor", label: "Parent/Teacher Advisor" },'
            break
        }
    }
    if ($newDash.Count -gt $dashLines.Count) {
        Set-Content $dashJs $newDash
        Write-Host "Patched dashboard sidebar"
    }
}

# --- 5. Find Notice Agent proxy for manual wiring ---
Write-Host "`n--- Notice Agent proxy files (mirror for Advisor) ---"
$noticeHits = @()
Get-ChildItem $ErpRoot -Recurse -File -Include *.js,*.ts,*.mjs -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch 'node_modules' } |
    ForEach-Object {
        if (Select-String -Path $_.FullName -Pattern '/api/notice-agent' -Quiet) {
            $noticeHits += $_.FullName
        }
    }
if ($noticeHits.Count -eq 0) {
    Write-Warning "No /api/notice-agent routes found under ERP. Register registerAdvisorProxy.js in your ERP API server manually."
} else {
    $noticeHits | ForEach-Object { Write-Host "  $_" }
    Write-Host "Add registerAdvisorProxy(app) in the same server entry as notice-agent, or forward /api/advisor/* the same way."
}

Write-Host "`nSet ADVISOR_BACKEND_URL on the ERP server (e.g. http://127.0.0.1:8787). Restart ERP + Advisor uvicorn."
Write-Host "Done."
