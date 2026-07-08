$ErrorActionPreference = "Stop"

Write-Host "Enabling and validating WSL / virtualization prerequisites..."
try {
    wsl --set-default-version 2
} catch {
    Write-Warning "Could not set WSL default version right now. A reboot may still be pending."
}

try {
    wsl --update --web-download
} catch {
    Write-Warning "WSL kernel update did not finish. This usually succeeds after reboot."
}

try {
    wsl --install -d Ubuntu
} catch {
    Write-Warning "Ubuntu distribution could not be installed yet. This is expected if Windows is waiting for reboot."
}

Write-Host "Opening firewall for HTTP/HTTPS..."
netsh advfirewall firewall add rule name="CarWash HTTP 80" dir=in action=allow protocol=TCP localport=80 | Out-Null
netsh advfirewall firewall add rule name="CarWash HTTPS 443" dir=in action=allow protocol=TCP localport=443 | Out-Null

Write-Host "Preparation completed. A reboot is required before Docker Linux engine can become healthy."
