import os
import logging
from web3 import Web3

# Setup logging
logger = logging.getLogger("SLH_Web3")

class SLHWeb3:
    def __init__(self):
        self.bsc_rpc_url = os.getenv("BSC_RPC_URL", "https://bsc-dataseed.binance.org/")
        self.sela_token_address = os.getenv("SELA_TOKEN_ADDRESS", "0xACb0A09414CEA1C879c67bB7A877E4e19480f022")
        
        try:
            self.w3 = Web3(Web3.HTTPProvider(self.bsc_rpc_url))
            if self.w3.is_connected():
                logger.info(f"✅ Connected to BSC. Chain ID: {self.w3.eth.chain_id}")
            else:
                logger.error("❌ Failed to connect to BSC")
                self.w3 = None
        except Exception as e:
            logger.error(f"❌ Web3 connection error: {e}")
            self.w3 = None
        
        # ABI מלא יותר לטוקן ERC-20
        self.erc20_abi = [
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
        
        # אתחול חוזה הטוקן
        if self.w3 and self.sela_token_address:
            try:
                self.token_contract = self.w3.eth.contract(
                    address=Web3.to_checksum_address(self.sela_token_address),
                    abi=self.erc20_abi
                )
                logger.info("✅ Token contract initialized successfully")
            except Exception as e:
                logger.error(f"❌ Error initializing token contract: {e}")
                self.token_contract = None
        else:
            self.token_contract = None
    
    def get_balance(self, address):
        """קבלת יתרת SELA של כתובת"""
        if not self.token_contract:
            logger.error("Token contract not available")
            return 0
        
        try:
            checksum_address = Web3.to_checksum_address(address)
            balance = self.token_contract.functions.balanceOf(checksum_address).call()
            decimals = self.token_contract.functions.decimals().call()
            
            human_balance = balance / (10 ** decimals)
            logger.info(f"Balance for {address}: {human_balance} SELA")
            
            return human_balance
        except Exception as e:
            logger.error(f"Error getting balance for {address}: {e}")
            return 0
    
    def is_valid_address(self, address):
        """וידוא שכתובת תקינה"""
        return Web3.is_address(address)
    
    def get_token_info(self):
        """קבלת מידע על הטוקן"""
        if not self.token_contract:
            return None
        
        try:
            symbol = self.token_contract.functions.symbol().call()
            name = self.token_contract.functions.name().call()
            decimals = self.token_contract.functions.decimals().call()
            total_supply = self.token_contract.functions.totalSupply().call()
            
            return {
                "symbol": symbol,
                "name": name,
                "decimals": decimals,
                "total_supply": total_supply,
                "total_supply_human": total_supply / (10 ** decimals),
                "address": self.sela_token_address,
                "chain_id": self.w3.eth.chain_id if self.w3 else None
            }
        except Exception as e:
            logger.error(f"Error getting token info: {e}")
            return None
    
    def is_connected(self):
        """בדיקה אם מחובר ל-Blockchain"""
        return self.w3 and self.w3.is_connected()

# יצירת instance גלובלי
slh_web3 = SLHWeb3()
