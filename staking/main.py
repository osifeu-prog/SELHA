import os
import json
import logging
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from web3 import Web3
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StakingSystem:
    def __init__(self, web3: Web3, token_contract):
        self.w3 = web3
        self.token_contract = token_contract
        self.staking_file = "data/staking.json"
        self.load_data()
    
    def load_data(self):
        try:
            with open(self.staking_file, 'r') as f:
                self.data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.data = {
                "pools": {
                    "sela_pool": {
                        "total_staked": 0,
                        "apy": 15.0,
                        "created_at": int(time.time())
                    }
                },
                "users": {},
                "rewards": {}
            }
            self.save_data()
    
    def save_data(self):
        try:
            with open(self.staking_file, 'w') as f:
                json.dump(self.data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving staking data: {e}")
            return False
    
    def stake_tokens(self, user_id: str, amount: float) -> Dict[str, Any]:
        if user_id not in self.data["users"]:
            self.data["users"][user_id] = {}
        
        user_stake = self.data["users"][user_id]
        current_stake = user_stake.get("staked_amount", 0)
        
        user_stake["staked_amount"] = current_stake + amount
        user_stake["staked_since"] = int(time.time())
        user_stake["last_claim"] = int(time.time())
        
        # Update pool total
        self.data["pools"]["sela_pool"]["total_staked"] += amount
        
        self.save_data()
        
        return {
            "user_id": user_id,
            "staked_amount": user_stake["staked_amount"],
            "total_staked": self.data["pools"]["sela_pool"]["total_staked"],
            "apy": self.data["pools"]["sela_pool"]["apy"]
        }
    
    def calculate_rewards(self, user_id: str) -> float:
        if user_id not in self.data["users"]:
            return 0.0
        
        user_stake = self.data["users"][user_id]
        staked_amount = user_stake.get("staked_amount", 0)
        staked_since = user_stake.get("staked_since", time.time())
        last_claim = user_stake.get("last_claim", staked_since)
        
        if staked_amount == 0:
            return 0.0
        
        # Calculate time elapsed in years
        time_elapsed = time.time() - last_claim
        years_elapsed = time_elapsed / 31536000  # seconds in year
        
        # Calculate rewards
        apy = self.data["pools"]["sela_pool"]["apy"]
        rewards = staked_amount * (apy / 100) * years_elapsed
        
        return rewards
    
    def claim_rewards(self, user_id: str) -> Dict[str, Any]:
        rewards = self.calculate_rewards(user_id)
        
        if rewards <= 0:
            return {"rewards": 0, "message": "No rewards to claim"}
        
        # Update user's last claim time
        self.data["users"][user_id]["last_claim"] = int(time.time())
        
        # Add to rewards history
        if user_id not in self.data["rewards"]:
            self.data["rewards"][user_id] = []
        
        self.data["rewards"][user_id].append({
            "amount": rewards,
            "claimed_at": int(time.time())
        })
        
        self.save_data()
        
        return {
            "user_id": user_id,
            "rewards_claimed": rewards,
            "total_staked": self.data["users"][user_id]["staked_amount"],
            "apy": self.data["pools"]["sela_pool"]["apy"]
        }
    
    def get_user_staking_info(self, user_id: str) -> Dict[str, Any]:
        if user_id not in self.data["users"]:
            return {
                "staked_amount": 0,
                "rewards": 0,
                "apy": self.data["pools"]["sela_pool"]["apy"]
            }
        
        user_stake = self.data["users"][user_id]
        rewards = self.calculate_rewards(user_id)
        
        return {
            "staked_amount": user_stake.get("staked_amount", 0),
            "rewards": rewards,
            "apy": self.data["pools"]["sela_pool"]["apy"],
            "staked_since": user_stake.get("staked_since"),
            "last_claim": user_stake.get("last_claim")
        }
    
    def get_pool_info(self) -> Dict[str, Any]:
        pool = self.data["pools"]["sela_pool"]
        return {
            "total_staked": pool["total_staked"],
            "apy": pool["apy"],
            "active_stakers": len(self.data["users"]),
            "created_at": pool["created_at"]
        }

# Staking API
staking_app = FastAPI(title="SELA Staking API")

# Initialize staking system (in production, pass real web3 and contract)
staking_system = StakingSystem(None, None)

@staking_app.get("/")
async def staking_root():
    return {"message": "SELA Staking System", "status": "active"}

@staking_app.get("/pool")
async def get_pool_info():
    return staking_system.get_pool_info()

@staking_app.get("/user/{user_id}")
async def get_user_staking(user_id: str):
    return staking_system.get_user_staking_info(user_id)

@staking_app.post("/stake/{user_id}")
async def stake_tokens(user_id: str, stake_data: dict):
    amount = stake_data.get("amount", 0)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")
    
    result = staking_system.stake_tokens(user_id, amount)
    return result

@staking_app.post("/claim/{user_id}")
async def claim_rewards(user_id: str):
    result = staking_system.claim_rewards(user_id)
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(staking_app, host="0.0.0.0", port=8081)
