# APScheduler setup
# src/orchestration/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging
import atexit

from config import Config
from ingestion.fetcher import fetch_current_weather

logger = logging.getLogger(__name__)

def start_scheduler():
    """
    Initialize and start the background scheduler.
    Schedules the weather fetch job to run every hour.
    """
    scheduler = BackgroundScheduler()
    
    # Schedule the job
    scheduler.add_job(
        func=fetch_current_weather,
        trigger=IntervalTrigger(hours=Config.FETCH_INTERVAL_HOURS),
        id='fetch_weather_job',
        name='Fetch current weather for all cities',
        replace_existing=True
    )
    
    # Start scheduler
    scheduler.start()
    logger.info(f"Scheduler started. Job running every {Config.FETCH_INTERVAL_HOURS} hour(s).")
    
    # Shut down scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())
    return scheduler