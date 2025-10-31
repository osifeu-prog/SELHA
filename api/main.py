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

# Configuration - BSC Mainnet
PORT = int(os.getenv("PORT", 8080))
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
BSC_RPC_URL = os.getenv("BSC_RPC_URL", "https://bsc-dataseed.binance.org/")
SELA_TOKEN_ADDRESS = os.getenv("SELA_TOKEN_ADDRESS", "0xACb0A09414CEA1C879c67bB7A877E4e19480f022")
MIN_NIS_TO_UNLOCK = int(os.getenv("MIN_NIS_TO_UNLOCK", "39"))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SLH_API")

# FastAPI app
app = FastAPI(title="SLH API", description="SELA Community Trading System")

# Debug - log startup
logger.info("🚀 SLH API Starting Up...")
logger.info(f"🔗 BSC RPC: {BSC_RPC_URL}")
logger.info(f"🏷️ SELA Token Address: {SELA_TOKEN_ADDRESS}")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Web3
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

# ABI מלא לטוקן ERC-20 (מתוקן)
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
        "stateMutability": "view"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
        "stateMutability": "view"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function",
        "stateMutability": "view"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function",
        "stateMutability": "view"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
        "stateMutability": "view"
    }
]

# Initialize token contract
token_contract = None
token_info = {}

if w3 and SELA_TOKEN_ADDRESS:
    try:
        checksum_address = Web3.to_checksum_address(SELA_TOKEN_ADDRESS)
        
        # בדיקה אם החוזה קיים
        code = w3.eth.get_code(checksum_address)
        is_contract = code != b''
        
        if is_contract:
            token_contract = w3.eth.contract(address=checksum_address, abi=ERC20_ABI)
            
            # נסה לקבל מידע על הטוקן
            try:
                symbol = token_contract.functions.symbol().call()
                name = token_contract.functions.name().call()
                decimals = token_contract.functions.decimals().call()
                
                token_info = {
                    "symbol": symbol,
                    "name": name,
                    "decimals": decimals,
                    "address": checksum_address,
                    "is_contract": True
                }
                logger.info(f"✅ SELA Token Contract: {symbol} ({name}) - Decimals: {decimals}")
                
            except Exception as e:
                logger.warning(f"⚠️ Contract exists but ABI may not match: {e}")
                # נשתמש בערכים ברירת מחדל
                token_info = {
                    "symbol": "SELA",
                    "name": "SELA Token", 
                    "decimals": 18,
                    "address": checksum_address,
                    "is_contract": True,
                    "abi_warning": True
                }
        else:
            logger.warning(f"⚠️ SELA contract address is not a contract, using fallback mode")
            token_info = {
                "symbol": "SELA",
                "name": "SELA Token",
                "decimals": 18,
                "address": checksum_address,
                "is_contract": False
            }
            
    except Exception as e:
        logger.error(f"❌ Error checking token contract: {e}")
        token_info = {"error": str(e)}
else:
    logger.error("❌ Web3 or token address not available")

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

def get_sela_balance(address: str) -> float:
    """קבלת יתרת SELA - עם fallback אם החוזה לא עובד"""
    if not w3:
        return 0.0
    
    try:
        checksum_address = Web3.to_checksum_address(address)
        
        if token_contract:
            # נסה לקבל יתרה מהחוזה האמיתי
            try:
                balance = token_contract.functions.balanceOf(checksum_address).call()
                decimals = token_info.get("decimals", 18)
                human_balance = balance / (10 ** decimals)
                logger.info(f"✅ Real SELA balance for {address}: {human_balance}")
                return human_balance
            except Exception as e:
                logger.warning(f"⚠️ Could not get real SELA balance: {e}")
        
        # Fallback - בדיקה אם יש טוקנים בכתובת (לדוגמה בלבד)
        # במציאות, כאן תהיה הלוגיקה האמיתית לבדיקת יתרות
        logger.info(f"🔍 Checking wallet {checksum_address} for SELA tokens")
        
        # לדוגמה - נחזיר 0 כרגע
        return 0.0
        
    except Exception as e:
        logger.error(f"Error getting SELA balance for {address}: {e}")
        return 0.0

def get_bnb_balance(address: str) -> float:
    """קבלת יתרת BNB"""
    if not w3:
        return 0.0
    
    try:
        checksum_address = Web3.to_checksum_address(address)
        balance = w3.eth.get_balance(checksum_address)
        bnb_balance = balance / (10 ** 18)  # BNB has 18 decimals
        return bnb_balance
    except Exception as e:
        logger.error(f"Error getting BNB balance for {address}: {e}")
        return 0.0

def get_token_info_safe():
    """קבלת מידע על הטוקן"""
    return token_info

# Load initial data
config_data = load_json(CONFIG_FILE, DEFAULT_CONFIG)
unlocked_users = load_json(UNLOCKED_FILE, {})
pending_requests = load_json(PENDING_FILE, {})

logger.info("✅ Data loaded successfully")

# Routes
@app.get("/")
async def root():
    return {
        "message": "SLH API - SELA Community Trading System", 
        "status": "operational",
        "version": "2.0.0",
        "web3_connected": w3 and w3.is_connected(),
        "token_contract_ready": token_contract is not None
    }

@app.get("/healthz")
async def health_check():
    web3_status = w3 and w3.is_connected()
    
    return {
        "status": "healthy" if web3_status else "degraded",
        "web3_connected": web3_status,
        "chain_id": w3.eth.chain_id if w3 else None,
        "token_info": token_info,
        "service": "SLH API"
    }

@app.get("/config")
async def get_config():
    return config_data

@app.post("/config")
async def update_config(
    config_update: ConfigUpdate,
    x_admin_token: str = Header(None)
):
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
    return {"price_nis": config_data["price_nis"]}

@app.post("/config/price")
async def update_price(
    price_data: dict,
    x_admin_token: str = Header(None)
):
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

@app.get("/wallet/balance/{address}")
async def get_wallet_balance(address: str):
    """קבלת כל המידע על הארנק - SELA + BNB"""
    logger.info(f"GET /wallet/balance/{address} called")
    
    if not w3:
        return {
            "error": "Web3 not connected", 
            "sela_balance": 0,
            "bnb_balance": 0,
            "sela_value_nis": 0,
            "price_nis": config_data["price_nis"]
        }
    
    if not Web3.is_address(address):
        return {
            "error": "Invalid address format",
            "sela_balance": 0,
            "bnb_balance": 0,
            "sela_value_nis": 0,
            "price_nis": config_data["price_nis"]
        }
    
    try:
        checksum_address = Web3.to_checksum_address(address)
        
        # קבלת יתרות
        sela_balance = get_sela_balance(checksum_address)
        bnb_balance = get_bnb_balance(checksum_address)
        sela_value_nis = sela_balance * config_data["price_nis"]
        
        return {
            "address": checksum_address,
            "sela_balance": round(sela_balance, 6),
            "bnb_balance": round(bnb_balance, 6),
            "sela_value_nis": round(sela_value_nis, 2),
            "price_nis": config_data["price_nis"],
            "token_info": token_info
        }
    except Exception as e:
        logger.error(f"Error getting wallet balance for {address}: {e}")
        return {
            "error": str(e),
            "sela_balance": 0,
            "bnb_balance": 0,
            "sela_value_nis": 0,
            "price_nis": config_data["price_nis"]
        }

@app.get("/token/info")
async def get_token_info():
    return get_token_info_safe()

@app.get("/unlock/status/{chat_id}")
async def get_unlock_status(chat_id: str):
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
    verify_admin_token(x_admin_token)
    
    chat_id = request.chat_id
    logger.info(f"POST /unlock/grant for chat_id: {chat_id}")
    
    pending_data = pending_requests.get(chat_id, {})
    
    unlocked_users[chat_id] = {
        "wallet_address": pending_data.get("wallet_address", ""),
        "unlocked_at": str(int(time.time()))
    }
    
    if chat_id in pending_requests:
        del pending_requests[chat_id]
    
    save_json(UNLOCKED_FILE, unlocked_users)
    save_json(PENDING_FILE, pending_requests)
    
    logger.info(f"Unlock granted for chat_id: {chat_id}")
    return {"status": "granted", "chat_id": chat_id}

@app.get("/unlock/pending")
async def get_pending_requests(x_admin_token: str = Header(None)):
    verify_admin_token(x_admin_token)
    return pending_requests

@app.get("/debug/token")
async def debug_token():
    """Debug endpoint for token contract"""
    if not w3:
        return {"error": "Web3 not connected"}
    
    try:
        checksum_address = Web3.to_checksum_address(SELA_TOKEN_ADDRESS)
        code = w3.eth.get_code(checksum_address)
        has_code = code != b''
        
        return {
            "token_address": SELA_TOKEN_ADDRESS,
            "checksum_address": checksum_address,
            "is_contract": has_code,
            "has_contract_code": has_code,
            "code_length": len(code),
            "chain_id": w3.eth.chain_id,
            "token_info": token_info
        }
    except Exception as e:
        return {"error": str(e)}

logger.info("✅ All routes registered successfully")
