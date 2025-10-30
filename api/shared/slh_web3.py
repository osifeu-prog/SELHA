# api/shared/slh_web3.py
import os
from web3 import Web3

# תאימות בין גרסאות web3: geth_poa_middleware (ישן) / ExtraDataToPOAMiddleware (חדש)
def _make_injector():
    try:
        from web3.middleware import geth_poa_middleware  # web3<=6.* לעתים קיים
        def _inject(w3: Web3):
            w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        return _inject
    except Exception:
        try:
            from web3.middleware import ExtraDataToPOAMiddleware  # web3>=6 שינוי שם
            def _inject(w3: Web3):
                w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
            return _inject
        except Exception:
            # fallback: לא מזריקים (יתכן לא צריך), אבל משאירים פונקציה ריקה
            def _inject(_w3: Web3):  # noqa: ARG001
                pass
            return _inject

_inject_poa = _make_injector()

ERC20_ABI_MIN = [
    {"constant": True, "inputs": [{"name": "owner", "type": "address"}], "name": "balanceOf",
     "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals",
     "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "symbol",
     "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}],
     "name": "transfer", "outputs": [{"name": "", "type": "bool"}], "type": "function"}
]

def get_web3() -> Web3:
    rpc = os.getenv("BSC_RPC_URL", "").strip()
    if not rpc:
        raise RuntimeError("BSC_RPC_URL missing")
    w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 15}))
    _inject_poa(w3)
    return w3

def erc20_contract(w3: Web3, token_address: str):
    return w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=ERC20_ABI_MIN)
