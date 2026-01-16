# SQLAlchemy table definitions
"""
Database models for weather data storage using SQLAlchemy
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, 
    Index, UniqueConstraint, create_engine, text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class WeatherData(Base):
    """
    Main table for storing weather observations
    
    Implements idempotency through unique constraint on (city, timestamp)
    Includes indexes for efficient querying by city and time range
    """
    __tablename__ = 'weather_data'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Location information
    city = Column(String(100), nullable=False, index=True)
    country_code = Column(String(2), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # Weather measurements
    temperature = Column(Float, nullable=False)  # Celsius
    feels_like = Column(Float, nullable=False)   # Celsius
    temp_min = Column(Float)                     # Celsius
    temp_max = Column(Float)                     # Celsius
    pressure = Column(Integer)                   # hPa
    humidity = Column(Integer)                   # Percentage
    wind_speed = Column(Float)                   # m/s
    wind_deg = Column(Integer)                   # Degrees
    clouds = Column(Integer)                     # Percentage
    visibility = Column(Integer)                 # Meters
    
    # Weather conditions
    weather_main = Column(String(50))            # e.g., "Rain", "Clear"
    weather_description = Column(String(100))    # e.g., "light rain"
    
    # Temporal information
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    sunrise = Column(DateTime(timezone=True))
    sunset = Column(DateTime(timezone=True))
    
    # Metadata
    source = Column(String(50), nullable=False)  # 'api', 'backfill', 'synthetic'
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    
    # Constraints for idempotency
    __table_args__ = (
        # Prevent duplicate records for same city at same time
        UniqueConstraint('city', 'timestamp', name='uq_city_timestamp'),
        # Composite index for common query pattern
        Index('idx_city_timestamp', 'city', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<WeatherData(city='{self.city}', temp={self.temperature}°C, time={self.timestamp})>"
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'city': self.city,
            'country_code': self.country_code,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'temperature': self.temperature,
            'feels_like': self.feels_like,
            'temp_min': self.temp_min,
            'temp_max': self.temp_max,
            'pressure': self.pressure,
            'humidity': self.humidity,
            'wind_speed': self.wind_speed,
            'wind_deg': self.wind_deg,
            'clouds': self.clouds,
            'visibility': self.visibility,
            'weather_main': self.weather_main,
            'weather_description': self.weather_description,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'sunrise': self.sunrise.isoformat() if self.sunrise else None,
            'sunset': self.sunset.isoformat() if self.sunset else None,
            'source': self.source,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class JobHistory(Base):
    """
    Optional table to track orchestration job executions
    Useful for monitoring and debugging
    """
    __tablename__ = 'job_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_name = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False)  # 'success', 'failed', 'running'
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Float)
    cities_processed = Column(Integer)
    records_inserted = Column(Integer)
    records_updated = Column(Integer)
    error_message = Column(String(500))
    
    def __repr__(self):
        return f"<JobHistory(job='{self.job_name}', status='{self.status}', started={self.started_at})>"


def create_tables(engine):
    """
    Create all tables if they don't exist
    
    Args:
        engine: SQLAlchemy engine instance
    """
    Base.metadata.create_all(engine)
    print("✓ Database tables created successfully")


def get_table_info(engine):
    """
    Get information about existing tables for verification
    
    Args:
        engine: SQLAlchemy engine instance
        
    Returns:
        dict: Table information
    """
    with engine.connect() as conn:
        # Check if tables exist
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """))
        tables = [row[0] for row in result]
        
        # Get row counts
        counts = {}
        for table in tables:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            counts[table] = result.scalar()
        
        return {
            'tables': tables,
            'row_counts': counts
        }