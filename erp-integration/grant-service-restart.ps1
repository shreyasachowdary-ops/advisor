# Run ONCE in an Administrator PowerShell.
# Lets the account LMSDEV_GPU\LNPLL0C.L query, start, stop and restart ONLY the
# Flask_dev and Nginx_dev services, so deploy.ps1 can be run without admin.
# Nothing else about the services or the account changes.

$sid = "S-1-5-21-357975382-678716224-966086402-1006"   # LMSDEV_GPU\LNPLL0C.L
$ace = "(A;;CCLCSWRPWPDTLOCRRC;;;$sid)"                # query + start + stop + read

foreach ($svc in "Flask_dev", "Nginx_dev") {
    $sd = ((sc.exe sdshow $svc) -join "").Trim()
    if (-not $sd.StartsWith("D:")) { Write-Host "Could not read $svc permissions: $sd"; continue }
    if ($sd.Contains($sid)) { Write-Host "$svc already allows this account."; continue }

    # Put the new rule at the end of the D: (access) part, before any S: (audit) part.
    $i = $sd.IndexOf("S:")
    $new = if ($i -ge 0) { $sd.Substring(0, $i) + $ace + $sd.Substring($i) } else { $sd + $ace }

    Write-Host "$svc old: $sd"
    sc.exe sdset $svc $new
    Write-Host "$svc new: $new"
}
