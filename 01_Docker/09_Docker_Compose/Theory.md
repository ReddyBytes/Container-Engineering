# Docker Compose

## The Story: Orchestrating a Band vs One Musician

Imagine you're at a jazz concert. One musician — a solo pianist — is straightforward. You just tell them to start playing. But a full band? You need a drummer, bassist, guitarist, vocalist, and horn section. They need to start in the right order (drummer sets the tempo first), play in the same key, and know when to stop together. One person trying to coordinate all of that with separate instructions to each musician would be chaos.

Docker Compose is the conductor for your containerized application. Instead of running five separate `docker run` commands with different flags, different network names, and different volume configurations — hoping you remember to do it in the right order — you write one `docker-compose.yaml` file that describes the whole band. Then you say `docker compose up`, and every service starts, configured correctly, connected to the right network, with the right volumes.

This is why teams adopt Docker Compose immediately after learning basic Docker. It's not a separate product — it's the natural next step for anything beyond a single container.

---

## 📌 Learning Priority

**Must Learn** — core concepts, needed to understand the rest of this file:
[Compose File Structure](#docker-composeyaml-structure) · [Service Configuration](#service-configuration-deep-dive) · [depends_on and Readiness](#depends_on--start-order-vs-readiness)

**Should Learn** — important for real projects and interviews:
[Compose Commands](#compose-commands) · [Networks in Compose](#networks-in-compose) · [Environment Variables](#environment-variables-in-compose)

**Good to Know** — useful in specific situations, not needed daily:
[Compose Profiles](#compose-profiles) · [Compose Overrides](#compose-overrides)

**Reference** — skim once, look up when needed:
[Volumes in Compose](#volumes-in-compose) · [Compose Stack Diagram](#the-mermaid-view-of-a-compose-stack)

---

## What Compose Solves

Before Compose, running a three-service application meant:

```bash
# Had to remember all of this, in this order, every time
docker network create myapp-net
docker volume create pgdata

docker run -d \
  --name postgres \
  --network myapp-net \
  -v pgdata:/var/lib/postgresql/data \
  -e POSTGRES_PASSWORD=secret \
  postgres:16

docker run -d \
  --name redis \
  --network myapp-net \
  redis:7

docker run -d \
  --name web \
  --network myapp-net \
  -p 8080:8080 \
  -e DATABASE_URL=postgresql://postgres:secret@postgres:5432/mydb \
  -e REDIS_URL=redis://redis:6379 \
  myapp:latest
```

With Compose:

```bash
docker compose up -d
# That's it. All three services, configured correctly.
```

---

## docker-compose.yaml Structure

The Compose file has four top-level sections:

```yaml
# The Compose spec (modern format — no 'version' needed with Compose v2)
services:       # containers to run
networks:       # networks to create
volumes:        # volumes to create
configs:        # configs to inject (Swarm feature)
```

---

## Service Configuration Deep Dive

Each service under `services:` is the Compose equivalent of a `docker run` command. Here's the mapping:

```yaml
services:
  web:
    # image: the Docker image to use (alternative to 'build')
    image: nginx:1.25

    # build: build from a Dockerfile instead of pulling an image
    build:
      context: ./web             # path to build context
      dockerfile: Dockerfile     # Dockerfile name (default: "Dockerfile")
      args:
        APP_VERSION: "1.0.0"

    # container_name: set a fixed name (optional — Compose auto-names otherwise)
    container_name: my-web

    # ports: publish ports (host:container)
    ports:
      - "8080:80"
      - "443:443"

    # environment: set environment variables
    environment:
      APP_ENV: production
      DATABASE_URL: postgresql://user:pass@db:5432/mydb

    # env_file: load variables from a file
    env_file:
      - .env
      - .env.production

    # volumes: mount volumes or bind mounts
    volumes:
      - mydata:/data                      # named volume
      - ./config:/etc/myapp:ro            # bind mount (read-only)
      - type: tmpfs                       # tmpfs (long form)
        target: /tmp

    # networks: connect to specific networks
    networks:
      - frontend
      - backend

    # depends_on: start order dependency
    depends_on:
      db:
        condition: service_healthy    # wait for db health check

    # restart: restart policy
    restart: unless-stopped

    # healthcheck: how to test if this service is healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s

    # command: override the Dockerfile CMD
    command: gunicorn --workers 4 app:app

    # entrypoint: override the Dockerfile ENTRYPOINT
    entrypoint: ["/docker-entrypoint.sh"]

    # user: run as a specific user
    user: "1001:1001"

    # working_dir: override WORKDIR
    working_dir: /app

    # labels: attach metadata
    labels:
      com.example.service: "web"

    # logging: configure log driver
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

    # deploy: swarm/scale options
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: "0.5"
          memory: 512M
```

---

## `depends_on` — Start Order vs Readiness

`depends_on` is one of the most misunderstood Compose features. Understanding it prevents a whole class of startup bugs.

### The Misunderstanding

```yaml
services:
  web:
    depends_on:
      - db
```

Many developers read this as "web waits for db to be ready." **This is wrong.** `depends_on` with only the service name waits for the **container to start** (i.e., the Docker process to exist), not for the service inside it to be ready. Postgres might take 5 seconds to initialize its data directory. The web container starts right away and immediately crashes with "connection refused."

### The Correct Pattern

Use `condition: service_healthy` combined with a `healthcheck` on the dependency:

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: secret
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5
      start_period: 10s     # give Postgres 10s to start before failures count

  web:
    image: myapp:latest
    depends_on:
      db:
        condition: service_healthy   # wait until db passes its healthcheck
```

Now Compose waits for Postgres to pass `pg_isready` before starting the web container.

---

## Networks in Compose

By default, Compose creates one network for your project and connects all services to it. Services can reach each other by service name (automatic DNS, same as user-defined bridge networks).

You can define multiple networks for isolation:

```yaml
services:
  frontend:
    networks:
      - public

  api:
    networks:
      - public
      - private

  db:
    networks:
      - private

networks:
  public:
    driver: bridge
  private:
    driver: bridge
    internal: true      # no outbound internet access
```

---

## Volumes in Compose

Named volumes must be declared at the top level:

```yaml
services:
  db:
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:                         # minimal: Docker manages everything
    driver: local                 # explicit driver (local is default)

  pgdata-external:
    external: true                # volume was created outside Compose — don't manage it
    name: my-existing-pgdata
```

---

## The Mermaid View of a Compose Stack

```mermaid
graph TD
    subgraph ComposeStack["Docker Compose Stack: myapp"]
        direction TB

        subgraph PublicNet["Network: public-net"]
            NGINX["nginx service\n:80, :443"]
            API["api service\n:8000"]
        end

        subgraph PrivateNet["Network: private-net"]
            API2["api service\n(also on private)"]
            DB["postgres service"]
            REDIS["redis service"]
        end

        VOL_PG["Volume: pgdata\n(postgres data)"]
        VOL_REDIS["Volume: redis-data\n(redis data)"]
    end

    USER["🌐 User\nport 80/443"] --> NGINX
    NGINX --> API
    API2 --> DB
    API2 --> REDIS
    DB --> VOL_PG
    REDIS --> VOL_REDIS

    note1["API connects both networks\n(bridges public ↔ private)"]
```

---

## Compose Commands

```bash
# Start all services (build if needed)
docker compose up

# Start detached (background)
docker compose up -d

# Start and force rebuild images
docker compose up -d --build

# Stop and remove containers + networks (keep volumes)
docker compose down

# Stop and remove everything including volumes (DATA LOSS!)
docker compose down -v

# View running services
docker compose ps

# View logs from all services
docker compose logs

# Follow logs from a specific service
docker compose logs -f web

# Exec into a running service container
docker compose exec web bash
docker compose exec db psql -U postgres

# Run a one-off command (new container, same config)
docker compose run --rm web python manage.py migrate

# Scale a service
docker compose up -d --scale web=3

# Pull latest images for all services
docker compose pull

# Build images
docker compose build
docker compose build --no-cache web

# Show configuration (merged, resolved)
docker compose config

# Restart a specific service
docker compose restart web
```

---

## Environment Variables in Compose

Compose has a layered approach to environment variable injection:

### 1. `.env` File (Project-level defaults)

A `.env` file in the same directory as your `docker-compose.yaml` is automatically loaded by Compose. Variables defined here are used for **variable substitution in the yaml file itself**:

```bash
# .env
APP_VERSION=1.2.3
POSTGRES_PASSWORD=mysecretpassword
WEB_PORT=8080
```

```yaml
# docker-compose.yaml
services:
  web:
    image: myapp:${APP_VERSION}      # substituted from .env
    ports:
      - "${WEB_PORT}:8080"
  db:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}  # substituted from .env
```

### 2. `env_file` directive (Per-service environment injection)

```yaml
services:
  web:
    env_file:
      - .env              # load all KEY=VALUE pairs as container env vars
      - .env.production   # additional file (values here override .env)
```

### 3. `environment` directive (Inline, highest priority)

```yaml
services:
  web:
    environment:
      APP_ENV: production    # always this value, can't be overridden from file
      PORT: 8080
```

Priority (highest to lowest): `environment` directive > `env_file` > `.env` file.

---

## Compose Profiles

Profiles let you run subsets of services. Useful for services only needed in certain environments (e.g., a test database, a debug tool):

```yaml
services:
  web:
    image: myapp:latest           # no profile = always started

  db:
    image: postgres:16
    profiles: ["backend"]         # only starts when 'backend' profile is active

  pgadmin:
    image: dpage/pgadmin4
    profiles: ["tools"]           # only starts when 'tools' profile is active
```

```bash
docker compose up                           # starts only 'web'
docker compose --profile backend up         # starts 'web' and 'db'
docker compose --profile backend --profile tools up   # all three
```

---

## Compose Overrides

`docker-compose.override.yml` is automatically merged with `docker-compose.yaml` when you run `docker compose up`. This is the standard pattern for dev vs prod differences:

**`docker-compose.yaml`** (production config — version controlled)
```yaml
services:
  web:
    image: myapp:${APP_VERSION}
    restart: unless-stopped

  db:
    image: postgres:16
    volumes:
      - pgdata:/var/lib/postgresql/data
```

**`docker-compose.override.yml`** (dev overrides — gitignored)
```yaml
services:
  web:
    build: .                          # build from source in dev
    volumes:
      - ./src:/app/src                # hot-reload source code
    environment:
      APP_ENV: development
      DEBUG: "true"

  db:
    ports:
      - "5432:5432"                   # expose db port for local debugging
```

For staging/production explicit override:
```bash
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d
```

---

## Summary

- Compose turns multi-container setup from many manual commands into a single `docker compose up`.
- `docker-compose.yaml` defines services, networks, and volumes declaratively.
- `depends_on` with `condition: service_healthy` is the correct way to wait for service readiness (not just container start).
- All services on the default Compose network can reach each other by service name.
- `.env` substitutes variables in the yaml; `env_file` injects variables into containers.
- Profiles allow subsets of services for different environments.
- `docker-compose.override.yml` is automatically merged — great for dev-specific settings.
- `docker compose down -v` removes volumes (destroys database data). Never use in production without understanding the implications.



---

## 📝 Practice Questions

- 📝 [Q62 · docker-compose-depends-on](../docker_practice_questions_100.md#q62--thinking--docker-compose-depends-on)
- 📝 [Q75 · docker-compose-profiles](../docker_practice_questions_100.md#q75--thinking--docker-compose-profiles)
- 📝 [Q83 · scenario-compose-migration](../docker_practice_questions_100.md#q83--design--scenario-compose-migration)
- 📝 [Q85 · scenario-startup-order](../docker_practice_questions_100.md#q85--design--scenario-startup-order)


---

🚀 **Apply this:** Wire up a multi-container stack → [Project 02 — Multi-Container App with Compose](../../05_Capstone_Projects/02_Multi_Container_App_Compose/01_MISSION.md)
## 📂 Navigation

**In this folder:**
| File | |
|---|---|
| 📖 **Theory.md** | ← you are here |
| [⚡ Cheatsheet.md](./Cheatsheet.md) | Quick reference |
| [🎯 Interview_QA.md](./Interview_QA.md) | Interview prep |
| [💻 Code_Example.md](./Code_Example.md) | Working code |

⬅️ **Prev:** [08 — Networking](../08_Networking/Theory.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [10 — Docker Registry](../10_Docker_Registry/Theory.md)
🏠 **[Home](../../README.md)**
