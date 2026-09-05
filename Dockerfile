FROM node:20-slim

# Install Python and build tools
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy root package files
COPY package*.json ./
COPY pyproject.toml requirements.txt runtime.txt ./

# Copy source code
COPY src ./src
COPY nonogram-web ./nonogram-web

# Install Python dependencies (nonogram CLI)
RUN pip install --no-cache-dir -r requirements.txt

# Install root npm dependencies (sets PYTHONPATH etc)
RUN npm install

# Install and build Next.js
WORKDIR /app/nonogram-web
RUN npm install
RUN npm run build

WORKDIR /app

# Expose port
EXPOSE 8080

# Set Python path and start app
ENV PYTHONPATH=/app/src
CMD ["sh", "-c", "cd nonogram-web && npm start"]
