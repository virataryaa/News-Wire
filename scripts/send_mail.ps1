# Sends the daily Commodity Wire output via the logged-in Outlook desktop client.
# Same approach as the working Certs Automation pipeline: Outlook COM automation,
# no SMTP password to manage.

$ErrorActionPreference = "Stop"

$NewsRoot = Split-Path -Parent $PSScriptRoot
$OutputFile = Join-Path $NewsRoot "output\latest.html"
$LogDir = Join-Path $NewsRoot "logs"
$LogFile = Join-Path $LogDir "mail.log"
$Recipient = "virat.arya@etgworld.com"

if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

function Write-Log($msg) {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "[$stamp] $msg" | Out-File -FilePath $LogFile -Append -Encoding utf8
}

try {
    if (-not (Test-Path $OutputFile)) {
        Write-Log "Output file not found, skipping mail: $OutputFile"
        exit 1
    }

    $lastWrite = (Get-Item $OutputFile).LastWriteTime.Date
    if ($lastWrite -ne (Get-Date).Date) {
        Write-Log "Output file is from $lastWrite, not today, nothing new was found today, skipping mail."
        exit 0
    }

    $html = Get-Content -Path $OutputFile -Raw -Encoding UTF8
    $today = Get-Date -Format "dd MMM yyyy"

    $outlook = New-Object -ComObject Outlook.Application
    $mail = $outlook.CreateItem(0)
    $mail.To = $Recipient
    $mail.Subject = "Commodity Wire - $today"
    $mail.HTMLBody = $html
    $mail.Send()

    Write-Log "Sent to $Recipient"
}
catch {
    Write-Log "FAILED: $_"
    exit 1
}
