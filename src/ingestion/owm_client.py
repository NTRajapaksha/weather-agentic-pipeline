# OpenWeatherMap API client
# src/ingestion/owm_client.py
import requests
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from config import Config

logger = logging.getLogger(__name__)

class OWMClient:
    """Client for interacting with OpenWeatherMap API"""
    
    def __init__(self):
        self.api_key = Config.OPENWEATHERMAP_API_KEY
        self.base_url = Config.OWM_BASE_URL
        
        if not self.api_key:
            logger.warning("OpenWeatherMap API key not found in config")

    def get_current_weather(self, city: str, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """
        Fetch current weather for a specific location.
        Uses lat/lon for better precision, falls back to city name if needed.
        """
        try:
            # Construct URL parameters
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key,
                'units': 'metric'  # Get temperature in Celsius
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return self._transform_current_weather(data, city)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API Request failed for {city}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing weather data for {city}: {e}")
            return None

    def _transform_current_weather(self, raw_data: Dict, city_name: str) -> Dict[str, Any]:
        """
        Transform raw OWM API response to DB schema format.
        """
        try:
            # Extract main weather data
            main = raw_data.get('main', {})
            wind = raw_data.get('wind', {})
            weather = raw_data.get('weather', [{}])[0]
            sys = raw_data.get('sys', {})
            clouds = raw_data.get('clouds', {})
            
            return {
                'city': city_name, # Use our clean name from cities.json
                'country_code': sys.get('country', 'XX'),
                'latitude': raw_data.get('coord', {}).get('lat', 0.0),
                'longitude': raw_data.get('coord', {}).get('lon', 0.0),
                
                # Metrics
                'temperature': main.get('temp'),
                'feels_like': main.get('feels_like'),
                'temp_min': main.get('temp_min'),
                'temp_max': main.get('temp_max'),
                'pressure': main.get('pressure'),
                'humidity': main.get('humidity'),
                'wind_speed': wind.get('speed'),
                'wind_deg': wind.get('deg'),
                'clouds': clouds.get('all'),
                'visibility': raw_data.get('visibility'),
                
                # Conditions
                'weather_main': weather.get('main'),
                'weather_description': weather.get('description'),
                
                # Timestamps (Convert to timezone-aware UTC)
                'timestamp': datetime.fromtimestamp(raw_data.get('dt'), tz=timezone.utc),
                'sunrise': datetime.fromtimestamp(sys.get('sunrise', 0), tz=timezone.utc),
                'sunset': datetime.fromtimestamp(sys.get('sunset', 0), tz=timezone.utc),
                
                'source': 'api'
            }
        except KeyError as e:
            logger.error(f"Missing key in API response for {city_name}: {e}")
            raise