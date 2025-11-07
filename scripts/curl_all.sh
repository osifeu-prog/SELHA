
#!/usr/bin/env bash
set -euo pipefail
if [ -z "${SLH_API_BASE:-}" ]; then echo "Set SLH_API_BASE env"; exit 1; fi
echo "[GET] /healthz"; curl -fsS "$SLH_API_BASE/healthz" | jq . || true
echo "[GET] /config"; curl -fsS "$SLH_API_BASE/config" | jq . || true
echo "[GET] /config/price"; curl -fsS "$SLH_API_BASE/config/price" | jq . || true
echo "[GET] /wallet/balance/{address}"; curl -fsS "$SLH_API_BASE/wallet/balance/0x693db6c817083818696a7228aEbfBd0Cd3371f02" | jq . || true
