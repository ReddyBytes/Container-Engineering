# Docker Registry — Cheatsheet

## Registry Authentication

```bash
# Login to Docker Hub
docker login

# Login to Docker Hub with credentials
docker login -u myusername -p mypassword

# Login to AWS ECR (get temp token via AWS CLI)
aws ecr get-login-password --region us-east-1 \
  | docker login --username AWS --password-stdin \
    123456789012.dkr.ecr.us-east-1.amazonaws.com

# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io \
  --username MY_GITHUB_USER --password-stdin

# Login to self-hosted registry
docker login harbor.company.com

# Logout
docker logout
docker logout harbor.company.com
```

---

## Tagging Images

```bash
# Tag during build
docker build -t my-app:v1.0.0 .

# Re-tag an existing image
docker tag my-app:v1.0.0 ghcr.io/my-org/my-app:v1.0.0

# Tag with multiple tags (semver + SHA + latest)
docker tag my-app:v1.0.0 ghcr.io/my-org/my-app:v1.0.0
docker tag my-app:v1.0.0 ghcr.io/my-org/my-app:v1
docker tag my-app:v1.0.0 ghcr.io/my-org/my-app:latest

# Tag with git SHA
docker build -t my-app:$(git rev-parse --short HEAD) .
```

---

## Pushing and Pulling

```bash
# Push image
docker push ghcr.io/my-org/my-app:v1.0.0

# Push all tags for an image
docker push ghcr.io/my-org/my-app --all-tags

# Pull image
docker pull ghcr.io/my-org/my-app:v1.0.0

# Pull specific digest (truly immutable)
docker pull my-app@sha256:abc123...

# Inspect remote image without pulling
docker manifest inspect ghcr.io/my-org/my-app:v1.0.0
```

---

## ECR Quick Reference

```bash
# Create repository
aws ecr create-repository --repository-name my-app --region us-east-1

# List repositories
aws ecr describe-repositories --region us-east-1

# List images in a repo
aws ecr list-images --repository-name my-app --region us-east-1

# Delete image
aws ecr batch-delete-image \
  --repository-name my-app \
  --image-ids imageTag=v1.0.0

# Enable scan on push
aws ecr put-image-scanning-configuration \
  --repository-name my-app \
  --image-scanning-configuration scanOnPush=true

# Get scan results
aws ecr describe-image-scan-findings \
  --repository-name my-app \
  --image-id imageTag=v1.0.0

# Set lifecycle policy (keep only last 10 images)
aws ecr put-lifecycle-policy \
  --repository-name my-app \
  --lifecycle-policy-text file://lifecycle-policy.json
```

---

## Vulnerability Scanning

```bash
# Docker Scout — quick view
docker scout quickview my-app:v1.0.0

# Docker Scout — full CVE list
docker scout cves my-app:v1.0.0

# Docker Scout — compare versions
docker scout compare my-app:v1.0.0 --to my-app:v1.0.1

# Trivy — scan image
trivy image my-app:v1.0.0

# Trivy — scan only HIGH/CRITICAL
trivy image --severity HIGH,CRITICAL my-app:v1.0.0

# Trivy — fail CI if CRITICAL found
trivy image --exit-code 1 --severity CRITICAL my-app:v1.0.0

# Trivy — scan Dockerfile for misconfigurations
trivy config ./Dockerfile
```

---

## Image Naming Convention

```
registry/namespace/repository:tag

Examples:
  nginx:1.25                                        # Docker Hub official
  bitnami/postgresql:16.2                           # Docker Hub vendor
  ghcr.io/my-org/my-app:v1.0.0                     # GHCR
  123456789.dkr.ecr.us-east-1.amazonaws.com/app:1  # ECR
  harbor.company.com/production/api:2025-01-15      # Harbor
```

---

## Tagging Strategy Reference

| Strategy | Example | Use Case |
|----------|---------|----------|
| Semver | `v1.2.3` | Public APIs, versioned releases |
| Git SHA | `a3f9b2c` | CI/CD, internal deployments |
| Date | `2025-01-15` | Nightly builds |
| Branch | `main`, `feature-x` | Preview environments |
| `latest` | `latest` | **Local dev only, never production** |

---

## Credentials File

```bash
# View stored credentials
cat ~/.docker/config.json

# Use credential store instead of plain text
# Install docker-credential-osxkeychain (macOS)
# or docker-credential-secretservice (Linux)
```

---

## 📂 Navigation

| | Link |
|---|---|
| Previous | [09 · Docker Compose](../09_Docker_Compose/Cheatsheet.md) |
| Theory | [Registry Theory](./Theory.md) |
| Interview Q&A | [Registry Interview Q&A](./Interview_QA.md) |
| Next | [11 · Multi-Stage Builds](../11_Multi_Stage_Builds/Cheatsheet.md) |
