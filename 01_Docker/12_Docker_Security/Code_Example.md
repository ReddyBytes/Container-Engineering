# Docker Security — Code Examples

All examples are production-quality with detailed comments explaining every decision.

---

## 1. Non-Root User — Three Approaches for Different Base Images

The single most impactful security change in a Dockerfile. Covered for Debian-based, Alpine-based, and distroless images.

```dockerfile
# ============================================================
# APPROACH A: Debian/Ubuntu-based images (python:*-slim, node:*, etc.)
# useradd is the Debian/Ubuntu tool — not available on Alpine
# ============================================================
FROM python:3.12-slim

WORKDIR /app

# Install deps as root — pip needs system write access
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create a system user with a fixed UID/GID
# --uid 1001: fixed UID ensures consistency across environments (e.g., Kubernetes SecurityContext)
# --gid 1001: matching GID
# --no-create-home: no home directory (reduces attack surface — no ~/.bashrc, ~/.ssh, etc.)
# --shell /usr/sbin/nologin: prevents interactive login even if someone gets a shell
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --no-create-home \
            --shell /usr/sbin/nologin appuser

# Copy source code and set ownership in one step
# --chown avoids a separate RUN chown layer (saves image size)
COPY --chown=1001:1001 . .

# All subsequent RUN, CMD, ENTRYPOINT run as appuser
USER 1001   # use numeric UID — works even if /etc/passwd is stripped (e.g., distroless)

EXPOSE 8000
CMD ["python", "app.py"]


# ============================================================
# APPROACH B: Alpine-based images (python:*-alpine, node:*-alpine)
# Alpine uses BusyBox adduser — different flags from useradd
# ============================================================
FROM python:3.12-alpine

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Alpine BusyBox addgroup/adduser syntax:
# -S: system user/group (no login, UID < 1000)
# -u 1001: explicit UID
# -G appgroup: assign to group
# -H: no home directory
# -D: no password
RUN addgroup -S -g 1001 appgroup && \
    adduser -S -u 1001 -G appgroup -H -D appuser

COPY --chown=1001:1001 . .
USER 1001
CMD ["python", "app.py"]


# ============================================================
# APPROACH C: Distroless final image (no shell, no package manager)
# Best for production — minimal attack surface
# Use a builder stage to compile/install, then copy artifacts to distroless
# ============================================================
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
# --prefix=/install: install packages to a custom prefix so we can copy just the deps
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt
COPY . .

# Distroless has no shell, no apt, no pip — nothing to exploit interactively
# UID 65532 is the 'nonroot' user built into distroless images
FROM gcr.io/distroless/python3-debian12
COPY --from=builder /install /usr/local
COPY --from=builder /app /app
WORKDIR /app
USER 65532   # nonroot — already defined in the distroless image
CMD ["app.py"]
```

---

## 2. Hardening a Running Container — Capabilities and Read-Only Filesystem

Most applications need zero Linux capabilities beyond the defaults. Drop everything, add back only what's required.

```bash
# ============================================================
# CAPABILITIES: drop all, add only what's needed
# ============================================================

# Run with NO capabilities at all
# Suitable for: stateless API servers, data processors, most web apps
docker run \
  --cap-drop ALL \
  --name hardened-app \
  my-app:v1.0.0

# Run with only NET_BIND_SERVICE (needed to bind port 80 or 443 as non-root)
# Without this, a non-root process cannot bind to ports < 1024
docker run \
  --cap-drop ALL \
  --cap-add NET_BIND_SERVICE \
  -p 80:80 \
  --name web-app \
  my-nginx:v1.0.0

# See which capabilities a running container has
docker inspect hardened-app \
  --format '{{.HostConfig.CapAdd}} {{.HostConfig.CapDrop}}'
# Output: [] [ALL] — confirms all dropped, none added

# ============================================================
# READ-ONLY FILESYSTEM: prevents an attacker writing malware or backdoors
# ============================================================

# Run with read-only root filesystem
# If the app tries to write anywhere, it will get "Read-only file system" error
docker run \
  --read-only \
  --name readonly-demo \
  nginx:alpine

# Most apps legitimately need to write to /tmp (temp files) or /var/run (PID files)
# Use --tmpfs to allow writes to specific paths in memory (not disk)
docker run \
  --read-only \
  --tmpfs /tmp:noexec,nosuid,size=64m \   # ← 64MB in-memory /tmp; noexec prevents running binaries
  --tmpfs /var/run:noexec,nosuid,size=10m \
  -v app-logs:/app/logs \                 # ← volume for logs that must persist
  --name secure-app \
  my-app:v1.0.0

# Verify: try to write outside allowed paths — should fail
docker exec readonly-demo sh -c "echo test > /opt/test" 2>&1
# sh: can't create /opt/test: Read-only file system

# Verify: writing to tmpfs works
docker exec secure-app sh -c "echo test > /tmp/test && echo success"
# success

# ============================================================
# COMBINED: drop caps + read-only + no privilege escalation
# --security-opt no-new-privileges: prevents setuid binaries from escalating
# This is the hardened runtime baseline for production
# ============================================================
docker run \
  --cap-drop ALL \
  --cap-add NET_BIND_SERVICE \
  --read-only \
  --tmpfs /tmp:noexec,nosuid,size=64m \
  --security-opt no-new-privileges \
  -p 80:80 \
  --name production-app \
  my-app:v1.0.0
```

---

## 3. Secrets Management — The Right Way vs the Wrong Way

Secrets in environment variables are a common and serious mistake. Here are the three correct patterns.

```bash
# ============================================================
# WRONG: secret visible in docker inspect, /proc/self/environ, CI logs
# ============================================================
docker run -e DATABASE_PASSWORD=supersecret my-app   # BAD

# Anyone on the host can see this:
docker inspect my-container | grep -i password
# Also visible in: /proc/1/environ inside the container

# ============================================================
# PATTERN 1: Mount a secret file (works in Docker Compose + Docker run)
# The app reads the file, not an env var
# ============================================================

# Create the secret file (outside the repo, never committed to git)
mkdir -p /run/secrets
echo -n "supersecret-db-password" > /run/secrets/db_password
chmod 600 /run/secrets/db_password   # only root can read it

# Mount it read-only at a predictable path
docker run \
  -v /run/secrets/db_password:/run/secrets/db_password:ro \  # :ro = read-only mount
  my-app:v1.0.0
# App code: open('/run/secrets/db_password').read().strip()

# ============================================================
# PATTERN 2: Docker Compose secrets (cleaner syntax)
# ============================================================
```

```yaml
# docker-compose.yml
services:
  app:
    image: my-app:v1.0.0
    secrets:
      - db_password          # mounted at /run/secrets/db_password inside container
      - api_key              # mounted at /run/secrets/api_key

secrets:
  db_password:
    file: ./secrets/db_password.txt   # plain text file, never commit to git
  api_key:
    file: ./secrets/api_key.txt
```

```dockerfile
# ============================================================
# PATTERN 3: BuildKit build-time secrets
# For secrets needed ONLY during build (npm tokens, pip extra indexes, SSH keys)
# The secret is NEVER stored in any image layer
# ============================================================

# In Dockerfile — use --mount=type=secret (requires BuildKit)
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc \
    npm ci
# /root/.npmrc exists only for this RUN instruction
# It does NOT appear in docker history or any image layer

# At build time, pass the secret file
docker buildx build \
  --secret id=npmrc,src="${HOME}/.npmrc" \   # src = path to the secret on your host
  -t my-app:v1.0.0 .

# Verify the secret is not in any layer
docker history my-app:v1.0.0
# No layer contains .npmrc content — confirmed clean
```

---

## 4. Image Scanning and Supply Chain Security

Scan images before pushing, pin base images by digest, and enforce a quality gate in CI.

```bash
# ============================================================
# SCAN WITH TRIVY (most comprehensive open-source scanner)
# ============================================================

# Full scan — OS packages + language packages (pip, npm, cargo, etc.)
trivy image my-app:v1.0.0

# Severity filter — only HIGH and CRITICAL (actionable in most teams)
trivy image --severity HIGH,CRITICAL my-app:v1.0.0

# CI gate: exit 1 on any CRITICAL finding — blocks the push
trivy image \
  --exit-code 1 \
  --severity CRITICAL \
  --no-progress \           # suppress progress bars in CI logs
  my-app:v1.0.0 || {
    echo "CRITICAL vulnerabilities found — blocking push"
    exit 1
  }

# Scan the Dockerfile for misconfigurations (running as root, no HEALTHCHECK, etc.)
trivy config ./Dockerfile

# ============================================================
# BASE IMAGE PINNING BY DIGEST
# A tag can be overwritten — a digest cannot. Pin by digest for reproducibility.
# ============================================================

# Get the digest of an image you trust
docker pull python:3.12.3-slim
docker inspect python:3.12.3-slim --format '{{index .RepoDigests 0}}'
# python:3.12.3-slim@sha256:a1b2c3d4e5f6...

# Pin by digest in the Dockerfile
```

```dockerfile
# BAD: tag can be silently updated; you might get a different image tomorrow
FROM python:3.12.3-slim

# GOOD: digest is immutable — this exact image, always, on every build
FROM python:3.12.3-slim@sha256:a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890
```

```bash
# ============================================================
# DOCKER SCOUT (for interactive review in Docker Desktop)
# ============================================================

# Quick summary: vulnerability counts by severity
docker scout quickview my-app:v1.0.0

# Full CVE detail with recommended fixes
docker scout cves my-app:v1.0.0

# Only show CVEs that have an available fix (prioritize these)
docker scout cves --only-fixed my-app:v1.0.0

# Compare before/after a base image update
docker scout compare my-app:v1.0.0 --to my-app:v1.0.1
# Shows: new vulnerabilities introduced, fixed vulnerabilities, unchanged
```

---

## 5. The Docker Socket Risk — Safe Alternatives for CI/CD

Mounting the Docker socket into a container is a common CI pattern that grants root-equivalent host access. Here are the safe alternatives.

```bash
# ============================================================
# THE DANGER: what a socket-mounted container can do
# ============================================================
# A container with the socket mounted can escape to the host like this:
docker run \
  -v /var/run/docker.sock:/var/run/docker.sock \  # full Docker control
  docker:cli \
  docker run \
    --privileged \
    -v /:/host \          # mount the entire host filesystem
    --rm \
    -it alpine \
    chroot /host          # now you have root on the host
# This is a complete container escape — don't mount the socket in production

# ============================================================
# SAFE ALTERNATIVE 1: Kaniko (builds images without the Docker daemon)
# Used in Kubernetes CI/CD — runs as a regular non-privileged pod
# ============================================================
```

```yaml
# kubernetes-kaniko-build-job.yaml
# Kaniko builds the image entirely in user space — no daemon, no socket, no privilege
apiVersion: batch/v1
kind: Job
metadata:
  name: kaniko-build
spec:
  template:
    spec:
      containers:
        - name: kaniko
          image: gcr.io/kaniko-project/executor:latest
          args:
            - "--context=git://github.com/my-org/my-app"   # build context from git
            - "--dockerfile=Dockerfile"
            - "--destination=ghcr.io/my-org/my-app:v1.0.0" # push directly to registry
          volumeMounts:
            - name: registry-creds
              mountPath: /kaniko/.docker              # registry auth
      volumes:
        - name: registry-creds
          secret:
            secretName: ghcr-credentials
      restartPolicy: Never
```

```bash
# ============================================================
# SAFE ALTERNATIVE 2: Rootless Docker daemon (for Linux hosts)
# The daemon runs as your user — container root maps to your user UID
# A container breakout gets your UID, not host root
# ============================================================

# Install rootless Docker (run as the non-root user you want to own it)
dockerd-rootless-setuptool.sh install

# Start and enable the user-mode daemon
systemctl --user start docker
systemctl --user enable docker

# Set the socket path for your CLI
export DOCKER_HOST="unix://${XDG_RUNTIME_DIR}/docker.sock"

# Verify: the daemon is running as your UID, not root
ps aux | grep dockerd
# youruser  12345  dockerd  ...  ← not root

# ============================================================
# SAFE ALTERNATIVE 3: Docker socket proxy (restrict what's allowed)
# Tecnativa/docker-socket-proxy blocks dangerous API endpoints
# ============================================================
```

```yaml
# docker-compose.yml — socket proxy in front of the real socket
services:
  socket-proxy:
    image: tecnativa/docker-socket-proxy:latest
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro   # proxy reads the real socket
    environment:
      CONTAINERS: 1     # allow: list containers
      IMAGES: 1         # allow: list images
      POST: 0           # DENY: no container creation, no exec
      DELETE: 0         # DENY: no container or image deletion
      BUILD: 0          # DENY: no builds via the socket

  ci-agent:
    image: my-ci-agent
    environment:
      # Point the CI agent at the proxy socket, not the real one
      DOCKER_HOST: tcp://socket-proxy:2375
    depends_on:
      - socket-proxy
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

⬅️ **Prev:** [11 — Multi-Stage Builds](../11_Multi_Stage_Builds/Code_Example.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [13 — Docker Swarm](../13_Docker_Swarm/Code_Example.md)
🏠 **[Home](../../README.md)**
