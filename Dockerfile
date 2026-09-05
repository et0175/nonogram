# Full-stack build: Python 3.11 + Node.js 20 in single container
# Uses python:3.11 base (Debian-based) for Python + adds Node.js
FROM python:3.11

WORKDIR /app

# Install system dependencies and Node.js in single layer
# All dependencies must be in one RUN to ensure they work together
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libffi-dev \
    libjpeg-dev \
    zlib1g-dev \
    curl \
    gnupg \
    ca-certificates && \
    # Install Node.js 20 from NodeSource
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    # Clean up apt cache
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Verify tools are available
RUN python --version && node --version && npm --version

# Copy Python package files early for better caching
COPY pyproject.toml requirements.txt ./
COPY src ./src

# Install Python dependencies and the nonogram package
RUN python -m pip install --no-cache-dir --upgrade pip && \
    python -m pip install --no-cache-dir -r requirements.txt && \
    python -m pip install --no-cache-dir -e .

# Verify nonogram CLI is available
RUN nonogram --help

# Copy application code
COPY . .

# Install Node.js dependencies with npm ci (production-ready)
WORKDIR /app/nonogram-web
RUN npm ci --legacy-peer-deps

# Build Next.js application
RUN npm run build

# Set environment variables
ENV PYTHONPATH=/app/src
ENV NODE_ENV=production
ENV PORT=8080

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/api/generate || exit 1

# Start the application
WORKDIR /app
CMD ["sh", "-c", "export PYTHONPATH=/app/src:$PYTHONPATH && cd nonogram-web && npm start"]
