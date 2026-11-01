param([switch]$Install)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if ($Install) {
    if (-not (Test-Path '.venv/Scripts/python.exe')) { python -m venv .venv }
    & .venv/Scripts/python.exe -m pip install -r backend/requirements-lock.txt
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed' }
    Push-Location frontend
    try {
        if (Get-Command npm -ErrorAction SilentlyContinue) { npm ci }
        elseif (Test-Path '../scripts/package/bin/npm-cli.js') { node ../scripts/package/bin/npm-cli.js ci --cache ../.npm-cache }
        else { throw 'Please install Node.js with npm first' }
        if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed' }
    } finally { Pop-Location }
}
& .venv/Scripts/python.exe -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Database migration failed' }
$backendJob = Start-Job -ArgumentList $PSScriptRoot -ScriptBlock {param($root) Set-Location $root; & .venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000}
Write-Host 'Open http://127.0.0.1:5173 (Ctrl+C stops both services)'
try {
    Set-Location frontend
    node node_modules/vite/bin/vite.js --host 127.0.0.1
} finally {Stop-Job $backendJob;Remove-Job $backendJob}
