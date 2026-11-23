# Run ONCE in an Administrator PowerShell:
#   powershell -ExecutionPolicy Bypass -File D:\ds_projects\agenticAI\Shreyas\advisor\erp-integration\install-advisor-service.ps1
#
# Creates two Windows services with NSSM (the same tool used for Flask_dev and Nginx_dev),
# so the advisor starts by itself when the server boots and restarts if it crashes:
#   Ollama_dev   - "ollama serve" on 127.0.0.1:11434 (the LLM the advisor uses)
#   Advisor_dev  - the advisor FastAPI backend on 127.0.0.1:8787 (starts after Ollama_dev)
# Both run as the built-in Windows system account (LocalSystem, like LMSFirewallWorker),
# so no password is needed. Both listen only on 127.0.0.1; the public still goes through Flask login.
# Flask_dev, Nginx_dev and the ERP are not changed.
# Safe to run again: existing services are updated, not duplicated.

$ErrorActionPreference = "Stop"

$nssm        = "C:\nssm\win64\nssm.exe"
$account     = "LocalSystem"   # built-in system account: no password needed
$accountSid  = "S-1-5-21-357975382-678716224-966086402-1006"   # LMSDEV_GPU\LNPLL0C.L (gets restart rights)

$ollamaDir   = "C:\Users\LNPLL0C.L\AppData\Local\Programs\Ollama"
$ollamaExe   = "$ollamaDir\ollama.exe"
$ollamaApp   = "$ollamaDir\ollama app.exe"
$ollamaModels= "D:\OllamaModels"   # the folder Ollama uses now (has gemma4:12b, nomic-embed-text, qwen3.8)

$backendDir  = "D:\ds_projects\agenticAI\Shreyas\advisor\backend"
$python      = "$backendDir\.venv\Scripts\python.exe"
$logDir      = "$backendDir\logs"

# ---- checks -------------------------------------------------------------------
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
           ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { throw "Please run this in an Administrator PowerShell." }
foreach ($f in $nssm, $ollamaExe, $python) {
    if (-not (Test-Path $f)) { throw "Not found: $f" }
}
New-Item -ItemType Directory -Force $logDir | Out-Null

# ---- helper: run nssm and stop with its message if it fails ---------------------
function Invoke-Nssm {
    $out = & $nssm @args 2>&1
    if ($LASTEXITCODE -ne 0) { throw "nssm $($args[0]) $($args[1]) $($args[2]) failed: $(($out | Out-String) -replace "`0", '')" }
}

# ---- helper: create or update one NSSM service --------------------------------
function Install-NssmService {
    param($Name, $Exe, $AppArgs, $Dir, $Description, $EnvExtra, $DependsOn)

    $exists = $null -ne (Get-Service $Name -ErrorAction SilentlyContinue)
    if ($exists) {
        Write-Host "$Name exists - stopping it to update settings."
        & $nssm stop $Name | Out-Null
        Invoke-Nssm set $Name Application $Exe
    } else {
        Write-Host "Creating $Name."
        Invoke-Nssm install $Name $Exe
    }
    Invoke-Nssm set $Name AppParameters $AppArgs
    Invoke-Nssm set $Name AppDirectory  $Dir
    Invoke-Nssm set $Name DisplayName   $Name
    Invoke-Nssm set $Name Description   $Description
    Invoke-Nssm set $Name Start         SERVICE_AUTO_START
    Invoke-Nssm set $Name ObjectName    $account

    # Logs, rotated at 10 MB so they don't fill the disk.
    Invoke-Nssm set $Name AppStdout      "$logDir\$Name.out.log"
    Invoke-Nssm set $Name AppStderr      "$logDir\$Name.err.log"
    Invoke-Nssm set $Name AppRotateFiles  1
    Invoke-Nssm set $Name AppRotateOnline 1
    Invoke-Nssm set $Name AppRotateBytes  10485760

    # If the program exits or crashes, start it again after 5 seconds.
    Invoke-Nssm set $Name AppExit Default Restart
    Invoke-Nssm set $Name AppRestartDelay 5000

    Invoke-Nssm set $Name AppEnvironmentExtra @EnvExtra
    if ($DependsOn) { Invoke-Nssm set $Name DependOnService $DependsOn }
}

# ---- helper: let LNPLL0C.L start/stop/restart the service without admin --------
function Grant-RestartRight {
    param($Name)
    $ace = "(A;;CCLCSWRPWPDTLOCRRC;;;$accountSid)"
    $sd = ((sc.exe sdshow $Name) -join "").Trim()
    if (-not $sd.StartsWith("D:")) { Write-Host "Could not read $Name permissions: $sd"; return }
    if ($sd.Contains($accountSid)) { return }
    $i = $sd.IndexOf("S:")
    $new = if ($i -ge 0) { $sd.Substring(0, $i) + $ace + $sd.Substring($i) } else { $sd + $ace }
    sc.exe sdset $Name $new | Out-Null
}

# ---- 1. Ollama as a service -----------------------------------------------------
# The tray app ("ollama app.exe") also runs "ollama serve" on port 11434, so it is
# closed first. Its Startup shortcut, if any, is renamed (not deleted) so it does not
# fight the service after the next login.
Write-Host "Closing the Ollama tray app (the service replaces it)."
Get-Process "ollama app", "ollama" -ErrorAction SilentlyContinue | Stop-Process -Force
foreach ($lnk in "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\Ollama.lnk",
                 "C:\Users\LNPLL0C.L\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\Ollama.lnk") {
    if (Test-Path $lnk) { Rename-Item $lnk "$lnk.disabled" -Force; Write-Host "Disabled tray autostart: $lnk" }
}

Install-NssmService -Name "Ollama_dev" -Exe $ollamaExe -AppArgs "serve" -Dir $ollamaDir `
    -Description "Ollama LLM server for the ChildConnect advisor (127.0.0.1:11434)" `
    -EnvExtra @("OLLAMA_HOST=127.0.0.1:11434", "OLLAMA_MODELS=$ollamaModels")
Grant-RestartRight "Ollama_dev"

# ---- 2. Advisor backend as a service --------------------------------------------
# Stop the copy that was started by hand, so port 8787 is free.
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match "uvicorn" -and $_.CommandLine -match "app\.main:app" } |
    ForEach-Object { Write-Host "Stopping hand-started backend (PID $($_.ProcessId))."; Stop-Process -Id $_.ProcessId -Force }

Install-NssmService -Name "Advisor_dev" -Exe $python `
    -AppArgs "-m uvicorn app.main:app --host 127.0.0.1 --port 8787" -Dir $backendDir `
    -Description "ChildConnect advisor backend (FastAPI, 127.0.0.1:8787), used by /advisor" `
    -EnvExtra @("PYTHONUNBUFFERED=1", "PYTHONIOENCODING=utf-8") `
    -DependsOn "Ollama_dev"
Grant-RestartRight "Advisor_dev"

# ---- 3. start and check ---------------------------------------------------------
Write-Host "Starting Ollama_dev and Advisor_dev."
& $nssm start Ollama_dev  | Out-Null
& $nssm start Advisor_dev | Out-Null

$ok = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep 2
    try {
        $r = Invoke-WebRequest http://127.0.0.1:8787/api/health -UseBasicParsing -TimeoutSec 5
        Write-Host "Advisor health: $($r.Content)"; $ok = $true; break
    } catch {}
}
Get-Service Ollama_dev, Advisor_dev | Format-Table Name, Status, StartType -AutoSize
if ($ok) { Write-Host "Done. Both services start automatically on boot." -ForegroundColor Green }
else     { Write-Host "Advisor did not answer yet. Check $logDir\Advisor_dev.err.log" -ForegroundColor Yellow }
