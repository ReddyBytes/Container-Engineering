# Docker in CI/CD — Code Examples

---

## Example 1: Complete GitHub Actions Workflow — Build, Test, Push to GHCR

```yaml
# .github/workflows/docker.yml
name: Build, Test, and Push

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

# Required for GHCR push (packages:write)
permissions:
  contents: read
  packages: write

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}   # e.g., my-org/my-app

jobs:
  build-test-push:
    runs-on: ubuntu-latest

    steps:
      # --------------------------------------------------------
      # Step 1: Check out the repository
      # --------------------------------------------------------
      - name: Checkout code
        uses: actions/checkout@v4

      # --------------------------------------------------------
      # Step 2: Set up Docker Buildx
      # Required for BuildKit features: caching, multi-platform
      # --------------------------------------------------------
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      # --------------------------------------------------------
      # Step 3: Generate image tags and labels
      # Creates: ghcr.io/my-org/my-app:sha-a3f9b2c
      #          ghcr.io/my-org/my-app:main (on main branch)
      #          ghcr.io/my-org/my-app:v1.2.3 (on git tag)
      # --------------------------------------------------------
      - name: Docker metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=sha
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}

      # --------------------------------------------------------
      # Step 4: Run the test suite BEFORE building the final image
      # Build to the test stage, run tests, fail fast if they fail
      # --------------------------------------------------------
      - name: Run tests
        run: |
          docker build \
            --target tester \
            --cache-from type=gha \
            -t my-app:test \
            .
          docker run --rm my-app:test

      # --------------------------------------------------------
      # Step 5: Authenticate to GHCR
      # Uses GITHUB_TOKEN — no extra secrets needed
      # Only run on main branch push, not on PRs
      # --------------------------------------------------------
      - name: Log in to GHCR
        if: github.event_name != 'pull_request'
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      # --------------------------------------------------------
      # Step 6: Build and push the production image
      # Only push on main branch (not on PRs)
      # Uses GitHub Actions cache for fast layer caching
      # --------------------------------------------------------
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      # --------------------------------------------------------
      # Step 7: Scan for vulnerabilities
      # Fails the job if CRITICAL CVEs are found
      # --------------------------------------------------------
      - name: Scan for vulnerabilities
        if: github.event_name != 'pull_request'
        run: |
          docker run --rm \
            -v /var/run/docker.sock:/var/run/docker.sock \
            aquasec/trivy:latest image \
              --exit-code 1 \
              --severity CRITICAL \
              --no-progress \
              ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:sha-${{ github.sha }}

      # --------------------------------------------------------
      # Step 8: Print the image digest for traceability
      # --------------------------------------------------------
      - name: Image summary
        if: github.event_name != 'pull_request'
        run: |
          echo "### Docker Image" >> $GITHUB_STEP_SUMMARY
          echo "**Tags:** ${{ steps.meta.outputs.tags }}" >> $GITHUB_STEP_SUMMARY
          echo "**Digest:** ${{ steps.build-push.outputs.digest }}" >> $GITHUB_STEP_SUMMARY
```

---

## Example 2: Multi-Platform Build Workflow

```yaml
# .github/workflows/multiplatform.yml
name: Multi-Platform Build

on:
  push:
    tags:
      - 'v*'   # Only build multi-platform on version tags (expensive)

permissions:
  contents: read
  packages: write

jobs:
  build-multiplatform:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      # --------------------------------------------------------
      # QEMU enables emulation of arm64 on the amd64 runner
      # Without this, arm64 builds fail
      # --------------------------------------------------------
      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3

      # --------------------------------------------------------
      # Buildx is required for multi-platform builds
      # --------------------------------------------------------
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Generate metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository }}
          tags: |
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=semver,pattern={{major}}

      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      # --------------------------------------------------------
      # Build for both architectures simultaneously
      # Docker creates a manifest list — one tag serves both
      # A Mac (arm64) pulls the arm64 image automatically
      # An EC2 instance (amd64) pulls the amd64 image automatically
      # --------------------------------------------------------
      - name: Build and push multi-platform
        uses: docker/build-push-action@v5
        with:
          context: .
          platforms: linux/amd64,linux/arm64
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          # Registry cache for cross-run persistence
          cache-from: type=registry,ref=ghcr.io/${{ github.repository }}:buildcache
          cache-to: type=registry,ref=ghcr.io/${{ github.repository }}:buildcache,mode=max
```

---

## Example 3: Full Pipeline with Layer Caching Comparison

```yaml
# .github/workflows/caching-demo.yml
name: Build with Caching

on: [push]

permissions:
  contents: read
  packages: write

jobs:
  # -------------------------------------------------------
  # Option A: GitHub Actions cache (recommended for most teams)
  # -------------------------------------------------------
  build-gha-cache:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3

      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build with GHA cache
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.sha }}
          # type=gha uses GitHub's built-in Actions cache
          # mode=max caches ALL layers including intermediate stages
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # -------------------------------------------------------
  # Option B: Registry cache (useful for self-hosted runners
  # or when sharing cache across different CI systems)
  # -------------------------------------------------------
  build-registry-cache:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3

      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build with registry cache
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.sha }}
          # Pull cached layers from the registry before building
          cache-from: type=registry,ref=ghcr.io/${{ github.repository }}:cache
          # Push updated cache back to the registry after building
          cache-to: type=registry,ref=ghcr.io/${{ github.repository }}:cache,mode=max
```

---

## Example 4: Deploy to Kubernetes After Push

```yaml
# .github/workflows/deploy.yml
name: Build, Push, Deploy

on:
  push:
    branches: [main]

permissions:
  contents: read
  packages: write

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    environment: production   # Requires approval in GitHub environments settings

    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3

      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:${{ github.sha }}
            ghcr.io/${{ github.repository }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max

      # --------------------------------------------------------
      # Deploy to Kubernetes by updating the image tag
      # KUBECONFIG secret contains the cluster kubeconfig
      # --------------------------------------------------------
      - name: Set up kubectl
        uses: azure/setup-kubectl@v3

      - name: Deploy to Kubernetes
        run: |
          # Write kubeconfig from secret
          echo "${{ secrets.KUBECONFIG }}" > /tmp/kubeconfig
          export KUBECONFIG=/tmp/kubeconfig

          # Update the deployment image
          kubectl set image deployment/my-app \
            app=ghcr.io/${{ github.repository }}:${{ github.sha }} \
            --namespace production

          # Wait for the rollout to complete
          kubectl rollout status deployment/my-app \
            --namespace production \
            --timeout=300s

          # Show what's running
          kubectl get pods --namespace production -l app=my-app

      - name: Deployment summary
        run: |
          echo "### Deployed" >> $GITHUB_STEP_SUMMARY
          echo "Image: \`ghcr.io/${{ github.repository }}:${{ github.sha }}\`" >> $GITHUB_STEP_SUMMARY
          echo "Commit: ${{ github.sha }}" >> $GITHUB_STEP_SUMMARY
          echo "Deployed at: $(date -u)" >> $GITHUB_STEP_SUMMARY
```

---

## Dockerfile for CI/CD (with test stage)

```dockerfile
# ============================================================
# Dependencies stage: install deps (cached separately)
# ============================================================
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --only=production

FROM node:20-alpine AS dev-deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci    # includes devDependencies

# ============================================================
# Test stage: run the full test suite
# docker build --target tester -t app:test .
# docker run --rm app:test
# ============================================================
FROM dev-deps AS tester
WORKDIR /app
COPY . .
# Exit code non-zero if any tests fail → CI step fails
RUN npm test

# ============================================================
# Build stage: compile TypeScript
# ============================================================
FROM dev-deps AS builder
WORKDIR /app
COPY . .
RUN npm run build    # outputs to /app/dist

# ============================================================
# Production stage: minimal final image
# Only production deps + compiled output
# ============================================================
FROM node:20-alpine AS production
WORKDIR /app
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
COPY --from=deps /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
COPY package.json ./
USER appuser
EXPOSE 3000
CMD ["node", "dist/server.js"]
```

---

## 📂 Navigation

| | Link |
|---|---|
| Previous | [13 · Docker Swarm](../13_Docker_Swarm/Code_Example.md) |
| Theory | [CI/CD Theory](./Theory.md) |
| Cheatsheet | [CI/CD Cheatsheet](./Cheatsheet.md) |
| Interview Q&A | [CI/CD Interview Q&A](./Interview_QA.md) |
| Next | [15 · Best Practices](../15_Best_Practices/Theory.md) |
