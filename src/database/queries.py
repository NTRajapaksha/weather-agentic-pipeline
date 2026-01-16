# Query helper functions
"""
Query helper functions for retrieving weather data
These functions will be used by the AI agent
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from sqlalchemy import desc, func, and_
import logging

from .models import WeatherData
from .connection import get_db_manager

logger = logging.getLogger(__name__)


def get_latest_weather(city: str) -> Optional[Dict]:
    """
    Get the most recent weather record for a city
    
    Args:
        city: City name (case-insensitive)
        
    Returns:
        dict: Weather data or None if city not found
        
    Example:
        >>> data = get_latest_weather("Colombo")
        >>> print(f"Temperature: {data['temperature']}°C")
    """
    try:
        db = get_db_manager()
        with db.get_session() as session:
            # Query most recent record for city (case-insensitive)
            record = session.query(WeatherData)\
                .filter(func.lower(WeatherData.city) == city.lower())\
                .order_by(desc(WeatherData.timestamp))\
                .first()
            
            if record:
                logger.info(f"Found latest weather for {city}: {record.temperature}°C at {record.timestamp}")
                return record.to_dict()
            else:
                logger.warning(f"No weather data found for city: {city}")
                return None
                
    except Exception as e:
        logger.error(f"Error querying latest weather for {city}: {e}")
        raise


def get_weather_history(city: str, days: int = 7) -> List[Dict]:
    """
    Get weather history for a city over the last N days
    Returns records sorted by timestamp (newest first)
    
    Args:
        city: City name (case-insensitive)
        days: Number of days to look back (default: 7)
        
    Returns:
        list: List of weather records, empty list if none found
        
    Example:
        >>> history = get_weather_history("London", days=7)
        >>> print(f"Found {len(history)} records")
    """
    try:
        db = get_db_manager()
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        with db.get_session() as session:
            records = session.query(WeatherData)\
                .filter(
                    and_(
                        func.lower(WeatherData.city) == city.lower(),
                        WeatherData.timestamp >= cutoff_date
                    )
                )\
                .order_by(desc(WeatherData.timestamp))\
                .all()
            
            logger.info(f"Found {len(records)} weather records for {city} in last {days} days")
            return [record.to_dict() for record in records]
            
    except Exception as e:
        logger.error(f"Error querying weather history for {city}: {e}")
        raise


def get_weather_statistics(city: str, days: int = 7) -> Optional[Dict]:
    """
    Get aggregated weather statistics for a city over the last N days
    Calculates average, min, max temperatures and common conditions
    
    Args:
        city: City name (case-insensitive)
        days: Number of days to look back (default: 7)
        
    Returns:
        dict: Aggregated statistics or None if insufficient data
        
    Example:
        >>> stats = get_weather_statistics("Tokyo", days=7)
        >>> print(f"Average temp: {stats['avg_temperature']}°C")
    """
    try:
        db = get_db_manager()
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        with db.get_session() as session:
            # Get aggregated data
            result = session.query(
                func.avg(WeatherData.temperature).label('avg_temp'),
                func.min(WeatherData.temperature).label('min_temp'),
                func.max(WeatherData.temperature).label('max_temp'),
                func.avg(WeatherData.humidity).label('avg_humidity'),
                func.avg(WeatherData.wind_speed).label('avg_wind'),
                func.count(WeatherData.id).label('record_count')
            ).filter(
                and_(
                    func.lower(WeatherData.city) == city.lower(),
                    WeatherData.timestamp >= cutoff_date
                )
            ).first()
            
            if result and result.record_count > 0:
                # Get most common weather condition
                common_condition = session.query(
                    WeatherData.weather_main,
                    func.count(WeatherData.weather_main).label('count')
                ).filter(
                    and_(
                        func.lower(WeatherData.city) == city.lower(),
                        WeatherData.timestamp >= cutoff_date
                    )
                ).group_by(WeatherData.weather_main)\
                 .order_by(desc('count'))\
                 .first()
                
                return {
                    'city': city,
                    'days_analyzed': days,
                    'record_count': result.record_count,
                    'avg_temperature': round(result.avg_temp, 1) if result.avg_temp else None,
                    'min_temperature': round(result.min_temp, 1) if result.min_temp else None,
                    'max_temperature': round(result.max_temp, 1) if result.max_temp else None,
                    'avg_humidity': round(result.avg_humidity, 1) if result.avg_humidity else None,
                    'avg_wind_speed': round(result.avg_wind, 1) if result.avg_wind else None,
                    'most_common_condition': common_condition[0] if common_condition else None
                }
            else:
                logger.warning(f"No statistics available for {city} in last {days} days")
                return None
                
    except Exception as e:
        logger.error(f"Error calculating weather statistics for {city}: {e}")
        raise


def get_all_cities() -> List[str]:
    """
    Get list of all cities currently in the database
    
    Returns:
        list: Sorted list of unique city names
        
    Example:
        >>> cities = get_all_cities()
        >>> print(f"Tracking {len(cities)} cities")
    """
    try:
        db = get_db_manager()
        with db.get_session() as session:
            cities = session.query(WeatherData.city)\
                .distinct()\
                .order_by(WeatherData.city)\
                .all()
            
            city_list = [city[0] for city in cities]
            logger.info(f"Found {len(city_list)} unique cities in database")
            return city_list
            
    except Exception as e:
        logger.error(f"Error fetching city list: {e}")
        raise


def get_city_data_range(city: str) -> Optional[Dict]:
    """
    Get the date range of available data for a city
    
    Args:
        city: City name (case-insensitive)
        
    Returns:
        dict: Date range info or None if city not found
        
    Example:
        >>> range_info = get_city_data_range("Paris")
        >>> print(f"Data from {range_info['earliest']} to {range_info['latest']}")
    """
    try:
        db = get_db_manager()
        with db.get_session() as session:
            result = session.query(
                func.min(WeatherData.timestamp).label('earliest'),
                func.max(WeatherData.timestamp).label('latest'),
                func.count(WeatherData.id).label('count')
            ).filter(
                func.lower(WeatherData.city) == city.lower()
            ).first()
            
            if result and result.count > 0:
                return {
                    'city': city,
                    'earliest': result.earliest.isoformat() if result.earliest else None,
                    'latest': result.latest.isoformat() if result.latest else None,
                    'total_records': result.count
                }
            else:
                return None
                
    except Exception as e:
        logger.error(f"Error getting data range for {city}: {e}")
        raise


def search_cities(query: str, limit: int = 10) -> List[str]:
    """
    Search for cities matching a query string
    Useful for handling partial or misspelled city names
    
    Args:
        query: Search string
        limit: Maximum number of results
        
    Returns:
        list: List of matching city names
        
    Example:
        >>> matches = search_cities("lon")
        >>> print(matches)  # ['London', 'Colombo', ...]
    """
    try:
        db = get_db_manager()
        with db.get_session() as session:
            cities = session.query(WeatherData.city)\
                .filter(WeatherData.city.ilike(f'%{query}%'))\
                .distinct()\
                .limit(limit)\
                .all()
            
            return [city[0] for city in cities]
            
    except Exception as e:
        logger.error(f"Error searching cities with query '{query}': {e}")
        raise