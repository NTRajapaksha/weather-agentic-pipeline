# src/api/server.py
from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Optional, Dict
import logging
import time

from config import Config
from agent.bot import WeatherAgent
from database.connection import get_db_manager

# Configure logging
logger = logging.getLogger(__name__)

# 1. Define Request/Response Models
class QueryRequest(BaseModel):
    message: str
    api_token: Optional[str] = None

class QueryResponse(BaseModel):
    response: str
    tool_calls: list = [] # Optional: to show debug info about what tools were used

class HealthResponse(BaseModel):
    status: str
    database: str
    uptime_seconds: float

# 2. Initialize App and Agent
app = FastAPI(
    title="Weather Agent API",
    description="AI Agent that answers weather questions using DB + External APIs",
    version="1.0.0"
)

# Global agent instance
agent = None
start_time = time.time()

@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup"""
    global agent
    agent = WeatherAgent()
    logger.info("API Server started, Agent initialized")

# 3. Security Dependency (Simple Token Check)
async def verify_token(token: str = None):
    # In production, use headers. For simplicity, we accept it in the body or allow if undefined in config
    expected_token = Config.API_TOKEN
    if expected_token and expected_token != "dev-token-change-me":
        if token != expected_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API Token"
            )
    return True

# 4. Endpoints

@app.post("/query", response_model=QueryResponse)
async def query_agent(request: QueryRequest):
    """
    Main endpoint to chat with the Weather Agent.
    """
    try:
        # Verify token (optional based on your config)
        if request.api_token:
            await verify_token(request.api_token)
            
        logger.info(f"Received query: {request.message}")
        
        # Get response from Agent
        response_text = agent.chat(request.message)
        
        return QueryResponse(response=response_text)
        
    except Exception as e:
        logger.error(f"Query processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Check system health (Database connection & Uptime).
    """
    db = get_db_manager()
    health = db.check_health()
    
    return HealthResponse(
        status="healthy" if health['connected'] else "unhealthy",
        database="connected" if health['connected'] else "disconnected",
        uptime_seconds=time.time() - start_time
    )

@app.get("/metrics")
async def get_metrics():
    """
    Get database statistics.
    """
    db = get_db_manager()
    return db.get_database_stats()