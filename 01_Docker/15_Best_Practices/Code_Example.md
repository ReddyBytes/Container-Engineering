# Docker Best Practices — Code Examples

All examples are production-quality with detailed comments explaining every decision.

---

## 1. Layer Optimization — Cache Ordering and RUN Consolidation

The two most impactful Dockerfile optimizations: copy dependency manifests before source code, and combine related RUN instructions into one layer.

```dockerfile
# ============================================================
# BEFORE: Slow, cache-busting, bloated layers
# Every code change re-runs pip install (2–3 minutes in CI)
# ============================================================
FROM python:3.12-slim

WORKDIR /app

# BAD: copying all source first — any .py file change busts the pip install cache
COPY . .

# BAD: apt-get update in a separate layer — the package list is cached stale
RUN apt-get update
RUN apt-get install -y curl

# BAD: cleanup in a separate layer — the apt cache still exists in the previous layer
# (layers are immutable — deleting in layer N doesn't remove data from layer N-1)
RUN rm -rf /var/lib/apt/lists/*

RUN pip install -r requirements.txt

CMD ["python", "app.py"]


# ============================================================
# AFTER: Cache-optimized, minimal layers
# Only the layers below the first changed file are rebuilt
# ============================================================
FROM python:3.12-slim

WORKDIR /app

# GOOD: install system packages in ONE combined RUN instruction
# The cache cleanup (rm -rf) must be in the SAME layer as the install
# --no-install-recommends: skip suggested packages — saves ~30% of package install size
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*   # ← same layer — this actually removes the files

# GOOD: copy ONLY the dependency manifest first
# This layer is cached until requirements.txt changes
# Changing app.py does NOT rebuild this layer → pip install is fast in CI
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Source code comes last — it changes most often
# Only this layer and below rebuild on code changes
COPY . .

RUN useradd --uid 1001 --no-create-home --shell /usr/sbin/nologin appuser
USER 1001

CMD ["python", "app.py"]
```

```bash
# Prove the cache behavior: change only source code and time the rebuild
echo "# updated" >> app.py
time docker build -t my-app:test .
# You should see "CACHED" for the pip install step
# Rebuilds only the COPY . . layer and below — typically < 5 seconds
```

---

## 2. Base Image Selection — Size and CVE Comparison

The base image choice sets the floor for image size and vulnerability count. This example compares options and shows how to measure the difference.

```bash
# ============================================================
# Pull and compare common Python base images
# ============================================================
for tag in "python:3.12" "python:3.12-slim" "python:3.12-alpine"; do
  docker pull "$tag" -q
  SIZE=$(docker image inspect "$tag" --format '{{.Size}}' | numfmt --to=iec)
  LAYERS=$(docker history "$tag" --no-trunc --quiet | wc -l | tr -d ' ')
  echo "${tag}: ${SIZE} (${LAYERS} layers)"
done
# python:3.12:        ~1.04GB (14 layers)  ← full Debian + build tools
# python:3.12-slim:   ~130MB  (9 layers)   ← Debian, Python only
# python:3.12-alpine: ~55MB   (7 layers)   ← Alpine/musl, smallest

# ============================================================
# Scan each for CVEs to find the safest base
# ============================================================
for tag in "python:3.12" "python:3.12-slim" "python:3.12-alpine"; do
  echo "=== $tag CVE summary ==="
  trivy image --severity HIGH,CRITICAL --no-progress "$tag" 2>/dev/null \
    | grep "Total:"
done
# slim and alpine typically have far fewer CVEs than the full image
```

```dockerfile
# ============================================================
# CHOOSING THE RIGHT BASE: decision table
# ============================================================

# Use python:3.12-slim when:
# - You need Debian compatibility (most pip packages work here)
# - Some packages require glibc (e.g., numpy, pandas prebuilt wheels)
FROM python:3.12-slim

# Use python:3.12-alpine when:
# - You want the smallest possible image
# - All your dependencies have pure-Python or Alpine-compatible wheels
# CAUTION: packages with C extensions (numpy, psycopg2) may need extra build steps
FROM python:3.12-alpine

# Use gcr.io/distroless for maximum production hardening:
# - No shell (/bin/sh), no package manager, no curl — nothing to exploit interactively
# - Run as non-root (UID 65532) by default
# - Requires multi-stage build (builder prepares artifacts, distroless just runs them)
FROM gcr.io/distroless/python3-debian12

# Use scratch for Go binaries:
# - Zero OS: just your statically compiled binary
# - Image size = binary size (often 10–20 MB)
# Only works for statically compiled languages
FROM scratch
COPY my-go-binary /app
ENTRYPOINT ["/app"]
```

---

## 3. Health Checks, Logging, and Signals — Observability Patterns

A production container must be observable. These patterns ensure Docker knows when your app is healthy and that logs reach your logging system.

```dockerfile
# ============================================================
# HEALTH CHECK: Docker monitors app health, not just process liveness
# ============================================================
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --uid 1001 --no-create-home appuser
USER 1001

# --interval=30s: check every 30 seconds
# --timeout=5s: fail the check if no response within 5 seconds
# --start-period=15s: don't count failures during the first 15s (startup grace)
# --retries=3: mark unhealthy only after 3 consecutive failures
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python3 -c \
      "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" \
      || exit 1

# LOGGING: Python buffers stdout by default — disable it
# Without this, log lines appear in batches rather than immediately
# PYTHONUNBUFFERED=1 forces line-by-line flushing to stdout/stderr
ENV PYTHONUNBUFFERED=1

# Signal handling: use exec form (JSON array) NOT shell form (string)
# Shell form: CMD "python app.py" → shell is PID 1, python is a child
#   → SIGTERM goes to shell, which may not forward it to Python → unclean shutdown
# Exec form: CMD ["python", "app.py"] → python IS PID 1, receives SIGTERM directly
CMD ["python", "app.py"]
```

```bash
# ============================================================
# Verify health check behavior
# ============================================================

docker run -d --name health-demo my-app:v1.0.0

# Watch health status transition: starting → healthy (or unhealthy)
watch -n 2 'docker inspect health-demo --format "{{.State.Health.Status}}"'

# View the last 5 health check results (timestamp + exit code + output)
docker inspect health-demo \
  --format '{{range .State.Health.Log}}{{.Start}} exit={{.ExitCode}} output={{.Output}}
{{end}}' | tail -5

# ============================================================
# Logging: write to stdout/stderr, Docker collects it
# ============================================================

# Good: logs flow to docker logs automatically
docker logs health-demo
docker logs --follow health-demo         # tail -f equivalent
docker logs --since 5m health-demo       # last 5 minutes
docker logs --timestamps health-demo     # include timestamps

# Configure the logging driver for production (send to centralized system)
docker run \
  --log-driver awslogs \                  # send to AWS CloudWatch
  --log-opt awslogs-region=us-east-1 \
  --log-opt awslogs-group=/my-app/prod \
  my-app:v1.0.0

# Or configure globally in /etc/docker/daemon.json:
# { "log-driver": "json-file", "log-opts": { "max-size": "10m", "max-file": "3" } }
```

---

## 4. Environment Configuration — The 12-Factor Pattern

The same image must run in dev, staging, and production. Differentiate using environment variables at runtime, never baked-in config.

```dockerfile
# ============================================================
# BAD: environment-specific config baked into the image
# This image can only run in production — you can't use it in dev
# ============================================================
FROM node:20-alpine
WORKDIR /app
COPY . .
RUN npm ci --omit=dev

# BAD: production-only values hardcoded
ENV NODE_ENV=production
ENV DATABASE_URL=postgres://prod-db.internal:5432/myapp
ENV LOG_LEVEL=warning
ENV PORT=3000

CMD ["node", "src/index.js"]


# ============================================================
# GOOD: sensible defaults only, all config injectable at runtime
# ============================================================
FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev
COPY src/ ./src/

RUN addgroup -S appgroup && adduser -S -G appgroup appuser
USER appuser

# GOOD: only set defaults that make sense for local dev
# Every environment-specific value is overridden at runtime
ENV NODE_ENV=development    # override to 'production' at runtime
ENV LOG_LEVEL=info          # override to 'warning' in prod
ENV PORT=3000               # expose this port at runtime with -p

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost:3000/health || exit 1

CMD ["node", "src/index.js"]
```

```bash
# ============================================================
# Runtime configuration: same image, different envs
# ============================================================

# Local development
docker run \
  -e NODE_ENV=development \
  -e DATABASE_URL=postgres://localhost:5432/myapp_dev \
  -e LOG_LEVEL=debug \
  -p 3000:3000 \
  my-app:v1.0.0

# Staging
docker run \
  -e NODE_ENV=staging \
  -e DATABASE_URL=postgres://staging-db:5432/myapp \
  -e LOG_LEVEL=info \
  -p 3000:3000 \
  my-app:v1.0.0

# Production
docker run \
  -e NODE_ENV=production \
  -e DATABASE_URL=postgres://prod-db:5432/myapp \
  -e LOG_LEVEL=warning \
  -p 3000:3000 \
  my-app:v1.0.0

# In Docker Compose: use .env files per environment
# docker compose --env-file .env.staging up
```

---

## 5. Production Pre-Push Checklist — Automation and Verification

A scripted checklist that enforces every best practice before an image is pushed to any registry.

```bash
#!/usr/bin/env bash
# check-image.sh — run this before every docker push
# Usage: ./check-image.sh my-app:v1.0.0

set -euo pipefail

IMAGE="${1:?Usage: $0 <image:tag>}"
PASS=0
FAIL=0

check() {
  local name="$1"
  local result="$2"
  if [[ "$result" == "pass" ]]; then
    echo "  [PASS] $name"
    ((PASS++))
  else
    echo "  [FAIL] $name"
    ((FAIL++))
  fi
}

echo "=== Pre-push checklist for: $IMAGE ==="

# 1. Check: image is not tagged 'latest'
if [[ "${IMAGE##*:}" != "latest" ]]; then
  check "Not using :latest tag" pass
else
  check "Not using :latest tag" fail
fi

# 2. Check: container does not run as root (UID 0)
# Run a quick test container and check the UID
RUNNING_UID=$(docker run --rm --entrypoint id "$IMAGE" -u 2>/dev/null || echo "0")
if [[ "$RUNNING_UID" != "0" ]]; then
  check "Runs as non-root (UID=$RUNNING_UID)" pass
else
  check "Runs as non-root" fail
fi

# 3. Check: HEALTHCHECK is defined in the image
HAS_HEALTH=$(docker inspect "$IMAGE" --format '{{.Config.Healthcheck}}' 2>/dev/null)
if [[ -n "$HAS_HEALTH" && "$HAS_HEALTH" != "<nil>" ]]; then
  check "HEALTHCHECK defined" pass
else
  check "HEALTHCHECK defined" fail
fi

# 4. Check: Trivy scan — no CRITICAL vulnerabilities
if trivy image \
    --exit-code 1 \
    --severity CRITICAL \
    --no-progress \
    --quiet \
    "$IMAGE" 2>/dev/null; then
  check "No CRITICAL CVEs (Trivy)" pass
else
  check "No CRITICAL CVEs (Trivy)" fail
fi

# 5. Check: Dockerfile misconfigurations
if trivy config \
    --exit-code 1 \
    --no-progress \
    --quiet \
    ./Dockerfile 2>/dev/null; then
  check "No Dockerfile misconfigs (Trivy)" pass
else
  check "No Dockerfile misconfigs (Trivy)" fail
fi

# 6. Check: .dockerignore exists
if [[ -f ".dockerignore" ]]; then
  check ".dockerignore exists" pass
else
  check ".dockerignore exists" fail
fi

# Summary
echo ""
echo "Result: ${PASS} passed, ${FAIL} failed"
if [[ "$FAIL" -gt 0 ]]; then
  echo "Fix the failing checks before pushing."
  exit 1
else
  echo "All checks passed — safe to push."
fi
```

```bash
# Make the script executable and run it
chmod +x check-image.sh
./check-image.sh my-app:v1.0.0

# Integrate into your Makefile:
# push: check-image build-push
# check-image:
#     ./check-image.sh $(IMAGE):$(TAG)
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

⬅️ **Prev:** [14 — Docker in CI/CD](../14_Docker_in_CICD/Code_Example.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [16 — BuildKit and Docker Scout](../16_BuildKit_and_Docker_Scout/Code_Example.md)
🏠 **[Home](../../README.md)**
