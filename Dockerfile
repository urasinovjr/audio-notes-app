FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install UV
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml .
COPY uv.lock* ./
COPY README.md .

# Install dependencies via UV
RUN uv sync --frozen

# Copy application code
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .
# COPY .env* ./

# Create uploads directory
RUN mkdir -p uploads

# Expose port
EXPOSE 8000

# Run with migrations
CMD ["sh", "-c", ". .venv/bin/activate && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
