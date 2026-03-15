# Docker in CI/CD — Interview Q&A

---

## Beginner

**Q1: Why do teams use Docker in CI/CD pipelines?**

Docker guarantees environment consistency. The container built in CI is byte-for-byte identical to what runs in production — same OS, same libraries, same configuration. This eliminates "it works on my machine" failures and "it passed CI but failed in production" surprises.

Additional benefits:
- CI runs are fast and isolated (no dependency pollution between builds)
- Image tags give you exact traceability — you always know what code is in production
- Rolling back is fast: redeploy the previous image tag
- The build artifact (the image) is also the deployment artifact — no separate packaging step

---

**Q2: What is the basic flow of a Docker-based CI/CD pipeline?**

```
git push
  → CI triggered (GitHub Actions workflow starts)
  → docker build (creates image from Dockerfile)
  → docker run tests (run test suite inside the container)
  → trivy image scan (check for CVEs)
  → docker push (push to registry with git SHA tag)
  → deploy (kubectl apply or service update with new tag)
```

Each step is a gate. If any step fails (tests fail, CVE found), the pipeline stops and nothing gets deployed.

---

**Q3: What are the three main GitHub Actions for Docker workflows?**

1. **`docker/setup-buildx-action`** — Sets up Docker Buildx (the BuildKit-based build engine). Required for caching, multi-platform builds, and advanced Dockerfile features.

2. **`docker/login-action`** — Authenticates to a container registry (GHCR, Docker Hub, ECR, GCR). Must run before push.

3. **`docker/build-push-action`** — Builds the Docker image and optionally pushes it. Handles caching, multi-platform, tags, and labels. This is the main action for CI Docker builds.

---

**Q4: What GITHUB_TOKEN is and why it's used for GHCR authentication?**

`GITHUB_TOKEN` is a short-lived, automatically-generated token that GitHub creates for each workflow run. It has permissions scoped to the repository the workflow is running in. For GHCR, this token is sufficient to push images under `ghcr.io/OWNER/IMAGE` — no additional secrets need to be configured.

This is the recommended approach because the token:
- Is short-lived (expires when the workflow ends)
- Needs no rotation
- Has no way to be accidentally leaked in secrets management

---

**Q5: How do you tag Docker images in CI to ensure traceability?**

Use the git commit SHA as the image tag:

```yaml
tags: ghcr.io/my-org/app:${{ github.sha }}
```

`github.sha` is the full git commit hash (e.g., `a3f9b2c1d2e3f4...`). Every push produces a unique tag that directly references the exact commit that built it. In production, you can always look up what code is running by checking the deployed tag against git history.

---

## Intermediate

**Q6: How does Docker layer caching work in GitHub Actions, and what's the difference between `type=gha` and `type=registry` cache?**

Docker builds in layers, and BuildKit can save those layers to an external cache store. In CI, two options exist:

**`type=gha`** (GitHub Actions cache):
- Stores BuildKit cache in GitHub's built-in cache storage
- Fast: cache stored close to the runner
- Free: no registry storage costs
- Easy: no extra setup needed
- Limitation: cache is scoped to a branch and has a 10 GB limit

```yaml
cache-from: type=gha
cache-to: type=gha,mode=max
```

**`type=registry`** (Registry cache):
- Stores cache as a separate manifest in your container registry
- Works across any CI system (not GitHub-specific)
- Costs registry storage
- Better for teams using multiple CI systems or self-hosted runners

```yaml
cache-from: type=registry,ref=ghcr.io/my-org/app:buildcache
cache-to: type=registry,ref=ghcr.io/my-org/app:buildcache,mode=max
```

---

**Q7: How do you build multi-platform images in GitHub Actions?**

GitHub Actions runners are typically `linux/amd64`. To build `linux/arm64` images, you use QEMU emulation via BuildKit:

```yaml
- uses: docker/setup-qemu-action@v3     # Enables arm64 emulation
- uses: docker/setup-buildx-action@v3  # Required for multi-platform

- uses: docker/build-push-action@v5
  with:
    platforms: linux/amd64,linux/arm64  # Build both architectures
    push: true
    tags: ghcr.io/my-org/app:v1.0.0
```

Docker creates a manifest list — a single tag that serves the correct architecture to each platform automatically. `docker pull my-app:v1.0.0` on a Mac with Apple Silicon gets the `arm64` image; on an EC2 instance it gets the `amd64` image.

---

**Q8: What is docker/metadata-action and why is it useful?**

`docker/metadata-action` automatically generates image tags and labels based on git context:

```yaml
- id: meta
  uses: docker/metadata-action@v5
  with:
    images: ghcr.io/my-org/app
    tags: |
      type=semver,pattern={{version}}        # v1.2.3 from git tag
      type=semver,pattern={{major}}.{{minor}} # v1.2
      type=sha                               # sha-a3f9b2c
      type=ref,event=branch                  # main, feature-xyz
```

Without this action, you'd write shell scripts to detect whether you're on a git tag, a branch, or a PR, and generate appropriate tags for each case. metadata-action handles all of this automatically and follows Docker Hub and OCI label conventions.

---

**Q9: How do you use OIDC to authenticate GitHub Actions to ECR without storing AWS credentials?**

OIDC (OpenID Connect) lets GitHub Actions prove its identity to AWS without storing static access keys. AWS issues short-lived credentials during the workflow run:

1. Configure an IAM OIDC provider for GitHub in AWS
2. Create an IAM role that trusts the GitHub OIDC provider, scoped to your repository
3. In the workflow, request an OIDC token and exchange it for AWS credentials:

```yaml
permissions:
  id-token: write    # Required to request OIDC token

steps:
  - uses: aws-actions/configure-aws-credentials@v4
    with:
      role-to-assume: arn:aws:iam::123456789:role/github-ecr-push
      aws-region: us-east-1

  - uses: aws-actions/amazon-ecr-login@v2
```

No `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` secrets are needed. The credentials are short-lived (15 minutes to 1 hour) and cannot be exfiltrated meaningfully.

---

**Q10: How do you integrate vulnerability scanning into a CI pipeline so it fails the build on critical CVEs?**

```yaml
- name: Scan for vulnerabilities
  run: |
    # Install Trivy
    curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin

    # Scan and fail if CRITICAL vulnerabilities found
    trivy image \
      --exit-code 1 \
      --severity CRITICAL \
      --no-progress \
      ghcr.io/my-org/app:${{ github.sha }}
```

`--exit-code 1` causes Trivy to return a non-zero exit code when vulnerabilities matching the severity filter are found. GitHub Actions treats non-zero exit codes as step failures, which stops the workflow and prevents the deploy step from running.

---

## Advanced

**Q11: How do you design a CI/CD pipeline that uses separate stages for different environments?**

A typical three-environment pipeline:

```yaml
on:
  push:
    branches: [main, staging]
  release:
    types: [published]

jobs:
  build-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build and test
        run: |
          docker build --target tester -t app:test .
          docker run --rm app:test
      - name: Build production image
        uses: docker/build-push-action@v5
        with:
          push: true
          tags: ghcr.io/my-org/app:${{ github.sha }}

  deploy-staging:
    needs: build-and-test
    if: github.ref == 'refs/heads/staging'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to staging
        run: kubectl set image deployment/app app=ghcr.io/my-org/app:${{ github.sha }}
        env:
          KUBECONFIG: ${{ secrets.STAGING_KUBECONFIG }}

  deploy-production:
    needs: build-and-test
    if: github.event_name == 'release'
    runs-on: ubuntu-latest
    environment: production    # Requires manual approval
    steps:
      - name: Deploy to production
        run: kubectl set image deployment/app app=ghcr.io/my-org/app:${{ github.sha }}
        env:
          KUBECONFIG: ${{ secrets.PROD_KUBECONFIG }}
```

The `environment: production` setting requires a manual approval in GitHub before the deploy job runs.

---

**Q12: How does Docker build caching interact with multi-stage builds in CI?**

Each stage in a multi-stage build has its own cache entries. The cache key is the content of each layer's inputs. When using `mode=max`, ALL intermediate layers from ALL stages are cached — not just the final stage.

The practical implication: if your test stage and your build stage share base layers (e.g., both start from `FROM golang:1.22 AS builder`), those layers are cached and reused. Only the layers that actually changed need to be rebuilt.

For maximum cache hit rates in CI:
1. Use `mode=max` to cache all layers
2. Order your Dockerfile to put slow, rarely-changing layers first (dependency installation before source code copy)
3. Use the same Buildx builder instance across workflow runs (GitHub Actions cache handles this automatically)
4. Consider using a dedicated "dependencies" stage that's separate from the "build" stage — deps change less often than source code

---

**Q13: What's the difference between CI tagging strategy for library packages vs. deployed services?**

**Deployed services** (APIs, web apps) need traceability above all — use git SHA as the primary tag, add semver on releases:
- `app:a3f9b2c` — always (every build)
- `app:v1.2.3` — on git tags (releases)
- `app:main` — floating tag for latest on main branch (staging auto-deploys)

**Library images** (base images, build tools shared across teams) need stable references — use semver more prominently:
- `my-builder:3.2.1` — exact version
- `my-builder:3.2` — minor floating
- `my-builder:3` — major floating
- `my-builder:latest` — latest stable (acceptable for internal tooling, not runtime apps)

The key difference: for deployed services, you want to know exactly what's running and roll back easily. For base images shared as dependencies, you want stable references that don't break consumers when the digest changes.

---

## 📂 Navigation

| | Link |
|---|---|
| Previous | [13 · Docker Swarm](../13_Docker_Swarm/Interview_QA.md) |
| Theory | [CI/CD Theory](./Theory.md) |
| Cheatsheet | [CI/CD Cheatsheet](./Cheatsheet.md) |
| Code Examples | [CI/CD Code Examples](./Code_Example.md) |
| Next | [15 · Best Practices](../15_Best_Practices/Interview_QA.md) |
