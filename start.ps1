Write-Host "Demarrage Dourbia..." -ForegroundColor Cyan

# Redis
Write-Host "[1/3] Redis..." -ForegroundColor Yellow
$redis = Get-Process redis-server -ErrorAction SilentlyContinue
if (-not $redis) {
    Start-Process "C:\Redis\redis-server.exe" -WindowStyle Minimized
    Start-Sleep -Seconds 2
    Write-Host "  Redis OK" -ForegroundColor Green
} else {
    Write-Host "  Redis deja actif" -ForegroundColor Green
}

# PostgreSQL
Write-Host "[2/3] PostgreSQL..." -ForegroundColor Yellow
$pg = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
if ($pg) {
    if ($pg.Status -ne "Running") {
        Start-Service $pg.Name
        Start-Sleep -Seconds 3
    }
    Write-Host "  PostgreSQL OK" -ForegroundColor Green
} else {
    Write-Host "  PostgreSQL introuvable" -ForegroundColor Red
}

# Docker
Write-Host "[3/3] Docker..." -ForegroundColor Yellow
$docker = Get-Process "Docker Desktop" -ErrorAction SilentlyContinue
if (-not $docker) {
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    Start-Sleep -Seconds 10
    Write-Host "  Docker demarre" -ForegroundColor Green
} else {
    Write-Host "  Docker deja actif" -ForegroundColor Green
}

# AgentLocation (Yasmine)
Write-Host "Lancement Yasmine (Location)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd E:\claude\AgentLocation; python -m uvicorn api.routes:app --host 0.0.0.0 --port 5000"

# AgentPrincipal (Chatbot)
Write-Host "Lancement AgentPrincipal..." -ForegroundColor Cyan
Set-Location "E:\claude\AgentPrincipal"
python chat.py
