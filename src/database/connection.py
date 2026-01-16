# Database connection logic
"""
Database connection management with connection pooling and health checks
"""
import os
import time
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Generator
import logging

from .models import Base, create_tables, get_table_info

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages database connections, initialization, and health checks
    Implements connection pooling for production use
    """
    
    def __init__(self, database_url: str = None):
        """
        Initialize database manager
        
        Args:
            database_url: PostgreSQL connection string
                         Format: postgresql://user:password@host:port/dbname
        """
        self.database_url = database_url or os.getenv(
            'DATABASE_URL',
            'postgresql://weatheruser:weatherpass@localhost:5432/weatherdb'
        )
        
        # Create engine with connection pooling
        self.engine = create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=5,           # Number of connections to maintain
            max_overflow=10,       # Additional connections when pool is full
            pool_pre_ping=True,    # Verify connections before use
            pool_recycle=3600,     # Recycle connections after 1 hour
            echo=False             # Set to True for SQL query logging
        )
        
        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        logger.info(f"Database manager initialized with URL: {self._masked_url()}")
    
    def _masked_url(self) -> str:
        """Return database URL with masked password for logging"""
        if '@' in self.database_url:
            parts = self.database_url.split('@')
            credentials = parts[0].split('://')
            if len(credentials) > 1 and ':' in credentials[1]:
                user = credentials[1].split(':')[0]
                return f"{credentials[0]}://{user}:****@{parts[1]}"
        return self.database_url
    
    def initialize_database(self, retry_attempts: int = 5, retry_delay: int = 5) -> bool:
        """
        Initialize database: create tables if they don't exist
        Implements retry logic for database availability
        
        Args:
            retry_attempts: Number of connection attempts
            retry_delay: Seconds to wait between attempts
            
        Returns:
            bool: True if successful, False otherwise
        """
        for attempt in range(1, retry_attempts + 1):
            try:
                logger.info(f"Initializing database (attempt {attempt}/{retry_attempts})...")
                
                # Test connection
                with self.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                
                # Create tables
                create_tables(self.engine)
                
                # Verify tables were created
                info = get_table_info(self.engine)
                logger.info(f"Database initialized. Tables: {info['tables']}")
                
                return True
                
            except Exception as e:
                logger.error(f"Database initialization attempt {attempt} failed: {e}")
                if attempt < retry_attempts:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error("Database initialization failed after all attempts")
                    return False
    
    def check_health(self) -> dict:
        """
        Check database health and return status information
        
        Returns:
            dict: Health status with connection info and basic stats
        """
        try:
            with self.engine.connect() as conn:
                # Test query
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
                
                # Get database stats
                info = get_table_info(self.engine)
                
                return {
                    'status': 'healthy',
                    'connected': True,
                    'tables': info['tables'],
                    'row_counts': info['row_counts']
                }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'connected': False,
                'error': str(e)
            }
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions
        Automatically handles commit/rollback and cleanup
        
        Usage:
            with db_manager.get_session() as session:
                session.query(WeatherData).all()
        
        Yields:
            Session: SQLAlchemy session
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Session error: {e}")
            raise
        finally:
            session.close()
    
    def get_database_stats(self) -> dict:
        """
        Get comprehensive database statistics
        
        Returns:
            dict: Statistics including city count, date ranges, etc.
        """
        try:
            with self.get_session() as session:
                # Total records
                total_records = session.execute(
                    text("SELECT COUNT(*) FROM weather_data")
                ).scalar()
                
                # Unique cities
                unique_cities = session.execute(
                    text("SELECT COUNT(DISTINCT city) FROM weather_data")
                ).scalar()
                
                # Date range
                date_range = session.execute(text("""
                    SELECT 
                        MIN(timestamp) as earliest,
                        MAX(timestamp) as latest
                    FROM weather_data
                """)).fetchone()
                
                # Records by source
                by_source = session.execute(text("""
                    SELECT source, COUNT(*) as count
                    FROM weather_data
                    GROUP BY source
                """)).fetchall()
                
                return {
                    'total_records': total_records,
                    'unique_cities': unique_cities,
                    'earliest_record': date_range[0].isoformat() if date_range[0] else None,
                    'latest_record': date_range[1].isoformat() if date_range[1] else None,
                    'by_source': {row[0]: row[1] for row in by_source}
                }
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {'error': str(e)}
    
    def close(self):
        """Close database connections"""
        self.engine.dispose()
        logger.info("Database connections closed")


# Global instance (initialized in main.py)
db_manager: DatabaseManager = None


def get_db_manager() -> DatabaseManager:
    """
    Get the global database manager instance
    
    Returns:
        DatabaseManager: The global database manager
    """
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager