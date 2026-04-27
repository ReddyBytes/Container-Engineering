# Architecture — JWT Auth API in Docker

## 🗺️ System Overview

Think of Docker Compose as a local data center in a file. Each service is a separate machine. They share a private network and talk to each other by service name, not IP address.

The JWT Auth API has two moving parts: the **FastAPI application** (stateless, handles HTTP) and **PostgreSQL** (stateful, stores users). In Docker Compose, these become two containers on the same bridge network.

---

## Request Flow

```
                        ┌─────────────────────────────────┐
                        │        Docker Host               │
                        │                                 │
  Client (curl/         │   ┌──────────────────────────┐  │
  Postman/browser)      │   │  app_network (bridge)    │  │
       │                │   │                          │  │
       │  :8000         │   │  ┌────────────────────┐  │  │
       └───────────────────►│  │  fastapi container │  │  │
                        │   │  │                    │  │  │
                        │   │  │  /register         │  │  │
                        │   │  │  /login            │  │  │
                        │   │  │  /me (protected)   │  │  │
                        │   │  └────────┬───────────┘  │  │
                        │   │           │               │  │
                        │   │           │  SQLAlchemy   │  │
                        │   │           │  db:5432      │  │
                        │   │           ▼               │  │
                        │   │  ┌────────────────────┐  │  │
                        │   │  │  postgres container │  │  │
                        │   │  │                    │  │  │
                        │   │  │  named volume:     │  │  │
                        │   │  │  postgres_data     │  │  │
                        │   │  └────────────────────┘  │  │
                        │   └──────────────────────────┘  │
                        └─────────────────────────────────┘

  Health check flow:
  Docker daemon ──► GET /health (every 30s) ──► fastapi container
  Docker daemon ──► pg_isready (every 10s)  ──► postgres container
```

**Key networking rule:** The FastAPI app connects to PostgreSQL using `db` as the hostname — the Compose service name. From inside the `app_network`, `db:5432` resolves to the PostgreSQL container's IP. `localhost:5432` does not work between containers.

---

## Multi-Stage Build Layers

The Dockerfile has two stages. The builder stage is disposable — it only exists to compile and install dependencies. The runtime stage is the final image that ships.

```
Stage 1: builder (python:3.12-slim)
┌─────────────────────────────────────┐
│  Base OS layer                      │  ~120MB
│  ├── build-essential (gcc, etc.)    │  ~50MB   ← only needed during build
│  ├── pip install -r requirements    │  ~200MB  ← installs into /install
│  └── /install/  (compiled .so libs) │
└─────────────────────────────────────┘
         │
         │  COPY --from=builder /install /usr/local
         ▼
Stage 2: runtime (python:3.12-slim)
┌─────────────────────────────────────┐
│  Base OS layer                      │  ~120MB
│  ├── /usr/local/  (deps only)       │  ~80MB   ← no build tools
│  └── /app/        (app code only)   │  ~1MB
└─────────────────────────────────────┘
  Final image size: ~200MB vs ~400MB for single-stage
```

**Why this matters:** Build tools like `gcc` are needed to compile Python packages with C extensions (like `psycopg2`). But you do not need `gcc` at runtime. The multi-stage build discards the builder layer entirely — it never appears in the final image.

---

## Docker Compose Network Diagram

```
docker-compose.yml defines:

  services:
    app:  ─────────────────────────────────────────────┐
      image: jwt-api:latest                             │
      ports: "8000:8000"  ◄── exposed to host          │
      depends_on: db (with health condition)            │
      networks: [app_network]  ◄────────────────────┐  │
                                                     │  │
    db:  ─────────────────────────────────────────── │──┘
      image: postgres:15-alpine                       │
      volumes: [postgres_data:/var/lib/postgresql]    │
      networks: [app_network]  ◄────────────────────┘
      (NOT exposed to host in prod)

  networks:
    app_network:
      driver: bridge  ◄── private virtual LAN

  volumes:
    postgres_data:
      driver: local  ◄── persists across container restarts
```

Inside `app_network`, the containers can reach each other by service name. Outside the network (on your laptop), only port 8000 is reachable. The PostgreSQL port 5432 is intentionally not exposed to the host in production.

---

## Environment Variable Hierarchy

Secrets flow from the most specific source down. Docker Compose resolves variables in this order:

```
.env.example  (template, committed to git)
     │
     │  copy and fill in real values
     ▼
.env          (real secrets, gitignored)
     │
     │  docker compose --env-file .env  (or auto-loaded)
     ▼
docker-compose.yml  environment: block
     │
     │  passed into container at runtime
     ▼
Container ENV vars
     │
     │  read by Python: os.getenv("SECRET_KEY")
     ▼
Application

─────────────────────────────────────────
Production alternative: Docker Secrets
─────────────────────────────────────────
docker secret create jwt_secret ./secret.txt
     │
     │  mounted at /run/secrets/jwt_secret
     ▼
Container reads file: open("/run/secrets/jwt_secret").read()
```

**Rule:** Never use `ENV SECRET_KEY=myvalue` in a Dockerfile. That secret is baked into every layer of the image and visible to anyone who runs `docker history`. Always inject secrets at runtime via environment variables or mounted secret files.

---

## Tech Stack

| Component | Version | Role |
|---|---|---|
| FastAPI | 0.111.x | HTTP framework, route handling, request validation |
| Uvicorn | 0.29.x | ASGI server that runs FastAPI |
| SQLAlchemy | 2.x | ORM — maps Python classes to PostgreSQL tables |
| psycopg2-binary | 2.9.x | PostgreSQL driver (psycopg2 compiled for convenience) |
| PyJWT | 2.8.x | Encodes and decodes JWT tokens |
| bcrypt | 4.x | Password hashing — never store plaintext passwords |
| python-dotenv | 1.x | Loads `.env` file into `os.environ` |
| PostgreSQL | 15-alpine | Relational database — alpine variant for smaller image |
| python base image | 3.12-slim | Debian slim — smaller than full, larger than alpine |

**Why `python:3.12-slim` and not `python:3.12-alpine`?** Alpine uses musl libc. `psycopg2` and some other packages require glibc. You would need to add build tools inside the alpine image anyway, negating the size benefit. Slim (Debian) is the pragmatic choice for Python apps with compiled dependencies.

---

## 📂 Navigation

⬅️ **Prev:** [06 — Production K8s Cluster](../../05_Capstone_Projects/06_Production_K8s_Cluster/01_MISSION.md) &nbsp;&nbsp; ➡️ **Next:** [08 — E-Commerce API on K8s](../08_Ecommerce_API_K8s/01_MISSION.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
