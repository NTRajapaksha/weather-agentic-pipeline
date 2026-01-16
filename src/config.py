# Configuration management
"""
Configuration management for the weather agent pipeline
Loads settings from environment variables with sensible defaults
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()


class Config:
    """Central configuration class for the application"""
    
    # Project paths
    PROJECT_ROOT = Path(__file__).parent.parent
    DATA_DIR = PROJECT_ROOT / 'data'
    CITIES_FILE = DATA_DIR / 'cities.json'
    
    # Database configuration
    DATABASE_URL = os.getenv(
        'DATABASE_URL',
        'postgresql://weatheruser:weatherpass@localhost:5432/weatherdb'
    )
    
    # API Keys
    OPENWEATHERMAP_API_KEY = os.getenv('OPENWEATHERMAP_API_KEY', '')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    
    # OpenWeatherMap API settings
    OWM_BASE_URL = 'https://api.openweathermap.org/data/2.5/weather'
    OWM_RATE_LIMIT_PER_MINUTE = 60  # Free tier limit
    OWM_RATE_LIMIT_PER_DAY = 1000   # Free tier limit
    
    # OpenAI settings
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
    OPENAI_TEMPERATURE = float(os.getenv('OPENAI_TEMPERATURE', '0.7'))
    
    # Orchestration settings
    FETCH_INTERVAL_HOURS = int(os.getenv('FETCH_INTERVAL_HOURS', '1'))
    BACKFILL_DAYS = int(os.getenv('BACKFILL_DAYS', '60'))
    
    # Application settings
    CITIES_LIMIT = int(os.getenv('CITIES_LIMIT', '100'))
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # API settings (for FastAPI server)
    API_HOST = os.getenv('API_HOST', '0.0.0.0')
    API_PORT = int(os.getenv('API_PORT', '8000'))
    API_TOKEN = os.getenv('API_TOKEN', 'dev-token-change-me')
    
    # Retry settings
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_DELAY = int(os.getenv('RETRY_DELAY', '5'))
    
    @classmethod
    def validate(cls) -> bool:
        """
        Validate that all required configuration is present
        
        Returns:
            bool: True if valid, raises ValueError if invalid
        """
        errors = []
        
        # Check required API keys
        if not cls.OPENWEATHERMAP_API_KEY:
            errors.append("OPENWEATHERMAP_API_KEY is required")
        
        if not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is required")
        
        # Check cities file exists
        if not cls.CITIES_FILE.exists():
            errors.append(f"Cities file not found: {cls.CITIES_FILE}")
        
        # Check database URL format
        if not cls.DATABASE_URL.startswith('postgresql://'):
            errors.append("DATABASE_URL must be a PostgreSQL connection string")
        
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ValueError(error_msg)
        
        return True
    
    @classmethod
    def get_summary(cls) -> dict:
        """
        Get a summary of current configuration (safe for logging)
        
        Returns:
            dict: Configuration summary with masked secrets
        """
        return {
            'database_url': cls._mask_secret(cls.DATABASE_URL),
            'openweathermap_key': cls._mask_secret(cls.OPENWEATHERMAP_API_KEY),
            'openai_key': cls._mask_secret(cls.OPENAI_API_KEY),
            'openai_model': cls.OPENAI_MODEL,
            'fetch_interval_hours': cls.FETCH_INTERVAL_HOURS,
            'backfill_days': cls.BACKFILL_DAYS,
            'cities_limit': cls.CITIES_LIMIT,
            'log_level': cls.LOG_LEVEL,
            'api_host': cls.API_HOST,
            'api_port': cls.API_PORT
        }
    
    @staticmethod
    def _mask_secret(secret: str, visible_chars: int = 4) -> str:
        """
        Mask a secret string for safe logging
        
        Args:
            secret: The secret to mask
            visible_chars: Number of characters to show at start
            
        Returns:
            str: Masked secret
        """
        if not secret:
            return '<not set>'
        if len(secret) <= visible_chars:
            return '****'
        return secret[:visible_chars] + '****'


def setup_logging(level: str = None):
    """
    Configure application logging
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    log_level = level or Config.LOG_LEVEL
    
    # Create logs directory if it doesn't exist
    logs_dir = Config.PROJECT_ROOT / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            # Console handler
            logging.StreamHandler(),
            # File handler
            logging.FileHandler(logs_dir / 'weather_agent.log')
        ]
    )
    
    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured at {log_level} level")
    logger.info(f"Log file: {logs_dir / 'weather_agent.log'}")


# Initialize logging on import
setup_logging()