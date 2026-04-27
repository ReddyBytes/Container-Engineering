# 05 — Architecture: CI/CD Build, Push, Deploy

---

## ## The Big Picture

Imagine a relay race. Each runner (job) passes the baton to the next. If any
runner drops the baton (job fails), the race stops. Nobody crosses the finish
line (production) unless every leg was run cleanly.

In GitHub Actions, jobs are the runners and `needs:` is the baton handoff.

---

## ## Pipeline Architecture

```
Developer: git push origin main
                  |
                  v
    +-----------------------------------+
    |       GitHub Actions              |
    |                                   |
    |  job: test                        |
    |    1. checkout code               |
    |    2. docker build --target builder|
    |    3. docker run pytest           |
    |    Result: PASS or FAIL           |
    +--------+--------------------------+
             | needs: test (PASS only)
             v
    +-----------------------------------+
    |  job: build-push                  |
    |    1. docker/setup-buildx-action  |
    |    2. docker/login-action (GHCR)  |
    |    3. docker/metadata-action      |
    |       tags: sha-<GIT_SHA>         |
    |            latest                 |
    |    4. docker/build-push-action    |
    |       platforms: amd64,arm64      |
    |       push: true                  |
    +--------+--------------------------+
             | needs: build-push
             v
    +-----------------------------------+
    |  job: deploy-staging              |
    |    1. decode KUBECONFIG_B64 secret|
    |    2. kubectl set image           |
    |       deployment/myapi            |
    |       myapi=ghcr.io/USER/myapi:SHA|
    |    3. kubectl rollout status      |
    |       --timeout=3m                |
    +--------+--------------------------+
             | needs: deploy-staging
             | environment: production
             |   -> PAUSED: waiting for
             |      human approval
             v
    +-----------------------------------+
    |  job: deploy-prod                 |
    |    (same as staging, prod ns)     |
    +-----------------------------------+
             |
             v
    Kubernetes cluster updated
```

---

## ## Image Tagging Strategy

Two tags are pushed for every successful build on `main`:

```
ghcr.io/USERNAME/myapi:sha-abc1234def567890   <-- immutable, specific to this commit
ghcr.io/USERNAME/myapi:latest                 <-- mutable, always points to newest
```

Why use the SHA tag in deployments (not `latest`):

- `latest` is a moving target. Two pods might pull different images if a new
  build happens mid-rollout.
- The SHA is immutable. The cluster state is exactly reproducible by looking
  at the image tag in `kubectl describe deployment`.
- Rolling back means changing the image tag to a previous SHA. No guessing.

---

## ## Multi-Platform Build

Docker Buildx builds images for multiple CPU architectures in one step:

```
linux/amd64  <-- standard cloud VMs (AWS x86, GKE default nodes)
linux/arm64  <-- Apple M1/M2, AWS Graviton, newer cost-optimized nodes
```

A single manifest list is pushed to the registry. When a node pulls the image,
Docker automatically selects the right architecture layer. One pipeline, one
push, runs everywhere.

---

## ## Manual Approval Gate

GitHub Environments let you require human review before a job runs.

```
Settings → Environments → production
  └── Protection rules
        └── Required reviewers: [YOUR_USERNAME]
```

When the `deploy-prod` job is reached, the pipeline pauses:

```
This workflow run is waiting for a required review
[Review deployments]
```

You click "Approve and deploy." Only then does the job run. This creates an
audit trail: who approved, when, and for which commit SHA.

---

## ## Tech Stack

| Component        | Technology                            |
|------------------|---------------------------------------|
| CI runner        | GitHub Actions (ubuntu-latest)        |
| Image registry   | GitHub Container Registry (GHCR)      |
| Multi-arch build | Docker Buildx                         |
| Test runner      | pytest inside Docker                  |
| Deploy mechanism | kubectl set image                     |
| Secrets storage  | GitHub Actions Secrets (base64 kubeconfig) |
| Approval gate    | GitHub Environments                   |

---

## ## Folder Structure

```
05_CICD_Build_Push_Deploy/
|
+-- app/
|   +-- main.py           # FastAPI: /, /health, /items (GET/POST)
|   +-- test_main.py      # pytest: test_health, test_root, test_create_item, etc.
|
+-- Dockerfile            # FROM python AS builder; FROM python AS runtime
+-- requirements.txt      # fastapi, uvicorn, pytest, httpx
|
+-- k8s/
|   +-- deployment.yaml   # image: ghcr.io/USERNAME/myapi:latest (placeholder)
|
+-- scripts/
|   +-- update-image.sh   # sed-based alternative to kubectl set image
|
+-- .github/
|   +-- workflows/
|       +-- deploy.yaml   # 4-job pipeline
|
+-- src/
    +-- starter.py
    +-- solution.py
```

---

## ## Data Flow: A Single Deployment

```
1. Developer edits app/main.py, commits, pushes to main
   git push origin main

2. GitHub detects push event, triggers deploy.yaml workflow

3. test job:
   docker build --target builder -t myapi-test .
   docker run myapi-test python -m pytest app/test_main.py -v
   -> all tests pass

4. build-push job:
   SHA = "abc1234def567890..."
   docker buildx build --platform linux/amd64,linux/arm64 \
     -t ghcr.io/USERNAME/myapi:sha-abc1234 \
     -t ghcr.io/USERNAME/myapi:latest \
     --push .

5. deploy-staging job:
   kubectl set image deployment/myapi myapi=ghcr.io/USERNAME/myapi:sha-abc1234 -n staging
   kubectl rollout status deployment/myapi -n staging --timeout=3m
   -> rollout complete

6. deploy-prod job: (waiting for approval)
   [Reviewer approves in GitHub UI]
   kubectl set image deployment/myapi myapi=ghcr.io/USERNAME/myapi:sha-abc1234 -n production
   kubectl rollout status deployment/myapi -n production --timeout=5m
   -> rollout complete

Total time: ~8 minutes from push to production
```

---

⬅️ **Prev:** [04 — Full-Stack on K8s](../04_Full_Stack_on_K8s/01_MISSION.md) &nbsp;&nbsp; ➡️ **Next:** [06 — Production K8s Cluster](../06_Production_K8s_Cluster/01_MISSION.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
