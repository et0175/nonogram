FROM python:3.11-slim

# Force rebuild - 2026-09-05T18:20:00Z
# Install Node.js 20 from system repos
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js via apt
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy files
COPY . .

# Install Python deps
RUN pip3 install -e . --no-cache-dir

# Install Node deps and build Next.js app
WORKDIR /app/nonogram-web
RUN npm install --no-cache-dir
RUN npm run build

WORKDIR /app/nonogram-web
EXPOSE 8080
ENV PYTHONPATH=/app/src
ENV PORT=8080
ENV NODE_ENV=production
CMD ["npm", "start", "--", "-H", "0.0.0.0"]
