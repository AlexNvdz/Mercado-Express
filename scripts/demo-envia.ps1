<#
Starts the Envia demo on this Windows machine with one command:
  Postgres (Docker container backend-api-db-1), backend-api on 127.0.0.1:8001,
  Django on 127.0.0.1:8081, an ngrok tunnel to the backend, and registers the
  tunnel's URL as Envia's tracking webhook (app/scripts/envia_webhook.py).
Backend, Django and ngrok each open in their own window: close a window (or
Ctrl+C in it) to stop that piece. Close the ngrok window when the demo ends:
while it runs, the backend is reachable from the internet.

Run from the repo root:
  powershell -ExecutionPolicy Bypass -File scripts\demo-envia.ps1
  powershell -ExecutionPolicy Bypass -File scripts\demo-envia.ps1 -NoTunnel   # no ngrok/webhook
  powershell -ExecutionPolicy Bypass -File scripts\demo-envia.ps1 -Db mercadoexpress

Needs: Docker Desktop, uv, ngrok with its authtoken (ngrok config
add-authtoken ...), backend-api/.env with ENVIA_API_KEY and ENVIA_WEBHOOK_TOKEN
(and ENVIA_WEBHOOK_SECRET to check signatures), front-end/.env.
The default database is the throwaway copy migcheck_envia, never the dev DB.
#>
param(
    [string]$Db = "migcheck_envia",
    [int]$ApiPort = 8001,
    [int]$WebPort = 8081,
    [switch]$NoTunnel
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$api = Join-Path $root "backend-api"
$web = Join-Path $root "front-end"
$apiUrl = "http://127.0.0.1:$ApiPort"
$webUrl = "http://127.0.0.1:$WebPort"

function Wait-Url([string]$url, [int]$seconds) {
    $deadline = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $deadline) {
        try { Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 3 | Out-Null; return $true }
        catch { Start-Sleep -Seconds 1 }
    }
    return $false
}

# PowerShell 5.1 turns any stderr line of a native command into an error, and
# "Stop" makes that fatal (uv prints "Building ..." there). Exit codes are
# checked by hand instead.
function Invoke-Native([scriptblock]$command) {
    $ErrorActionPreference = "Continue"
    & $command
}

function Test-Port([int]$port) {
    [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
}

function Start-Window([string]$title, [string]$dir, [string]$command) {
    $full = "`$Host.UI.RawUI.WindowTitle = '$title'; $command"
    Start-Process powershell -WorkingDirectory $dir -ArgumentList "-NoExit", "-Command", $full | Out-Null
}

# 1. Postgres in Docker
Write-Host "1/5 Base de datos ($Db)..."
Invoke-Native { docker info } *> $null
if ($LASTEXITCODE -ne 0) { throw "Docker no responde: abre Docker Desktop y vuelve a correr el script." }
Invoke-Native { docker start backend-api-db-1 } *> $null
$ready = $false
foreach ($i in 1..30) {
    Invoke-Native { docker exec backend-api-db-1 pg_isready -q } *> $null
    if ($LASTEXITCODE -eq 0) { $ready = $true; break }
    Start-Sleep -Seconds 1
}
if (-not $ready) { throw "Postgres (backend-api-db-1) no arranco." }
$exists = Invoke-Native { docker exec backend-api-db-1 psql -U mercadoexpress -d postgres -Atc "select 1 from pg_database where datname='$Db'" 2>$null }
if ($exists -ne "1") { throw "La base '$Db' no existe en backend-api-db-1." }

# 2. backend-api (--reload: psycopg async needs it on Windows)
Write-Host "2/5 Backend en $apiUrl ..."
if (Test-Port $ApiPort) {
    Write-Host "    El puerto $ApiPort ya esta en uso: uso lo que ya corre ahi."
} else {
    Start-Window "MercadoExpress API :$ApiPort" $api "`$env:POSTGRES_DB='$Db'; `$env:PUBLIC_BASE_URL='$apiUrl'; uv run uvicorn app.main:app --reload --host 127.0.0.1 --port $ApiPort"
}
if (-not (Wait-Url "$apiUrl/health" 60)) { throw "El backend no respondio en $apiUrl/health (mira su ventana)." }

# 3. Django, pointed at that backend
Write-Host "3/5 Django en $webUrl ..."
if (Test-Port $WebPort) {
    Write-Host "    El puerto $WebPort ya esta en uso: uso lo que ya corre ahi."
} else {
    Start-Window "MercadoExpress Django :$WebPort" $web "`$env:MERCADOEXPRESS_API_BASE_URL='$apiUrl'; uv run manage.py runserver 127.0.0.1:$WebPort"
}
if (-not (Wait-Url "$webUrl/" 60)) { throw "Django no respondio en $webUrl (mira su ventana)." }

if ($NoTunnel) {
    Write-Host "4/5 Sin tunel (-NoTunnel): Envia no podra avisar; usa los botones manuales o 'Sincronizar rastreo'."
} else {
    # 4. ngrok, reusing a tunnel already pointing at the backend port
    Write-Host "4/5 Tunel ngrok..."
    $public = $null
    try {
        $public = ((Invoke-RestMethod http://127.0.0.1:4040/api/tunnels -TimeoutSec 3).tunnels |
            Where-Object { $_.proto -eq "https" -and $_.config.addr -match ":$ApiPort$" } |
            Select-Object -First 1).public_url
    } catch { }
    if (-not $public) {
        $ngrok = (Get-Command ngrok -ErrorAction SilentlyContinue).Source
        if (-not $ngrok) {
            $ngrok = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Ngrok.Ngrok*\ngrok.exe" -ErrorAction SilentlyContinue |
                Select-Object -First 1 -ExpandProperty FullName
        }
        if (-not $ngrok) { throw "No encuentro ngrok: instalalo con 'winget install Ngrok.Ngrok' y corre 'ngrok update'." }
        Start-Process $ngrok -ArgumentList "http", "127.0.0.1:$ApiPort" | Out-Null
        foreach ($i in 1..30) {
            Start-Sleep -Seconds 1
            try {
                $public = ((Invoke-RestMethod http://127.0.0.1:4040/api/tunnels -TimeoutSec 3).tunnels |
                    Where-Object { $_.proto -eq "https" } | Select-Object -First 1).public_url
            } catch { }
            if ($public) { break }
        }
        if (-not $public) { throw "ngrok no abrio el tunel (revisa su ventana: authtoken?)." }
    }
    Write-Host "    $public"

    # 5. Point Envia's webhook at the tunnel (the URL changes on every ngrok start)
    Write-Host "5/5 Registrando el webhook en Envia..."
    Push-Location $api
    try {
        $out = Invoke-Native { uv run python -m app.scripts.envia_webhook $public 2>$null }
        if ($LASTEXITCODE -ne 0) { throw "No se pudo registrar el webhook en Envia." }
        $out | Where-Object { $_ -notmatch "^ENVIA_WEBHOOK_SECRET=" } | ForEach-Object { Write-Host "    $_" }
        $secret = ($out | Where-Object { $_ -match "^ENVIA_WEBHOOK_SECRET=" }) -replace "^ENVIA_WEBHOOK_SECRET=", ""
        if ($secret -and -not (Select-String -Path .env -Pattern "^ENVIA_WEBHOOK_SECRET=.+" -Quiet)) {
            Write-Host "    Agrega a backend-api/.env la linea ENVIA_WEBHOOK_SECRET=<auth_token> para verificar firmas (el script la imprime)."
        }
    } finally { Pop-Location }
}

Write-Host ""
Write-Host "Listo. Panel: $webUrl/panel/   API: $apiUrl/docs"
if (-not $NoTunnel) { Write-Host "Webhook: $public/api/v1/webhooks/envia   Inspector ngrok: http://127.0.0.1:4040" }
Start-Process "$webUrl/panel/"
