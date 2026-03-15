# Module 16 — BuildKit and Docker Scout: Cheatsheet

## BuildKit Basics

| Command | What It Does |
|---------|-------------|
| `docker buildx ls` | List all builder instances |
| `docker buildx create --name mybuilder --use` | Create and activate a new builder |
| `docker buildx inspect --bootstrap` | Inspect active builder, start it if not running |
| `docker buildx rm mybuilder` | Remove a builder instance |
| `docker buildx build .` | Build with BuildKit (same as `docker build` on Docker 23+) |
| `DOCKER_BUILDKIT=1 docker build .` | Force BuildKit on older Docker versions |

---

## Parser Directive (Required for Advanced Features)

```dockerfile
# syntax=docker/dockerfile:1
```

Always the **first line** of the Dockerfile when using cache mounts, secret mounts, or heredoc syntax.

---

## Build Cache

```bash
# Inline cache (simple, single-image)
docker buildx build \
  --cache-to type=inline \
  --push -t registry/image:tag .

# Registry cache (recommended — all stages, mode=max)
docker buildx build \
  --cache-from type=registry,ref=registry/image:cache \
  --cache-to   type=registry,ref=registry/image:cache,mode=max \
  --push -t registry/image:latest .

# GitHub Actions cache backend
docker buildx build \
  --cache-from type=gha \
  --cache-to   type=gha,mode=max \
  -t myapp:latest .
```

---

## BuildKit Mount Types

### Cache Mount — Skip Re-downloads

```dockerfile
# Python pip cache
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Node npm cache
RUN --mount=type=cache,target=/root/.npm \
    npm ci

# apt cache (use sharing=locked to prevent corruption)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y curl
```

### Secret Mount — Never in Layers

```dockerfile
# Use secret in Dockerfile
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc \
    npm install
```

```bash
# Pass secret at build time
docker buildx build --secret id=npmrc,src=.npmrc -t myapp .
```

### SSH Mount — Private Git Repos

```dockerfile
RUN --mount=type=ssh \
    git clone git@github.com:org/private-repo.git
```

```bash
eval $(ssh-agent) && ssh-add ~/.ssh/id_ed25519
docker buildx build --ssh default -t myapp .
```

---

## Heredoc Syntax

```dockerfile
# syntax=docker/dockerfile:1

# Multi-command RUN
RUN <<EOF
apt-get update
apt-get install -y curl wget
rm -rf /var/lib/apt/lists/*
EOF

# Inline file creation
COPY <<EOF /etc/myconfig.conf
key=value
debug=false
EOF
```

---

## Multi-Platform Builds

```bash
# Build for amd64 + arm64 and push manifest list
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --push \
  -t registry/image:latest .

# Use BUILDPLATFORM to avoid slow emulation
FROM --platform=$BUILDPLATFORM golang:1.22 AS build
ARG TARGETARCH
RUN GOARCH=$TARGETARCH go build -o /server .
```

---

## Docker Build Cloud

```bash
# Create a cloud builder
docker buildx create --driver cloud ORG/BUILDERNAME

# Build using cloud builder
docker buildx build \
  --builder cloud-ORG-BUILDERNAME \
  --platform linux/amd64,linux/arm64 \
  --push \
  -t registry/image:latest .
```

---

## Docker Scout

```bash
# Quick vulnerability summary
docker scout quickview IMAGE

# Full CVE list
docker scout cves IMAGE

# Filter by severity + only fixable
docker scout cves --only-severity critical,high --only-fixed IMAGE

# Suggest better base image
docker scout recommendations IMAGE

# Compare two image versions
docker scout compare IMAGE:old IMAGE:new

# Generate SBOM
docker scout sbom IMAGE
docker scout sbom --format spdx-json IMAGE > sbom.spdx.json
docker scout sbom --format cyclonedx IMAGE > sbom.cyclonedx.json

# Evaluate against policies
docker scout policy IMAGE

# Exit non-zero if critical CVEs found (for CI gates)
docker scout cves --exit-code --only-severity critical IMAGE
```

---

## Scout CVE Severity Reference

| Level | Meaning | Typical Action |
|-------|---------|---------------|
| Critical | Easily exploitable, high impact | Block deployment immediately |
| High | Significant risk | Fix before next release |
| Medium | Limited exploitability | Track and fix |
| Low | Minimal risk | Address in maintenance windows |

---

## Alternative Scanning Tools

```bash
# Trivy — open-source, scan image
trivy image nginx:1.25

# Trivy — scan local filesystem
trivy fs .

# Trivy — generate SBOM
trivy image --format cyclonedx IMAGE > sbom.json

# Grype — open-source CVE scanner
grype IMAGE

# Syft — SBOM generation only
syft IMAGE -o spdx-json > sbom.json
```

---

## Common Patterns Quick Reference

```dockerfile
# Production-ready BuildKit Dockerfile skeleton
# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base
WORKDIR /app

FROM base AS deps
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    pip install -r requirements.txt

FROM base AS final
COPY --from=deps /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY . .
USER nobody
CMD ["python", "app.py"]
```

---

## 📂 Navigation

| | |
|---|---|
| **Previous** | [15_Best_Practices](../15_Best_Practices/Cheatsheet.md) |
| **Next** | [17_Docker_Init_and_Debug](../17_Docker_Init_and_Debug/Cheatsheet.md) |
| **Theory** | [Theory.md](./Theory.md) |
| **Interview Q&A** | [Interview_QA.md](./Interview_QA.md) |
| **Code Examples** | [Code_Example.md](./Code_Example.md) |
| **Module Index** | [01_Docker README](../README.md) |
