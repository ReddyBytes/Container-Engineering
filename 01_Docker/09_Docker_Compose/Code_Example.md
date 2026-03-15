# Docker Compose — Code Examples

Four complete, annotated examples covering the most common Compose patterns.

---

## 1. Full Web App + Postgres + Redis (Annotated)

This is a production-quality Compose file for a three-tier web application.

**`docker-compose.yaml`**
```yaml
# Docker Compose Specification (modern format — no 'version' key needed)
# This file defines the complete application stack

services:

  # ================================================================
  # web: The application server
  # ================================================================
  web:
    # Build from the Dockerfile in this directory.
    # In CI/production, replace with 'image: myregistry/myapp:${APP_VERSION}'
    build:
      context: .
      dockerfile: Dockerfile

    # Give the container a predictable name.
    # Omit this if you want to scale with --scale web=3
    container_name: myapp-web

    # Map host port 8080 to container port 8000
    ports:
      - "${WEB_PORT:-8080}:8000"   # WEB_PORT from .env, defaults to 8080

    # Load environment variables from files and inline
    # Priority: environment > env_file > .env substitution
    env_file:
      - .env                       # base variables
    environment:
      APP_ENV: production
      # Connect to 'db' by service name — Docker DNS resolves it
      DATABASE_URL: "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}"
      # Connect to 'redis' by service name
      REDIS_URL: "redis://redis:6379/0"

    # Named volumes and bind mounts
    volumes:
      - uploads:/app/uploads       # named volume: persists uploaded files
      - ./logs:/app/logs           # bind mount: logs visible on host for analysis

    # Connect to the backend network (not the public-facing one)
    networks:
      - frontend
      - backend

    # Wait for db to pass its health check before starting
    # Without condition: service_healthy, we'd get connection errors on startup
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

    # Health check: Docker (and orchestrators) use this to know when we're ready
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s         # allow 20s for first startup (migrations, etc.)

    # Always restart unless manually stopped
    restart: unless-stopped

    # Log rotation: prevent logs filling disk
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"

  # ================================================================
  # db: PostgreSQL database
  # ================================================================
  db:
    image: postgres:16-alpine     # alpine = smaller image

    container_name: myapp-db

    # NOTE: we do NOT publish the db port to the host in production.
    # Only the 'web' service (on the same 'backend' network) can reach it.
    # In development, use docker-compose.override.yml to publish 5432.

    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
      # Tune postgres for low memory environments
      POSTGRES_INITDB_ARGS: "--encoding=UTF8"

    # Named volume: CRITICAL — database data must survive container removal
    volumes:
      - pgdata:/var/lib/postgresql/data
      # Optional: place custom init SQL here (runs on first startup only)
      # - ./db/init:/docker-entrypoint-initdb.d:ro

    networks:
      - backend                   # only on backend network — not reachable from frontend

    # Health check: pg_isready exits 0 when Postgres accepts connections
    # This is used by 'web' service's depends_on condition
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-postgres}"]
      interval: 5s
      timeout: 5s
      retries: 10
      start_period: 15s          # Postgres init takes ~10s on first run

    restart: unless-stopped

    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  # ================================================================
  # redis: Cache and session store
  # ================================================================
  redis:
    image: redis:7-alpine

    container_name: myapp-redis

    # Persist Redis data to survive container restarts
    # --save 60 1: save if at least 1 key changed in 60 seconds
    # --loglevel warning: reduce log verbosity
    command: redis-server --save 60 1 --loglevel warning

    volumes:
      - redis-data:/data

    networks:
      - backend                   # only on backend — not reachable from frontend

    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 5s

    restart: unless-stopped

    logging:
      driver: json-file
      options:
        max-size: "5m"
        max-file: "3"

# ================================================================
# Networks: isolate tiers
# ================================================================
networks:
  frontend:
    driver: bridge
    # frontend: web ↔ external traffic

  backend:
    driver: bridge
    internal: false              # set to 'true' to block internet access from backend
    # backend: web ↔ db ↔ redis (private communication)

# ================================================================
# Volumes: persistent storage
# ================================================================
volumes:
  pgdata:                        # postgres data directory
    driver: local

  redis-data:                    # redis persistence
    driver: local

  uploads:                       # user-uploaded files
    driver: local
```

---

## 2. .env File Pattern

```bash
# .env
# ============================================================
# This file is used by Docker Compose for variable substitution
# in docker-compose.yaml AND (via env_file:) injected into containers.
#
# NEVER commit secrets to version control.
# Add .env to .gitignore.
# Provide a .env.example with safe placeholder values.
# ============================================================

# Application
APP_VERSION=1.2.3
WEB_PORT=8080

# Database credentials
POSTGRES_USER=appuser
POSTGRES_PASSWORD=change-me-in-production
POSTGRES_DB=appdb

# Redis (no credentials needed for dev; add AUTH in production)
REDIS_PASSWORD=

# Feature flags
DEBUG=false
LOG_LEVEL=info
```

```bash
# .env.example (COMMITTED — shows required variables without real values)
APP_VERSION=
WEB_PORT=8080
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=
REDIS_PASSWORD=
DEBUG=false
LOG_LEVEL=info
```

```bash
# In your .gitignore:
.env
.env.*
!.env.example
```

**Usage:**
```bash
# Copy example, fill in real values
cp .env.example .env
$EDITOR .env

# Verify Compose substitution worked
docker compose config | grep image
docker compose config | grep DATABASE_URL
```

---

## 3. Override File for Development

**`docker-compose.override.yml`** (gitignored — developer-local)

```yaml
# This file is AUTOMATICALLY merged with docker-compose.yaml
# when you run 'docker compose up'.
# It overrides production settings for local development.
# gitignore this file to keep dev settings local.

services:

  web:
    # In dev: build from source code, not a pulled image
    build:
      context: .
      dockerfile: Dockerfile
      target: development           # multi-stage: build dev stage, not production

    # Mount source code from host into container (hot-reload)
    volumes:
      - ./src:/app/src:cached       # :cached hint for Docker Desktop performance
      - ./tests:/app/tests
      # Keep the named volume for uploads (don't overwrite with bind mount)
      - uploads:/app/uploads

    environment:
      APP_ENV: development
      DEBUG: "true"
      LOG_LEVEL: debug
      # Override production DB URL to use the local dev db
      DATABASE_URL: "postgresql://${POSTGRES_USER:-devuser}:${POSTGRES_PASSWORD:-devpass}@db:5432/${POSTGRES_DB:-devdb}"

    # In dev: no auto-restart (you want to see when things crash)
    restart: "no"

    # Override ports for dev (might want a different port)
    ports:
      - "3000:8000"                 # different port in dev

  db:
    # Expose Postgres port to host in dev (for connecting with pgAdmin, DBeaver, etc.)
    # NEVER do this in production
    ports:
      - "5432:5432"

    environment:
      POSTGRES_USER: devuser
      POSTGRES_PASSWORD: devpass
      POSTGRES_DB: devdb

  redis:
    # Expose Redis port in dev (for Redis CLI, Redis Insight)
    ports:
      - "6379:6379"

  # Add a dev-only service: pgAdmin for database GUI
  pgadmin:
    image: dpage/pgadmin4:latest
    ports:
      - "5050:80"
    environment:
      PGADMIN_DEFAULT_EMAIL: dev@example.com
      PGADMIN_DEFAULT_PASSWORD: admin
    networks:
      - backend
    profiles:
      - tools                       # only start with: docker compose --profile tools up
```

**Usage:**
```bash
# Development (auto-merges override.yml)
docker compose up -d

# Development with optional tools (pgAdmin)
docker compose --profile tools up -d

# Production (explicit files — override.yml NOT included)
docker compose -f docker-compose.yaml up -d

# Check what the merged config looks like
docker compose config
```

---

## 4. Health Check Examples for Common Services

```yaml
# ============================================================
# Comprehensive health check examples for different services
# Copy the relevant sections into your docker-compose.yaml
# ============================================================

services:

  # --- PostgreSQL ---
  postgres:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: secret
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -h localhost"]
      interval: 5s
      timeout: 5s
      retries: 10
      start_period: 15s

  # --- MySQL / MariaDB ---
  mysql:
    image: mysql:8
    environment:
      MYSQL_ROOT_PASSWORD: secret
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "--silent"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 30s

  # --- Redis ---
  redis:
    image: redis:7
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  # --- MongoDB ---
  mongo:
    image: mongo:7
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')", "--quiet"]
      interval: 10s
      timeout: 10s
      retries: 5
      start_period: 30s

  # --- HTTP service (curl) ---
  web-app:
    image: myapp:latest
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s

  # --- HTTP service (wget — for alpine images without curl) ---
  alpine-app:
    image: myapp:alpine
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:8080/health"]
      interval: 30s
      timeout: 5s
      retries: 3

  # --- TCP check (no HTTP, just port open) ---
  tcp-service:
    image: myservice:latest
    healthcheck:
      test: ["CMD-SHELL", "nc -z localhost 9090 || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 3

  # --- File existence check (app writes /tmp/healthy when ready) ---
  worker:
    image: myworker:latest
    healthcheck:
      test: ["CMD-SHELL", "test -f /tmp/healthy"]
      interval: 10s
      timeout: 3s
      retries: 5
      start_period: 30s

  # --- Elasticsearch ---
  elasticsearch:
    image: elasticsearch:8.12.0
    environment:
      discovery.type: single-node
      xpack.security.enabled: "false"
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:9200/_cluster/health | grep -q '\"status\":\"green\\|yellow\"'"]
      interval: 15s
      timeout: 10s
      retries: 10
      start_period: 60s
```

---

## 5. Running the Stack

```bash
# ============================================================
# Complete workflow: start → test → manage → clean up
# ============================================================

# Start everything (detached)
docker compose up -d

# Wait for all services to be healthy
docker compose ps
# STATUS column should show "healthy" for all services after a few seconds

# Follow logs from all services
docker compose logs -f

# Follow logs from a specific service only
docker compose logs -f web

# Run a one-off command (e.g., database migrations)
docker compose run --rm web python manage.py migrate

# Execute commands in running containers
docker compose exec web bash
docker compose exec db psql -U appuser -d appdb

# Scale the web tier (run 3 web containers)
# Note: don't use container_name when scaling — it conflicts
docker compose up -d --scale web=3
docker compose ps   # shows web-1, web-2, web-3

# Restart a specific service (e.g., after config change)
docker compose restart web

# View resource usage
docker stats $(docker compose ps -q)

# Rebuild and restart the web service only
docker compose build web
docker compose up -d --no-deps web

# Stop everything (keep containers + volumes)
docker compose stop

# Resume stopped stack
docker compose start

# Tear down completely (remove containers + networks, keep volumes)
docker compose down

# Tear down and destroy ALL data (DESTRUCTIVE)
# Only do this if you want a completely fresh start
docker compose down -v --rmi local
```

---

## 📂 Navigation

**In this folder:**
| File | |
|---|---|
| [📖 Theory.md](./Theory.md) | Full explanation |
| [⚡ Cheatsheet.md](./Cheatsheet.md) | Quick reference |
| [🎯 Interview_QA.md](./Interview_QA.md) | Interview prep |
| 💻 **Code_Example.md** | ← you are here |

⬅️ **Prev:** [08 — Networking](../08_Networking/Code_Example.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [10 — Docker Registry](../10_Docker_Registry/Theory.md)
🏠 **[Home](../../README.md)**
