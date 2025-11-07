
param([string]$Base = $env:SLH_API_BASE)
if (-not $Base) { Write-Host "Set SLH_API_BASE env" -ForegroundColor Yellow; exit 1 }
Write-Host "Smoke: $Base" -ForegroundColor Cyan
try { Invoke-RestMethod -Uri "$Base/healthz" -Method Get | ConvertTo-Json -Depth 5 } catch { $_ }
try { Invoke-RestMethod -Uri "$Base/config" -Method Get | ConvertTo-Json -Depth 5 } catch { $_ }
try { Invoke-RestMethod -Uri "$Base/config/price" -Method Get | ConvertTo-Json -Depth 5 } catch { $_ }
try { Invoke-RestMethod -Uri "$Base/wallet/balance/0x693db6c817083818696a7228aEbfBd0Cd3371f02" -Method Get | ConvertTo-Json -Depth 5 } catch { $_ }
