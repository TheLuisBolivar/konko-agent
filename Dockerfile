# Konko AI Conversational Agent
# Multi-stage build for optimized production image

# ============================================
# Stage 1: Builder
# ============================================
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY pyproject.toml .
COPY README.md .
COPY packages/ packages/

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -e .

# ============================================
# Stage 2: Production
# ============================================
FROM python:3.11-slim AS production

WORKDIR /app

# Create non-root user for security
RUN groupadd -r konko && useradd -r -g konko konko

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY packages/ packages/
COPY configs/ configs/
COPY main.py .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV HOST=0.0.0.0
ENV PORT=8000

# Expose port
EXPOSE 8000

# Change to non-root user
USER konko

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["python", "main.py"]

# ============================================
# Stage 3: Development (optional)
# ============================================
FROM production AS development

USER root

# Install dev dependencies
RUN pip install --no-cache-dir pytest pytest-asyncio pytest-cov pylint radon

USER konko

CMD ["uvicorn", "agent_api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--reload"]
