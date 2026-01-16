# src/main.py
import logging
import sys
import uvicorn
from database.connection import get_db_manager
from ingestion.backfill import BackfillManager
from ingestion.fetcher import fetch_current_weather
from orchestration.scheduler import start_scheduler
from config import Config, setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

def check_and_run_backfill():
    """Check if database is empty and run backfill if needed."""
    db = get_db_manager()
    stats = db.get_database_stats()
    
    if stats.get('total_records', 0) == 0:
        logger.info("Database appears empty. Initiating historical backfill...")
        backfill = BackfillManager()
        backfill.run_backfill()
    else:
        logger.info(f"Database contains {stats.get('total_records')} records. Skipping backfill.")

def main():
    """
    Main application entry point.
    """
    logger.info("Starting Weather Agent Pipeline...")
    
    # 1. Initialize Database
    db = get_db_manager()
    if not db.initialize_database():
        logger.error("Failed to initialize database. Exiting.")
        sys.exit(1)
        
    # 2. Backfill Data (if needed)
    check_and_run_backfill()
    
    # 3. Initial Fetch (so we have current data immediately)
    logger.info("Running initial weather fetch...")
    fetch_current_weather()
    
    # 4. Start Scheduler (Background)
    # The scheduler runs in a separate thread managed by APScheduler
    scheduler = start_scheduler()
    
    # 5. Start API Server (Blocking)
    # This replaces the 'while True' loop
    logger.info(f"Starting API server on {Config.API_HOST}:{Config.API_PORT}")
    uvicorn.run(
        "api.server:app", 
        host=Config.API_HOST, 
        port=Config.API_PORT, 
        reload=False # Reload=False for production/docker
    )

if __name__ == "__main__":
    main()