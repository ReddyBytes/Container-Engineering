# Docker Registry — Code Examples

All examples are production-quality with detailed comments explaining every decision.

---

## 1. Image Naming, Tagging, and Pushing — Full Workflow

A complete push workflow covering Docker Hub, GHCR, and the tagging conventions that prevent production incidents.

```bash
# ============================================================
# IMAGE NAMING ANATOMY
# registry/namespace/repository:tag
# ============================================================

# Docker Hub: registry is implicit (docker.io)
# 'library' namespace is implicit for official images
docker pull nginx:1.25.5                          # = docker.io/library/nginx:1.25.5
docker pull bitnami/postgresql:16.2               # = docker.io/bitnami/postgresql:16.2

# GHCR: registry prefix required
docker pull ghcr.io/my-org/backend:v1.0.0

# ECR: account + region are part of the registry hostname
docker pull 123456789.dkr.ecr.us-east-1.amazonaws.com/my-app:v1.0.0

# ============================================================
# TAGGING STRATEGY: apply multiple tags to the same image
# docker tag does NOT copy the image — it just adds a new name pointer
# ============================================================
GIT_SHA=$(git rev-parse --short HEAD)   # e.g., a3f9b2c — immutable, traceable
VERSION="v1.2.3"                        # semver — human-readable, communicates severity
REGISTRY="ghcr.io/my-org"
IMAGE="my-app"

# Build once, tag multiple ways
docker build -t "${IMAGE}:${VERSION}" .

# Immutable tags — point to a specific build forever
docker tag "${IMAGE}:${VERSION}" "${REGISTRY}/${IMAGE}:${GIT_SHA}"   # exact commit
docker tag "${IMAGE}:${VERSION}" "${REGISTRY}/${IMAGE}:${VERSION}"   # semver

# Mutable "floating" tags — intentionally update to point to latest of a channel
docker tag "${IMAGE}:${VERSION}" "${REGISTRY}/${IMAGE}:v1"           # latest v1.x.x
docker tag "${IMAGE}:${VERSION}" "${REGISTRY}/${IMAGE}:latest"       # latest overall

# Push all four tags — they all reference the same image digest (one upload)
docker push "${REGISTRY}/${IMAGE}:${GIT_SHA}"
docker push "${REGISTRY}/${IMAGE}:${VERSION}"
docker push "${REGISTRY}/${IMAGE}:v1"
docker push "${REGISTRY}/${IMAGE}:latest"

# In deployment: reference the immutable tag — not latest
# kubectl set image deployment/my-app my-app=ghcr.io/my-org/my-app:a3f9b2c
```

---

## 2. AWS ECR — Full Lifecycle: Create, Push, Lifecycle Policy

The complete AWS ECR workflow from repository creation through automated cleanup of old images.

```bash
# ============================================================
# SETUP: variables used throughout
# ============================================================
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION="us-east-1"
REPO_NAME="my-app"
ECR_HOST="${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# ============================================================
# STEP 1: Create the ECR repository
# --image-scanning-configuration: automatically scan every pushed image
# --encryption-configuration: AES256 is default; use KMS for compliance
# ============================================================
aws ecr create-repository \
  --repository-name "$REPO_NAME" \
  --region "$AWS_REGION" \
  --image-scanning-configuration scanOnPush=true \
  --encryption-configuration encryptionType=AES256

# ============================================================
# STEP 2: Authenticate Docker to ECR
# ECR tokens are valid for 12 hours — refresh in CI with each job
# --password-stdin: reads from stdin, never exposes token in process list
# ============================================================
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login \
    --username AWS \
    --password-stdin \
    "$ECR_HOST"

# ============================================================
# STEP 3: Build, tag, and push
# ============================================================
docker build -t "${REPO_NAME}:v1.0.0" .

docker tag "${REPO_NAME}:v1.0.0" "${ECR_HOST}/${REPO_NAME}:v1.0.0"
docker push "${ECR_HOST}/${REPO_NAME}:v1.0.0"

# ============================================================
# STEP 4: Set a lifecycle policy to auto-delete old images
# Without this, ECR fills up — you pay for every GB stored
# This policy: keep the 10 most recent images tagged with 'v*'; delete untagged after 1 day
# ============================================================
aws ecr put-lifecycle-policy \
  --repository-name "$REPO_NAME" \
  --lifecycle-policy '{
    "rules": [
      {
        "rulePriority": 1,
        "description": "Keep last 10 release images",
        "selection": {
          "tagStatus": "tagged",
          "tagPrefixList": ["v"],
          "countType": "imageCountMoreThan",
          "countNumber": 10
        },
        "action": { "type": "expire" }
      },
      {
        "rulePriority": 2,
        "description": "Delete untagged images after 1 day",
        "selection": {
          "tagStatus": "untagged",
          "countType": "sinceImagePushed",
          "countUnit": "days",
          "countNumber": 1
        },
        "action": { "type": "expire" }
      }
    ]
  }'

# ============================================================
# STEP 5: View scan results after push
# ECR scans in the background — check after a minute or two
# ============================================================
aws ecr describe-image-scan-findings \
  --repository-name "$REPO_NAME" \
  --image-id imageTag=v1.0.0 \
  --region "$AWS_REGION" \
  | python3 -m json.tool | grep -E '"severity"|"name"' | head -20
```

---

## 3. GitHub Container Registry (GHCR) — CI/CD Integration

GHCR is tightly coupled to GitHub Actions. This example shows the production pattern for pushing images in a CI workflow.

```yaml
# .github/workflows/build-push.yml
# Triggered on every push to main and on version tags (v*)

name: Build and Push to GHCR

on:
  push:
    branches: [main]
    tags: ["v*.*.*"]       # triggers on v1.2.3, v2.0.0, etc.
  pull_request:
    branches: [main]       # build but don't push on PRs

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}   # e.g., my-org/my-app

jobs:
  build-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write        # required to push to GHCR

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      # Login to GHCR using the built-in GITHUB_TOKEN
      # No secrets to manage — token is scoped to this repo and expires after job
      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      # Generate tags automatically:
      # - On main push: ghcr.io/org/app:main + ghcr.io/org/app:sha-a3f9b2c
      # - On tag v1.2.3: ghcr.io/org/app:1.2.3 + ghcr.io/org/app:1.2 + ghcr.io/org/app:latest
      - name: Extract metadata for Docker
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha,prefix=sha-

      # Build with BuildKit (faster, better caching) and push
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: ${{ github.event_name != 'pull_request' }}   # only push on non-PR events
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha       # use GitHub Actions cache for layer caching
          cache-to: type=gha,mode=max
```

```bash
# After the workflow runs, pull the image using any of the generated tags:
docker pull ghcr.io/my-org/my-app:main        # latest from main branch
docker pull ghcr.io/my-org/my-app:1.2.3       # exact semver
docker pull ghcr.io/my-org/my-app:sha-a3f9b2c # exact commit, immutable
```

---

## 4. Image Vulnerability Scanning with Trivy

Scan images before pushing and fail the build if critical vulnerabilities are found. Use in CI to enforce a security gate.

```bash
# ============================================================
# INSTALL TRIVY
# ============================================================
# macOS
brew install trivy

# Linux (Debian/Ubuntu)
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh \
  | sudo sh -s -- -b /usr/local/bin v0.50.0

# ============================================================
# BASIC SCAN: scan an image for OS and language CVEs
# ============================================================
trivy image python:3.11-slim
# TABLE output: Package | Vulnerability ID | Severity | Installed | Fixed | Title

# ============================================================
# SEVERITY FILTER: only report HIGH and CRITICAL
# These are the ones that require immediate action
# ============================================================
trivy image --severity HIGH,CRITICAL python:3.11-slim

# ============================================================
# CI GATE: exit code 1 if any CRITICAL CVEs found
# Use this as a required check before pushing
# ============================================================
trivy image \
  --exit-code 1 \
  --severity CRITICAL \
  --no-progress \
  my-app:v1.0.0
# Returns exit code 0 if no CRITICAL found (CI passes)
# Returns exit code 1 if CRITICAL found (CI fails — block the push)

# ============================================================
# DOCKERFILE MISCONFIGURATION SCAN
# Catches: running as root, no USER, using 'latest', no HEALTHCHECK
# ============================================================
trivy config ./Dockerfile

# ============================================================
# COMPARE BASE IMAGES to find the smallest attack surface
# ============================================================
for tag in "python:3.11" "python:3.11-slim" "python:3.11-alpine"; do
  echo "=== $tag ==="
  trivy image --severity CRITICAL,HIGH --no-progress "$tag" 2>/dev/null \
    | tail -3
done
# Helps you pick the base image with the fewest CVEs

# ============================================================
# DOCKER SCOUT (built into Docker Desktop)
# ============================================================
# Quick summary view
docker scout quickview my-app:v1.0.0

# Full CVE list with remediation advice
docker scout cves my-app:v1.0.0

# Only show vulnerabilities with available fixes (actionable)
docker scout cves --only-fixed my-app:v1.0.0

# Compare two versions to see if a rebuild improved things
docker scout compare my-app:v1.0.0 --to my-app:v1.0.1
```

---

## 5. Local Private Registry — Harbor or docker/registry

Run a local registry for air-gapped environments, offline development, or testing push/pull flows without hitting Docker Hub rate limits.

```bash
# ============================================================
# OPTION A: Minimal local registry (development only)
# Uses the official 'registry:2' image — no auth, no UI, no scanning
# Only for local/dev use — not for production
# ============================================================
docker run -d \
  --name local-registry \
  --restart always \
  -p 5000:5000 \
  -v registry-data:/var/lib/registry \   # ← named volume: data persists across restarts
  registry:2

# Tag and push to the local registry
docker tag nginx:alpine localhost:5000/nginx:alpine
docker push localhost:5000/nginx:alpine

# Pull from the local registry
docker pull localhost:5000/nginx:alpine

# List all repositories in the local registry (Registry v2 API)
curl http://localhost:5000/v2/_catalog
# {"repositories":["nginx"]}

# List tags for a specific repository
curl http://localhost:5000/v2/nginx/tags/list
# {"name":"nginx","tags":["alpine"]}

# ============================================================
# OPTION B: Harbor (production self-hosted registry)
# Harbor adds: auth, RBAC, image scanning, replication, audit logs
# Deploy via Docker Compose using the official installer
# ============================================================

# Download the Harbor installer
curl -LO https://github.com/goharbor/harbor/releases/download/v2.10.0/harbor-online-installer-v2.10.0.tgz
tar xvf harbor-online-installer-v2.10.0.tgz
cd harbor

# Edit harbor.yml: set hostname, TLS cert paths, admin password
cp harbor.yml.tmpl harbor.yml
# Minimum required edits:
#   hostname: harbor.mycompany.com
#   certificate: /your/cert/server.crt
#   private_key: /your/cert/server.key

# Run the install script (generates docker-compose.yml + configs, then starts services)
sudo ./install.sh --with-trivy   # --with-trivy enables built-in vulnerability scanning

# After install, push to Harbor:
docker login harbor.mycompany.com
docker tag my-app:v1.0.0 harbor.mycompany.com/production/my-app:v1.0.0
docker push harbor.mycompany.com/production/my-app:v1.0.0
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

⬅️ **Prev:** [09 — Docker Compose](../09_Docker_Compose/Code_Example.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [11 — Multi-Stage Builds](../11_Multi_Stage_Builds/Code_Example.md)
🏠 **[Home](../../README.md)**
