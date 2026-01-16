# src/agent/tools.py
import json
import logging
from typing import Optional, Tuple

# Absolute imports
from config import Config
from database.queries import get_latest_weather, get_weather_history
from ingestion.owm_client import OWMClient

logger = logging.getLogger(__name__)

def get_city_coordinates(city_name: str) -> Optional[Tuple[float, float]]:
    """Helper to find lat/lon for a city from our local config file"""
    try:
        with open(Config.CITIES_FILE, 'r') as f:
            data = json.load(f)
            cities = data.get('cities', [])
            
            for city in cities:
                if city['name'].lower() == city_name.lower():
                    return city['lat'], city['lon']
        return None
    except Exception as e:
        logger.error(f"Error reading cities file: {e}")
        return None

def execute_tool_call(tool_name, arguments):
    """
    Router to execute the correct python function based on agent's request.
    """
    try:
        args = json.loads(arguments)
        city = args.get("city")
        logger.info(f"Agent executing tool: {tool_name} with args: {args}")
        
        if tool_name == "get_current_weather":
            # 1. Try Database First
            data = get_latest_weather(city)
            if data:
                return json.dumps(data, default=str)
            
            # 2. Fallback: Call API Directly if DB misses
            logger.info(f"Data not found in DB for {city}, attempting live API fallback...")
            
            # Look up coordinates
            coords = get_city_coordinates(city)
            if not coords:
                return json.dumps({"error": f"City '{city}' not found in configuration list."})
            
            lat, lon = coords
            client = OWMClient()
            live_data = client.get_current_weather(city, lat, lon)
            
            if live_data:
                return json.dumps(live_data, default=str)
            else:
                return json.dumps({"error": "Failed to fetch live data from API."})

        elif tool_name == "get_weather_history":
            days = args.get("days", 7)
            data = get_weather_history(city, days)
            if not data:
                return json.dumps({"message": "No historical data available yet. History builds up over time."})
            return json.dumps(data, default=str)
            
        else:
            return json.dumps({"error": "Unknown tool"})
            
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        return json.dumps({"error": str(e)})

# Define the Schemas (What the AI sees)
WEATHER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Get the current weather for a specific city. Use this for questions like 'What is the weather in Tokyo?'",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The name of the city, e.g. London, Tokyo, Colombo"
                    }
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather_history",
            "description": "Get historical weather data for a city over the last N days. Use this for averages, trends, or past weather.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The name of the city"
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days to look back (default 7)",
                        "default": 7
                    }
                },
                "required": ["city"]
            }
        }
    }
]