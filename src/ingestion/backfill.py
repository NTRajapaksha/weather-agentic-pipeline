# Historical data backfill
# src/ingestion/backfill.py
import requests
import logging
import time
from datetime import datetime, timedelta, timezone
import pandas as pd
from sqlalchemy.dialects.postgresql import insert

from config import Config
from database.connection import get_db_manager
from database.models import WeatherData
from ingestion.fetcher import load_cities

logger = logging.getLogger(__name__)

class BackfillManager:
    """Manages historical data backfill using Open-Meteo API"""
    
    OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"
    
    def run_backfill(self):
        """Execute backfill for all cities"""
        logger.info(f"Starting backfill for last {Config.BACKFILL_DAYS} days...")
        
        cities = load_cities()
        db = get_db_manager()
        
        # Calculate dates
        end_date = datetime.now() - timedelta(days=1)
        start_date = end_date - timedelta(days=Config.BACKFILL_DAYS)
        
        total_records = 0
        
        with db.get_session() as session:
            for city in cities:
                try:
                    records = self._fetch_history(
                        city, 
                        start_date.strftime('%Y-%m-%d'), 
                        end_date.strftime('%Y-%m-%d')
                    )
                    
                    if records:
                        # Batch insert
                        for record in records:
                            stmt = insert(WeatherData).values(**record)
                            stmt = stmt.on_conflict_do_nothing() # Skip if exists
                            session.execute(stmt)
                        
                        session.commit()
                        total_records += len(records)
                        logger.info(f"Backfilled {len(records)} records for {city['name']}")
                    
                    # Rate limit for Open-Meteo
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Backfill failed for {city['name']}: {e}")
                    session.rollback()

        logger.info(f"Backfill completed. Total records inserted: {total_records}")

    def _fetch_history(self, city: dict, start: str, end: str) -> list:
        """Fetch historical data from Open-Meteo"""
        params = {
            "latitude": city['lat'],
            "longitude": city['lon'],
            "start_date": start,
            "end_date": end,
            "hourly": "temperature_2m,relative_humidity_2m,pressure_msl,wind_speed_10m,weather_code,cloud_cover",
            "timezone": "UTC"
        }
        
        response = requests.get(self.OPEN_METEO_URL, params=params)
        
        if response.status_code != 200:
            logger.error(f"Open-Meteo error: {response.text}")
            return []
            
        data = response.json()
        hourly = data.get('hourly', {})
        
        records = []
        if not hourly:
            return []
            
        # Parse result lists
        timestamps = hourly.get('time', [])
        temps = hourly.get('temperature_2m', [])
        humidities = hourly.get('relative_humidity_2m', [])
        pressures = hourly.get('pressure_msl', [])
        winds = hourly.get('wind_speed_10m', [])
        codes = hourly.get('weather_code', [])
        clouds = hourly.get('cloud_cover', [])
        
        for i, ts_str in enumerate(timestamps):
            # Convert ISO string to datetime object
            ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
            
            # Map WMO codes to description (Simplified)
            wmo_code = codes[i]
            condition, desc = self._map_wmo_code(wmo_code)
            
            records.append({
                'city': city['name'],
                'country_code': city['country'],
                'latitude': city['lat'],
                'longitude': city['lon'],
                'temperature': temps[i],
                'feels_like': temps[i], # Approximation for backfill
                'temp_min': temps[i],
                'temp_max': temps[i],
                'pressure': int(pressures[i]) if pressures[i] else None,
                'humidity': int(humidities[i]) if humidities[i] else None,
                'wind_speed': winds[i],
                'wind_deg': 0, # Not provided in basic archive
                'clouds': int(clouds[i]) if clouds[i] else 0,
                'visibility': 10000, # Default
                'weather_main': condition,
                'weather_description': desc,
                'timestamp': ts,
                'source': 'backfill'
            })
            
        return records

    def _map_wmo_code(self, code: int):
        """Helper to map Open-Meteo WMO codes to text"""
        # Simplified mapping
        if code == 0: return "Clear", "clear sky"
        if code in [1, 2, 3]: return "Clouds", "partly cloudy"
        if code in [45, 48]: return "Fog", "fog"
        if code in [51, 53, 55]: return "Drizzle", "drizzle"
        if code in [61, 63, 65]: return "Rain", "rain"
        if code in [71, 73, 75]: return "Snow", "snow"
        if code >= 95: return "Thunderstorm", "thunderstorm"
        return "Unknown", "unknown"