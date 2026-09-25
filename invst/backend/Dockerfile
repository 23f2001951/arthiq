FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/venv/bin:$PATH"

WORKDIR /app

# Install system dependencies for C-extensions and PDF generation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into isolated virtualenv
COPY requirements.txt pyproject.toml ./
RUN python -m venv /venv && \
    pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy source and config
COPY . .
RUN pip install --no-cache-dir -e .

EXPOSE 8000

# Run FastAPI production server
CMD ["uvicorn", "invst.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
