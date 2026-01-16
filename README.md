# Weather Agentic Pipeline

<div align="center">
  
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

</div>

---

## 🗃️ Architecture

The system is built with four distinct layers ensuring separation of concerns and modularity:

### Layer 1: Data Storage 💾
- **PostgreSQL 15** with optimized schema
- **Composite unique constraint** on `(city, timestamp)` ensures strict idempotency
- **Indexed queries** on city and timestamp for millisecond-level retrieval

### Layer 2: Ingestion & Orchestration 🔄
- **Current Data**: OpenWeatherMap API polled hourly for 100 cities
- **Historical Data**: Open-Meteo Archive API for 60-day backfill
- **Scheduler**: APScheduler manages cron jobs lightweight within the app container

### Layer 3: AI Agent (Brain) 🤖
- **Framework**: OpenAI Agents SDK with Function Calling
- **Model**: GPT-4o-mini
- **Tools**: `get_latest_weather`, `get_weather_history`
- **Guardrails**: Strictly scoped to weather-domain queries only

### Layer 4: API Interface 🌐
- **FastAPI** with auto-generated OpenAPI docs
- **Endpoints**: `/query` for natural language, `/health` for monitoring

---

## 🚀 Features

<table>
<tr>
<td width="50%">

### 🔄 ETL Pipeline
Hourly ingestion of weather data for 100+ cities with automatic error handling and retry logic.

### 📊 Historical Backfill
Automatically fetches the last 60 days of history on startup using Open-Meteo Archive API for comprehensive trend analysis.

### 💾 Idempotent Storage
Composite unique constraint ensures no duplicate records. Safe to re-run ingestion multiple times.

</td>
<td width="50%">

### 🤖 AI Agent
Specialized GPT-4o-mini agent with OpenAI Agents SDK that queries the database using natural language and custom tools.

### 🚀 FastAPI Server
Production-ready API with full OpenAPI documentation, health checks, and error handling.

### 🛡️ Smart Fallback
Database-first approach with automatic fallback to live API calls when historical data is unavailable.

</td>
</tr>
<tr>
<td colspan="2" align="center">

### 🐳 Fully Dockerized
Zero-config deployment with Docker Compose. Get started in minutes with a single command!

</td>
</tr>
</table>

---

## 🛠️ Prerequisites

<div align="center">

| Requirement | Version | Purpose |
|------------|---------|---------|
| 🐳 Docker | Latest | Container runtime |
| 🐙 Docker Compose | Latest | Orchestration |
| 🔑 OpenAI API Key | - | AI agent queries |
| 🌤️ OpenWeatherMap API Key | - | Weather data source |

</div>

## ⚡ Quick Start

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd weather-agent-pipeline
   ```

2. **Configure Environment**
   
   Create a `.env` file in the root directory:
   ```ini
   OPENAI_API_KEY=sk-your-key...
   OPENWEATHERMAP_API_KEY=your-owm-key...
   POSTGRES_USER=weatheruser
   POSTGRES_PASSWORD=weatherpass
   POSTGRES_DB=weatherdb
   API_TOKEN=secret-token
   ```

3. **Run with Docker**
   ```bash
   docker-compose up --build
   ```
   
   *Wait for the logs to say "Application startup complete". The first run will fetch current weather for all cities.*

## 🧪 Testing the Agent

You can query the agent via the API:

### 1. Current Weather ☀️

```bash
curl -X POST "http://localhost:8000/query" \
     -H "Content-Type: application/json" \
     -d '{"message": "What is the weather in Tokyo?"}'
```

**Expected Response:**
```json
{
  "response": "The current weather in Tokyo is clear with a temperature of 5.15°C, humidity at 42%, and wind speed of 2.06 m/s."
}
```

### 2. Historical Analysis 📈

```bash
curl -X POST "http://localhost:8000/query" \
     -H "Content-Type: application/json" \
     -d '{"message": "What was the temperature trend in London over the last 7 days?"}'
```

**Expected Response:**
```json
{
  "response": "Over the last 7 days in London, the average temperature was 8.4°C, with a high of 11.2°C and a low of 5.1°C. The most common condition was 'Clouds'."
}
```

### 3. Guardrails Test 🛡️

```bash
curl -X POST "http://localhost:8000/query" \
     -H "Content-Type: application/json" \
     -d '{"message": "Who won the World Cup?"}'
```

**Expected Response:**
```json
{
  "response": "I apologize, but I can only assist with weather-related questions."
}
```

### 4. Health Check ✅

```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## 🧪 Testing & Verification

The project includes a suite of verification scripts to validate the pipeline components (Ingestion, Database, AI Agent) directly inside the container.

### 1. Run Internal Test Scripts
Since the application runs in Docker, use `docker-compose exec` to run tests inside the app container.

**A. Pipeline & Ingestion Test**

Triggers the fetcher and backfill logic to verify data is being pulled and stored correctly.
```bash
docker-compose exec app python -m tests.test_ingestion
```

**B. AI Agent Test (Standard)**

Tests the `WeatherAgent` class directly, verifying tool execution and guardrails (e.g., refusing non-weather queries).
```bash
docker-compose exec app python -m tests.test_agent
```

**C. Beta Assistant Test (Optional)**

Verifies the alternative implementation using the OpenAI Assistants API (Beta) with Thread/Run state management.
```bash
docker-compose exec app python -m tests.test_beta
```

### 2. Database Verification
You can inspect the PostgreSQL database directly to verify data volume and idempotency.

**Access the Database Shell:**
```bash
docker-compose exec db psql -U weatheruser -d weatherdb
```

**Useful Verification Queries:**
```sql
-- Check total record count (Should be > 6,000 after backfill)
SELECT count(*) FROM weather_data;

-- Verify Data Sources (Live API vs. Backfill)
SELECT source, count(*) FROM weather_data GROUP BY source;

-- Check latest data for a specific city
SELECT timestamp, temperature, humidity, source 
FROM weather_data 
WHERE city = 'London' 
ORDER BY timestamp DESC 
LIMIT 5;

-- Exit the shell
\q
```

### 3. API Usage (Manual Testing)
You can query the running Agent via `curl` to simulate real user interactions.

**Current Weather Query:**
```bash
curl -X POST "http://localhost:8000/query" \
     -H "Content-Type: application/json" \
     -d '{"message": "What is the current weather in Tokyo?"}'
```

**Historical/Trend Query:**
```bash
curl -X POST "http://localhost:8000/query" \
     -H "Content-Type: application/json" \
     -d '{"message": "What was the temperature trend in New York over the last 7 days?"}'
```

**Guardrail Test:**
```bash
curl -X POST "http://localhost:8000/query" \
     -H "Content-Type: application/json" \
     -d '{"message": "Who won the World Cup?"}'
```

---

## 📂 Project Structure

```
weather-agent-pipeline/
├── 📁 src/
│   ├── 🔥 ingestion/      # Scripts for fetching API data
│   ├── 💾 database/       # Models and connection logic
│   ├── ⚙️  orchestration/  # Job scheduler
│   ├── 🤖 agent/          # AI logic and tool definitions
│   └── 🌐 api/            # FastAPI server endpoints
├── 📁 docs/               # Additional documentation
├── 🐳 docker-compose.yml  # Container orchestration
├── 📋 requirements.txt    # Python dependencies
└── 📖 README.md          # This file
```

---

## 🎯 Key Design Decisions

### Why PostgreSQL over BigQuery?
While BigQuery is powerful for large-scale analytics, **PostgreSQL was chosen for portability**. The entire stack runs in a single `docker-compose` file without requiring Google Cloud credentials, Service Accounts, or IAM setup. This optimizes for ease of deployment and review.

### Why Open-Meteo for Historical Data?
OpenWeatherMap's History API is a **paid feature** unavailable on the free tier. To fulfill the 60-day backfill requirement without cost, **Open-Meteo Archive API** was used. Data is normalized to match the OpenWeatherMap schema for consistency.

### Why APScheduler instead of Airflow?
For a single hourly job, Airflow introduces massive overhead (webserver, scheduler, Redis, workers). **APScheduler** runs lightweight threads within the main process, keeping the Docker image small (~200MB) and resource-efficient while maintaining reliability.

### Idempotency Implementation
The system uses PostgreSQL's `INSERT ... ON CONFLICT DO UPDATE` with a composite unique constraint on `(city, timestamp)`:

```python
stmt = insert(WeatherData).values(**data)
stmt = stmt.on_conflict_do_update(
    constraint='uq_city_timestamp',
    set_=data
)
```

This guarantees that re-running ingestion never creates duplicates.

---

## 📚 Documentation

For more detailed information, see:

* [Database Schema](docs/db_schema.md) - Complete schema documentation with example queries
* [Design Rationale](docs/rationale.md) - Architecture decisions and implementation details

## 🔧 Development

The pipeline automatically:
* **Ingests** current weather data every hour via APScheduler
* **Backfills** 60 days of historical data on first run
* **Stores** all data in a normalized PostgreSQL database with idempotency
* **Provides** natural language query capabilities through the AI agent
* **Falls back** to live API calls when database data is unavailable

### Agent Guardrails 🛡️

The agent is strictly scoped to weather domains via its system prompt:

> "You are a helpful Weather Assistant. You ONLY answer questions about weather. If a user asks about non-weather topics, politely refuse."

This ensures the agent stays focused and doesn't attempt to answer out-of-scope queries.

### Database-First Strategy

The tool logic implements a **"Database First, API Second"** mechanism:

1. Query DB for the requested city
2. If result is `None` (empty/missing), lookup coordinates from config
3. Call OpenWeatherMap API directly to fetch live data
4. Return fresh data to the user

---

## 📄 License

MIT License

Copyright (c) 2024

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.


### Development Setup

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---