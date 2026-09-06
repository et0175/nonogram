# Multi-stage build: Python base + Node.js for the full stack app

# Stage 1: Python environment with the nonogram CLI
FROM python:3.11-slim as python-base

WORKDIR /app

# Install system dependencies needed for Pillow and other packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy Python package files
COPY pyproject.toml requirements.txt ./
COPY src ./src

# Install Python dependencies and the nonogram package
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Full runtime - Node.js 20 with Python baked in
FROM node:20-slim

WORKDIR /app

# Install Python runtime from the previous stage
COPY --from=python-base /usr/local/bin/python* /usr/local/bin/
COPY --from=python-base /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=python-base /usr/local/bin/pip* /usr/local/bin/
COPY --from=python-base /usr/local/bin/nonogram /usr/local/bin/

# Verify nonogram CLI is available
RUN nonogram --help

# Copy application code
COPY . .

# Install Node.js dependencies
WORKDIR /app/nonogram-web
RUN npm install

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
