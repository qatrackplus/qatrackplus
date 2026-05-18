[CmdletBinding()]
param (
    [Parameter(Mandatory = $false)]
    [string]$RepoDir = $PWD,

    [Parameter(Mandatory = $false)]
    [string]$SqlInstance = "MSSQLSERVER",

    [Parameter(Mandatory = $false)]
    [string]$SqlHost = "localhost",

    [Parameter(Mandatory = $false)]
    [switch]$Smoke,

    [Parameter(Mandatory = $false)]
    [bool]$RootUrl = $true,

    [Parameter(Mandatory = $false)]
    [switch]$UseSqlite
)

$ErrorActionPreference = "Stop"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " Starting Automated QATrack+ Installation          " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Repository Directory: $RepoDir"
if ($UseSqlite) {
    Write-Host "Database Engine: SQLite (Local Verification Mode)"
} else {
    Write-Host "Database Engine: SQL Server"
    Write-Host "SQL Host: $SqlHost"
    Write-Host "SQL Instance: $SqlInstance"
}
Write-Host "Root URL Deployment: $RootUrl"
Write-Host "Run Smoke Test: $Smoke"
Write-Host "==================================================" -ForegroundColor Cyan

# -----------------------------------------------------------------------------
# 1. Enable SQL Server TCP/1433 using sqlserver.ps1
# -----------------------------------------------------------------------------
if (-not $UseSqlite) {
    Write-Host "[1/7] Configuring SQL Server TCP/1433 Networking..." -ForegroundColor Yellow
    $sqlScript = Join-Path $RepoDir "deploy\win\sqlserver.ps1"
    if (Test-Path $sqlScript) {
        & $sqlScript $SqlInstance
    } else {
        Write-Warning "deploy/win/sqlserver.ps1 not found, skipping TCP configuration."
    }
} else {
    Write-Host "[1/7] Skipping SQL Server Network Configuration (UseSqlite active)." -ForegroundColor Yellow
}

# -----------------------------------------------------------------------------
# 2. Provision SQL Server Database & Users via sqlcmd
# -----------------------------------------------------------------------------
if (-not $UseSqlite) {
    Write-Host "[2/7] Provisioning SQL Server Database and User Accounts..." -ForegroundColor Yellow
    $sqlCmdFile = Join-Path $env:TEMP "qatrack_provision.sql"
    $sqlScriptContent = @"
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'qatrackplus40')
BEGIN
    CREATE DATABASE qatrackplus40;
END
GO
USE qatrackplus40;
IF NOT EXISTS (SELECT * FROM sys.server_principals WHERE name = 'qatrack')
BEGIN
    CREATE LOGIN qatrack WITH PASSWORD = 'qatrackpass', DEFAULT_DATABASE = qatrackplus40, CHECK_POLICY = OFF;
END
IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'qatrack')
BEGIN
    CREATE USER qatrack FOR LOGIN qatrack;
    ALTER ROLE db_owner ADD MEMBER qatrack;
END
IF NOT EXISTS (SELECT * FROM sys.server_principals WHERE name = 'qatrack_reports')
BEGIN
    CREATE LOGIN qatrack_reports WITH PASSWORD = 'qatrackpass', DEFAULT_DATABASE = qatrackplus40, CHECK_POLICY = OFF;
END
IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'qatrack_reports')
BEGIN
    CREATE USER qatrack_reports FOR LOGIN qatrack_reports;
    ALTER ROLE db_datareader ADD MEMBER qatrack_reports;
END
GO
"@

    $sqlScriptContent | Out-File -FilePath $sqlCmdFile -Encoding utf8

    $sqlServerTarget = if ($SqlInstance -eq "MSSQLSERVER") { $SqlHost } else { "$SqlHost\$SqlInstance" }
    Write-Host "Connecting to SQL Server target: $sqlServerTarget"

    sqlcmd -S $sqlServerTarget -E -i $sqlCmdFile
    if ($LASTEXITCODE -ne 0) {
        throw "SQL Server provisioning failed via sqlcmd."
    }
    Remove-Item -Path $sqlCmdFile -ErrorAction SilentlyContinue
} else {
    Write-Host "[2/7] Skipping SQL Server Database Provisioning (UseSqlite active)." -ForegroundColor Yellow
}

# -----------------------------------------------------------------------------
# 3. Setup local_settings.py
# -----------------------------------------------------------------------------
Write-Host "[3/7] Setting up local_settings.py..." -ForegroundColor Yellow
$localSettingsPath = Join-Path $RepoDir "qatrack\local_settings.py"

if ($UseSqlite) {
    Write-Host "Generating test-only SQLite local_settings.py..."
    $sqliteContent = @"
DEBUG = False
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "db.sqlite3",
    }
}
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
USE_X_FORWARDED_HOST = True
TIME_ZONE = "America/Toronto"
"@
    if (-not $RootUrl) {
        $sqliteContent += "`nFORCE_SCRIPT_NAME = '/qatrack'`nLOGIN_EXEMPT_URLS = [r'^qatrack/accounts/', r'qatrack/api/*']`nLOGIN_REDIRECT_URL = '/qatrack/qa/unit/'`nLOGIN_URL = '/qatrack/accounts/login/'"
    }
    $sqliteContent | Out-File -FilePath $localSettingsPath -Encoding utf8 -Force
} else {
    $templatePath = Join-Path $RepoDir "deploy\win\local_settings.py"
    Copy-Item -Path $templatePath -Destination $localSettingsPath -Force

    if (-not $RootUrl) {
        Write-Host "Configuring subpath deployment (/qatrack) in local_settings.py..."
        $content = Get-Content -Path $localSettingsPath -Raw
        
        # Uncomment the script name and prefix configuration lines
        $content = $content -replace '# FORCE_SCRIPT_NAME = "/qatrack"', 'FORCE_SCRIPT_NAME = "/qatrack"'
        $content = $content -replace '# LOGIN_EXEMPT_URLS = \[r"\^qatrack/accounts/", r"qatrack/api/\*"\]', 'LOGIN_EXEMPT_URLS = [r"^qatrack/accounts/", r"qatrack/api/*"]'
        $content = $content -replace '# LOGIN_REDIRECT_URL = ''/qatrack/qa/unit/''', 'LOGIN_REDIRECT_URL = "/qatrack/qa/unit/"'
        $content = $content -replace '# LOGIN_URL = "/qatrack/accounts/login/"', 'LOGIN_URL = "/qatrack/accounts/login/"'
        
        $content | Out-File -FilePath $localSettingsPath -Encoding utf8 -Force
    }
}

# -----------------------------------------------------------------------------
# 4. Synchronize Dependencies using uv
# -----------------------------------------------------------------------------
Write-Host "[4/7] Synchronizing Python Dependencies via uv..." -ForegroundColor Yellow
cd $RepoDir
uv sync --extra win --extra mssql
if ($LASTEXITCODE -ne 0) {
    throw "uv sync dependency synchronization failed."
}

# -----------------------------------------------------------------------------
# 5. Run Database Migrations
# -----------------------------------------------------------------------------
Write-Host "[5/7] Running database migrations and settings..." -ForegroundColor Yellow
uv run python manage.py migrate
if ($LASTEXITCODE -ne 0) {
    throw "Database migration failed."
}

uv run python manage.py createcachetable
uv run python manage.py collectstatic --no-input

# -----------------------------------------------------------------------------
# 6. Load default data fixtures and create Superuser
# -----------------------------------------------------------------------------
Write-Host "[6/7] Seeding data fixtures and creating superuser..." -ForegroundColor Yellow
Get-ChildItem .\fixtures\defaults\*\*json | ForEach-Object {
    Write-Host "Loading fixture: $($_.Name)"
    uv run python manage.py loaddata $_.FullName
}

$env:DJANGO_SUPERUSER_USERNAME = "admin"
$env:DJANGO_SUPERUSER_PASSWORD = "adminpassword"
$env:DJANGO_SUPERUSER_EMAIL = "admin@example.com"
uv run python manage.py createsuperuser --no-input

# -----------------------------------------------------------------------------
# 7. Smoke Test
# -----------------------------------------------------------------------------
if ($Smoke) {
    Write-Host "[7/7] Executing HTTP Smoke Test..." -ForegroundColor Yellow

    # Copy modern QATrackCherryPyService.py to root directory for CherryPy startup
    Copy-Item -Path "deploy\win\QATrackCherryPyService.py" -Destination "QATrackCherryPyService.py" -Force

    # Set temporary virtual env environment variable so the cherrypy service picks it up
    $env:VIRTUAL_ENV = Join-Path $RepoDir ".venv"

    # Start CherryPy in the background
    Write-Host "Starting CherryPy web server on Port 8080..."
    $cherryPyJob = Start-Process -FilePath "uv" -ArgumentList "run", "python", "QATrackCherryPyService.py", "serve" -PassThru -NoNewWindow

    # Allow time for Django & CherryPy to initialize and listen
    Start-Sleep -Seconds 15

    $loginUrl = if ($RootUrl) { "http://127.0.0.1:8080/accounts/login/" } else { "http://127.0.0.1:8080/qatrack/accounts/login/" }
    Write-Host "Sending HTTP Smoke Test request to: $loginUrl"

    try {
        $response = Invoke-WebRequest -Uri $loginUrl -UseBasicParsing -TimeoutSec 10
        Write-Host "HTTP Response Code: $($response.StatusCode)"
        if ($response.StatusCode -ne 200) {
            throw "Smoke test failed! HTTP status is $($response.StatusCode) instead of 200."
        }
        Write-Host "HTTP Smoke Test SUCCESSFUL!" -ForegroundColor Green
    }
    catch {
        Write-Error "HTTP request to login page failed: $_"
        throw "Smoke test HTTP request failed."
    }
    finally {
        # Gracefully stop the process
        Write-Host "Tearing down CherryPy web server process..."
        if (-not $cherryPyJob.HasExited) {
            Stop-Process -Id $cherryPyJob.Id -Force
        }
        Start-Sleep -Seconds 2
        Remove-Item -Path "QATrackCherryPyService.py" -ErrorAction SilentlyContinue
        
        # Clean up database artifact if we are testing via SQLite
        if ($UseSqlite) {
            Write-Host "Cleaning up test database artifact (db.sqlite3)..."
            Remove-Item -Path "db.sqlite3" -ErrorAction SilentlyContinue
        }
    }
} else {
    Write-Host "[7/7] Skipping HTTP Smoke Test (Smoke switch not set)." -ForegroundColor Yellow
}

Write-Host "==================================================" -ForegroundColor Green
if ($UseSqlite) {
    Write-Host " QATrack+ SQLite Test Install Completed Successfully! " -ForegroundColor Green
} else {
    Write-Host " QATrack+ Installation completed successfully!     " -ForegroundColor Green
}
Write-Host "==================================================" -ForegroundColor Green
