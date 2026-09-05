# Full-stack build: Python 3.11 base + Node.js 20 for frontend
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for:
# - Pillow, NumPy (build-essential, libjpeg-dev, zlib1g-dev)
# - Python packages in general
# - curl for healthchecks
# - Node.js installation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libffi-dev \
    libjpeg-dev \
    zlib1g-dev \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 (from NodeSource)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

# Copy Python package files and source
COPY pyproject.toml requirements.txt ./
COPY src ./src

# Install Python dependencies and the nonogram package
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -e .

# Verify nonogram CLI is available
RUN nonogram --help

# Copy application code (excluding dirs in .dockerignore)
COPY . .

# Install Node.js dependencies
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

# Start the application
WORKDIR /app
CMD ["sh", "-c", "export PYTHONPATH=/app/src:$PYTHONPATH && cd nonogram-web && npm start"]
