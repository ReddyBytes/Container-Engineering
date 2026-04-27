# Build Guide — JWT Auth API in Docker

Ten steps from blank directory to running containers. Each step has a hint if you want to try it yourself, and a complete answer if you want to follow along.

Work in a clean project directory:

```bash
mkdir jwt-docker && cd jwt-docker
mkdir src
```

---

## Step 1 — Write the FastAPI App

The application has three routes: `POST /register` creates a user (hashes the password, stores in PostgreSQL), `POST /login` checks credentials and returns a JWT, and `GET /me` is a protected route that decodes the token and returns the current user.

<details>
<summary>💡 Hint</summary>

Your app needs to:
- Connect to PostgreSQL via SQLAlchemy using `DATABASE_URL` from env
- Hash passwords with `bcrypt` before storing
- On login, verify the hash and return a signed JWT
- On `/me`, read the `Authorization: Bearer <token>` header, decode the JWT, and return the user

The database URL format for SQLAlchemy + psycopg2:
```
postgresql://user:password@host:port/dbname
```

Inside Docker Compose, `host` is the service name: `db`.

</details>

<details>
<summary>✅ Answer</summary>

Copy `src/solution.py` into your project as `src/main.py`. The full annotated implementation is in `src/solution.py` in this project folder.

Key structure:
```
src/
└── main.py   ← FastAPI app (copy from solution.py)
requirements.txt
Dockerfile
docker-compose.yml
.env.example
.env
```

</details>

---

## Step 2 — Write the Multi-Stage Dockerfile

The builder stage installs all dependencies (including build tools needed for psycopg2). The runtime stage copies only the installed packages and app code — no build tools, no cache, no bloat.

<details>
<summary>💡 Hint</summary>

Structure:
```
FROM python:3.12-slim AS builder
  # install build dependencies (libpq-dev, gcc)
  # pip install --prefix=/install -r requirements.txt

FROM python:3.12-slim AS runtime
  # COPY --from=builder /install /usr/local
  # COPY src/ /app/src/
  # create non-root user
  # HEALTHCHECK with curl or wget
  # CMD uvicorn
```

The `--prefix=/install` flag in pip tells it to put all installed packages into `/install` instead of the system Python path. Then you copy that directory wholesale into the runtime stage.

Non-root user pattern:
```dockerfile
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser
```

</details>

<details>
<summary>✅ Answer</summary>

```dockerfile
# ── Stage 1: builder ──────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# libpq-dev: PostgreSQL C headers needed to compile psycopg2
# gcc: C compiler needed by psycopg2-binary build
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# --prefix=/install puts compiled packages into a separate directory
# so we can copy them cleanly into the runtime stage
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt


# ── Stage 2: runtime ──────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# libpq5: the runtime PostgreSQL client library (not the dev headers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Copy compiled packages from builder — no build tools come with them
COPY --from=builder /install /usr/local

# Copy app source
COPY src/ ./src/

# Create non-root user — running as root in a container is a security risk
RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup appuser
USER appuser

# Docker will poll this endpoint to determine container health
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

# --host 0.0.0.0 is required — default 127.0.0.1 is unreachable from outside the container
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

</details>

---

## Step 3 — Write .dockerignore

Without `.dockerignore`, Docker copies your entire build context into the daemon — including `.env`, `__pycache__`, `.git`, and any local virtualenvs. The `.dockerignore` file works exactly like `.gitignore`.

<details>
<summary>💡 Hint</summary>

You want to exclude: Python bytecode, virtual environments, `.env` files, `.git`, editor directories, and any local test artifacts.

</details>

<details>
<summary>✅ Answer</summary>

```
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.egg-info/

# Virtual environments
.venv/
venv/
env/

# Secrets — never bake these into the image
.env
.env.*
!.env.example

# Git
.git/
.gitignore

# Editor
.vscode/
.idea/

# Test artifacts
.pytest_cache/
.coverage
htmlcov/

# Docker
docker-compose.override.yml
```

The `!.env.example` line is an exception — it un-excludes the example file so it can be inspected inside the image if needed (it contains no real secrets).

</details>

---

## Step 4 — Write docker-compose.yml

Compose describes the two services, the shared network, and the named volume. The `depends_on` condition with `service_healthy` is the key — it makes the API wait for PostgreSQL's health check to pass before starting.

<details>
<summary>💡 Hint</summary>

Structure:
```yaml
services:
  app:
    build: .
    ports: ["8000:8000"]
    environment:
      DATABASE_URL: postgresql://...
      SECRET_KEY: ${SECRET_KEY}
    depends_on:
      db:
        condition: service_healthy
    networks: [app_network]

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      ...
    volumes: [postgres_data:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      ...
    networks: [app_network]

networks:
  app_network:
    driver: bridge

volumes:
  postgres_data:
```

PostgreSQL's `pg_isready` command exits 0 when the database is accepting connections.

</details>

<details>
<summary>✅ Answer</summary>

```yaml
version: "3.9"

services:

  app:
    build: .
    image: jwt-api:latest          # tag the built image for reuse
    container_name: jwt_api
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      SECRET_KEY: ${SECRET_KEY}
      ALGORITHM: HS256
      ACCESS_TOKEN_EXPIRE_MINUTES: 30
    depends_on:
      db:
        condition: service_healthy  # wait for postgres health check to pass
    networks:
      - app_network
    restart: on-failure

  db:
    image: postgres:15-alpine
    container_name: jwt_postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data  # named volume persists data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    networks:
      - app_network
    # port 5432 intentionally NOT exposed to host in prod

networks:
  app_network:
    driver: bridge

volumes:
  postgres_data:  # Docker manages the storage location
```

</details>

---

## Step 5 — Write .env.example and .env

`.env.example` is a template with placeholder values. It goes into version control. `.env` has your real secrets. It never goes into version control.

<details>
<summary>💡 Hint</summary>

Create `.env.example` with fake values that show the expected format. Then create `.env` with real values. Make sure `.gitignore` has `.env`.

For `SECRET_KEY`, use a long random string. In a real project: `openssl rand -hex 32`.

</details>

<details>
<summary>✅ Answer</summary>

`.env.example`:
```bash
# Copy this file to .env and fill in real values
# Never commit .env to version control

POSTGRES_USER=appuser
POSTGRES_PASSWORD=changeme
POSTGRES_DB=authdb

# Generate with: openssl rand -hex 32
SECRET_KEY=your-secret-key-here
```

`.env` (your actual file):
```bash
POSTGRES_USER=appuser
POSTGRES_PASSWORD=supersecretpassword123
POSTGRES_DB=authdb
SECRET_KEY=3d6f45a5fc12445dbac2f59c3b6c7cb1d35aa1e3a2f78e67c9b12345abcdef01
```

Add to `.gitignore`:
```
.env
```

</details>

---

## Step 6 — Build and Test Locally

Build the image and start both containers. Watch PostgreSQL health checks pass before the API starts.

<details>
<summary>💡 Hint</summary>

```bash
docker compose up --build
```

Watch for two things in the output:
1. `jwt_postgres` health check passing: look for `healthy` status
2. `jwt_api` starting only after db is healthy

To run detached: `docker compose up --build -d`

Check container status: `docker compose ps`

</details>

<details>
<summary>✅ Answer</summary>

```bash
# Build the image and start all services
docker compose up --build

# Expected output sequence:
# [+] Building ... jwt-api:latest
# [+] Running
#  ✔ Container jwt_postgres  Started
#  - Container jwt_api       Waiting   ← waiting for db health check
#  ✔ Container jwt_api       Started   ← started after db healthy

# Verify both containers are running and healthy:
docker compose ps
```

Expected `docker compose ps` output:
```
NAME            IMAGE              STATUS
jwt_api         jwt-api:latest     Up (healthy)
jwt_postgres    postgres:15-alpine Up (healthy)
```

View logs:
```bash
docker compose logs app    # FastAPI logs
docker compose logs db     # PostgreSQL logs
docker compose logs -f     # follow all logs
```

</details>

---

## Step 7 — Test Auth Endpoints with curl

Register a user, log in to get a token, then call the protected `/me` route with the token.

<details>
<summary>💡 Hint</summary>

The three endpoints:
- `POST /register` — body: `{"username": "...", "password": "..."}`
- `POST /login` — body: same, returns `{"access_token": "...", "token_type": "bearer"}`
- `GET /me` — header: `Authorization: Bearer <token>`

</details>

<details>
<summary>✅ Answer</summary>

```bash
# Register a new user
curl -s -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "secret123"}' | python3 -m json.tool

# Expected:
# {
#     "message": "User registered successfully",
#     "username": "alice"
# }

# Log in and capture the token
TOKEN=$(curl -s -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "secret123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "Token: $TOKEN"

# Call the protected route
curl -s http://localhost:8000/me \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Expected:
# {
#     "username": "alice",
#     "id": 1
# }

# Verify health endpoint
curl -s http://localhost:8000/health
# Expected: {"status": "ok"}
```

Try a bad password — you should get a 401:
```bash
curl -s -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "wrongpassword"}'
# Expected: {"detail": "Invalid credentials"}
```

</details>

---

## Step 8 — Add docker-compose.override.yml for Dev

In development you want **hot reload**: when you save a file, Uvicorn restarts automatically. You do not want this in production. The override file is automatically merged by Compose in dev without touching the base `docker-compose.yml`.

<details>
<summary>💡 Hint</summary>

`docker-compose.override.yml` is auto-loaded when you run `docker compose up`. It merges with `docker-compose.yml`. For prod, you skip it by explicitly specifying the base file.

For hot reload:
- Mount the source directory as a volume into the container
- Add `--reload` flag to the uvicorn command

</details>

<details>
<summary>✅ Answer</summary>

`docker-compose.override.yml`:
```yaml
# Auto-loaded in development. Not used in production.
# Adds hot reload and exposes postgres port for local inspection.

version: "3.9"

services:

  app:
    volumes:
      # Mount source code — changes reflect immediately without rebuild
      - ./src:/app/src
    command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
    environment:
      # Override token expiry for easier dev testing
      ACCESS_TOKEN_EXPIRE_MINUTES: 60

  db:
    ports:
      # Expose postgres to host — lets you inspect with psql or TablePlus
      - "5432:5432"
```

In dev, just run:
```bash
docker compose up  # loads both docker-compose.yml AND docker-compose.override.yml
```

In prod, skip the override:
```bash
docker compose -f docker-compose.yml up
```

Test that hot reload works:
1. Add a new route to `src/main.py`: `@app.get("/ping") def ping(): return {"pong": True}`
2. Save the file
3. Watch Uvicorn restart in the logs
4. `curl http://localhost:8000/ping`

</details>

---

## Step 9 — Tag and Push to Docker Hub

Your image exists locally. To share it or deploy it from any machine, push it to a registry. Docker Hub is the default public registry.

<details>
<summary>💡 Hint</summary>

Docker Hub image names follow the format: `username/repository:tag`

Steps:
1. `docker login`
2. Tag the existing image with your Docker Hub username
3. Push

</details>

<details>
<summary>✅ Answer</summary>

```bash
# Log in to Docker Hub (prompts for username and password/token)
docker login

# Tag the image — replace YOURUSERNAME with your Docker Hub username
docker tag jwt-api:latest YOURUSERNAME/jwt-api:1.0.0
docker tag jwt-api:latest YOURUSERNAME/jwt-api:latest  # also tag as latest

# Push both tags
docker push YOURUSERNAME/jwt-api:1.0.0
docker push YOURUSERNAME/jwt-api:latest

# Verify on Docker Hub:
# https://hub.docker.com/r/YOURUSERNAME/jwt-api
```

Expected push output:
```
The push refers to repository [docker.io/YOURUSERNAME/jwt-api]
1a2b3c4d5e6f: Pushed
7g8h9i0j1k2l: Pushed
1.0.0: digest: sha256:abc123... size: 1234
```

Now anyone (or any server) can run your image:
```bash
docker pull YOURUSERNAME/jwt-api:1.0.0
```

</details>

---

## Step 10 — Run in Production Mode

Production mode: no override file, no hot reload, no postgres port exposed to host, secrets from `--env-file`, no source code volume mount.

<details>
<summary>💡 Hint</summary>

For a single container (no Compose):
```bash
docker run --env-file .env.prod -p 8000:8000 YOURUSERNAME/jwt-api:1.0.0
```

For Compose without override:
```bash
docker compose -f docker-compose.yml up -d
```

</details>

<details>
<summary>✅ Answer</summary>

**Option A: docker run with --env-file (no database, useful for testing the image)**

```bash
# Create a prod env file with real values
cp .env .env.prod
# edit .env.prod — set POSTGRES_PASSWORD and SECRET_KEY to real values

docker run -d \
  --name jwt_api_prod \
  -p 8000:8000 \
  --env-file .env.prod \
  --restart unless-stopped \
  YOURUSERNAME/jwt-api:1.0.0

docker logs jwt_api_prod   # verify it started
docker inspect --format='{{.State.Health.Status}}' jwt_api_prod  # should be "healthy"
```

**Option B: Compose without the override (prod stack with PostgreSQL)**

```bash
# Skip docker-compose.override.yml entirely
docker compose -f docker-compose.yml up -d

docker compose ps         # verify both containers healthy
docker compose logs app   # check for startup errors
```

Differences from dev:
- No source code volume mount — app runs from the baked-in image
- No `--reload` — Uvicorn does not watch for file changes
- PostgreSQL port 5432 is NOT exposed to the host
- Token expiry uses the value from `.env`, not the dev override

```bash
# Clean up
docker compose down          # stop and remove containers
docker compose down -v       # also delete the postgres_data volume (destructive)
```

</details>

---

## 📂 Navigation

⬅️ **Prev:** [06 — Production K8s Cluster](../../05_Capstone_Projects/06_Production_K8s_Cluster/01_MISSION.md) &nbsp;&nbsp; ➡️ **Next:** [08 — E-Commerce API on K8s](../08_Ecommerce_API_K8s/01_MISSION.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
