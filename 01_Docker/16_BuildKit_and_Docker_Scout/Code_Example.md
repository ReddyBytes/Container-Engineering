# Module 16 — BuildKit and Docker Scout: Code Examples

## Example 1: Dockerfile with BuildKit Cache Mounts (Python + apt)

This Dockerfile uses cache mounts so that neither pip downloads nor apt packages are re-fetched on every build, while keeping both out of the final image.

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

WORKDIR /app

# Install system dependencies with apt cache mounts
# sharing=locked prevents corruption when multiple builds run in parallel
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies with pip cache mount
# The cache persists on the build host but never enters the image
FROM base AS deps
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# Final stage: lean production image
FROM base AS final
# Copy installed packages from deps stage
COPY --from=deps /usr/local/lib/python3.12/site-packages \
                 /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

COPY src/ ./src/

# Run as non-root user
RUN useradd --no-create-home --uid 1001 appuser
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build command:
```bash
docker buildx build -t myapp:latest .
```

On the first build, packages are downloaded normally. On subsequent builds, pip finds its cache at `/root/.cache/pip` on the build host and skips re-downloading packages that haven't changed — even if `requirements.txt` was modified (only the changed packages are downloaded).

---

## Example 2: Dockerfile Using Build Secrets (Node.js with private registry)

The `.npmrc` file contains a private registry token. We never want this in the image.

```dockerfile
# syntax=docker/dockerfile:1
FROM node:20-slim AS deps

WORKDIR /app
COPY package.json package-lock.json ./

# The secret is available ONLY during this RUN step
# It is never written to any layer — docker history shows nothing
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc \
    npm ci --only=production

# Final production image
FROM node:20-slim AS final
WORKDIR /app

# Copy only production node_modules
COPY --from=deps /app/node_modules ./node_modules
COPY src/ ./src/
COPY package.json .

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 --ingroup nodejs nodeuser
USER nodeuser

EXPOSE 3000
CMD ["node", "src/server.js"]
```

Your local `.npmrc`:
```ini
@myorg:registry=https://npm.pkg.github.com
//npm.pkg.github.com/:_authToken=ghp_xxxxxxxxxxxxxxxxxxxx
```

Build command:
```bash
# The --secret flag reads the file but never puts it in the image
docker buildx build \
  --secret id=npmrc,src=.npmrc \
  -t myapp:latest .
```

Verify the secret is not in the image:
```bash
# This will show nothing related to the npmrc or token
docker history myapp:latest

# The token will not appear anywhere
docker run --rm myapp:latest cat /root/.npmrc 2>&1
# => cat: /root/.npmrc: No such file or directory
```

---

## Example 3: Multi-Platform Build with buildx

Build a Go application for both Intel servers and ARM-based AWS Graviton or Apple Silicon:

```dockerfile
# syntax=docker/dockerfile:1

# Builder stage runs on the build machine's native architecture
# BUILDPLATFORM = architecture of the machine running the build
# TARGETPLATFORM = architecture of the final image
FROM --platform=$BUILDPLATFORM golang:1.22-alpine AS build

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .

# Cross-compile for the target architecture without QEMU emulation
ARG TARGETARCH
ARG TARGETOS
RUN CGO_ENABLED=0 GOOS=$TARGETOS GOARCH=$TARGETARCH \
    go build -ldflags="-w -s" -o /server ./cmd/server

# Minimal final image — no OS, no shell
FROM gcr.io/distroless/static:nonroot
COPY --from=build /server /server
USER nonroot:nonroot
EXPOSE 8080
ENTRYPOINT ["/server"]
```

Build commands:
```bash
# Create a builder with multi-platform support (first time only)
docker buildx create --name multiplatform --use
docker buildx inspect --bootstrap

# Build and push manifest list for both architectures
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --push \
  -t registry.example.com/myapp:latest \
  -t registry.example.com/myapp:v1.2.3 \
  .

# Verify the manifest
docker buildx imagetools inspect registry.example.com/myapp:latest
```

Expected output from `imagetools inspect`:
```
Name:      registry.example.com/myapp:latest
MediaType: application/vnd.oci.image.index.v1+json
Digest:    sha256:abc123...

Manifests:
  Name:      registry.example.com/myapp:latest@sha256:def456...
  MediaType: application/vnd.oci.image.manifest.v1+json
  Platform:  linux/amd64

  Name:      registry.example.com/myapp:latest@sha256:ghi789...
  MediaType: application/vnd.oci.image.manifest.v1+json
  Platform:  linux/arm64
```

---

## Example 4: Docker Scout Scanning Commands

```bash
# ── Quick Overview ─────────────────────────────────────────────────────────

# Instant summary: CVE count by severity, base image, size
docker scout quickview myapp:latest

# Scan a public image
docker scout quickview nginx:1.24

# ── CVE Scanning ───────────────────────────────────────────────────────────

# List all CVEs
docker scout cves myapp:latest

# Only show Critical and High
docker scout cves --only-severity critical,high myapp:latest

# Only show vulnerabilities that have a fix available
docker scout cves --only-fixed myapp:latest

# Combined: critical/high + fixable only (useful pre-deploy gate)
docker scout cves --only-severity critical,high --only-fixed myapp:latest

# Output as JSON (for processing in scripts)
docker scout cves --format json myapp:latest > cve-report.json

# ── CI Gate: Fail Build on Critical CVEs ───────────────────────────────────

# Exit with code 1 if any critical CVEs are found
docker scout cves --exit-code --only-severity critical myapp:latest
echo "Exit code: $?"

# ── Recommendations ────────────────────────────────────────────────────────

# Suggest a base image upgrade that reduces CVE count
docker scout recommendations myapp:latest

# ── Comparison ─────────────────────────────────────────────────────────────

# Compare old vs new: did we add or fix vulnerabilities?
docker scout compare myapp:1.0.0 myapp:2.0.0

# ── SBOM Generation ────────────────────────────────────────────────────────

# Human-readable SBOM
docker scout sbom myapp:latest

# Export as SPDX JSON (government/enterprise compliance)
docker scout sbom --format spdx-json myapp:latest > sbom.spdx.json

# Export as CycloneDX (OWASP standard)
docker scout sbom --format cyclonedx myapp:latest > sbom.cyclonedx.json

# ── Policy Evaluation ──────────────────────────────────────────────────────

# Evaluate against org policies (configured in Docker Scout dashboard)
docker scout policy myapp:latest --org myorg
```

---

## Example 5: GitHub Actions Workflow with BuildKit Registry Cache

Complete CI workflow: build with full registry cache, multi-platform, push to GitHub Container Registry, then scan with Docker Scout.

```yaml
# .github/workflows/docker-build.yml
name: Build and Scan

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
      id-token: write  # For Scout OIDC auth

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      # Set up QEMU for multi-platform builds (arm64 emulation)
      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3

      # Set up BuildKit builder
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      # Log in to GitHub Container Registry
      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      # Generate image metadata (tags + labels)
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=sha,prefix=sha-
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=raw,value=latest,enable={{is_default_branch}}

      # Build and push with registry cache
      # --cache-from: pull cache from previous build
      # --cache-to: push new cache after build (mode=max caches all stages)
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          platforms: linux/amd64,linux/arm64
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=registry,ref=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:cache
          cache-to: type=registry,ref=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:cache,mode=max
          secrets: |
            npmrc=${{ secrets.NPMRC_FILE }}

      # Scan with Docker Scout — fail on critical CVEs
      - name: Docker Scout CVE scan
        uses: docker/scout-action@v1
        with:
          command: cves
          image: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
          only-severities: critical,high
          exit-code: true
          # Post results as PR comment
          github-token: ${{ secrets.GITHUB_TOKEN }}

      # Generate and upload SBOM as workflow artifact
      - name: Generate SBOM
        uses: docker/scout-action@v1
        with:
          command: sbom
          image: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
          format: spdx-json
          output: sbom.spdx.json

      - name: Upload SBOM artifact
        uses: actions/upload-artifact@v4
        with:
          name: sbom
          path: sbom.spdx.json
```

This workflow:
1. Sets up QEMU for arm64 cross-compilation
2. Builds for both `linux/amd64` and `linux/arm64`
3. Pulls the previous build's cache from the registry, pushes the new cache after
4. On main branch pushes: also scans with Scout and fails if Critical/High CVEs exist
5. Generates and saves an SBOM as a workflow artifact for compliance

---

## 📂 Navigation

| | |
|---|---|
| **Previous** | [15_Best_Practices](../15_Best_Practices/Code_Example.md) |
| **Next** | [17_Docker_Init_and_Debug](../17_Docker_Init_and_Debug/Code_Example.md) |
| **Theory** | [Theory.md](./Theory.md) |
| **Cheatsheet** | [Cheatsheet.md](./Cheatsheet.md) |
| **Interview Q&A** | [Interview_QA.md](./Interview_QA.md) |
| **Module Index** | [01_Docker README](../README.md) |
