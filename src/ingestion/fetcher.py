# Current weather fetcher
# src/ingestion/fetcher.py
import json
import logging
import time
from typing import List, Dict
from sqlalchemy.dialects.postgresql import insert

from config import Config
from database.connection import get_db_manager
from database.models import WeatherData
from ingestion.owm_client import OWMClient

logger = logging.getLogger(__name__)

def load_cities() -> List[Dict]:
    """Load cities from JSON file"""
    try:
        with open(Config.CITIES_FILE, 'r') as f:
            data = json.load(f)
            return data.get('cities', [])[:Config.CITIES_LIMIT]
    except Exception as e:
        logger.error(f"Failed to load cities file: {e}")
        return []

def fetch_current_weather():
    """
    Main function to fetch weather for all cities and save to DB.
    Handles rate limiting and database upserts.
    """
    logger.info("Starting weather fetch job...")
    
    client = OWMClient()
    db = get_db_manager()
    cities = load_cities()
    
    success_count = 0
    error_count = 0
    
    with db.get_session() as session:
        for city in cities:
            try:
                name = city['name']
                lat = city['lat']
                lon = city['lon']
                
                # Fetch data
                weather_data = client.get_current_weather(name, lat, lon)
                
                if weather_data:
                    # Create UPSERT statement (PostgreSQL specific)
                    # This handles the requirement: "Same timestamp + city = no duplicate"
                    stmt = insert(WeatherData).values(**weather_data)
                    stmt = stmt.on_conflict_do_update(
                        constraint='uq_city_timestamp',
                        set_=weather_data
                    )
                    
                    session.execute(stmt)
                    session.commit()
                    success_count += 1
                    logger.info(f"Updated weather for {name}")
                else:
                    error_count += 1
                
                # Rate limiting (conservative 1 sec pause)
                time.sleep(1.0) 
                
            except Exception as e:
                logger.error(f"Failed to process {city.get('name')}: {e}")
                error_count += 1
                session.rollback()

    logger.info(f"Job completed. Success: {success_count}, Errors: {error_count}")