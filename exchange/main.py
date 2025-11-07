from fastapi import FastAPI
import uvicorn
import asyncio
import logging
from datetime import datetime

app = FastAPI(title="SELA Exchange Engine")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.get("/")
async def root():
    return {
        "message": "🚀 SELA Exchange Engine is running!",
        "status": "active",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "exchange-engine"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
