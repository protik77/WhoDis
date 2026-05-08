FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock README.md ./

# Install dependencies (but not the project itself yet)
RUN uv sync --frozen --no-install-project --group dev --all-extras

# Copy application code
COPY whodis/ ./whodis/
COPY tests/ ./tests/
COPY alembic/ ./alembic/
COPY run.py ./
COPY Makefile ./

# Install the project
RUN uv sync --frozen --group dev --all-extras

# Create data directory and volume
RUN mkdir -p data
VOLUME /app/data

# Expose port
EXPOSE 8000

# Run the application
CMD ["uv", "run", "uvicorn", "whodis.main:app", "--host", "0.0.0.0", "--port", "8000"]
