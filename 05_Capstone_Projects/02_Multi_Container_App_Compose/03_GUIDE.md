# 03 — Guide: Multi-Container App with Docker Compose

Steps 1–4 have partial guidance. Steps 5–11 are command-driven with expected output shown. Use the hints when you are stuck; try each step yourself first.

---

## ## Step 1 — Set Up Project Structure

```bash
mkdir -p app
touch app/main.py Dockerfile requirements.txt docker-compose.yaml .env
```

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

---

## ## Step 2 — Write the FastAPI App

Create `app/main.py` with three key behaviors:

- `POST /items` — writes a new item to Postgres
- `GET /items` — checks Redis first; on cache miss, queries Postgres, writes result to Redis with a 60-second TTL; the response includes a `"source"` field (`"cache"` or `"database"`)
- `GET /health` — verifies both Postgres and Redis connections are live

<details>
<summary>💡 Hint</summary>

Use FastAPI's `lifespan` context manager to set up connection pools on startup and close them on shutdown:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, redis_client
    db_pool = await asyncpg.create_pool(...)
    redis_client = aioredis.Redis(...)
    yield
    await db_pool.close()
    await redis_client.close()

app = FastAPI(lifespan=lifespan)
```

For Redis caching in `GET /items`:

```python
cached = await redis_client.get("items:all")
if cached:
    return {"items": json.loads(cached), "source": "cache"}
# ... query postgres ...
await redis_client.setex("items:all", CACHE_TTL, json.dumps(items))
return {"items": items, "source": "database"}
```

When you `POST /items`, delete the cache key so the next GET reads fresh data:
```python
await redis_client.delete("items:all")
```

</details>

<details>
<summary>✅ Answer</summary>

See `src/solution.py` for the complete implementation. The key patterns are:

- `asyncpg.create_pool(...)` on startup — pool handles connection reuse
- `conn.execute(CREATE TABLE IF NOT EXISTS ...)` — idempotent schema migration on startup
- `redis_client.get` / `redis_client.setex` / `redis_client.delete` for the cache pattern
- `/health` endpoint does a `SELECT 1` and a `redis_client.ping()` and reports each

</details>

**Expected:** `app/main.py` implemented with all four endpoints.

---

## ## Step 3 — Write docker-compose.yaml

Write a Compose file with three services. You will configure each one yourself — use the hints if you get stuck.

**db service requirements:**
- Image: `postgres:16-alpine`
- Environment vars from `.env`
- Named volume mounted at `/var/lib/postgresql/data`
- Health check using `pg_isready`

**cache service requirements:**
- Image: `redis:7-alpine`
- Command: `redis-server --appendonly yes`
- Named volume mounted at `/data`
- Health check: `redis-cli ping`

**api service requirements:**
- Build from local `Dockerfile`
- Env file: `.env`
- Expose port `8000:8000`
- `depends_on` both `db` and `cache` with `condition: service_healthy`

<details>
<summary>💡 Hint — depends_on syntax</summary>

```yaml
depends_on:
  db:
    condition: service_healthy
  cache:
    condition: service_healthy
```

Without `condition: service_healthy`, Compose only waits for the container to start, not for Postgres to be ready to accept connections. This causes race-condition crashes during `docker compose up`.

</details>

<details>
<summary>💡 Hint — pg_isready healthcheck</summary>

```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 10s
```

`pg_isready` is a Postgres utility that returns exit code 0 when the server is ready to accept connections. It ships inside the `postgres:16-alpine` image.

</details>

<details>
<summary>✅ Answer</summary>

See `src/solution.py` (the Compose config is shown as a comment block at the bottom) or refer to the original `Code_Example.md` in `05_Capstone_Projects/02_Multi_Container_App_Compose/` for the full annotated `docker-compose.yaml`.

</details>

---

## ## Step 4 — Configure .env

Edit `.env` with your values:

```
POSTGRES_USER=appuser
POSTGRES_PASSWORD=supersecret
POSTGRES_DB=appdb
POSTGRES_HOST=db
POSTGRES_PORT=5432
REDIS_HOST=cache
REDIS_PORT=6379
```

The values `db` and `cache` for `POSTGRES_HOST` and `REDIS_HOST` are the Compose service names. On the shared Compose network, these names resolve to the correct container IPs automatically.

**Never commit `.env` to git:**
```bash
echo ".env" >> .gitignore
```

---

## ## Step 5 — Start Everything

```bash
docker compose up -d
```

**Expected output:**
```
[+] Running 4/4
 ✔ Network myapp_app-network   Created
 ✔ Container myapp-db-1        Started
 ✔ Container myapp-cache-1     Started
 ✔ Container myapp-api-1       Started
```

Compose starts `db` and `cache` first, waits for their health checks to pass, then starts `api`.

---

## ## Step 6 — Check Status

```bash
docker compose ps
```

**Expected:**
```
NAME              STATUS         PORTS
myapp-api-1       Up (healthy)   0.0.0.0:8000->8000/tcp
myapp-cache-1     Up (healthy)   6379/tcp
myapp-db-1        Up (healthy)   5432/tcp
```

All three should show `Up (healthy)`. If `api` shows `Up` without `(healthy)`, wait 10 seconds and re-check — the startup health check needs a moment.

If any container shows `Up (unhealthy)`:
```bash
docker compose logs db
docker compose logs cache
docker compose logs api
```

---

## ## Step 7 — Test the API

Create items:
```bash
curl -X POST http://localhost:8000/items \
  -H "Content-Type: application/json" \
  -d '{"name": "keyboard", "price": 149.99}'
```

Fetch all items (first request — expect `"source": "database"`):
```bash
curl http://localhost:8000/items
```

Fetch again immediately (expect `"source": "cache"`):
```bash
curl http://localhost:8000/items
```

Check health:
```bash
curl http://localhost:8000/health
```

**Expected:**
```json
{"status": "ok", "postgres": "connected", "redis": "connected"}
```

---

## ## Step 8 — View Logs

Follow all services:
```bash
docker compose logs -f
```

Follow one service:
```bash
docker compose logs -f api
```

Exit with `Ctrl+C`.

---

## ## Step 9 — Stop the Stack

```bash
docker compose down
```

`docker compose down` does **not** delete named volumes. Your Postgres data survives.

---

## ## Step 10 — Verify Data Survived Restart

Bring the stack back up:
```bash
docker compose up -d
```

Fetch items:
```bash
curl http://localhost:8000/items
```

**Expected:** your items from Step 7 are still there. The `postgres-data` named volume preserved them across the restart.

To destroy the data:
```bash
docker compose down -v
```

The `-v` flag removes named volumes. This is permanent.

---

## ## Step 11 — Dev Mode with docker-compose.override.yml

Create `docker-compose.override.yml`:

```yaml
services:
  api:
    volumes:
      - ./app:/app/app   # ← bind mount — code changes visible instantly
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    environment:
      LOG_LEVEL: debug
```

Compose merges override files automatically. Restart:
```bash
docker compose up -d
```

Edit `app/main.py`. Watch the container reload:
```bash
docker compose logs -f api
```

**Expected:**
```
WARNING:  StatReload detected changes in 'app/main.py'. Reloading...
INFO:     Application startup complete.
```

Never ship the override file to CI or production. It is for local development only.

---

## ## Cleanup

```bash
docker compose down -v
docker rmi myapp-api
```

---

⬅️ **Prev:** [01 — Dockerize a Python App](../01_Dockerize_a_Python_App/01_MISSION.md) &nbsp;&nbsp; ➡️ **Next:** [03 — Deploy App to Kubernetes](../03_Deploy_App_to_Kubernetes/01_MISSION.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
