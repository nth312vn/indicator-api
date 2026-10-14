# Multi-stage build for optimal image size, build speed, and container security
ARG PYTHON_VERSION=3.11-slim

# ==========================================
# Stage 1: Build C libraries & Python packages
# ==========================================
FROM python:${PYTHON_VERSION} AS builder

WORKDIR /build

# Support proxy build arguments for corporate / proxied environments
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
ENV http_proxy=${HTTP_PROXY} \
    https_proxy=${HTTPS_PROXY} \
    no_proxy=${NO_PROXY}

# Install build tools and compilation dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    autotools-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Download and compile TA-Lib C library (v0.4.0)
# Updating config.guess & config.sub ensures smooth compilation on both x86_64 and arm64/Apple Silicon
RUN curl -fsSL https://github.com/ta-lib/ta-lib/releases/download/v0.4.0/ta-lib-0.4.0-src.tar.gz -o ta-lib-0.4.0-src.tar.gz \
    || curl -fsSL http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz -o ta-lib-0.4.0-src.tar.gz \
    && tar -xzf ta-lib-0.4.0-src.tar.gz \
    && cd ta-lib \
    && cp /usr/share/misc/config.guess /usr/share/misc/config.sub . \
    && ./configure --prefix=/usr \
    && make \
    && make install \
    && cd .. \
    && rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# Configure pip with project proxy settings
COPY pip.conf /etc/pip.conf
ENV PIP_CONFIG_FILE=/etc/pip.conf

# Create virtual environment and install Python packages
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt


# ==========================================
# Stage 2: Minimal runtime image
# ==========================================
FROM python:${PYTHON_VERSION} AS runtime

# Python environment settings
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    LD_LIBRARY_PATH="/usr/lib:/usr/local/lib:$LD_LIBRARY_PATH" \
    PIP_CONFIG_FILE=/etc/pip.conf \
    PORT=8000

WORKDIR /app

# Copy pip proxy configuration to runtime
COPY pip.conf /etc/pip.conf

# Copy compiled TA-Lib C shared libraries from builder
COPY --from=builder /usr/lib/libta_lib* /usr/lib/
RUN ldconfig

# Copy pre-installed virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create a non-root system user for security
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

# Copy application source code and tests with appropriate permissions
COPY --chown=appuser:appuser app /app/app
COPY --chown=appuser:appuser tests /app/tests
COPY --chown=appuser:appuser .env.example /app/.env.example

# Switch to unprivileged user
USER appuser

EXPOSE 8000

# Container healthcheck using standard library urllib
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

# Start FastAPI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
