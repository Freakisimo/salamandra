FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies manifest
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code and schema
COPY src/ ./src/

# Default port expected by Cloud Run
ENV PORT=8080
ENV PYTHONPATH=/app
EXPOSE 8080

# AGENT_FILE can be passed at runtime (e.g., src/agents/orchestrator.py)
ENV AGENT_FILE="src/agents/orchestrator.py"

CMD python ${AGENT_FILE}
