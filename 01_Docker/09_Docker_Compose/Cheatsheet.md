# Docker Compose — Cheatsheet

## Core Commands

```bash
# Start all services
docker compose up                          # foreground, shows logs
docker compose up -d                       # detached (background)
docker compose up -d --build               # force rebuild images before starting

# Stop
docker compose stop                        # stop containers (keep them)
docker compose down                        # stop + remove containers + networks
docker compose down -v                     # + remove named volumes (DATA LOSS!)
docker compose down --rmi all              # + remove images built by Compose

# Status
docker compose ps                          # list service containers
docker compose ps --services               # list just service names

# Logs
docker compose logs                        # all services
docker compose logs web                    # specific service
docker compose logs -f web                 # follow
docker compose logs --tail 50 web         # last 50 lines
docker compose logs -t web                 # with timestamps

# Exec / run
docker compose exec SERVICE COMMAND        # exec in running container
docker compose exec web bash
docker compose exec db psql -U postgres
docker compose run --rm SERVICE COMMAND    # one-off container with same config

# Build
docker compose build                       # build all images
docker compose build web                   # build specific service
docker compose build --no-cache web        # no cache
docker compose pull                        # pull latest images

# Scale
docker compose up -d --scale web=3        # run 3 web containers

# Other
docker compose config                      # show resolved config
docker compose config --services           # list service names
docker compose restart web                 # restart a service
docker compose top                         # running processes
docker compose events                      # real-time events
```

---

## docker-compose.yaml Structure

```yaml
# Top-level sections
services: {}   # container definitions
networks: {}   # network definitions (optional, auto-created if omitted)
volumes: {}    # named volume definitions (must declare if used)
configs: {}    # Swarm configs (optional)
secrets: {}    # Swarm secrets (optional)
```

---

## Service Keys Reference

```yaml
services:
  myservice:
    image: nginx:1.25                  # pull this image
    build: ./path                      # or build from Dockerfile
    build:
      context: ./path
      dockerfile: Dockerfile.prod
      args:
        VERSION: "1.0"
    container_name: my-nginx          # fixed name (skip for multiple replicas)
    restart: unless-stopped           # no | always | on-failure | unless-stopped
    ports:
      - "8080:80"                     # HOST:CONTAINER
      - "127.0.0.1:8081:80"          # bind to specific host IP
    expose:
      - "8080"                        # expose to other services, not host
    environment:
      KEY: value
      KEY2: ${VARIABLE}              # from .env file
    env_file:
      - .env
      - .env.local
    volumes:
      - myvolume:/data               # named volume
      - ./local:/container:ro        # bind mount (read-only)
      - type: tmpfs                  # tmpfs
        target: /tmp
    networks:
      - mynet
    depends_on:
      other-service:
        condition: service_healthy   # or: service_started | service_completed_successfully
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    command: ["python", "app.py"]    # override CMD
    entrypoint: ["/init.sh"]         # override ENTRYPOINT
    user: "1001:1001"
    working_dir: /app
    labels:
      com.example.type: "web"
    profiles:
      - dev                          # only start with --profile dev
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: "0.5"
          memory: 256M
```

---

## Networks and Volumes Sections

```yaml
networks:
  default:                    # override the auto-created default network
    driver: bridge

  mynet:
    driver: bridge
    ipam:
      config:
        - subnet: "172.28.0.0/16"

  internal-net:
    internal: true            # no outbound internet access

  existing-net:
    external: true            # use a network created outside Compose
    name: my-existing-network

volumes:
  mydata:                     # minimal — Docker manages it
  mydata2:
    driver: local
    driver_opts:
      type: nfs
      o: addr=nfs-server,rw
      device: ":/exports/data"
  external-vol:
    external: true            # created outside Compose — don't manage
    name: my-existing-volume
```

---

## Environment Variables Priority

| Source | Priority | Use for |
|---|---|---|
| `environment:` in YAML | Highest | Service-specific, always-set values |
| `env_file:` files | Middle | Bulk injection from files |
| `.env` file | Lowest | Variable substitution in YAML, default values |
| Shell environment | Highest (for substitution) | CI/CD runtime values |

Note: `.env` is for **YAML substitution** (`${VAR}` in yaml), while `env_file` injects into the **container**.

---

## `depends_on` Conditions

```yaml
depends_on:
  service-name:
    condition: service_started         # container started (default — weak)
    condition: service_healthy         # passed health check (use this!)
    condition: service_completed_successfully  # exited with code 0 (one-time jobs)
```

---

## Override Files

```bash
# Automatic merge (always applied)
docker compose up              # loads: docker-compose.yaml + docker-compose.override.yml

# Explicit file specification
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d

# Multiple environments
docker compose -f base.yaml -f staging.yaml up
```

---

## Profiles

```bash
docker compose --profile dev up          # start services with profile 'dev'
docker compose --profile dev --profile tools up   # multiple profiles
COMPOSE_PROFILES=dev,tools docker compose up      # via env var
```

---

## 📂 Navigation

**In this folder:**
| File | |
|---|---|
| [📖 Theory.md](./Theory.md) | Full explanation |
| ⚡ **Cheatsheet.md** | ← you are here |
| [🎯 Interview_QA.md](./Interview_QA.md) | Interview prep |
| [💻 Code_Example.md](./Code_Example.md) | Working code |

⬅️ **Prev:** [08 — Networking](../08_Networking/Cheatsheet.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [10 — Docker Registry](../10_Docker_Registry/Cheatsheet.md)
🏠 **[Home](../../README.md)**
