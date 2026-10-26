$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$file = Join-Path $root 'evidence/runtime/processes.json'
if (Test-Path -LiteralPath $file) {
    foreach ($entry in (Get-Content -LiteralPath $file -Raw | ConvertFrom-Json)) {
        $process = Get-Process -Id $entry.id -ErrorAction SilentlyContinue
        if ($process -and $process.StartTime.ToUniversalTime().ToString('o') -eq $entry.started) { Stop-Process -Id $process.Id }
    }
    Remove-Item -LiteralPath $file
}
Write-Output 'STOPPED project services'
