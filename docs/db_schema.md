# Database Schema Documentation

## Overview
The system uses **PostgreSQL 15** as the primary data store. The schema is designed to support high-frequency writes (upserts) and efficient time-series querying for the AI agent.

## Tables

### 1. `weather_data`
Stores current and historical weather observations for all monitored cities.

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL (PK) | Auto-incrementing primary key |
| `city` | VARCHAR(100) | Name of the city (Indexed) |
| `country_code` | VARCHAR(2) | ISO 3166-1 alpha-2 country code |
| `latitude` | FLOAT | Geographic latitude |
| `longitude` | FLOAT | Geographic longitude |
| `temperature` | FLOAT | Current temperature in Celsius |
| `feels_like` | FLOAT | Perceived temperature in Celsius |
| `humidity` | INTEGER | Humidity percentage |
| `pressure` | INTEGER | Atmospheric pressure in hPa |
| `wind_speed` | FLOAT | Wind speed in m/s |
| `weather_main` | VARCHAR(50) | Primary weather condition (e.g., "Rain", "Clear") |
| `weather_description` | VARCHAR(100) | Detailed description (e.g., "light rain") |
| `timestamp` | TIMESTAMPTZ | Time of observation in UTC (Indexed) |
| `source` | VARCHAR(50) | Origin of data: 'api', 'backfill', or 'synthetic' |
| `created_at` | TIMESTAMPTZ | Record creation time (default: now) |

### Constraints & Indexes
* **Composite Unique Constraint (`uq_city_timestamp`)**: Ensures idempotency. We cannot have two records for the same city at the exact same second. This allows safe `UPSERT` operations.
* **Index (`idx_city_timestamp`)**: A composite index on `city` + `timestamp` optimizes the most common query: *"Get weather history for City X ordered by time."*

---

### 2. `job_history` (Optional)
Tracks the execution status of the orchestration jobs.

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL (PK) | Primary key |
| `job_name` | VARCHAR(100) | Name of the scheduled task |
| `status` | VARCHAR(20) | 'success', 'failed', 'running' |
| `started_at` | TIMESTAMPTZ | Execution start time |
| `records_inserted` | INTEGER | Count of new records added |

## Data Flow
1.  **Ingestion**: Python script fetches data from OpenWeatherMap.
2.  **Normalization**: Data is cleaned and mapped to the schema.
3.  **Storage**: `INSERT ... ON CONFLICT (city, timestamp) DO UPDATE` ensures existing records are updated while new ones are inserted.
4.  **Retrieval**: AI Agent queries views or direct selects via SQLAlchemy.

---

## 🧪 Verification Queries

The following SQL queries can be used to verify database integrity and data quality after deployment.

### Data Volume Checks

**Total Record Count** (Should be > 6,000 after 60-day backfill for 100 cities)
```sql
SELECT count(*) FROM weather_data;
```

**Records Per City** (Should show roughly equal distribution)
```sql
SELECT city, count(*) as record_count 
FROM weather_data 
GROUP BY city 
ORDER BY record_count DESC 
LIMIT 10;
```

### Data Source Distribution

**Verify Backfill vs Live Data**
```sql
SELECT source, count(*) as count 
FROM weather_data 
GROUP BY source 
ORDER BY count DESC;
```

### Temporal Coverage

**Date Range Per City**
```sql
SELECT 
    city,
    MIN(timestamp) as earliest_record,
    MAX(timestamp) as latest_record,
    MAX(timestamp) - MIN(timestamp) as coverage_duration
FROM weather_data
GROUP BY city
ORDER BY coverage_duration DESC
LIMIT 10;
```

**Check for Data Gaps** (Identifies cities with fewer than expected records)
```sql
SELECT city, count(*) as records
FROM weather_data
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY city
HAVING count(*) < 150  -- Assuming hourly data = ~168 records/week
ORDER BY records ASC;
```

### Idempotency Verification

**Detect Duplicate Timestamps** (Should return 0 rows if idempotency is working)
```sql
SELECT city, timestamp, count(*) as duplicate_count
FROM weather_data
GROUP BY city, timestamp
HAVING count(*) > 1;
```

### Recent Data Quality

**Latest Records Per City** (Verify freshness)
```sql
SELECT city, temperature, humidity, timestamp, source
FROM weather_data
WHERE timestamp > NOW() - INTERVAL '2 hours'
ORDER BY timestamp DESC
LIMIT 20;
```

**Check for Null Values** (Data quality validation)
```sql
SELECT 
    count(*) as total_records,
    count(*) FILTER (WHERE temperature IS NULL) as null_temp,
    count(*) FILTER (WHERE humidity IS NULL) as null_humidity,
    count(*) FILTER (WHERE weather_main IS NULL) as null_weather
FROM weather_data;
```

### Performance Metrics

**Index Usage Check** (Verify query performance)
```sql
EXPLAIN ANALYZE
SELECT * FROM weather_data
WHERE city = 'London' 
  AND timestamp > NOW() - INTERVAL '7 days'
ORDER BY timestamp DESC;
```

### Access the Database Shell

To run these queries, connect to the PostgreSQL container:

```bash
docker-compose exec db psql -U weatheruser -d weatherdb
```

Exit with `\q` when finished.