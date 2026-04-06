param(
    [string]$PublicKey = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDVMlMnHePZpQ2IZhTR8mVyoJKef6kpBwOc8tq8qzLgys03nb+oGbDsvptZgTlbdCC2XfQFiLBu0e8jEdgf0Ot7qjCQPN3qfbtaZ6ViQEV5YsPFUoIfXQfYkyNCqaKs1szB7Aq/wzQXumzpZuUHPndUufKl/SFbgOiYa05WoXxdd2KwR1ta9pmw2WidCBvwejJ+NO8n9fqfnOt+XfK+UxPa0iewyzH457H0m2nF4gCZUp0m8AawrAIxuJb+A+lZ4mHcfR6p3ysLFvUwDXI4qkjIl1KMB7G7XYT7O3AADqg4jqX2GwuTl4tQTpD1jvn6qsH2hmVVKuAa8AEMh0mDV+QfL4AxGrdmjtL8xOKv6u20DHwIrOH6S8fj7CgepeTX4QcI7EuFkdiJm1XU3fknhKFRf+dz7FyjXzAMrfNdryhntaz1phWFY+h2Ej5Dg/sjfgZ6tF1UqNaRtSL57AGGot+dAfvWpCQAalzDF79ZcWeRF2EbdVv5sm87HD6onSRzfl5oAcUUam9ZFuBD5RpPFHCdIYCjIxzlWpxHEjCPDfaIeLvIBJxGoof0MLID+SMK3fjl0YmP14LaHWJVJklpnY9nt/tcNCM4KwAu/i+EK+3KCnSG/1cmF78BBxkdvM6HiMnJ6LPAFUOrPEVszqcFnR9fr65FqRZ24JpYOV6FSM2ZpQ== david@ubuntu2"
)

# Requires Administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "Please run this script as Administrator!"
    exit 1
}

Write-Host "=== Windows OpenSSH Server Setup ===" -ForegroundColor Cyan

# Step 1: Install OpenSSH Server
Write-Host "`n[1/5] Installing OpenSSH Server..." -ForegroundColor Yellow
$sshServer = Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH.Server*'
if ($sshServer.State -eq 'Installed') {
    Write-Host "  Already installed, skipping." -ForegroundColor Green
} else {
    Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
    $check = Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH.Server*'
    if ($check.State -ne 'Installed') {
        Write-Error "Installation failed! State: $($check.State)"
        exit 1
    }
    Write-Host "  Done." -ForegroundColor Green
}

# Step 2: Enable and start sshd
Write-Host "`n[2/5] Enabling sshd service (auto-start)..." -ForegroundColor Yellow
Set-Service -Name sshd -StartupType 'Automatic'
Start-Service sshd
$status = Get-Service -Name sshd
if ($status.Status -eq 'Running') {
    Write-Host "  sshd is running." -ForegroundColor Green
} else {
    Write-Error "sshd failed to start."
    exit 1
}

# Step 3: Firewall rule
Write-Host "`n[3/5] Configuring firewall (TCP 22 inbound)..." -ForegroundColor Yellow
$rule = Get-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -ErrorAction SilentlyContinue
if ($rule) {
    Write-Host "  Rule already exists, skipping." -ForegroundColor Green
} else {
    New-NetFirewallRule `
        -Name "OpenSSH-Server-In-TCP" `
        -DisplayName "OpenSSH Server (sshd)" `
        -Enabled True `
        -Direction Inbound `
        -Protocol TCP `
        -Action Allow `
        -LocalPort 22 | Out-Null
    Write-Host "  Firewall rule created." -ForegroundColor Green
}

# Step 4: Set default shell to PowerShell
Write-Host "`n[4/5] Setting default shell to PowerShell..." -ForegroundColor Yellow
$psPath = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
if (Test-Path $psPath) {
    New-ItemProperty `
        -Path "HKLM:\SOFTWARE\OpenSSH" `
        -Name DefaultShell `
        -Value $psPath `
        -PropertyType String `
        -Force | Out-Null
    Write-Host "  Default shell set to PowerShell." -ForegroundColor Green
} else {
    Write-Warning "  PowerShell not found, skipping."
}

# Step 5: Configure SSH public key
Write-Host "`n[5/5] Configuring SSH public key..." -ForegroundColor Yellow
if ($PublicKey -ne "") {
    # Check if current user is Administrator (admin users use a different authorized_keys path)
    $isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

    if ($isAdmin) {
        # Admin users: key must go to C:\ProgramData\ssh\administrators_authorized_keys
        $authFile = "C:\ProgramData\ssh\administrators_authorized_keys"
        Write-Host "  Admin user detected, writing to $authFile" -ForegroundColor Yellow
    } else {
        $sshDir = "$env:USERPROFILE\.ssh"
        if (-not (Test-Path $sshDir)) {
            New-Item -ItemType Directory -Path $sshDir -Force | Out-Null
        }
        $authFile = "$sshDir\authorized_keys"
    }

    # Write key if not already present
    $keyExists = $false
    if (Test-Path $authFile) {
        $existing = Get-Content $authFile -ErrorAction SilentlyContinue
        if ($existing -contains $PublicKey) { $keyExists = $true }
    }
    if (-not $keyExists) {
        Set-Content -Path $authFile -Value $PublicKey -Encoding UTF8
        Write-Host "  Public key written to $authFile" -ForegroundColor Green
    } else {
        Write-Host "  Public key already exists, skipping." -ForegroundColor Green
    }

    # Fix permissions: only SYSTEM and Administrators, no inheritance
    $acl = New-Object System.Security.AccessControl.FileSecurity
    $acl.SetAccessRuleProtection($true, $false)
    $ruleSystem = New-Object System.Security.AccessControl.FileSystemAccessRule(
        "SYSTEM", "FullControl", "Allow")
    $ruleAdmins = New-Object System.Security.AccessControl.FileSystemAccessRule(
        "Administrators", "FullControl", "Allow")
    $acl.AddAccessRule($ruleSystem)
    $acl.AddAccessRule($ruleAdmins)
    Set-Acl -Path $authFile -AclObject $acl
    Write-Host "  Permissions fixed (SYSTEM + Administrators only)." -ForegroundColor Green

    # Make sure sshd_config has not commented out AuthorizedKeysFile for admins
    $sshdConfig = "C:\ProgramData\ssh\sshd_config"
    if (Test-Path $sshdConfig) {
        $content = Get-Content $sshdConfig
        # Comment out the Match Group administrators block that overrides AuthorizedKeysFile
        $newContent = $content | ForEach-Object {
            if ($_ -match "^\s*AuthorizedKeysFile\s+__PROGRAMDATA__") {
                "# $_"
            } elseif ($_ -match "^\s*Match Group administrators") {
                "# $_"
            } else {
                $_
            }
        }
        Set-Content -Path $sshdConfig -Value $newContent -Encoding UTF8
        Write-Host "  sshd_config updated (admin AuthorizedKeysFile override removed)." -ForegroundColor Green
        Restart-Service sshd
        Write-Host "  sshd restarted." -ForegroundColor Green
    }
} else {
    Write-Host "  No public key provided, skipping." -ForegroundColor Gray
}

# Done
Write-Host "`n=== Setup Complete! ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "sshd status : $((Get-Service sshd).Status)"
Write-Host "Port        : 22 (TCP)"
Write-Host "StartupType : $((Get-Service sshd).StartType)"
Write-Host ""
Write-Host "Test from Ubuntu: ssh -p 2222 $env:USERNAME@localhost"
Write-Host "To restart sshd : Restart-Service sshd"
