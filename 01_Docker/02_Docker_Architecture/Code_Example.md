# Docker Architecture — Code Examples

All examples are production-quality with detailed comments explaining every decision.

---

## 1. Tracing `docker run` — Every Component in the Chain

This demo makes the architecture concrete by surfacing what each layer does when you run a single command. Run these as you read the Theory to see the chain in real time.

```bash
# -----------------------------------------------
# STEP 1: The CLI constructs a REST API call
# Use the --log-level flag to see the API calls the CLI makes
# -----------------------------------------------
docker --log-level=debug run --rm alpine echo hello 2>&1 | grep -E "(POST|GET|PUT|DELETE)"
# You'll see lines like:
# POST /v1.44/containers/create
# POST /v1.44/containers/{id}/start
# DELETE /v1.44/containers/{id}

# -----------------------------------------------
# STEP 2: The daemon checks the local image cache first
# Pull an image that isn't cached to observe the download sequence
# -----------------------------------------------
docker image rm alpine 2>/dev/null || true   # ensure not cached
docker pull alpine
# Output shows:
# "Pulling from library/alpine"   ← dockerd contacted Docker Hub
# "c926b61bad3b: Pull complete"   ← layer downloaded by containerd
# "Digest: sha256:..."             ← content-addressed hash, immutable reference

# -----------------------------------------------
# STEP 3: Confirm dockerd delegated to containerd
# On Linux, containerd has its own namespace for Docker ("moby")
# -----------------------------------------------
sudo ctr -n moby images list 2>/dev/null | grep alpine
# If this returns a result, containerd holds the image independently of dockerd
# Kubernetes uses containerd directly via CRI — Docker is optional

# -----------------------------------------------
# STEP 4: Inspect the shim that survives runc
# -----------------------------------------------
docker run -d --name arch-demo alpine sleep 120

# Find the shim process — one per container, stays after runc exits
ps aux | grep containerd-shim | grep -v grep
# containerd-shim-runc-v2 <container-id> ...
# This shim is what keeps stdin/stdout pipes open for docker logs

# runc has already exited — it only runs during container creation
# (runc is not visible in ps because it completes its job and exits)

# Cleanup
docker stop arch-demo && docker rm arch-demo
```

---

## 2. The Docker Socket — Direct API Calls

The Docker CLI is just a REST client. You can call the same API directly with `curl` to understand exactly what the CLI does under the hood.

```bash
# The Docker daemon listens on a Unix socket at /var/run/docker.sock
# curl --unix-socket lets you speak HTTP over a Unix socket

# List all running containers (equivalent to: docker ps)
curl --unix-socket /var/run/docker.sock \
  http://localhost/v1.44/containers/json \
  | python3 -m json.tool

# Get Docker system info (equivalent to: docker info)
curl --unix-socket /var/run/docker.sock \
  http://localhost/v1.44/info \
  | python3 -m json.tool | head -40

# Pull an image via the API directly (equivalent to: docker pull nginx)
curl --unix-socket /var/run/docker.sock \
  -X POST \
  "http://localhost/v1.44/images/create?fromImage=nginx&tag=alpine"
# The response is a stream of JSON progress events — same as docker pull output

# Create a container via the API
curl --unix-socket /var/run/docker.sock \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"Image":"alpine","Cmd":["echo","hello from API"]}' \
  http://localhost/v1.44/containers/create
# Returns: {"Id":"<container_id>","Warnings":[]}

# -----------------------------------------------
# WHY THIS MATTERS:
# CI tools (Jenkins, GitHub Actions runners), Portainer, Watchtower,
# and many other tools talk to Docker exactly this way.
# Anyone who can reach this socket has full Docker control.
# -----------------------------------------------

# Check socket permissions — only root and docker group can access it
ls -la /var/run/docker.sock
# srw-rw---- 1 root docker
# Adding a user to 'docker' group grants them root-equivalent access on the host
```

---

## 3. OverlayFS Layers — Seeing the Copy-on-Write Filesystem

Docker images are stacked read-only layers with a thin writable layer on top. This demo exposes that structure directly.

```bash
# Pull a Python image — it has multiple layers
docker pull python:3.11-slim

# List the layers (each line is one Dockerfile instruction that changed the filesystem)
docker history python:3.11-slim
# IMAGE         CREATED      CREATED BY                                      SIZE
# <hash>        ...          CMD ["python3"]                                  0B
# <hash>        ...          ENV PYTHON_PIP_VERSION=23.0.1                    0B
# <hash>        ...          RUN /bin/sh -c set -eux; apt-get update ...      30MB
# ...

# -----------------------------------------------
# Inspect the actual OverlayFS layers on disk
# -----------------------------------------------
docker run -d --name overlay-demo python:3.11-slim sleep 120

# Find the OverlayFS mount info for this container
docker inspect overlay-demo | python3 -m json.tool | grep -A 20 '"GraphDriver"'
# "LowerDir": "/var/lib/docker/overlay2/<hash>/diff:..."  ← stacked read-only layers
# "UpperDir": "/var/lib/docker/overlay2/<hash>/diff"      ← writable container layer
# "WorkDir":  "/var/lib/docker/overlay2/<hash>/work"      ← OverlayFS internal

# Write a file inside the container — it goes to UpperDir (writable layer only)
docker exec overlay-demo sh -c "echo hello > /tmp/myfile"

# Inspect what's in the writable UpperDir — should contain our file
UPPER_DIR=$(docker inspect overlay-demo \
  --format '{{.GraphDriver.Data.UpperDir}}')
sudo ls "$UPPER_DIR/tmp/"
# myfile — only in the writable layer, image layers are untouched

# Show layer sharing: multiple containers share the same read-only layers
docker run -d --name overlay-demo2 python:3.11-slim sleep 120

# Both containers share the same LowerDir (same image layers)
docker inspect overlay-demo  --format '{{.GraphDriver.Data.LowerDir}}' | tr ':' '\n' | wc -l
docker inspect overlay-demo2 --format '{{.GraphDriver.Data.LowerDir}}' | tr ':' '\n' | wc -l
# Same number of lower layers — Docker stores them once and shares them

# Cleanup
docker stop overlay-demo overlay-demo2 && docker rm overlay-demo overlay-demo2
```

---

## 4. Docker Contexts — Managing Multiple Daemons

Docker contexts let you switch which daemon your CLI talks to — local, remote, or via SSH — without changing any flags.

```bash
# List existing contexts
docker context ls
# NAME       TYPE    DESCRIPTION                               DOCKER ENDPOINT
# default *  moby    Current DOCKER_HOST based configuration   unix:///var/run/docker.sock

# Create a context that connects to a remote daemon over SSH
# 'ssh://user@host' uses your existing SSH key — no password prompt if key is configured
docker context create remote-dev \
  --description "Dev server" \
  --docker "host=ssh://deploy@dev.example.com"

# Create a context for a TCP endpoint (less secure — only in trusted networks)
docker context create remote-prod \
  --description "Production server (TCP)" \
  --docker "host=tcp://prod.example.com:2376,tls-verify=true,ca=/certs/ca.pem,cert=/certs/cert.pem,key=/certs/key.pem"

# Switch contexts — all subsequent docker commands hit the remote daemon
docker context use remote-dev
docker ps                   # ← runs on remote-dev server, not local
docker images               # ← images on remote-dev server

# Run a container on the remote daemon from your local terminal
docker run -d --name remote-nginx nginx

# Switch back to local
docker context use default
docker ps                   # ← local containers again

# Remove a context
docker context rm remote-dev

# One-time override without switching: use DOCKER_CONTEXT env var or --context flag
docker --context remote-prod ps
DOCKER_CONTEXT=remote-prod docker images
```

---

## 5. Private Registry Authentication — Login, Tag, Push, Pull

The registry is a first-class component of the architecture. This example covers the full workflow for AWS ECR, GHCR, and a self-hosted registry.

```bash
# ============================================================
# DOCKER HUB (default registry)
# ============================================================
docker login                          # prompts for username + password/token
# Credentials stored in ~/.docker/config.json
# Use an access token (not password) — generated in Docker Hub account settings

# ============================================================
# AWS ECR (most common in enterprise)
# ============================================================
# ECR tokens expire every 12 hours — use the AWS CLI to refresh
AWS_ACCOUNT=123456789012
AWS_REGION=us-east-1
ECR_HOST="${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Get a temporary token from AWS STS and pipe it into docker login
# --password-stdin: reads password from stdin (safer than --password flag which exposes it in process list)
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login \
    --username AWS \
    --password-stdin \
    "$ECR_HOST"

# Tag your local image for ECR (tag = full registry path)
docker tag my-app:1.0.0 "${ECR_HOST}/my-app:1.0.0"

# Push — Docker resolves the registry from the image name prefix
docker push "${ECR_HOST}/my-app:1.0.0"

# Pull (on a different machine or in Kubernetes)
docker pull "${ECR_HOST}/my-app:1.0.0"

# ============================================================
# GITHUB CONTAINER REGISTRY (GHCR)
# ============================================================
# GITHUB_TOKEN is available automatically in GitHub Actions
# For local use, generate a Personal Access Token with 'write:packages' scope
echo "$GITHUB_TOKEN" \
  | docker login ghcr.io \
    --username "$GITHUB_ACTOR" \
    --password-stdin

docker tag my-app:1.0.0 ghcr.io/my-org/my-app:1.0.0
docker push ghcr.io/my-org/my-app:1.0.0

# ============================================================
# VIEW STORED CREDENTIALS
# ============================================================
cat ~/.docker/config.json
# Shows base64-encoded credentials per registry
# WARNING: these are not encrypted — use a credential store (docker-credential-osxkeychain on macOS)
docker info | grep "Credential Store"
# If configured: "Credentials Store: osxkeychain" (macOS) or "secretservice" (Linux)
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

⬅️ **Prev:** [01 — Virtualization and Containers](../01_Virtualization_and_Containers/Code_Example.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [03 — Installation and Setup](../03_Installation_and_Setup/Code_Example.md)
🏠 **[Home](../../README.md)**
