# Downloads the specific version of WinSW and renames it
$WinSwUrl = "https://github.com/winsw/winsw/releases/download/v2.12.0/WinSW-x64.exe"
$RepoRoot = (Resolve-Path "$PSScriptRoot\..\..").Path

$OutputExe = Join-Path $RepoRoot "qatrack-service.exe"

Write-Host "Downloading WinSW service wrapper to $OutputExe..."
Invoke-WebRequest -Uri $WinSwUrl -OutFile $OutputExe

Write-Host "Copying service configuration files to $RepoRoot..."
Copy-Item "$PSScriptRoot\qatrack-service.xml" -Destination $RepoRoot
Copy-Item "$PSScriptRoot\run_cherrypy.py" -Destination $RepoRoot

Write-Host "Installing the service..."
Start-Process -FilePath $OutputExe -ArgumentList "install" -Wait -NoNewWindow

Write-Host "Starting the service..."
Start-Process -FilePath $OutputExe -ArgumentList "start" -Wait -NoNewWindow

Write-Host "Service installed and started successfully!"