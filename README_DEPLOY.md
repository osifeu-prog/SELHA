
# SELHA Production Pack (2025-11-07)
Two services: **api/** (FastAPI+Web3) and **bot/** (PTB v21). No local .env; all config in Railway Variables.

## Railway Variables
### API
- ADMIN_TOKEN=<secret>
- PRICE_NIS=444
- MIN_NIS_TO_UNLOCK=39
- TELEGRAM_GROUP=optional
- CHAIN_ID=56 # or 97
- BSC_RPC_URL=https://bsc-dataseed.binance.org # or testnet url
- SELA_TOKEN_ADDRESS=0x...

### BOT
- TELEGRAM_BOT_TOKEN=<token>
- SLH_API_BASE=https://<api>.up.railway.app
- ADMIN_TOKEN=<same-as-api>
- ADMIN_CHAT_ID=<your chat id>
- WEBHOOK_URL=https://<bot>.up.railway.app/webhook
- LOG_LEVEL=INFO

## Validate
$env:SLH_API_BASE="https://<api>.up.railway.app"
./scripts/smoke_api.ps1
