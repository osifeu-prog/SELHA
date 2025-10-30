import os
from web3 import Web3

class SLHWeb3:
    def __init__(self):
        self.bsc_rpc_url = os.getenv("BSC_RPC_URL")
        self.sela_token_address = os.getenv("SELA_TOKEN_ADDRESS")
        self.w3 = Web3(Web3.HTTPProvider(self.bsc_rpc_url))
        
        # ABI בסיסי לטוקן ERC-20
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
            }
        ]
        
        self.token_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(self.sela_token_address),
            abi=self.erc20_abi
        )
    
    def get_balance(self, address):
        """קבלת יתרת SELA של כתובת"""
        try:
            checksum_address = Web3.to_checksum_address(address)
            balance = self.token_contract.functions.balanceOf(checksum_address).call()
            decimals = self.token_contract.functions.decimals().call()
            
            return balance / (10 ** decimals)
        except Exception as e:
            print(f"Error getting balance for {address}: {e}")
            return 0
    
    def is_valid_address(self, address):
        """וידוא שכתובת תקינה"""
        return Web3.is_address(address)
    
    def get_token_info(self):
        """קבלת מידע על הטוקן"""
        try:
            symbol = self.token_contract.functions.symbol().call()
            name = self.token_contract.functions.name().call()
            decimals = self.token_contract.functions.decimals().call()
            
            return {
                "symbol": symbol,
                "name": name,
                "decimals": decimals,
                "address": self.sela_token_address
            }
        except Exception as e:
            print(f"Error getting token info: {e}")
            return None

# יצירת instance גלובלי
slh_web3 = SLHWeb3()
