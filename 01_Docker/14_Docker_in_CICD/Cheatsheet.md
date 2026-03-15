# Docker in CI/CD — Cheatsheet

## Core GitHub Actions for Docker

```yaml
# Setup Buildx (required for caching and multi-platform)
- uses: docker/setup-buildx-action@v3

# Setup QEMU (required for arm64 emulation on amd64 runners)
- uses: docker/setup-qemu-action@v3

# Login to GHCR
- uses: docker/login-action@v3
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}

# Login to Docker Hub
- uses: docker/login-action@v3
  with:
    username: ${{ secrets.DOCKERHUB_USERNAME }}
    password: ${{ secrets.DOCKERHUB_TOKEN }}

# Login to ECR
- uses: aws-actions/amazon-ecr-login@v2

# Build and push
- uses: docker/build-push-action@v5
  with:
    context: .
    push: true
    tags: ghcr.io/my-org/app:${{ github.sha }}
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

---

## Smart Tagging with metadata-action

```yaml
- name: Docker metadata
  id: meta
  uses: docker/metadata-action@v5
  with:
    images: ghcr.io/my-org/app
    tags: |
      type=semver,pattern={{version}}
      type=semver,pattern={{major}}.{{minor}}
      type=sha
      type=ref,event=branch
      type=ref,event=pr

- name: Build and push
  uses: docker/build-push-action@v5
  with:
    tags: ${{ steps.meta.outputs.tags }}
    labels: ${{ steps.meta.outputs.labels }}
```

---

## Caching Strategies

```yaml
# GitHub Actions cache (fastest, no registry storage)
cache-from: type=gha
cache-to: type=gha,mode=max

# Registry cache (works across different CI systems)
cache-from: type=registry,ref=ghcr.io/my-org/app:buildcache
cache-to: type=registry,ref=ghcr.io/my-org/app:buildcache,mode=max

# Inline cache (embed cache metadata in the image itself)
# Requires: --build-arg BUILDKIT_INLINE_CACHE=1
cache-from: type=registry,ref=ghcr.io/my-org/app:latest
```

---

## Multi-Platform Builds

```yaml
- uses: docker/setup-qemu-action@v3
- uses: docker/setup-buildx-action@v3
- uses: docker/build-push-action@v5
  with:
    platforms: linux/amd64,linux/arm64
    push: true
    tags: ghcr.io/my-org/app:v1.0.0
```

```bash
# Local multi-platform build
docker buildx create --use --name multibuilder
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --push \
  -t ghcr.io/my-org/app:v1.0.0 \
  .
```

---

## Testing in CI

```yaml
# Build + test in one step
- run: |
    docker build --target tester -t app:test .
    docker run --rm app:test

# Build, test, then push only if tests pass
- run: docker build -t app:ci .
- run: docker run --rm app:ci npm test
- run: |
    docker tag app:ci ghcr.io/my-org/app:${{ github.sha }}
    docker push ghcr.io/my-org/app:${{ github.sha }}
```

---

## Vulnerability Scanning in CI

```yaml
# Trivy — fail on CRITICAL
- name: Scan image
  run: |
    trivy image \
      --exit-code 1 \
      --severity CRITICAL \
      --no-progress \
      ghcr.io/my-org/app:${{ github.sha }}

# Docker Scout
- name: Scout quickview
  uses: docker/scout-action@v1
  with:
    command: quickview
    image: ghcr.io/my-org/app:${{ github.sha }}
    sarif-file: scout-results.sarif

# Upload SARIF to GitHub Security tab
- uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: scout-results.sarif
```

---

## AWS ECR with OIDC (No Static Credentials)

```yaml
permissions:
  id-token: write
  contents: read

- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::123456789012:role/github-actions
    aws-region: us-east-1

- name: Login to ECR
  id: ecr-login
  uses: aws-actions/amazon-ecr-login@v2

- name: Build and push to ECR
  uses: docker/build-push-action@v5
  with:
    push: true
    tags: ${{ steps.ecr-login.outputs.registry }}/my-app:${{ github.sha }}
```

---

## Tag Reference

| Git Event | Tag Example | Pattern |
|---|---|---|
| Push to main | `sha-a3f9b2c` | `type=sha` |
| Push to main | `main` | `type=ref,event=branch` |
| Git tag `v1.2.3` | `v1.2.3`, `v1.2`, `v1` | `type=semver,pattern={{version}}` |
| Pull request | `pr-42` | `type=ref,event=pr` |

---

## 📂 Navigation

| | Link |
|---|---|
| Previous | [13 · Docker Swarm](../13_Docker_Swarm/Cheatsheet.md) |
| Theory | [CI/CD Theory](./Theory.md) |
| Interview Q&A | [CI/CD Interview Q&A](./Interview_QA.md) |
| Code Examples | [CI/CD Code Examples](./Code_Example.md) |
| Next | [15 · Best Practices](../15_Best_Practices/Cheatsheet.md) |
