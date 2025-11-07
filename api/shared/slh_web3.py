
from functools import lru_cache
from web3 import Web3
from web3.middleware import geth_poa_middleware

ERC20_ABI = [
  {"inputs":[{"internalType":"address","name":"owner","type":"address"}],
   "name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],
   "stateMutability":"view","type":"function"},
  {"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],
   "stateMutability":"view","type":"function"},
  {"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],
   "stateMutability":"view","type":"function"}
]

@lru_cache(maxsize=1)
def get_web3(rpc_url:str, chain_id:int):
    w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 20}))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    return w3

def erc20_contract(w3: Web3, token_address: str):
    return w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=ERC20_ABI)
