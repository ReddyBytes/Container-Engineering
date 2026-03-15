# Docker Swarm — Cheatsheet

## Swarm Initialization

```bash
# Initialize a new Swarm (this machine becomes manager)
docker swarm init

# Init with specific IP for multi-network hosts
docker swarm init --advertise-addr 192.168.1.10

# Get join tokens
docker swarm join-token worker     # worker join command
docker swarm join-token manager    # manager join command

# Join as a worker (run on worker machine)
docker swarm join --token SWMTKN-1-abc123 192.168.1.10:2377

# Leave the Swarm (on a node)
docker swarm leave

# Force-leave (on manager)
docker swarm leave --force

# Promote worker to manager
docker node promote worker-node-1

# Demote manager to worker
docker node demote manager-node-2
```

---

## Node Management

```bash
# List all nodes in the Swarm
docker node ls

# Inspect a node
docker node inspect worker-1

# View tasks running on a node
docker node ps worker-1

# Drain a node (move all tasks away, for maintenance)
docker node update --availability drain worker-1

# Re-activate after maintenance
docker node update --availability active worker-1

# Remove a node from the Swarm
docker node rm worker-1
```

---

## Service Management

```bash
# Create a service
docker service create \
  --name web \
  --replicas 3 \
  --publish 80:80 \
  nginx:1.25

# Create with environment variables
docker service create \
  --name api \
  --replicas 2 \
  --env PORT=3000 \
  --env NODE_ENV=production \
  my-org/api:v1.0.0

# Create with resource limits
docker service create \
  --name web \
  --replicas 3 \
  --limit-cpu 0.5 \
  --limit-memory 256M \
  nginx:1.25

# List services
docker service ls

# Inspect a service (desired vs actual state)
docker service inspect web
docker service inspect --pretty web

# List tasks (containers) for a service
docker service ps web

# View logs from all replicas
docker service logs web
docker service logs -f web      # follow
docker service logs --tail 50 web

# Scale a service
docker service scale web=5
docker service scale web=2 api=4    # scale multiple at once

# Remove a service
docker service rm web
```

---

## Rolling Updates

```bash
# Update image with rolling update
docker service update \
  --image nginx:1.26 \
  --update-parallelism 1 \
  --update-delay 10s \
  web

# Update with rollback on failure
docker service update \
  --image my-app:v2.0.0 \
  --update-failure-action rollback \
  web

# Rollback to previous version manually
docker service rollback web

# Update environment variable
docker service update \
  --env-add LOG_LEVEL=debug \
  web

# Update port mapping
docker service update \
  --publish-add 443:443 \
  web
```

---

## Stack Management

```bash
# Deploy a stack from a Compose file
docker stack deploy -c docker-compose.yml my-app

# List stacks
docker stack ls

# List services in a stack
docker stack services my-app

# List all tasks in a stack
docker stack ps my-app

# Update a stack (re-deploy with new Compose file)
docker stack deploy -c docker-compose.yml my-app    # same command

# Remove a stack (removes all services, networks, configs)
docker stack rm my-app
```

---

## Overlay Networks

```bash
# Create an overlay network
docker network create --driver overlay my-network

# Create with encryption (for cross-node traffic)
docker network create --driver overlay --opt encrypted my-secure-network

# Attach service to network
docker service create --network my-network --name api my-org/api:v1

# List networks
docker network ls
```

---

## Secrets

```bash
# Create secret from stdin
echo "password123" | docker secret create db_password -

# Create secret from file
docker secret create ssl_cert ./cert.pem

# List secrets
docker secret ls

# Remove secret (must not be in use)
docker secret rm db_password

# Use secret in a service (mounted at /run/secrets/db_password)
docker service create \
  --name db \
  --secret db_password \
  postgres:16
```

---

## Compose File — Deploy Section

```yaml
version: "3.9"
services:
  web:
    image: my-org/web:v1.0.0
    deploy:
      replicas: 3
      update_config:
        parallelism: 1          # update 1 replica at a time
        delay: 10s              # wait 10s between updates
        failure_action: rollback
        order: start-first      # new before old (zero-downtime)
      rollback_config:
        parallelism: 1
        delay: 5s
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      resources:
        limits:
          cpus: "0.5"
          memory: 256M
        reservations:
          cpus: "0.25"
          memory: 128M
      placement:
        constraints:
          - node.role == worker
          - node.labels.type == frontend
    ports:
      - "80:80"
```

---

## 📂 Navigation

| | Link |
|---|---|
| Previous | [12 · Docker Security](../12_Docker_Security/Cheatsheet.md) |
| Theory | [Swarm Theory](./Theory.md) |
| Interview Q&A | [Swarm Interview Q&A](./Interview_QA.md) |
| Code Examples | [Swarm Code Examples](./Code_Example.md) |
| Next | [14 · Docker in CI/CD](../14_Docker_in_CICD/Cheatsheet.md) |
