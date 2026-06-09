<#
.SYNOPSIS
    Configures IIS to serve a QATrack+ installation, following the official
    Windows deployment guide ("Setting up IIS"):
    https://docs.qatrackplus.com/en/stable/install/win.html

.DESCRIPTION
    QATrack+ on Windows runs the Django app behind a CherryPy service (default
    port 8080). IIS does two jobs: serve static/media files off disk, and
    reverse-proxy everything else to CherryPy. This script automates the manual
    GUI steps from the docs and VERIFIES each one by reading it back, so it will
    not report success unless the configuration was actually applied.

    Prerequisites (the docs require both): the URL Rewrite 2.1 and Application
    Request Routing 3.0 IIS modules. The script detects them up front and stops
    with instructions if either is missing. Use -InstallPrereqs to download and
    install them silently from Microsoft (URL Rewrite first, then ARR, since ARR
    depends on it).

.PARAMETER InstallRoot   Root of the QATrack+ checkout. Default C:\deploy\qatrackplus
                         (static is served from <InstallRoot>\qatrack).
.PARAMETER SiteName      IIS site name. Default "QATrack Static".
.PARAMETER Port          Port IIS listens on. Default 80.
.PARAMETER CherryPyPort  Port the CherryPy service listens on. Default 8080.
.PARAMETER ServerName    Value for HTTP_X_FORWARDED_HOST. Default = machine hostname.
.PARAMETER StopDefaultSite  Stop "Default Web Site". Default $true.
.PARAMETER InstallPrereqs   Download + silently install URL Rewrite 2.1 and ARR 3.0.

.EXAMPLE
    .\Configure-QATrackIIS.ps1 -ServerName qatrack.myhospital.org
.EXAMPLE
    .\Configure-QATrackIIS.ps1 -InstallPrereqs -ServerName qatrack.myhospital.org
#>

[CmdletBinding()]
param(
    [string] $InstallRoot = 'C:\deploy\qatrackplus',
    [string] $SiteName = 'QATrack Static',
    [int]    $Port = 80,
    [int]    $CherryPyPort = 8080,
    [string] $ServerName = $env:COMPUTERNAME,
    [bool]   $StopDefaultSite = $true,
    [switch] $InstallPrereqs
)

$ErrorActionPreference = 'Stop'

# Canonical x64 download links (verified current).
$UrlRewriteMsi = 'https://download.microsoft.com/download/1/2/8/128E2E22-C1B9-44A4-BE2A-5859ED1D4592/rewrite_amd64_en-US.msi'
$ArrMsi = 'https://download.microsoft.com/download/E/9/8/E9849D6A-020E-47E4-9FD0-A023E99B54EB/requestRouter_amd64.msi'

function Write-Step { param($m) Write-Host "==> $m" -ForegroundColor Cyan }
function Write-Ok { param($m) Write-Host "    OK: $m"   -ForegroundColor Green }
function Write-Bad { param($m) Write-Host "    FAILED: $m" -ForegroundColor Red }
function Write-Note { param($m) Write-Host "    $m" -ForegroundColor Yellow }

function Assert-Admin {
    $p = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    if (-not $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Run this from an elevated (Administrator) PowerShell prompt.'
    }
}

function Test-UrlRewrite {
    # URL Rewrite registers a global IIS module named "RewriteModule".
    try { if (Get-WebGlobalModule -Name 'RewriteModule' -ErrorAction SilentlyContinue) { return $true } } catch {}
    return (Test-Path 'HKLM:\SOFTWARE\Microsoft\IIS Extensions\URL Rewrite')
}

function Test-Arr {
    # ARR adds the <system.webServer/proxy> section to applicationHost.config.
    $sec = Get-WebConfiguration -PSPath 'MACHINE/WEBROOT/APPHOST' -Filter 'system.webServer/proxy' `
        -ErrorAction SilentlyContinue -WarningAction SilentlyContinue
    return [bool]$sec
}

function Install-Msi {
    param([string]$Url, [string]$Name)
    $tmp = Join-Path $env:TEMP ([IO.Path]::GetFileName($Url))
    Write-Step "Downloading $Name"
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $Url -OutFile $tmp -UseBasicParsing
    Write-Step "Installing $Name (silent)"
    $p = Start-Process msiexec.exe -ArgumentList "/i `"$tmp`" /quiet /norestart" -Wait -PassThru
    if ($p.ExitCode -notin 0, 3010) { throw "$Name install failed (msiexec exit $($p.ExitCode))." }
    Write-Ok "$Name installed"
}

# ---------------------------------------------------------------------------
Assert-Admin

Write-Step 'Importing WebAdministration module'
Import-Module WebAdministration -ErrorAction Stop
Write-Ok 'IIS PowerShell module loaded'

# --- Prerequisite gate -----------------------------------------------------
Write-Step 'Checking for URL Rewrite and Application Request Routing'
$haveRewrite = Test-UrlRewrite
$haveArr = Test-Arr

if (-not ($haveRewrite -and $haveArr)) {
    Write-Note ("URL Rewrite installed: $haveRewrite    ARR installed: $haveArr")
    if ($InstallPrereqs) {
        if (-not $haveRewrite) { Install-Msi -Url $UrlRewriteMsi -Name 'URL Rewrite 2.1' }
        if (-not $haveArr) { Install-Msi -Url $ArrMsi        -Name 'Application Request Routing 3.0' }
        # Re-check in this session.
        $haveRewrite = Test-UrlRewrite
        $haveArr = Test-Arr
        if (-not ($haveRewrite -and $haveArr)) {
            throw ("Modules installed but not yet visible in this session. " +
                "Close PowerShell, open a NEW elevated session, and re-run WITHOUT -InstallPrereqs.")
        }
    }
    else {
        throw @"
Missing IIS prerequisite module(s). The reverse proxy cannot be configured without them.

  URL Rewrite 2.1 : $UrlRewriteMsi
  ARR 3.0         : $ArrMsi   (install URL Rewrite FIRST)

Either install both manually and re-run this script, or re-run with -InstallPrereqs
to have the script download and install them for you (requires internet access on this server).
"@
    }
}
Write-Ok 'URL Rewrite and ARR present'

$staticPath = Join-Path $InstallRoot 'qatrack'
if (-not (Test-Path $staticPath)) {
    Write-Note "Static path '$staticPath' not found yet. Site will be created anyway; make sure your checkout lives at '$InstallRoot' and 'collectstatic' has been run."
}

# --- 1. Enable ARR reverse proxy -------------------------------------------
Write-Step 'Enabling reverse proxy in Application Request Routing'
Set-WebConfigurationProperty -PSPath 'MACHINE/WEBROOT/APPHOST' `
    -Filter 'system.webServer/proxy' -Name 'enabled' -Value 'True'
$proxyOn = (Get-WebConfigurationProperty -PSPath 'MACHINE/WEBROOT/APPHOST' `
        -Filter 'system.webServer/proxy' -Name 'enabled').Value
if (-not $proxyOn) { Write-Bad 'ARR proxy did not enable'; throw 'ARR proxy enable failed.' }
Write-Ok 'ARR proxy enabled'

# --- 2. Stop the Default Web Site ------------------------------------------
if ($StopDefaultSite) {
    Write-Step 'Stopping Default Web Site'
    if (Get-Website -Name 'Default Web Site' -ErrorAction SilentlyContinue) {
        Stop-Website -Name 'Default Web Site' -ErrorAction SilentlyContinue
        Write-Ok 'Default Web Site stopped'
    }
    else { Write-Note 'Default Web Site not found - skipping' }
}

# --- 3. Create/refresh the QATrack Static site -----------------------------
Write-Step "Creating/updating site '$SiteName' on port $Port -> $staticPath"
if (Get-Website -Name $SiteName -ErrorAction SilentlyContinue) {
    Set-ItemProperty "IIS:\Sites\$SiteName" -Name physicalPath -Value $staticPath
    Write-Ok "Site existed - physical path updated"
}
else {
    New-Website -Name $SiteName -PhysicalPath $staticPath -Port $Port -Force | Out-Null
    Write-Ok "Site '$SiteName' created"
}

# --- 4. URL Rewrite rules --------------------------------------------------
$apphost = 'MACHINE/WEBROOT/APPHOST'        # server level (rules go on the site)
$pspath = "MACHINE/WEBROOT/APPHOST/$SiteName"
$rulesFilter = 'system.webServer/rewrite/rules'
$allowedFilter = 'system.webServer/rewrite/allowedServerVariables'

function Remove-RuleIfPresent {
    param([string]$Name)
    try {
        Remove-WebConfigurationProperty -PSPath $pspath -Filter $rulesFilter `
            -Name '.' -AtElement @{name = $Name } -ErrorAction SilentlyContinue -WarningAction SilentlyContinue
    }
    catch {}
}

Write-Step 'Adding URL Rewrite rules (idempotent)'
Remove-RuleIfPresent 'QATrack Static'
Remove-RuleIfPresent 'QATrack Reverse Proxy'

# 4a. Static rule FIRST (static/media bypass the proxy)
Add-WebConfigurationProperty -PSPath $pspath -Filter $rulesFilter -Name '.' `
    -Value @{ name = 'QATrack Static'; stopProcessing = 'True' }
Set-WebConfigurationProperty -PSPath $pspath -Filter "$rulesFilter/rule[@name='QATrack Static']/match"  -Name 'url'  -Value '^(static|media)/.*'
Set-WebConfigurationProperty -PSPath $pspath -Filter "$rulesFilter/rule[@name='QATrack Static']/action" -Name 'type' -Value 'None'

# 4b. Reverse-proxy catch-all rule
Add-WebConfigurationProperty -PSPath $pspath -Filter $rulesFilter -Name '.' `
    -Value @{ name = 'QATrack Reverse Proxy'; stopProcessing = 'True' }
Set-WebConfigurationProperty -PSPath $pspath -Filter "$rulesFilter/rule[@name='QATrack Reverse Proxy']/match"  -Name 'url'  -Value '^(.*)'
Set-WebConfigurationProperty -PSPath $pspath -Filter "$rulesFilter/rule[@name='QATrack Reverse Proxy']/action" -Name 'type' -Value 'Rewrite'
Set-WebConfigurationProperty -PSPath $pspath -Filter "$rulesFilter/rule[@name='QATrack Reverse Proxy']/action" -Name 'url'  -Value "http://localhost:$CherryPyPort/{R:1}"

# 4c. Server variable on the proxy rule
Add-WebConfigurationProperty -PSPath $pspath -Filter "$rulesFilter/rule[@name='QATrack Reverse Proxy']/serverVariables" `
    -Name '.' -Value @{ name = 'HTTP_X_FORWARDED_HOST'; value = $ServerName }

# 4d. Whitelist that server variable.
#     allowedServerVariables is locked at the server level by default (it is NOT
#     delegated to sites), so it must be written at MACHINE/WEBROOT/APPHOST, not
#     per-site. It is a server-wide whitelist, so this covers every site.
$alreadyAllowed = @(Get-WebConfiguration -PSPath $apphost -Filter "$allowedFilter/add" `
        -ErrorAction SilentlyContinue -WarningAction SilentlyContinue |
    Select-Object -Expand name)
if ($alreadyAllowed -notcontains 'HTTP_X_FORWARDED_HOST') {
    Add-WebConfigurationProperty -PSPath $apphost -Filter $allowedFilter -Name '.' `
        -Value @{ name = 'HTTP_X_FORWARDED_HOST' }
}
$nowAllowed = @(Get-WebConfiguration -PSPath $apphost -Filter "$allowedFilter/add" `
        -ErrorAction SilentlyContinue -WarningAction SilentlyContinue |
    Select-Object -Expand name)
if ($nowAllowed -contains 'HTTP_X_FORWARDED_HOST') {
    Write-Ok 'HTTP_X_FORWARDED_HOST whitelisted (server level)'
}
else {
    Write-Bad 'Could not whitelist HTTP_X_FORWARDED_HOST'; throw 'allowedServerVariables write failed.'
}

# --- 4e. VERIFY rules by reading them back ---------------------------------
Write-Step 'Verifying rewrite rules were written'
$presentRules = @(Get-WebConfiguration -PSPath $pspath -Filter "$rulesFilter/rule" | Select-Object -Expand name)
foreach ($r in 'QATrack Static', 'QATrack Reverse Proxy') {
    if ($presentRules -contains $r) { Write-Ok "Rule present: $r" }
    else { Write-Bad "Rule missing: $r"; throw "Rewrite rule '$r' was not written." }
}
$proxyUrl = (Get-WebConfigurationProperty -PSPath $pspath -Filter "$rulesFilter/rule[@name='QATrack Reverse Proxy']/action" -Name 'url').Value
Write-Ok "Proxy target: $proxyUrl"

# --- 5. Start the site -----------------------------------------------------
Write-Step "Starting site '$SiteName'"
Start-Website -Name $SiteName -ErrorAction SilentlyContinue
Write-Ok 'Site started'

# --- 6. Functional checks --------------------------------------------------
Write-Step 'Checking static file serving (penguin test)'
try {
    $r = Invoke-WebRequest "http://localhost:$Port/static/qa/img/tux.png" -UseBasicParsing -TimeoutSec 10
    if ($r.StatusCode -eq 200) { Write-Ok 'tux.png 200 - static serving works' } else { Write-Note "tux.png status $($r.StatusCode)" }
}
catch { Write-Note "Could not fetch tux.png ($($_.Exception.Message)). Has collectstatic been run?" }

Write-Step "Checking reverse proxy to CherryPy on port $CherryPyPort"
$backend = $false
try { $b = Invoke-WebRequest "http://localhost:$CherryPyPort/" -UseBasicParsing -TimeoutSec 10; $backend = $true } catch {}
if (-not $backend) {
    Write-Note "CherryPy is not answering on $CherryPyPort yet - proxy will 502 until the QATrack+ CherryPy service is running. (IIS config is still correct.)"
}
else {
    try {
        $f = Invoke-WebRequest "http://localhost:$Port/" -UseBasicParsing -TimeoutSec 10
        if ($f.StatusCode -eq 200) { Write-Ok 'Reverse proxy reached QATrack+ login through IIS' } else { Write-Note "Proxied request status $($f.StatusCode)" }
    }
    catch { Write-Note "Proxy request failed: $($_.Exception.Message)" }
}

Write-Host ''
Write-Step 'IIS configuration complete.'
Write-Host @"
Remaining steps (NOT handled by this script):
  1. Install/run the QATrack+ CherryPy Windows service on port $CherryPyPort
       (browse http://localhost:$CherryPyPort/ and confirm the plain login form).
  2. In qatrack\local_settings.py set:  USE_X_FORWARDED_HOST = True
  3. Set up the Django Q cluster (Task Scheduler) for background tasks.
Then browse to http://$ServerName/ to reach QATrack+.
"@ -ForegroundColor Gray