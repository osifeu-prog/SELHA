
import os, time
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, PlainTextResponse
from cachetools import TTLCache
from shared.slh_web3 import get_web3, erc20_contract

app = FastAPI(title="SLH API", version="2025-11-07")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_headers=["*"], allow_methods=["*"], allow_credentials=True)

ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN","")
PRICE_NIS   = float(os.environ.get("PRICE_NIS","444"))
MIN_NIS     = float(os.environ.get("MIN_NIS_TO_UNLOCK","39"))
TELEGRAM_GROUP = os.environ.get("TELEGRAM_GROUP","")
BSC_RPC_URL = os.environ.get("BSC_RPC_URL","")
SELA_TOKEN_ADDRESS = os.environ.get("SELA_TOKEN_ADDRESS","")
CHAIN_ID = int(os.environ.get("CHAIN_ID","56") or 56)

price_cache = TTLCache(maxsize=100, ttl=30)
balance_cache = TTLCache(maxsize=2000, ttl=15)

def require_admin(x_admin_token: Optional[str]):
    if not ADMIN_TOKEN:
        raise HTTPException(500, "ADMIN_TOKEN missing in env")
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(401, "Unauthorized")
    return True

@app.get("/healthz")
def healthz(): return {"ok": True, "ts": int(time.time())}

@app.get("/", response_class=PlainTextResponse)
def root(): return "SLH API alive"

@app.get("/robots.txt", response_class=PlainTextResponse)
def robots(): return "User-agent: *\nDisallow:"

@app.get("/favicon.ico", response_class=PlainTextResponse)
def favicon(): return ""

@app.get("/config")
def get_config():
    return {"price_nis": PRICE_NIS, "min_nis_to_unlock": MIN_NIS, "telegram_group": TELEGRAM_GROUP, "chain_id": CHAIN_ID}

@app.get("/config/price")
def get_price(): return {"price_nis": PRICE_NIS}

@app.get("/wallet/balance/{address}")
def wallet_balance(address: str):
    try:
        from web3 import Web3
        caddr = Web3.to_checksum_address(address)
    except Exception:
        raise HTTPException(400, "invalid address")

    cache_key = caddr
    if cache_key in balance_cache: return balance_cache[cache_key]
    out: Dict[str, Any] = {"address": caddr, "chain_id": CHAIN_ID}

    if not BSC_RPC_URL:
        out["error"] = "BSC_RPC_URL missing"; balance_cache[cache_key] = out; return out
    try:
        w3 = get_web3(BSC_RPC_URL, CHAIN_ID)
        wei = w3.eth.get_balance(caddr)
        out["bnb"] = float(wei) / 1e18
    except Exception as e:
        out["bnb_error"] = str(e)

    if SELA_TOKEN_ADDRESS:
        try:
            token = erc20_contract(w3, SELA_TOKEN_ADDRESS)
            bal = token.functions.balanceOf(caddr).call()
            dec = token.functions.decimals().call()
            sym = token.functions.symbol().call()
            out["token"] = {"address": SELA_TOKEN_ADDRESS, "symbol": sym, "balance": float(bal) / (10**dec), "decimals": dec}
        except Exception as e:
            out["token_error"] = f"{e}"
    else:
        out["token_info"] = "SELA_TOKEN_ADDRESS not set"

    balance_cache[cache_key] = out
    return out

@app.get("/unlock/status/{chat_id}")
def unlock_status(chat_id: str): return {"chat_id": chat_id, "unlocked": False, "min_nis_to_unlock": MIN_NIS, "price_nis": PRICE_NIS}

@app.post("/unlock/{chat_id}")
def unlock(chat_id: str, x_admin_token: Optional[str] = Header(None)):
    require_admin(x_admin_token); return {"chat_id": chat_id, "unlocked": True}

@app.get("/token/info")
def token_info(): return {"chain_id": CHAIN_ID, "token_address": SELA_TOKEN_ADDRESS or None}
