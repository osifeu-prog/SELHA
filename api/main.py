import os
import json
import logging
import time
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from web3 import Web3
import httpx
from dotenv import load_dotenv

load_dotenv()

# Configuration
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
BSC_RPC_URL = os.getenv("BSC_RPC_URL", "https://bsc-dataseed.binance.org/")
SELA_TOKEN_ADDRESS = os.getenv("SELA_TOKEN_ADDRESS", "0xACb0A09414CEA1C879c67bB7A877E4e19480f022")
MIN_NIS_TO_UNLOCK = int(os.getenv("MIN_NIS_TO_UNLOCK", "39"))

# Initialize Web3
try:
    w3 = Web3(Web3.HTTPProvider(BSC_RPC_URL))
    if w3.is_connected():
        logging.info(f"✅ Connected to BSC. Chain ID: {w3.eth.chain_id}")
    else:
        logging.error("❌ Failed to connect to BSC")
        w3 = None
except Exception as e:
    logging.error(f"❌ Web3 connection error: {e}")
    w3 = None

# ABI for ERC20 token
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

# Initialize token contract
if w3 and SELA_TOKEN_ADDRESS:
    try:
        token_contract = w3.eth.contract(
            address=Web3.to_checksum_address(SELA_TOKEN_ADDRESS),
            abi=ERC20_ABI
        )
    except Exception as e:
        logging.error(f"❌ Error initializing token contract: {e}")
        token_contract = None
else:
    token_contract = None

# Data storage
DATA_DIR = "data"
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
UNLOCKED_FILE = os.path.join(DATA_DIR, "unlocked.json")
PENDING_FILE = os.path.join(DATA_DIR, "pending.json")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Initialize default config
DEFAULT_CONFIG = {
    "price_nis": 444.0,
    "min_nis_to_unlock": MIN_NIS_TO_UNLOCK,
    "bank_accounts": [
        {
            "bank": "פועלים",
            "branch": "153",
            "account": "73462",
            "name": "קאופמן צביקה"
        }
    ],
    "telegram_group": None
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SLH_API")

# FastAPI app - זה מה שהיה חסר!
app = FastAPI(title="SLH API", description="SELA Community Trading API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class ConfigUpdate(BaseModel):
    price_nis: Optional[float] = None
    min_nis_to_unlock: Optional[int] = None
    bank_accounts: Optional[List] = None
    telegram_group: Optional[str] = None

class UnlockVerify(BaseModel):
    chat_id: str
    reference: str
    wallet_address: str

class UnlockGrant(BaseModel):
    chat_id: str

# Helper functions
def load_json(file_path, default=None):
    """טעינת קובץ JSON"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default if default is not None else {}

def save_json(file_path, data):
    """שמירת קובץ JSON"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving {file_path}: {e}")
        return False

def verify_admin_token(x_admin_token: str = Header(None)):
    """אימות טוקן מנהל"""
    if not ADMIN_TOKEN:
        logger.error("ADMIN_TOKEN not set in environment")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin token not configured"
        )
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token"
        )
    return True

def get_token_balance(address: str) -> float:
    """קבלת יתרת טוקנים"""
    if not token_contract:
        return 0.0
    
    try:
        checksum_address = Web3.to_checksum_address(address)
        balance = token_contract.functions.balanceOf(checksum_address).call()
        decimals = token_contract.functions.decimals().call()
        return balance / (10 ** decimals)
    except Exception as e:
        logger.error(f"Error getting balance for {address}: {e}")
        return 0.0

# Load initial data
config_data = load_json(CONFIG_FILE, DEFAULT_CONFIG)
unlocked_users = load_json(UNLOCKED_FILE, {})
pending_requests = load_json(PENDING_FILE, {})

# Routes
@app.get("/")
async def root():
    return {
        "message": "SLH API - SELA Community Trading System", 
        "status": "operational",
        "version": "1.0.0"
    }

@app.get("/healthz")
async def health_check():
    web3_status = w3 and w3.is_connected()
    return {
        "status": "healthy" if web3_status else "degraded",
        "web3_connected": web3_status,
        "chain_id": w3.eth.chain_id if web3_status else None,
        "service": "SLH API"
    }

@app.get("/config")
async def get_config():
    """קבלת כל הקונפיג"""
    logger.info("GET /config called")
    return config_data

@app.post("/config")
async def update_config(
    config_update: ConfigUpdate,
    x_admin_token: str = Header(None)
):
    """עדכון קונפיג"""
    verify_admin_token(x_admin_token)
    
    update_data = config_update.dict(exclude_unset=True)
    config_data.update(update_data)
    
    if save_json(CONFIG_FILE, config_data):
        logger.info(f"Config updated: {update_data}")
        return {"status": "updated", "config": config_data}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save config"
        )

@app.get("/config/price")
async def get_price():
    """קבלת מחיר SELA"""
    logger.info("GET /config/price called")
    return {"price_nis": config_data["price_nis"]}

@app.post("/config/price")
async def update_price(
    price_data: dict,
    x_admin_token: str = Header(None)
):
    """עדכון מחיר SELA"""
    verify_admin_token(x_admin_token)
    
    new_price = price_data.get("price_nis")
    if new_price is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="price_nis is required"
        )
    
    config_data["price_nis"] = float(new_price)
    
    if save_json(CONFIG_FILE, config_data):
        logger.info(f"Price updated to: {new_price}")
        return {"status": "updated", "price_nis": config_data["price_nis"]}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update price"
        )

@app.get("/token/balance/{address}")
async def get_balance(address: str):
    """קבלת יתרת SELA בכתובת"""
    logger.info(f"GET /token/balance/{address} called")
    
    if not w3:
        return {
            "error": "Web3 not connected", 
            "balance_sela": 0,
            "value_nis": 0,
            "price_nis": config_data["price_nis"]
        }
    
    if not Web3.is_address(address):
        return {
            "error": "Invalid address format",
            "balance_sela": 0,
            "value_nis": 0,
            "price_nis": config_data["price_nis"]
        }
    
    try:
        checksum_address = Web3.to_checksum_address(address)
        balance_sela = get_token_balance(checksum_address)
        value_nis = balance_sela * config_data["price_nis"]
        
        return {
            "address": checksum_address,
            "balance_sela": round(balance_sela, 6),
            "value_nis": round(value_nis, 2),
            "price_nis": config_data["price_nis"]
        }
    except Exception as e:
        logger.error(f"Error getting balance for {address}: {e}")
        return {
            "error": str(e),
            "balance_sela": 0,
            "value_nis": 0,
            "price_nis": config_data["price_nis"]
        }

@app.get("/token/info")
async def get_token_info():
    """קבלת מידע על הטוקן"""
    if not token_contract:
        return {"error": "Token contract not available"}
    
    try:
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
            "address": SELA_TOKEN_ADDRESS,
            "chain_id": w3.eth.chain_id if w3 else None
        }
    except Exception as e:
        logger.error(f"Error getting token info: {e}")
        return {"error": str(e)}

@app.get("/unlock/status/{chat_id}")
async def get_unlock_status(chat_id: str):
    """קבלת סטטוס Unlock"""
    is_unlocked = chat_id in unlocked_users
    user_data = unlocked_users.get(chat_id, {})
    
    return {
        "chat_id": chat_id,
        "unlocked": is_unlocked,
        "wallet_address": user_data.get("wallet_address"),
        "unlocked_at": user_data.get("unlocked_at")
    }

@app.post("/unlock/verify")
async def verify_unlock(request: UnlockVerify):
    """רישום בקשת אימות"""
    pending_requests[request.chat_id] = {
        "reference": request.reference,
        "wallet_address": request.wallet_address,
        "timestamp": str(int(time.time()))
    }
    
    if save_json(PENDING_FILE, pending_requests):
        logger.info(f"Unlock verification requested for chat_id: {request.chat_id}")
        return {"status": "pending", "message": "Verification request submitted"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save unlock request"
        )

@app.post("/unlock/grant")
async def grant_unlock(
    request: UnlockGrant,
    x_admin_token: str = Header(None)
):
    """אישור Unlock"""
    verify_admin_token(x_admin_token)
    
    chat_id = request.chat_id
    
    # קבלת נתונים מהבקשה הממתינה
    pending_data = pending_requests.get(chat_id, {})
    
    unlocked_users[chat_id] = {
        "wallet_address": pending_data.get("wallet_address", ""),
        "unlocked_at": str(int(time.time()))
    }
    
    # הסרה מרשימת הממתינים
    if chat_id in pending_requests:
        del pending_requests[chat_id]
    
    # שמירת השינויים
    save_json(UNLOCKED_FILE, unlocked_users)
    save_json(PENDING_FILE, pending_requests)
    
    logger.info(f"Unlock granted for chat_id: {chat_id}")
    return {"status": "granted", "chat_id": chat_id}

@app.get("/unlock/pending")
async def get_pending_requests(x_admin_token: str = Header(None)):
    """קבלת רשימת בקשות ממתינות"""
    verify_admin_token(x_admin_token)
    return pending_requests

@app.post("/unlock/revoke")
async def revoke_unlock(
    chat_id: str,
    x_admin_token: str = Header(None)
):
    """ביטול Unlock"""
    verify_admin_token(x_admin_token)
    
    if chat_id in unlocked_users:
        del unlocked_users[chat_id]
    
    if save_json(UNLOCKED_FILE, unlocked_users):
        logger.info(f"Unlock revoked for chat_id: {chat_id}")
        return {"status": "revoked", "chat_id": chat_id}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke unlock"
        )

# חשוב: אין יותר קריאה ל-uvicorn.run כאן למטה
# Railway ידאג להרצה אוטומטית
