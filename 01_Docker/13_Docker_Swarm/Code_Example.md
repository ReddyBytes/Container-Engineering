# Docker Swarm — Code Examples

---

## Example 1: Initialize Swarm and Add Workers

```bash
#!/bin/bash
# Run this on the machine that will be your first manager

# ============================================================
# Step 1: Initialize the Swarm
# ============================================================
docker swarm init --advertise-addr $(hostname -I | awk '{print $1}')
# Output includes a join token like:
# docker swarm join --token SWMTKN-1-abc123... 192.168.1.10:2377

# ============================================================
# Step 2: Save the worker join token
# ============================================================
WORKER_TOKEN=$(docker swarm join-token worker -q)
echo "Worker join command:"
echo "docker swarm join --token $WORKER_TOKEN $(hostname -I | awk '{print $1}'):2377"

# ============================================================
# Step 3: On each worker machine, run:
# (In practice, SSH into each worker and run this)
# ============================================================
# docker swarm join --token SWMTKN-1-abc123 192.168.1.10:2377

# ============================================================
# Step 4: Verify the cluster from the manager
# ============================================================
docker node ls
# ID                      HOSTNAME      STATUS   AVAILABILITY  MANAGER STATUS
# k3l9abcdef123 *         manager-1     Ready    Active        Leader
# m4n5ghijkl456           worker-1      Ready    Active
# o6p7mnopqr789           worker-2      Ready    Active
```

---

## Example 2: Create a Replicated Service and Scale It

```bash
# ============================================================
# Create a simple nginx service with 3 replicas
# ============================================================
docker service create \
  --name web \
  --replicas 3 \
  --publish 80:80 \
  --constraint "node.role == worker" \
  nginx:1.25

# Check service status
docker service ls
# NAME   MODE         REPLICAS  IMAGE       PORTS
# web    replicated   3/3       nginx:1.25  *:80->80/tcp

# See which nodes are running which tasks
docker service ps web
# ID           NAME    IMAGE       NODE       STATE    DESIRED STATE
# abc123def    web.1   nginx:1.25  worker-1   Running  Running
# ghi456jkl    web.2   nginx:1.25  worker-2   Running  Running
# mno789pqr    web.3   nginx:1.25  worker-1   Running  Running

# ============================================================
# Scale up to 5 replicas
# ============================================================
docker service scale web=5

# Scale down to 2
docker service scale web=2

# Scale multiple services at once
docker service scale web=4 api=3
```

---

## Example 3: Rolling Update

```bash
# ============================================================
# Perform a zero-downtime rolling update
# Replaces one replica at a time, waits between each
# ============================================================

# First, check current state
docker service inspect --pretty web

# ============================================================
# Update to a new image version
# --update-parallelism 1  = update 1 replica at a time
# --update-delay 15s      = wait 15 seconds between each
# --update-failure-action rollback = auto-rollback if health check fails
# ============================================================
docker service update \
  --image nginx:1.26 \
  --update-parallelism 1 \
  --update-delay 15s \
  --update-failure-action rollback \
  web

# Watch the rolling update progress in real-time
watch docker service ps web
# You'll see replicas cycling through: Shutdown → Running

# ============================================================
# If something goes wrong, manually rollback
# ============================================================
docker service rollback web
```

---

## Example 4: Deploy a Full Application Stack

### docker-compose.yml

```yaml
version: "3.9"

services:
  # Frontend nginx serving static files
  web:
    image: my-org/frontend:v1.0.0
    ports:
      - "80:80"
      - "443:443"
    networks:
      - frontend
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
        failure_action: rollback
        order: start-first        # Start new replica before killing old one
      rollback_config:
        parallelism: 1
        delay: 5s
      restart_policy:
        condition: on-failure
        max_attempts: 3
      resources:
        limits:
          cpus: "0.5"
          memory: 128M
      placement:
        constraints:
          - node.role == worker

  # API backend
  api:
    image: my-org/api:v1.0.0
    networks:
      - frontend
      - backend
    environment:
      - NODE_ENV=production
      - PORT=3000
    secrets:
      - db_password
      - jwt_secret
    deploy:
      replicas: 2
      update_config:
        parallelism: 1
        delay: 15s
        failure_action: rollback
      restart_policy:
        condition: on-failure
      resources:
        limits:
          cpus: "1.0"
          memory: 512M

  # PostgreSQL database (single replica — use external DB in production)
  db:
    image: postgres:16-alpine
    networks:
      - backend
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: myuser
    secrets:
      - db_password
    volumes:
      - pgdata:/var/lib/postgresql/data
    deploy:
      replicas: 1
      placement:
        constraints:
          - node.labels.db == true   # Pin to a specific node with SSD
      restart_policy:
        condition: on-failure

networks:
  frontend:
    driver: overlay
  backend:
    driver: overlay
    attachable: false   # Prevent ad-hoc containers from joining

volumes:
  pgdata:
    driver: local

secrets:
  db_password:
    external: true   # Created beforehand with: docker secret create db_password
  jwt_secret:
    external: true
```

### Deploy Commands

```bash
# ============================================================
# Pre-deploy: create secrets (do this ONCE)
# ============================================================
echo "postgres_password_here" | docker secret create db_password -
echo "jwt_secret_here" | docker secret create jwt_secret -

# Optionally label a node for the DB
docker node update --label-add db=true worker-2

# ============================================================
# Deploy the stack
# ============================================================
docker stack deploy -c docker-compose.yml my-app

# Monitor deployment progress
watch docker stack ps my-app

# ============================================================
# Inspect the running stack
# ============================================================
docker stack ls
docker stack services my-app
docker stack ps my-app

# View logs from a specific service
docker service logs -f my-app_api

# ============================================================
# Update the API service image
# ============================================================
docker service update --image my-org/api:v1.1.0 my-app_api

# Or re-deploy the full stack after editing docker-compose.yml
docker stack deploy -c docker-compose.yml my-app

# ============================================================
# Scale specific services
# ============================================================
docker service scale my-app_web=5 my-app_api=4

# ============================================================
# Tear down the stack
# ============================================================
docker stack rm my-app
# Note: volumes and secrets are NOT removed — data is preserved
```

---

## Example 5: Swarm Health Check and Self-Healing Demo

```bash
# ============================================================
# Create a service with a health check
# Swarm will restart tasks that fail health checks
# ============================================================
docker service create \
  --name healthy-web \
  --replicas 3 \
  --publish 8080:80 \
  --health-cmd "curl -f http://localhost/health || exit 1" \
  --health-interval 10s \
  --health-retries 3 \
  --health-timeout 5s \
  nginx:1.25

# ============================================================
# Demonstrate self-healing: kill a container manually
# Swarm will detect it and start a replacement
# ============================================================

# Find the container ID of one of the tasks
docker ps | grep healthy-web

# Kill it
docker rm -f <container-id>

# Watch Swarm start a replacement within seconds
watch docker service ps healthy-web
# The old task shows as "Shutdown" and a new "Running" task appears
```

---

## 📂 Navigation

| | Link |
|---|---|
| Previous | [12 · Docker Security](../12_Docker_Security/Theory.md) |
| Theory | [Swarm Theory](./Theory.md) |
| Cheatsheet | [Swarm Cheatsheet](./Cheatsheet.md) |
| Interview Q&A | [Swarm Interview Q&A](./Interview_QA.md) |
| Next | [14 · Docker in CI/CD](../14_Docker_in_CICD/Theory.md) |
