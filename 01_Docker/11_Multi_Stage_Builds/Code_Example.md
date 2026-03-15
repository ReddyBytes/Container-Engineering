# Multi-Stage Builds — Code Examples

---

## Example 1: Go Application (scratch-based, ~5 MB final image)

```dockerfile
# ============================================================
# Stage 1: Builder
# Use the official Go image — includes compiler, stdlib, tools
# ============================================================
FROM golang:1.22 AS builder

WORKDIR /app

# Copy dependency manifests first for better layer caching.
# These layers only rebuild when go.mod or go.sum change.
COPY go.mod go.sum ./
RUN go mod download

# Copy source code (this layer rebuilds on every code change)
COPY . .

# Build a statically linked binary:
#   CGO_ENABLED=0  — no C library linkage (required for scratch)
#   GOOS=linux     — compile for Linux (even if building on macOS)
#   -ldflags "-s -w" — strip debug symbols, reduces binary size ~20%
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o server .

# ============================================================
# Stage 2: Runtime
# scratch = completely empty image — no OS, no shell, nothing
# Final image size: only the binary (~5-15 MB)
# ============================================================
FROM scratch

# Copy the compiled binary from the builder stage
COPY --from=builder /app/server /server

# Copy CA certificates so HTTPS calls work
# (scratch has none — we grab them from the builder stage)
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

# No shell available in scratch, so use exec form
ENTRYPOINT ["/server"]
```

**Build and run:**
```bash
docker build -t go-app:v1.0.0 .
docker run -p 8080:8080 go-app:v1.0.0

# Check the size
docker images go-app:v1.0.0
# REPOSITORY   TAG     SIZE
# go-app       v1.0.0  8.2MB
```

---

## Example 1b: Go Application (Alpine-based, ~15 MB, includes shell)

Use this variant when you need a shell for debugging or need to run shell scripts at startup.

```dockerfile
FROM golang:1.22 AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o server .

# ============================================================
# Alpine is ~5 MB — includes shell, basic utilities, CA certs
# Good balance: tiny, but debuggable
# ============================================================
FROM alpine:3.19

# Install CA certificates for HTTPS and timezone data
RUN apk --no-cache add ca-certificates tzdata

WORKDIR /app

# Create a non-root user for security
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

# Copy only the binary
COPY --from=builder /app/server .

EXPOSE 8080
CMD ["./server"]
```

---

## Example 2: Python Application

```dockerfile
# ============================================================
# Stage 1: Builder
# Use full python image to install dependencies
# Full image has gcc and other build headers some packages need
# ============================================================
FROM python:3.12 AS builder

WORKDIR /app

# Install dependencies into a custom prefix directory
# --no-cache-dir   — don't cache pip's download cache
# --prefix=/install — install to /install instead of system path
# This directory is what we'll copy to the runtime image
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ============================================================
# Stage 2: Runtime
# python:3.12-slim is Python without build tools, headers, etc.
# Roughly 60% smaller than python:3.12
# ============================================================
FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source code
COPY src/ ./src/
COPY config/ ./config/

# Create a non-root user
RUN useradd --no-create-home --shell /bin/false appuser
USER appuser

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["python", "src/app.py"]
```

**requirements.txt:**
```
fastapi==0.111.0
uvicorn[standard]==0.30.1
pydantic==2.7.1
httpx==0.27.0
```

**Build and run:**
```bash
docker build -t python-app:v1.0.0 .
docker run -p 8000:8000 python-app:v1.0.0

# Compare sizes
docker images python-app
# python:3.12         ~1.0 GB (if built with no multi-stage)
# python-app:v1.0.0   ~130 MB (multi-stage with slim runtime)
```

---

## Example 3: Node.js Application → nginx Static Files

This pattern is perfect for React, Vue, Angular, or any frontend that builds to static HTML/CSS/JS.

```dockerfile
# ============================================================
# Stage 1: Build the frontend
# Install ALL dependencies (including devDependencies),
# run the build, and produce the /app/dist directory
# ============================================================
FROM node:20 AS builder

WORKDIR /app

# Copy package files first for layer caching.
# npm ci is preferred over npm install in CI:
#   - uses package-lock.json exactly
#   - fails if lock file is out of sync
#   - does not modify package-lock.json
COPY package.json package-lock.json ./
RUN npm ci

# Copy source code and build
# This produces a /app/dist folder with static assets
COPY . .
RUN npm run build

# ============================================================
# Stage 2: Serve with nginx
# The final image has ONLY nginx + the static files
# No Node.js runtime, no npm, no node_modules
# ============================================================
FROM nginx:1.25-alpine

# Copy the built static files from the builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Optional: custom nginx config for SPA routing
# COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

# nginx runs as the default CMD — no CMD needed
```

**nginx.conf for Single Page Application (SPA) routing:**
```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    # All routes fall back to index.html (for React Router, Vue Router, etc.)
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets aggressively
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

**Build and run:**
```bash
docker build -t frontend:v1.0.0 .
docker run -p 3000:80 frontend:v1.0.0

# Check the size
docker images frontend
# REPOSITORY   TAG     SIZE
# frontend     v1.0.0  23.4MB
# (vs ~650 MB if you served from node:20)
```

---

## Example 4: Multi-Stage with Test Stage (for CI)

```dockerfile
FROM golang:1.22 AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o server .

# ============================================================
# Test stage: run the full test suite
# Docker build --target tester fails the build if tests fail
# This stage is never used in production
# ============================================================
FROM golang:1.22 AS tester
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
# -v: verbose output   -race: detect data races   ./...: all packages
RUN go test -v -race ./...

# ============================================================
# Production stage: clean minimal image
# Only reachable if both builder and tester succeeded
# ============================================================
FROM alpine:3.19 AS production
RUN apk --no-cache add ca-certificates
WORKDIR /app
RUN addgroup -S app && adduser -S app -G app
COPY --from=builder /app/server .
RUN chown app:app server
USER app
EXPOSE 8080
CMD ["./server"]
```

**CI usage (GitHub Actions or any CI system):**
```bash
# Step 1: Run tests — fails the build if any test fails
docker build --target tester -t my-app:test .

# Step 2: Build the production image
docker build --target production -t my-app:${GIT_SHA} .

# Step 3: Push to registry
docker push my-app:${GIT_SHA}
```

---

## Size Comparison Script

```bash
#!/bin/bash
# Compare image sizes before and after multi-stage

echo "=== Single Stage (naive) ==="
docker build -f Dockerfile.single -t app:single . 2>/dev/null
docker images app:single --format "{{.Size}}"

echo "=== Multi-Stage ==="
docker build -f Dockerfile.multistage -t app:multi . 2>/dev/null
docker images app:multi --format "{{.Size}}"

echo "=== Layer inspection ==="
docker history app:multi
```

---

## 📂 Navigation

| | Link |
|---|---|
| Previous | [10 · Docker Registry](../10_Docker_Registry/Theory.md) |
| Theory | [Multi-Stage Theory](./Theory.md) |
| Cheatsheet | [Multi-Stage Cheatsheet](./Cheatsheet.md) |
| Interview Q&A | [Multi-Stage Interview Q&A](./Interview_QA.md) |
| Next | [12 · Docker Security](../12_Docker_Security/Theory.md) |
