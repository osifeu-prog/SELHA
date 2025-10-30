import os
import json
import logging
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from web3 import Web3
import httpx

# הגדרת לוגר
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SLH API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# נתיבים לקבצי נתונים
DATA_DIR = "data"
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
UNLOCKED_FILE = os.path.join(DATA_DIR, "unlocked.json")

# וידוא שתיקיית data קיימת
os.makedirs(DATA_DIR, exist_ok=True)

# אתחול Web3 עם BSC Mainnet
BSC_RPC_URL = os.getenv("BSC_RPC_URL", "https://bsc-dataseed.binance.org/")
SELA_TOKEN_ADDRESS = os.getenv("SELA_TOKEN_ADDRESS", "0xACb0A09414CEA1C879c67bB7A877E4e19480f022")

try:
    w3 = Web3(Web3.HTTPProvider(BSC_RPC_URL))
    if w3.is_connected():
        logger.info(f"✅ Connected to BSC Mainnet. Chain ID: {w3.eth.chain_id}")
    else:
        logger.error("❌ Failed to connect to BSC")
        w3 = None
except Exception as e:
    logger.error(f"❌ Web3 connection error: {e}")
    w3 = None

# ABI מלא יותר לטוקן ERC-20
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function"
    }
]

# מודלים
class ConfigUpdate(BaseModel):
    sela_price_nis: Optional[float] = None
    min_nis_to_unlock: Optional[int] = None
    community_invite_link: Optional[str] = None
    payment_accounts: Optional[List[Dict]] = None

class UnlockRequest(BaseModel):
    chat_id: int
    wallet_address: str
    payment_ref: Optional[str] = None

# פונקציות עזר
def load_config():
    """טעינת קונפיג מהקובץ"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
    
    # קונפיג ברירת מחדל
    default_config = {
        "sela_price_nis": 4.0,
        "min_nis_to_unlock": 39,
        "community_invite_link": "",
        "payment_accounts": [
            {
                "type": "בנק פועלים",
                "details": "סניף 153, חשבון 73462, שם: קאופמן צביקה"
            }
        ]
    }
    save_config(default_config)
    return default_config

def save_config(config):
    """שמירת קונפיג לקובץ"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        return False

def load_unlocked():
    """טעינת רשימת משתמשים מאושרים"""
    try:
        if os.path.exists(UNLOCKED_FILE):
            with open(UNLOCKED_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading unlocked: {e}")
    
    return {"approved": [], "pending": []}

def save_unlocked(data):
    """שמירת רשימת משתמשים מאושרים"""
    try:
        with open(UNLOCKED_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error saving unlocked: {e}")
        return False

def get_token_contract():
    """קבלת חוזה הטוקן"""
    if not w3 or not SELA_TOKEN_ADDRESS:
        return None
    try:
        return w3.eth.contract(
            address=Web3.to_checksum_address(SELA_TOKEN_ADDRESS),
            abi=ERC20_ABI
        )
    except Exception as e:
        logger.error(f"Error creating token contract: {e}")
        return None

# Dependency for admin authentication
def verify_admin_token(x_admin_token: str = Header(...)):
    if x_admin_token != os.getenv("ADMIN_TOKEN"):
        raise HTTPException(status_code=403, detail="Admin token required")
    return True

# endpoints
@app.get("/healthz")
async def health_check():
    web3_status = "connected" if w3 and w3.is_connected() else "disconnected"
    return {
        "status": "healthy", 
        "service": "SLH API",
        "web3": web3_status,
        "chain_id": w3.eth.chain_id if w3 else None
    }

@app.get("/config")
async def get_config():
    return load_config()

@app.post("/config")
async def update_config(
    update: ConfigUpdate,
    is_admin: bool = Depends(verify_admin_token)
):
    config = load_config()
    
    if update.sela_price_nis is not None:
        config["sela_price_nis"] = update.sela_price_nis
    if update.min_nis_to_unlock is not None:
        config["min_nis_to_unlock"] = update.min_nis_to_unlock
    if update.community_invite_link is not None:
        config["community_invite_link"] = update.community_invite_link
    if update.payment_accounts is not None:
        config["payment_accounts"] = update.payment_accounts
    
    if save_config(config):
        return {"status": "updated", "config": config}
    else:
        raise HTTPException(status_code=500, detail="Failed to save config")

@app.get("/config/price")
async def get_price():
    config = load_config()
    return {"sela_price_nis": config["sela_price_nis"]}

@app.post("/config/price")
async def set_price(price_data: dict, is_admin: bool = Depends(verify_admin_token)):
    config = load_config()
    config["sela_price_nis"] = price_data.get("sela_price_nis", config["sela_price_nis"])
    
    if save_config(config):
        return {"status": "price_updated", "new_price": config["sela_price_nis"]}
    else:
        raise HTTPException(status_code=500, detail="Failed to update price")

@app.get("/token/balance/{address}")
async def get_token_balance(address: str):
    try:
        if not w3:
            return {"error": "Web3 not connected", "balance": 0}
        
        # וידוא כתובת תקינה
        if not Web3.is_address(address):
            return {"error": "Invalid address", "balance": 0}
        
        checksum_address = Web3.to_checksum_address(address)
        
        # חוזה טוקן
        token_contract = get_token_contract()
        if not token_contract:
            return {"error": "Token contract not available", "balance": 0}
        
        # קבלת יתרה
        balance = token_contract.functions.balanceOf(checksum_address).call()
        decimals = token_contract.functions.decimals().call()
        
        # המרה לערך אנושי
        human_balance = balance / (10 ** decimals)
        
        # קבלת מידע נוסף על הטוקן
        symbol = token_contract.functions.symbol().call()
        name = token_contract.functions.name().call()
        
        return {
            "address": checksum_address,
            "balance": human_balance,
            "raw_balance": balance,
            "decimals": decimals,
            "symbol": symbol,
            "name": name,
            "token_address": SELA_TOKEN_ADDRESS
        }
        
    except Exception as e:
        logger.error(f"Error getting balance for {address}: {e}")
        return {"error": str(e), "balance": 0}

@app.get("/token/info")
async def get_token_info():
    """קבלת מידע על הטוקן"""
    try:
        token_contract = get_token_contract()
        if not token_contract:
            return {"error": "Token contract not available"}
        
        symbol = token_contract.functions.symbol().call()
        name = token_contract.functions.name().call()
        decimals = token_contract.functions.decimals().call()
        total_supply = token_contract.functions.totalSupply().call()
        
        return {
            "symbol": symbol,
            "name": name,
            "decimals": decimals,
            "total_supply": total_supply,
            "total_supply_human": total_supply / (10 ** decimals),
            "address": SELA_TOKEN_ADDRESS
        }
        
    except Exception as e:
        logger.error(f"Error getting token info: {e}")
        return {"error": str(e)}

@app.get("/unlock/status/{chat_id}")
async def get_unlock_status(chat_id: int):
    unlocked_data = load_unlocked()
    
    is_approved = any(user["chat_id"] == chat_id for user in unlocked_data["approved"])
    pending_request = next((user for user in unlocked_data["pending"] if user["chat_id"] == chat_id), None)
    
    return {
        "chat_id": chat_id,
        "approved": is_approved,
        "pending": pending_request is not None,
        "pending_data": pending_request
    }

@app.post("/unlock/verify")
async def verify_unlock(request: UnlockRequest):
    unlocked_data = load_unlocked()
    
    # בדיקה אם כבר מאושר
    if any(user["chat_id"] == request.chat_id for user in unlocked_data["approved"]):
        return {"status": "already_approved"}
    
    # בדיקה אם כבר ממתין
    existing_pending = next((user for user in unlocked_data["pending"] if user["chat_id"] == request.chat_id), None)
    if existing_pending:
        return {"status": "already_pending"}
    
    # הוספה לרשימת ממתינים
    unlocked_data["pending"].append({
        "chat_id": request.chat_id,
        "wallet_address": request.wallet_address,
        "payment_ref": request.payment_ref,
        "timestamp": os.times().elapsed
    })
    
    if save_unlocked(unlocked_data):
        return {"status": "pending_approval"}
    else:
        raise HTTPException(status_code=500, detail="Failed to save unlock request")

@app.post("/unlock/grant")
async def grant_unlock(chat_id: int, is_admin: bool = Depends(verify_admin_token)):
    unlocked_data = load_unlocked()
    
    # מצא ומחק מרשימת ממתינים
    pending_user = next((user for user in unlocked_data["pending"] if user["chat_id"] == chat_id), None)
    if not pending_user:
        raise HTTPException(status_code=404, detail="No pending request found")
    
    unlocked_data["pending"] = [user for user in unlocked_data["pending"] if user["chat_id"] != chat_id]
    
    # הוסף לרשימת מאושרים
    if not any(user["chat_id"] == chat_id for user in unlocked_data["approved"]):
        unlocked_data["approved"].append({
            "chat_id": chat_id,
            "wallet_address": pending_user["wallet_address"],
            "approved_at": os.times().elapsed,
            "approved_by": "admin"
        })
    
    if save_unlocked(unlocked_data):
        return {"status": "approved", "chat_id": chat_id}
    else:
        raise HTTPException(status_code=500, detail="Failed to grant unlock")

@app.post("/unlock/revoke")
async def revoke_unlock(chat_id: int, is_admin: bool = Depends(verify_admin_token)):
    unlocked_data = load_unlocked()
    
    # הסרה מרשימת מאושרים
    unlocked_data["approved"] = [user for user in unlocked_data["approved"] if user["chat_id"] != chat_id]
    
    if save_unlocked(unlocked_data):
        return {"status": "revoked", "chat_id": chat_id}
    else:
        raise HTTPException(status_code=500, detail="Failed to revoke unlock")

@app.get("/unlock/pending")
async def get_pending_requests(is_admin: bool = Depends(verify_admin_token)):
    unlocked_data = load_unlocked()
    return {"pending": unlocked_data["pending"]}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
