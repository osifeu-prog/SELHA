import os, time
from typing import Dict, Any, Optional
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from web3 import Web3

app = FastAPI(title="SLH API")

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "").strip()
SELA_TOKEN_ADDRESS = os.getenv("SELA_TOKEN_ADDRESS", "").strip()
BSC_RPC_URL = os.getenv("BSC_RPC_URL", "").strip()  # mainnet/testnet
GROUP_INVITE_LINK_ENV = os.getenv("GROUP_INVITE_LINK", "").strip()
DEFAULT_MIN_NIS = int(os.getenv("MIN_NIS_TO_UNLOCK", "39") or 39)

# ===== simple RAM stores (MVP) =====
CONFIG: Dict[str, Any] = {
    "price_nis": 444.0,
    "min_nis": DEFAULT_MIN_NIS,
    "group_invite_link": GROUP_INVITE_LINK_ENV or "",
    "accounts": []  # textual bank/pay channels
}
UNLOCKED: Dict[int, bool] = {}
PENDING: Dict[int, Dict[str, Any]] = {}

# ===== web3 init (lazy) =====
_w3: Optional[Web3] = None
_erc20_abi = [
    {"constant": True,"inputs": [],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"stateMutability":"view","type":"function"},
    {"constant": True,"inputs": [],"name":"symbol","outputs":[{"name":"","type":"string"}],"stateMutability":"view","type":"function"},
    {"constant": True,"inputs": [{"name":"owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
]

def get_w3() -> Web3:
    global _w3
    if _w3 is None:
        if not BSC_RPC_URL:
            raise HTTPException(status_code=500, detail="BSC_RPC_URL not configured")
        _w3 = Web3(Web3.HTTPProvider(BSC_RPC_URL, request_kwargs={"timeout": 10}))
        if not _w3.is_connected():
            raise HTTPException(status_code=500, detail="Failed to connect BSC RPC")
    return _w3

def erc20_balance(addr: str) -> Dict[str, Any]:
    if not Web3.is_address(addr):
        raise HTTPException(status_code=400, detail="invalid address")
    if not SELA_TOKEN_ADDRESS:
        raise HTTPException(status_code=500, detail="SELA_TOKEN_ADDRESS not configured")
    w3 = get_w3()
    token = w3.eth.contract(address=Web3.to_checksum_address(SELA_TOKEN_ADDRESS), abi=_erc20_abi)
    balance = token.functions.balanceOf(Web3.to_checksum_address(addr)).call()
    decimals = int(token.functions.decimals().call())
    symbol = token.functions.symbol().call()
    return {"ok": True, "balance": int(balance), "decimals": decimals, "symbol": symbol}

# ===== models =====
class PriceReq(BaseModel):
    price_nis: float

class MinReq(BaseModel):
    min_nis: int

class GroupReq(BaseModel):
    invite: str

class AccountReq(BaseModel):
    type: str
    details: str

class UnlockVerifyReq(BaseModel):
    chat_id: int
    reference: Optional[str] = None
    amount_nis: Optional[int] = None

class GrantReq(BaseModel):
    chat_id: int

def require_admin(token: str):
    if not ADMIN_TOKEN or token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="forbidden")

# ===== health =====
@app.get("/healthz")
def healthz():
    return {"ok": True, "msg": "slh api up"}

# ===== config =====
@app.get("/config")
def get_config():
    return CONFIG

@app.get("/config/price")
def get_price():
    return {"ok": True, "price_nis": CONFIG.get("price_nis")}

@app.post("/config/price")
def set_price(req: PriceReq, x_admin_token: str = Header(default="")):
    require_admin(x_admin_token)
    CONFIG["price_nis"] = float(req.price_nis)
    return {"ok": True, "price_nis": CONFIG["price_nis"]}

@app.get("/config/min")
def get_min():
    return {"ok": True, "min_nis": CONFIG.get("min_nis", DEFAULT_MIN_NIS)}

@app.post("/config/min")
def set_min(req: MinReq, x_admin_token: str = Header(default="")):
    require_admin(x_admin_token)
    CONFIG["min_nis"] = int(req.min_nis)
    return {"ok": True, "min_nis": CONFIG["min_nis"]}

@app.get("/config/accounts")
def get_accounts():
    return {"ok": True, "accounts": CONFIG.get("accounts", [])}

@app.post("/config/account")
def add_account(req: AccountReq, x_admin_token: str = Header(default="")):
    require_admin(x_admin_token)
    CONFIG.setdefault("accounts", []).append(f"{req.type}: {req.details}")
    return {"ok": True, "accounts": CONFIG["accounts"]}

@app.post("/config/group")
def set_group(req: GroupReq, x_admin_token: str = Header(default="")):
    require_admin(x_admin_token)
    CONFIG["group_invite_link"] = req.invite.strip()
    return {"ok": True, "group_invite_link": CONFIG["group_invite_link"]}

# ===== unlock flow =====
@app.post("/unlock/verify")
def unlock_verify(req: UnlockVerifyReq):
    PENDING[req.chat_id] = {
        "reference": req.reference,
        "amount_nis": req.amount_nis,
        "ts": int(time.time())
    }
    return {"ok": True, "pending": True}

@app.post("/unlock/grant")
def unlock_grant(req: GrantReq, x_admin_token: str = Header(default="")):
    require_admin(x_admin_token)
    UNLOCKED[req.chat_id] = True
    PENDING.pop(req.chat_id, None)
    return {"ok": True, "chat_id": req.chat_id, "unlocked": True}

@app.get("/status/{chat_id}")
def status(chat_id: int):
    return {
        "ok": True,
        "chat_id": chat_id,
        "unlocked": bool(UNLOCKED.get(chat_id, False)),
        "group_invite_link": CONFIG.get("group_invite_link", "")
    }

# ===== token balance =====
@app.get("/token/balance/{address}")
def token_balance(address: str):
    try:
        return erc20_balance(address)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
