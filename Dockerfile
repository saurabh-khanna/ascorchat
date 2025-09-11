FROM python:3.12.3-bullseye
SHELL ["/bin/bash", "-c"]

# Base environment settings
ENV PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=0 \
    SERVER_NAME=0.0.0.0 \
    PORT=8501

# System dependencies
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    nano python3-pip gettext chrpath libssl-dev libxft-dev \
    libfreetype6 libfreetype6-dev libfontconfig1 libfontconfig1-dev \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Upgrade pip/setuptools
RUN pip install --upgrade pip setuptools

WORKDIR /app

# Install Python requirements first (layer caching)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# OPTIONAL build/env hook (does nothing unless we add env/envs_export.sh or BUILD_COMMAND)
RUN if [ -f "./env/envs_export.sh" ]; then \
       echo "Sourcing env/envs_export.sh"; \
       source ./env/envs_export.sh; \
    else \
       echo "No env/envs_export.sh found, skipping"; \
    fi; \
    if [ -n "${BUILD_COMMAND:-}" ]; then \
       echo "Running BUILD_COMMAND=${BUILD_COMMAND}"; \
       eval "${BUILD_COMMAND}"; \
    else \
       echo "No BUILD_COMMAND provided, skipping"; \
    fi

# Create non-root user
RUN useradd -ms /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8501

# Healthcheck to help platforms know container readiness
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -fsS "http://localhost:${PORT}/_stcore/health" || exit 1

# Keep our existing workflow (run.sh uses $SERVER_NAME and $PORT)
ENTRYPOINT ["bash", "-lc", "./run.sh"]
