import os
import logging
import json
from web3 import Web3
import httpx
from typing import Dict, Any, Optional

logger = logging.getLogger("SLH_Web3_Enhanced")

class SLHWeb3Enhanced:
    def __init__(self):
        self.bsc_rpc_url = os.getenv("BSC_RPC_URL", "https://bsc-dataseed.binance.org/")
        self.eth_rpc_url = os.getenv("ETH_RPC_URL", "https://eth.llamarpc.com")
        self.sela_token_address = os.getenv("SELA_TOKEN_ADDRESS", "0xACb0A09414CEA1C879c67bB7A877E4e19480f022")
        
        # Initialize Web3 connections
        self.w3_bsc = None
        self.w3_eth = None
        self.token_contract_bsc = None
        self.token_contract_eth = None
        
        self._initialize_connections()
        self._initialize_contracts()
    
    def _initialize_connections(self):
        """Initialize Web3 connections"""
        try:
            self.w3_bsc = Web3(Web3.HTTPProvider(self.bsc_rpc_url))
            if self.w3_bsc.is_connected():
                logger.info(f"✅ Connected to BSC. Chain ID: {self.w3_bsc.eth.chain_id}")
            else:
                logger.error("❌ Failed to connect to BSC")
        except Exception as e:
            logger.error(f"❌ BSC Web3 connection error: {e}")
        
        try:
            self.w3_eth = Web3(Web3.HTTPProvider(self.eth_rpc_url))
            if self.w3_eth.is_connected():
                logger.info(f"✅ Connected to Ethereum. Chain ID: {self.w3_eth.eth.chain_id}")
            else:
                logger.error("❌ Failed to connect to Ethereum")
        except Exception as e:
            logger.error(f"❌ Ethereum Web3 connection error: {e}")
    
    def _initialize_contracts(self):
        """Initialize token contracts"""
        self.erc20_abi = [
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
                "constant": False,
                "inputs": [
                    {"name": "_to", "type": "address"},
                    {"name": "_value", "type": "uint256"}
                ],
                "name": "transfer",
                "outputs": [{"name": "", "type": "bool"}],
                "type": "function",
                "stateMutability": "nonpayable"
            }
        ]
        
        # Initialize BSC contract
        if self.w3_bsc and self.sela_token_address:
            try:
                checksum_address = Web3.to_checksum_address(self.sela_token_address)
                self.token_contract_bsc = self.w3_bsc.eth.contract(
                    address=checksum_address,
                    abi=self.erc20_abi
                )
                logger.info("✅ BSC Token contract initialized")
            except Exception as e:
                logger.error(f"❌ Error initializing BSC token contract: {e}")
        
        # Initialize Ethereum contract
        if self.w3_eth and self.sela_token_address:
            try:
                checksum_address = Web3.to_checksum_address(self.sela_token_address)
                self.token_contract_eth = self.w3_eth.eth.contract(
                    address=checksum_address,
                    abi=self.erc20_abi
                )
                logger.info("✅ Ethereum Token contract initialized")
            except Exception as e:
                logger.error(f"❌ Error initializing Ethereum token contract: {e}")
    
    def get_sela_balance(self, address: str, network: str = "bsc") -> float:
        """Get SELA balance for address"""
        if network == "bsc" and self.token_contract_bsc:
            contract = self.token_contract_bsc
            w3 = self.w3_bsc
        elif network == "eth" and self.token_contract_eth:
            contract = self.token_contract_eth
            w3 = self.w3_eth
        else:
            logger.error(f"No contract available for network: {network}")
            return 0.0
        
        try:
            checksum_address = Web3.to_checksum_address(address)
            balance = contract.functions.balanceOf(checksum_address).call()
            
            # Try to get decimals, default to 18
            try:
                decimals = contract.functions.decimals().call()
            except:
                decimals = 18
            
            human_balance = balance / (10 ** decimals)
            logger.info(f"✅ SELA balance for {address} on {network}: {human_balance}")
            
            return human_balance
        except Exception as e:
            logger.error(f"Error getting SELA balance for {address} on {network}: {e}")
            return 0.0
    
    def get_native_balance(self, address: str, network: str = "bsc") -> float:
        """Get native currency balance (BNB/ETH)"""
        w3 = self.w3_bsc if network == "bsc" else self.w3_eth
        if not w3:
            return 0.0
        
        try:
            checksum_address = Web3.to_checksum_address(address)
            balance_wei = w3.eth.get_balance(checksum_address)
            balance = balance_wei / (10 ** 18)
            symbol = "BNB" if network == "bsc" else "ETH"
            logger.info(f"✅ {symbol} balance for {address}: {balance}")
            return balance
        except Exception as e:
            logger.error(f"Error getting native balance for {address} on {network}: {e}")
            return 0.0
    
    def get_token_info(self, network: str = "bsc") -> Dict[str, Any]:
        """Get token information"""
        contract = self.token_contract_bsc if network == "bsc" else self.token_contract_eth
        if not contract:
            return {}
        
        try:
            symbol = contract.functions.symbol().call()
            name = contract.functions.name().call()
            decimals = contract.functions.decimals().call()
            
            return {
                "symbol": symbol,
                "name": name,
                "decimals": decimals,
                "address": self.sela_token_address,
                "network": "BSC" if network == "bsc" else "Ethereum"
            }
        except Exception as e:
            logger.error(f"Error getting token info for {network}: {e}")
            return {
                "symbol": "SELA",
                "name": "SELA Token",
                "decimals": 18,
                "address": self.sela_token_address,
                "network": "BSC" if network == "bsc" else "Ethereum"
            }
    
    def is_valid_address(self, address: str) -> bool:
        """Validate Ethereum address"""
        return Web3.is_address(address)
    
    def transfer_tokens(self, from_address: str, to_address: str, amount: float, 
                       private_key: str, network: str = "bsc") -> Dict[str, Any]:
        """Transfer SELA tokens"""
        if network == "bsc":
            w3 = self.w3_bsc
            contract = self.token_contract_bsc
            chain_id = 56
        else:
            w3 = self.w3_eth
            contract = self.token_contract_eth
            chain_id = 1
        
        if not w3 or not contract:
            return {"status": "error", "message": "Network not available"}
        
        try:
            # Get decimals
            try:
                decimals = contract.functions.decimals().call()
            except:
                decimals = 18
            
            amount_wei = int(amount * (10 ** decimals))
            
            # Build transaction
            transfer_txn = contract.functions.transfer(
                Web3.to_checksum_address(to_address),
                amount_wei
            ).build_transaction({
                'chainId': chain_id,
                'gas': 100000,
                'gasPrice': w3.to_wei('5', 'gwei'),
                'nonce': w3.eth.get_transaction_count(Web3.to_checksum_address(from_address)),
            })
            
            # Sign and send
            signed_txn = w3.eth.account.sign_transaction(transfer_txn, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            return {
                "status": "success",
                "tx_hash": tx_hash.hex(),
                "explorer_url": f"https://{'bscscan.com' if network == 'bsc' else 'etherscan.io'}/tx/{tx_hash.hex()}"
            }
            
        except Exception as e:
            logger.error(f"Transfer error: {e}")
            return {"status": "error", "message": str(e)}

# Global instance
slh_web3_enhanced = SLHWeb3Enhanced()
