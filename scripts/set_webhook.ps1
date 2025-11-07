
param([Parameter(Mandatory=$true)] [string]$BotToken,[Parameter(Mandatory=$true)] [string]$WebhookUrl)
Invoke-RestMethod -Method Post -Uri "https://api.telegram.org/bot$BotToken/setWebhook" -Body @{ url = $WebhookUrl }
