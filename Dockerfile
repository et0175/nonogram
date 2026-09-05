FROM python:3.11-bullseye

# Install Node.js (using nodesource for latest stable)
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    gnupg \
    lsb-release \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y nodejs \
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
EXPOSE 3000

# Set Python path and ensure both Python and npm are in PATH
# Railway sets PORT env var (default 8080), Next.js respects it
ENV PYTHONPATH=/app/src
ENV PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
CMD ["sh", "-c", "export PORT=${PORT:-3000} && cd nonogram-web && npm start"]
