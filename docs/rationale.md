# Architectural Rationale & Design Decisions

## 1. Technology Stack Selection

### **Language: Python 3.11**
Chosen for its dominance in Data Engineering and AI. It offers robust libraries for everything required: `pandas` for data manipulation, `sqlalchemy` for ORM, and the native `openai` SDK.

### **Database: PostgreSQL**
* **Why not BigQuery?** While BigQuery is excellent for analytics, Postgres was chosen for this self-contained "Agentic Pipeline" because:
    * It offers lower latency for single-row lookups (needed for the real-time "Current Weather" queries).
    * It is easier to containerize locally with Docker (zero cloud cost/setup for the reviewer).
    * It enforces strict schema constraints (Unique Constraints) which are vital for data integrity.

### **Orchestration: APScheduler**
* **Decision:** I chose `APScheduler` over heavy tools like Airflow or Prefect.
* **Reasoning:** The requirement is a single hourly loop. Airflow brings massive overhead (webserver, scheduler, redis, workers). `APScheduler` runs as a lightweight thread within our main Python process, reducing resource usage and deployment complexity.

### **AI Framework: OpenAI Assistants (Tools)**
* **Design:** Utilized the "Function Calling" (Tool Use) capability of GPT-4o-mini.
* **Why:** This allows the LLM to structure queries deterministically (`get_weather(city='Tokyo')`) rather than hallucinating SQL or parsing vague text. It strictly separates the "Brain" (LLM) from the "Data" (DB).

## 2. Key Design Patterns

### **Idempotency Strategy**
To prevent duplicate data during backfills or retries, I implemented a composite unique constraint on `(city, timestamp)`. The ingestion layer uses the `ON CONFLICT DO UPDATE` clause. This means we can re-run the backfill script 100 times, and the database will remain accurate without duplication.

### **Resilience & Fallback**
The agent is designed with a "Database First, API Fallback" approach:
1.  **Attempt 1:** Query the local database for recent weather.
2.  **Fallback:** If the data is stale (>1 hour) or missing (new city), the tool automatically calls the live OpenWeatherMap API and returns that result, ensuring the user always gets an answer.

## 3. Future Improvements (Production Readiness)
If this were going to a large-scale production environment, I would add:
* **Redis Caching:** To cache frequent queries like "Weather in London" to save DB hits.
* **Prometheus Metrics:** To expose scraping metrics (API latency, success rates) for Grafana dashboards.
* **Alembic Migrations:** For managing database schema changes over time.

## 4. Deviation from Requirements & Justification

### **Backfill Data Source (Open-Meteo vs. OpenWeatherMap)**
**Requirement:** "Backfill at least 2 months of historical weather data from OpenWeatherMap."

**Implementation:** I utilized the **Open-Meteo Archive API** for historical backfilling.

**Rationale:** The OpenWeatherMap "History API" is a paid feature that is not accessible via the standard Free Tier API key provided for this test. To adhere to the requirement of 60 days of history without incurring costs or requiring a paid subscription, I integrated Open-Meteo as a cost-effective, reliable alternative for historical data. The data schema was normalized to match the OpenWeatherMap format, ensuring consistency in the database regardless of the source.

### **Database Choice (PostgreSQL vs. BigQuery)**
**Requirement:** "Store in BigQuery (preferred) or another structured database."

**Implementation:** I chose **PostgreSQL 15**.

**Rationale:** While BigQuery is powerful for analytics, PostgreSQL was selected to maximize **portability and ease of evaluation**.
1.  **Zero-Config Deployment:** By using Postgres in Docker, the entire stack runs with a single `docker-compose up` command. Using BigQuery would require the evaluator to set up a Google Cloud Project, generate Service Account keys, and configure IAM permissions, which adds friction to the review process.
2.  **Idempotency Constraints:** PostgreSQL allows strict `UNIQUE` constraints and `ON CONFLICT` clauses, which are essential for the required idempotency (preventing duplicate rows) during high-frequency ingestion.

---

## 5. Testing & Quality Assurance Strategy

### **Test Coverage Philosophy**
The project implements a multi-layered testing approach to validate each component of the pipeline independently and in integration.

### **Test Suite Architecture**

#### **A. Ingestion Tests (`tests/test_ingestion.py`)**
**Purpose:** Validates data fetching, transformation, and storage logic.

**Coverage:**
* API connectivity and response parsing
* Data normalization from multiple sources (OpenWeatherMap + Open-Meteo)
* Database insertion and idempotency verification
* Error handling for network failures and malformed responses

**Key Test Cases:**
```python
# Verify backfill creates expected number of records
assert record_count >= 6000  # 100 cities × 60 days × 1 record/day minimum

# Verify no duplicate timestamps per city
assert duplicate_count == 0

# Verify source attribution is correct
assert 'backfill' in sources and 'api' in sources
```

**Run Command:**
```bash
docker-compose exec app python -m tests.test_ingestion
```

#### **B. Agent Tests (`tests/test_agent.py`)**
**Purpose:** Validates AI agent behavior, tool execution, and guardrails.

**Coverage:**
* Tool invocation correctness (correct city/timestamp passed to functions)
* Response formatting and natural language generation
* Guardrails enforcement (non-weather queries refused)
* Database query optimization (indexes used correctly)

**Key Test Cases:**
```python
# Test current weather query
response = agent.query("What's the weather in Tokyo?")
assert "Tokyo" in response and "temperature" in response.lower()

# Test historical analysis
response = agent.query("Temperature trend in London last 7 days")
assert "average" in response.lower() or "trend" in response.lower()

# Test guardrails
response = agent.query("Who won the World Cup?")
assert "weather" in response.lower() and "cannot" in response.lower()
```

**Run Command:**
```bash
docker-compose exec app python -m tests.test_agent
```

#### **C. Beta Assistant Tests (`tests/test_beta.py`)**
**Purpose:** Validates alternative OpenAI Assistants API implementation (Beta).

**Coverage:**
* Thread/Run state management
* Asynchronous message handling
* Tool execution in Assistant API context
* Streaming response handling

**Run Command:**
```bash
docker-compose exec app python -m tests.test_beta
```

### **Database Verification Strategy**

The testing approach includes direct SQL verification queries to validate:

1. **Data Volume:** Ensure expected number of records exist
2. **Temporal Coverage:** Verify 60-day historical range
3. **Idempotency:** Confirm no duplicate (city, timestamp) pairs
4. **Data Quality:** Check for null values and outliers
5. **Index Performance:** Verify queries use indexes efficiently

See [Database Schema Documentation](db_schema.md#-verification-queries) for complete query reference.

### **Manual Integration Testing**

The `/query` API endpoint serves as the final integration test, verifying:
* End-to-end pipeline flow (API → DB → Agent → Response)
* Error handling and graceful degradation
* Response time under realistic conditions

**Example Integration Test Flow:**
```bash
# 1. Verify system health
curl http://localhost:8000/health

# 2. Test current data retrieval
curl -X POST http://localhost:8000/query \
     -d '{"message": "Weather in Paris?"}'

# 3. Test historical analysis
curl -X POST http://localhost:8000/query \
     -d '{"message": "Temperature trend in Berlin last week?"}'

# 4. Verify guardrails
curl -X POST http://localhost:8000/query \
     -d '{"message": "What is 2+2?"}'
```

### **Continuous Validation**

**Health Check Endpoint (`/health`)**
* Database connectivity verification
* Service uptime tracking
* Response time monitoring

**Scheduled Job Monitoring**
* APScheduler logs track ingestion success/failure
* Optional `job_history` table records execution metadata

### **Quality Metrics**

| Metric | Target | Verification Method |
|--------|--------|---------------------|
| Test Coverage | >80% | `pytest --cov` |
| Database Records | >6,000 | `SELECT count(*)` |
| Query Response Time | <500ms | `/health` endpoint |
| Idempotency Violations | 0 | Duplicate detection query |
| Agent Accuracy | >95% | Manual test suite |

### **Why This Testing Strategy?**

1. **Layered Validation:** Each component is tested independently before integration testing
2. **Fast Feedback:** Tests run inside Docker for consistency with production environment
3. **Practical Focus:** Tests validate actual user workflows rather than abstract unit tests
4. **Database-Centric:** Direct SQL queries provide ground truth verification

## 6. Side Products & Utilities

During development of this agentic pipeline, several helper utilities and testing frameworks were created:

### **Testing Suite**
* **`tests/test_ingestion.py`**: Validates data fetching, normalization, and database storage
* **`tests/test_agent.py`**: Verifies AI agent tool execution and guardrails
* **`tests/test_beta.py`**: Alternative implementation using OpenAI Assistants API (Beta)

### **Database Verification Scripts**
A comprehensive set of SQL queries (documented in `db_schema.md`) for validating:
* Data volume and distribution across cities
* Idempotency (detecting duplicate records)
* Temporal coverage (ensuring 60-day backfill)
* Data quality (null checks, outliers)
* Index performance verification

### **Monitoring & Health Checks**
* **Health Endpoint (`/health`)**: FastAPI endpoint for uptime monitoring and database connectivity checks
* **Structured Logging**: APScheduler job execution logs for debugging ingestion failures

### **Configuration Management**
* **`.env.example`**: Template file documenting all required environment variables
* **City Configuration**: Centralized list of 100 monitored cities with coordinates

### **Development Tools**
* **Docker Compose**: Single-command deployment for consistent development/production environments
* **Hot Reload**: FastAPI development mode for rapid iteration

These utilities collectively reduce debugging time, ensure data quality, and provide production-readiness monitoring capabilities.
