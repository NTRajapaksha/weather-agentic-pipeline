#!/usr/bin/env python3


import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from database.connection import DatabaseManager
from database.queries import get_all_cities
from config import Config

def test_configuration():
    """Test that configuration is valid"""
    print("=== Testing Configuration ===")
    try:
        Config.validate()
        print("✓ Configuration valid")
        
        summary = Config.get_summary()
        print(f"✓ OpenWeatherMap Key: {summary['openweathermap_key']}")
        print(f"✓ OpenAI Key: {summary['openai_key']}")
        print(f"✓ Database URL: {summary['database_url']}")
        return True
    except ValueError as e:
        print(f"✗ Configuration error: {e}")
        return False

def test_database():
    """Test database connection and initialization"""
    print("=== Testing Database ===")
    try:
        # Initialize database manager
        db = DatabaseManager()
        
        # Initialize tables
        if db.initialize_database():
            print("✓ Database initialized successfully")
        else:
            print("✗ Database initialization failed")
            return False
        
        # Check health
        health = db.check_health()
        if health['status'] == 'healthy':
            print(f"✓ Database health: {health['status']}")
            print(f"✓ Tables: {health['tables']}")
            print(f"✓ Row counts: {health['row_counts']}")
        else:
            print(f"✗ Database unhealthy: {health}")
            return False
        
        # Get stats
        stats = db.get_database_stats()
        print(f"✓ Total records: {stats.get('total_records', 0)}")
        print(f"✓ Unique cities: {stats.get('unique_cities', 0)}")
        
        return True
    except Exception as e:
        print(f"✗ Database error: {e}")
        return False

def test_cities_file():
    """Test that cities file exists and is valid"""
    print("=== Testing Cities File ===")
    try:
        import json
        
        if not Config.CITIES_FILE.exists():
            print(f"✗ Cities file not found: {Config.CITIES_FILE}")
            return False
        
        with open(Config.CITIES_FILE, 'r') as f:
            data = json.load(f)
        
        cities = data.get('cities', [])
        print(f"✓ Found {len(cities)} cities")
        
        if len(cities) >= 100:
            print(f"✓ Have at least 100 cities")
        else:
            print(f"⚠ Warning: Only {len(cities)} cities (need 100)")
        
        # Show sample
        print(f"✓ Sample cities: {cities[0]['name']}, {cities[1]['name']}, {cities[2]['name']}")
        
        return True
    except Exception as e:
        print(f"✗ Cities file error: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("PHASE 0 & 1 VALIDATION TEST")
    print("=" * 60)
    
    results = {
        'Configuration': test_configuration(),
        'Cities File': test_cities_file(),
        'Database': test_database()
    }
    
    print("" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("🎉 All tests passed! Ready for Phase 2!")
    else:
        print("⚠️  Some tests failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == '__main__':
    main()