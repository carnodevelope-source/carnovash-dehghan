param(
    [Parameter(Mandatory = $true)][string]$BaseUrl
)

& (Join-Path $PSScriptRoot 'staging_verify.ps1') -BaseUrl $BaseUrl
Write-Output 'POST_DEPLOY_READ_ONLY_CHECK=PASS'
