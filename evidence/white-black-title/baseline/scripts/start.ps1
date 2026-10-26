$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
foreach ($port in @(3000,8000)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) { throw "Port $port đang được sử dụng." }
}
if (-not (Test-Path '.next/BUILD_ID')) { throw 'Chạy npm run build trước.' }
New-Item -ItemType Directory -Path evidence/runtime -Force | Out-Null
$python = Join-Path $root '.venv/Scripts/python.exe'
$node = (Get-Command node).Source
$env:BACKEND_URL = 'http://127.0.0.1:8000'
$env:APP_ORIGINS = 'http://127.0.0.1:3000,http://localhost:3000'
$api = Start-Process -FilePath $python -ArgumentList '-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','8000' -WorkingDirectory $root -WindowStyle Hidden -PassThru -RedirectStandardOutput 'evidence/runtime/api.log' -RedirectStandardError 'evidence/runtime/api-error.log'
$web = $null
try {
    $web = Start-Process -FilePath $node -ArgumentList 'node_modules/next/dist/bin/next','start','--hostname','127.0.0.1','--port','3000' -WorkingDirectory $root -WindowStyle Hidden -PassThru -RedirectStandardOutput 'evidence/runtime/web.log' -RedirectStandardError 'evidence/runtime/web-error.log'
    $ready = $false
    for ($n=0; $n -lt 40; $n++) {
        Start-Sleep -Milliseconds 500
        if ($api.HasExited -or $web.HasExited) { throw 'Dịch vụ dừng khi khởi động; xem evidence/runtime.' }
        try {
            $health = Invoke-RestMethod 'http://127.0.0.1:8000/health'
            $catalog = Invoke-RestMethod 'http://127.0.0.1:3000/api/v1/catalog'
            if ($health.status -eq 'ok' -and $catalog.organizer -eq 'CMC Infrasec') { $ready=$true; break }
        } catch { }
    }
    if (-not $ready) { throw 'Hết thời gian chờ dịch vụ.' }
    @(@{ id=$api.Id; started=$api.StartTime.ToUniversalTime().ToString('o') }, @{ id=$web.Id; started=$web.StartTime.ToUniversalTime().ToString('o') }) | ConvertTo-Json | Set-Content 'evidence/runtime/processes.json'
    Write-Output 'RUNNING http://127.0.0.1:3000 | CMC Infrasec x NextFest 26'
} catch {
    if ($web -and -not $web.HasExited) { Stop-Process -Id $web.Id }
    if (-not $api.HasExited) { Stop-Process -Id $api.Id }
    throw
}
