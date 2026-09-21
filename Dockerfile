FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for compilation if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY pyproject.toml .

# Expose default port
EXPOSE 8000

ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Start command
CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT}"]
