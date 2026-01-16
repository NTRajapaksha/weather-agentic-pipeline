from src.database.connection import get_db_manager
from src.ingestion.fetcher import fetch_current_weather
from src.ingestion.backfill import BackfillManager

# Initialize DB
db = get_db_manager()
db.initialize_database()

# 1. Test Fetcher (Current Data)
print("Fetching current weather...")
fetch_current_weather()

# 2. Test Backfill (Historical Data)
print("Running backfill...")
backfill = BackfillManager()
backfill.run_backfill()