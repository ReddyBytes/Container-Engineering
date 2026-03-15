# Docker Compose — Interview Q&A

## Beginner

**Q1: What is Docker Compose and why would you use it?**

Docker Compose is a tool for defining and running multi-container Docker applications. You describe your entire application stack — services, networks, volumes — in a single YAML file (`docker-compose.yaml`), then bring the whole stack up or down with one command.

Without Compose, running a multi-container app requires multiple `docker run` commands with carefully coordinated flags, network names, and volume names. It's error-prone, hard to document, and impossible to share reliably.

With Compose:
- The stack is defined as code — version-controlled alongside your application
- Any developer can run `docker compose up` to get a complete, correctly-configured environment
- `docker compose down` cleanly removes everything Compose created
- Environment differences (dev vs prod) can be handled with override files and profiles

Compose is standard for local development. It's also used in CI pipelines and smaller production deployments (for large-scale production, Kubernetes is more appropriate).

---

**Q2: What is the difference between `docker compose up` and `docker compose start`?**

`docker compose up`:
- Creates networks and volumes if they don't exist
- Builds images if `build:` is specified and the image doesn't exist
- Creates containers from the service configurations
- Starts all containers
- In the foreground by default (pass `-d` for detached)
- Shows logs from all services

`docker compose start`:
- Only starts containers that already exist but are stopped
- Does NOT create new containers, networks, or volumes
- Use it to resume a stack that was stopped with `docker compose stop`

In practice, you almost always use `docker compose up`. `docker compose start` is for the specific case of resuming a stopped (not down'd) stack.

---

**Q3: What is the difference between `docker compose down` and `docker compose stop`?**

`docker compose stop`:
- Sends SIGTERM to running containers, waits for them to stop
- Containers are stopped but NOT removed (they're in "exited" state)
- Networks and volumes are preserved
- Use to temporarily pause a stack — `docker compose start` to resume

`docker compose down`:
- Stops containers AND removes them
- Removes the networks Compose created
- Does NOT remove volumes by default (use `-v` flag to remove volumes)
- Removes any anonymous volumes created by the containers

The key distinction: `stop` is reversible with `start`. `down` removes containers — you'd need `up` to recreate them. Volumes are kept after `down` to prevent accidental data loss (you have to explicitly pass `-v` to nuke them).

---

**Q4: How does service discovery work in Docker Compose? How does the web service find the db service?**

When Compose starts your services, it automatically creates a user-defined bridge network for the project (named `<project>_default`). All services are attached to this network.

Docker's embedded DNS server (`127.0.0.11`) runs inside each container and resolves other container names on the same network. The service name in `docker-compose.yaml` becomes the DNS hostname.

```yaml
services:
  web:
    image: myapp
    environment:
      DATABASE_URL: postgresql://db:5432/mydb  # 'db' = service name = hostname
  db:
    image: postgres:16
```

Inside the `web` container, `db` resolves to the IP address of the `db` container. If Postgres restarts and gets a new IP, the DNS answer updates automatically — no reconfiguration needed in the app.

---

## Intermediate

**Q5: Explain the `depends_on` limitation and how to properly wait for a service to be ready.**

`depends_on` with just a service name waits for the **container to start**, not for the service inside it to be ready. This is a critical distinction:

```yaml
# This is WRONG — only waits for postgres container to start,
# not for postgres to finish initializing its data directory
web:
  depends_on:
    - db
```

When Postgres starts from scratch, it takes 5-10 seconds to initialize. The `web` service might start immediately after the container begins, before Postgres is ready to accept connections.

**The correct pattern** — combine `condition: service_healthy` with a `healthcheck`:

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: secret
    healthcheck:
      # pg_isready exits 0 when Postgres is ready to accept connections
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 10
      start_period: 15s   # grace period before failures count

  web:
    image: myapp
    depends_on:
      db:
        condition: service_healthy   # waits for pg_isready to pass
```

Now Compose ensures `db` passes its health check before starting `web`. No race conditions.

**Note:** `condition: service_healthy` only works when the dependency has a `healthcheck` defined. If there's no healthcheck, you'll get an error.

---

**Q6: How do you handle different configurations for development vs production in Docker Compose?**

The recommended approach is the **override file pattern**:

**`docker-compose.yaml`** — base config, production-ready, version-controlled:
```yaml
services:
  web:
    image: myapp:${APP_VERSION:-latest}
    restart: unless-stopped
    ports:
      - "80:8080"
    environment:
      APP_ENV: production
```

**`docker-compose.override.yml`** — dev overrides, automatically merged, typically gitignored:
```yaml
services:
  web:
    build: .                        # build from source in dev
    image: myapp:dev
    ports:
      - "8080:8080"                 # different port in dev
    volumes:
      - ./src:/app/src              # hot-reload
    environment:
      APP_ENV: development
      DEBUG: "true"
    restart: "no"                   # don't auto-restart in dev
```

```bash
docker compose up          # merges both files automatically
docker compose config      # shows the merged result
```

For production-specific file:
```bash
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d
```

This keeps a clean separation: the base file describes what the service IS, the override files describe what's different per environment.

---

**Q7: What is the difference between `.env` file substitution and `env_file` in Docker Compose?**

These are two different mechanisms that are often confused:

**`.env` file** (project-level, variable substitution in YAML):
- Automatically loaded by `docker compose` when present in the same directory
- Variables are used for **substituting `${VAR}` expressions in the YAML file**
- The variables themselves are not automatically injected into containers
- Example: `APP_VERSION=1.2.3` in `.env` makes `image: myapp:${APP_VERSION}` resolve to `myapp:1.2.3`

**`env_file:` directive** (service-level, container environment injection):
- Explicitly listed in the service configuration
- All `KEY=VALUE` pairs in the file are injected as **environment variables into the container**
- The Compose YAML doesn't see these — they go straight to the container at runtime
- Example: `DATABASE_URL=postgresql://...` in `.env.production` → `process.env.DATABASE_URL` inside the container

```yaml
# .env file (substitution)
IMAGE_TAG=1.2.3

services:
  web:
    image: myapp:${IMAGE_TAG}        # .env substitution → myapp:1.2.3
    env_file:
      - .env.runtime                 # these vars go INTO the container
    environment:
      ALWAYS_THIS: "value"           # inline, highest priority
```

---

## Advanced

**Q8: A Compose stack has a web service that keeps failing because the database isn't ready. You've added `depends_on` with `condition: service_healthy`, but the web service still fails sometimes. What else could be wrong?**

Several possible issues:

1. **The `healthcheck` start_period is too short.** On a slow machine or first run (when Postgres is initializing data directory), Postgres might take longer than `start_period` to become ready. The health check starts counting failures after `start_period`, so if the period is 10s but Postgres takes 15s, you'll see failures. Fix: increase `start_period`.

2. **The `retries` count is too low.** If `retries: 3` and each retry is `interval: 5s`, the total wait time is 15 seconds. If Postgres needs 20 seconds, Compose gives up and marks it unhealthy before it's actually ready.

3. **The healthcheck command itself is wrong.** Verify the health check command works:
   ```bash
   docker exec my-db pg_isready -U postgres
   # Exit code 0 = ready
   ```

4. **The `healthcheck` is defined at the image level, not overridden.** If the `postgres` image has a built-in healthcheck that uses `pg_isready`, your Compose definition might override it incorrectly.

5. **Application-level readiness vs network readiness.** `pg_isready` only checks that Postgres is accepting TCP connections. But the database might not have run migrations, or the specific database/user might not exist yet. For application readiness, consider using a startup probe in the web service itself (retry logic with exponential backoff) rather than relying entirely on `depends_on`.

6. **Restart policy conflict.** If `depends_on` is satisfied, the web container starts and immediately crashes due to a different config error. The crash looks like a DB connection issue. Check `docker compose logs web` for the actual error.

---

**Q9: What is the `docker compose run` command used for? How is it different from `docker compose exec`?**

`docker compose run SERVICE COMMAND` starts a **new** container from the service's configuration, runs the command, and exits. It doesn't require the service to already be running.

`docker compose exec SERVICE COMMAND` runs a command inside a **currently running** service container.

Typical uses of `docker compose run`:

```bash
# Run database migrations (service doesn't need to be running)
docker compose run --rm web python manage.py migrate

# Run tests
docker compose run --rm web pytest

# Open a shell for debugging before services start
docker compose run --rm web bash

# Run a one-off admin script
docker compose run --rm web python scripts/seed_data.py
```

`--rm` is important with `run` — without it, Compose creates a new container that persists in stopped state, accumulating over time.

Note: `docker compose run` starts any declared `depends_on` services (if not already running), so `docker compose run --rm web pytest` will start the database first if needed.

---

**Q10: How would you implement a health check for a non-HTTP service like Redis in Docker Compose?**

```yaml
services:
  redis:
    image: redis:7
    healthcheck:
      # redis-cli ping returns "PONG" and exits 0 when Redis is healthy
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 5s

  # For a MySQL database:
  mysql:
    image: mysql:8
    environment:
      MYSQL_ROOT_PASSWORD: secret
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "--silent"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

  # For a service with no built-in health command (use nc or wget):
  custom-tcp-service:
    image: myservice:latest
    healthcheck:
      test: ["CMD-SHELL", "nc -z localhost 9090 || exit 1"]
      interval: 10s
      timeout: 3s
      retries: 3

  # Any service can use a shell command for flexibility:
  worker:
    image: myworker:latest
    healthcheck:
      test: ["CMD-SHELL", "test -f /tmp/healthy || exit 1"]
      # App creates /tmp/healthy when it's ready, removes on shutdown
```

The health check command should:
- Return exit code 0 when healthy
- Return non-zero exit code when unhealthy
- Complete quickly (within `timeout`)

---

**Q11: What is the Compose project name and how does it affect resource naming?**

Every Docker Compose stack belongs to a **project**. By default, the project name is the name of the directory containing the `docker-compose.yaml` file.

The project name is prepended to all resources Compose creates:
- Containers: `<project>-<service>-<replica>` (e.g., `myapp-web-1`)
- Networks: `<project>_<network>` (e.g., `myapp_default`)
- Volumes: `<project>_<volume>` (e.g., `myapp_pgdata`)

Why this matters:
- If two projects in different directories both define a volume named `pgdata`, they get `project1_pgdata` and `project2_pgdata` — no conflict
- `docker compose down` only affects containers/networks/volumes with the current project prefix — doesn't touch other projects

Override the project name:
```bash
# Using CLI flag
docker compose -p myproject up

# Using environment variable
COMPOSE_PROJECT_NAME=myproject docker compose up

# Using .env file
echo "COMPOSE_PROJECT_NAME=myproject" >> .env
```

Useful when: running the same Compose file multiple times in different environments (staging vs prod on the same machine), or when the default directory name would conflict with another project.

---

## 📂 Navigation

**In this folder:**
| File | |
|---|---|
| [📖 Theory.md](./Theory.md) | Full explanation |
| [⚡ Cheatsheet.md](./Cheatsheet.md) | Quick reference |
| 🎯 **Interview_QA.md** | ← you are here |
| [💻 Code_Example.md](./Code_Example.md) | Working code |

⬅️ **Prev:** [08 — Networking](../08_Networking/Interview_QA.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [10 — Docker Registry](../10_Docker_Registry/Interview_QA.md)
🏠 **[Home](../../README.md)**
