FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- UPDATED SECTION ---
# Copy the entire project (src, tests, docs, README, etc.)
COPY . .
# ---------------------

# CRITICAL FIX: Add src to PYTHONPATH so imports like 'from database...' work
ENV PYTHONPATH="${PYTHONPATH}:/app/src"

# Run the application
CMD ["python", "src/main.py"]