# Docker Security — Cheatsheet

## Non-Root User Patterns

```dockerfile
# Debian/Ubuntu-based images
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --no-create-home appuser
USER appuser

# Alpine-based images
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

# Chown files to the non-root user
COPY --chown=appuser:appgroup . .
RUN chown -R appuser:appgroup /app
```

---

## Read-Only Filesystem

```bash
# Run with read-only root filesystem
docker run --read-only my-app

# Allow writing to /tmp only (in-memory tmpfs)
docker run --read-only --tmpfs /tmp my-app

# Multiple writable locations
docker run --read-only \
  --tmpfs /tmp:rw,size=64m \
  --tmpfs /var/run:rw \
  -v my-logs:/app/logs \
  my-app
```

---

## Linux Capabilities

```bash
# Drop all, add only what's needed
docker run --cap-drop ALL --cap-add NET_BIND_SERVICE my-app

# Drop specific capabilities
docker run --cap-drop SYS_ADMIN --cap-drop NET_ADMIN my-app

# Common capabilities reference:
# NET_BIND_SERVICE  — bind to ports < 1024
# CHOWN             — change file owner
# SETUID / SETGID   — change process UID/GID
# DAC_OVERRIDE      — bypass file permission checks
# KILL              — send signals to any process
```

---

## Secrets: The Right Way

```bash
# Docker secrets (Swarm mode)
echo "supersecret" | docker secret create db_password -
docker service create --secret db_password my-app

# Read in container at /run/secrets/db_password
```

```dockerfile
# BuildKit build secret (not stored in any layer)
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc \
    npm install
```

```bash
# Use build secret
docker build --secret id=npmrc,src=~/.npmrc .
```

```yaml
# Docker Compose secrets
services:
  app:
    secrets:
      - db_password
secrets:
  db_password:
    file: ./secrets/db_password.txt
```

**What to avoid:**
```bash
# BAD — secret visible in docker inspect
docker run -e DB_PASSWORD=secret my-app

# BAD — baked into image layer
ENV API_KEY=abc123
```

---

## Image Scanning

```bash
# Docker Scout
docker scout quickview my-app:v1.0.0
docker scout cves my-app:v1.0.0
docker scout cves --only-fixed my-app:v1.0.0

# Trivy
trivy image my-app:v1.0.0
trivy image --severity HIGH,CRITICAL my-app:v1.0.0
trivy image --exit-code 1 --severity CRITICAL my-app:v1.0.0   # fail CI
trivy config ./Dockerfile                                       # scan Dockerfile
trivy fs .                                                      # scan filesystem
```

---

## Security Options

```bash
# Run with no new privileges (prevents privilege escalation)
docker run --security-opt no-new-privileges my-app

# Apply seccomp profile
docker run --security-opt seccomp=/path/to/profile.json my-app

# Apply AppArmor profile
docker run --security-opt apparmor=my-profile my-app

# Disable seccomp (debug only, never production)
docker run --security-opt seccomp=unconfined my-app
```

---

## Base Image Best Practices

```dockerfile
# BAD
FROM python:latest            # floating tag, could change

# GOOD
FROM python:3.12.3-slim       # pinned version

# BEST (for critical systems)
FROM python:3.12.3-slim@sha256:a1b2c3d4e5f6...   # pinned digest
```

---

## What NOT to Do

| Anti-Pattern | Risk | Fix |
|---|---|---|
| `docker run --privileged` | Full host access | Remove `--privileged` |
| `-v /var/run/docker.sock:/var/run/docker.sock` | Container controls host Docker | Use Kaniko or Buildah |
| `ENV DB_PASSWORD=secret` | Secret in image layer | Use Docker secrets or mounted files |
| `FROM ubuntu:latest` | Non-deterministic, unfixed CVEs | Pin to `ubuntu:22.04` |
| Running as root (no USER) | Container escape = host root | Add `USER appuser` |
| No read-only filesystem | Attacker can write malware | Add `--read-only` + tmpfs |
| No vulnerability scanning | Unknown CVEs ship to prod | Add Trivy to CI pipeline |

---

## Docker Bench Security

```bash
# Run Docker's official security benchmark
docker run --rm --net host --pid host --userns host --cap-add audit_control \
  -v /etc:/etc:ro \
  -v /usr/bin/containerd:/usr/bin/containerd:ro \
  -v /var/lib:/var/lib:ro \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  docker/docker-bench-security
```

---

## 📂 Navigation

| | Link |
|---|---|
| Previous | [11 · Multi-Stage Builds](../11_Multi_Stage_Builds/Cheatsheet.md) |
| Theory | [Security Theory](./Theory.md) |
| Interview Q&A | [Security Interview Q&A](./Interview_QA.md) |
| Next | [13 · Docker Swarm](../13_Docker_Swarm/Cheatsheet.md) |
