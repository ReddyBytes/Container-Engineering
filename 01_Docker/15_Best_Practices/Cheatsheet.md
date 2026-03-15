# Docker Best Practices — Cheatsheet

## Base Image Selection

```dockerfile
# Ordered by size/security (smaller = better for prod)
FROM scratch                              # Go static binaries only (~0 MB base)
FROM gcr.io/distroless/static-debian12   # No shell, minimal OS (~5 MB)
FROM gcr.io/distroless/python3-debian12  # For Python apps
FROM alpine:3.19                          # ~5 MB, has shell
FROM python:3.12-alpine                   # Language + Alpine
FROM python:3.12-slim                     # Debian slim (~30 MB)
FROM python:3.12                          # Full Debian (~1 GB) — avoid for prod
```

---

## Layer Optimization

```dockerfile
# BAD: separate layers, cache stays in image
RUN apt-get update
RUN apt-get install -y curl
RUN rm -rf /var/lib/apt/lists/*

# GOOD: one layer, cleanup in same instruction
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*
```

---

## Cache-Friendly Layer Order

```dockerfile
# Pattern: rarely changing → often changing

# Go
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN go build -o server .

# Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "app.py"]

# Node.js
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build
```

---

## .dockerignore Template

```dockerignore
# Version control
.git
.gitignore

# Dependencies
node_modules
vendor
__pycache__
*.pyc
.pytest_cache

# Secrets and environment
.env
.env.*
*.pem
*.key
secrets/

# Test files
**/*.test.*
**/*.spec.*
coverage/

# Build output
dist/
build/

# IDE
.idea/
.vscode/
.DS_Store

# Docs and CI
*.md
docs/
.github/
```

---

## Non-Root User

```dockerfile
# Debian/Ubuntu
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --no-create-home appuser
COPY --chown=appuser:appgroup . .
USER appuser

# Alpine
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser
```

---

## Health Checks

```dockerfile
# HTTP
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# TCP
HEALTHCHECK --interval=30s --timeout=5s \
    CMD nc -z localhost 5432 || exit 1

# No health check (disable)
HEALTHCHECK NONE
```

---

## Logging Configuration

```dockerfile
# Python: send output to stdout unbuffered
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Node.js: naturally goes to stdout with console.log

# Nginx: redirect logs to stdout/stderr
RUN ln -sf /dev/stdout /var/log/nginx/access.log && \
    ln -sf /dev/stderr /var/log/nginx/error.log
```

---

## Tagging Reference

```bash
# NEVER in production
FROM myapp:latest
docker run myapp:latest

# Always use specific tags
docker build -t myapp:v1.2.3 .
docker build -t myapp:$(git rev-parse --short HEAD) .

# Both for a release
docker tag myapp:v1.2.3 myapp:v1.2
docker tag myapp:v1.2.3 myapp:v1
```

---

## Anti-Patterns Quick Reference

| Anti-Pattern | Fix |
|---|---|
| `FROM ubuntu:latest` | `FROM ubuntu:22.04` |
| No `USER` | Add `USER appuser` |
| `ENV DB_PASS=secret` | Use Docker secrets or mounted files |
| No `.dockerignore` | Create `.dockerignore` |
| Separate `apt-get update` and `install` | Combine in one `RUN` |
| `COPY . .` before deps | Copy dep manifest first |
| Logging to files | Log to stdout/stderr |
| Multiple services per container | One container per service |
| Build tools in prod image | Use multi-stage builds |
| No HEALTHCHECK | Add `HEALTHCHECK` instruction |

---

## Pre-Push Security Checklist

```
[ ] Pinned base image version (not latest)
[ ] Non-root USER set
[ ] .dockerignore created
[ ] No secrets in Dockerfile or ENV
[ ] Multi-stage build (build tools not in final image)
[ ] trivy image passed - no CRITICAL CVEs
[ ] HEALTHCHECK defined
[ ] Logging to stdout/stderr
[ ] Package caches cleaned in same RUN
[ ] --no-install-recommends used for apt
```

---

## Dockerfile Template (Production-Ready)

```dockerfile
FROM python:3.12-slim AS base
WORKDIR /app

# Install only what's needed, clean up in same layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Dependencies first (better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Source code
COPY --chown=appuser:appgroup . .

# Non-root user
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --no-create-home appuser
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "app.py"]
```

---

## 📂 Navigation

| | Link |
|---|---|
| Previous | [14 · Docker in CI/CD](../14_Docker_in_CICD/Cheatsheet.md) |
| Theory | [Best Practices Theory](./Theory.md) |
| Interview Q&A | [Best Practices Interview Q&A](./Interview_QA.md) |
| Next | [Section 03 — Docker → K8s Bridge](../../03_Docker_to_K8s/01_Docker_vs_K8s/Theory.md) |
