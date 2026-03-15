# Project 05: CI/CD — Build, Push, Deploy

You've been building images and applying manifests by hand. That works until the second person joins your team, or until you need to deploy at 3am after a hotfix. CI/CD automates everything: every push to main builds your image, runs tests, pushes to a registry, and updates your cluster. No manual steps, no "I forgot to push the new image" incidents.

In this project you'll build a complete GitHub Actions pipeline that takes code from a commit all the way to a running update in Kubernetes.

---

## What You'll Build

A GitHub Actions workflow with five stages:

1. **Test** — run the app's test suite inside Docker
2. **Build** — create a multi-platform image (amd64 + arm64) tagged with the git commit SHA
3. **Push** — push to GitHub Container Registry (GHCR), free and built into GitHub
4. **Deploy** — update the K8s deployment to use the new image tag
5. **Verify** — wait for the rollout to complete, fail the pipeline if it doesn't

Plus: a manual approval gate before the production deploy.

---

## Architecture

```
Developer pushes to main
          │
          ▼
  ┌───────────────────────────────────────────┐
  │           GitHub Actions                   │
  │                                            │
  │  job: test                                 │
  │    └── docker run pytest                  │
  │                                            │
  │  job: build-push (needs: test)            │
  │    └── docker buildx (amd64 + arm64)      │
  │    └── push to ghcr.io/USER/myapi:SHA     │
  │                                            │
  │  job: deploy-staging (needs: build-push)  │
  │    └── kubectl set image                  │
  │    └── kubectl rollout status             │
  │                                            │
  │  job: deploy-prod (needs: deploy-staging) │
  │    environment: production (manual approval)│
  │    └── kubectl set image                  │
  │    └── kubectl rollout status             │
  └───────────────────────────────────────────┘
          │
          ▼
  Kubernetes cluster updated
```

---

## Skills Practiced

- GitHub Actions workflow syntax (jobs, steps, needs, environment)
- Docker Buildx for multi-platform builds
- Authenticating to GHCR with GitHub tokens
- Storing kubeconfig and registry credentials as GitHub Secrets
- Using `kubectl` from a GitHub Actions runner
- Manual approval gates with GitHub Environments
- Image tag strategies (SHA vs latest vs semver)

---

## Prerequisites

| Tool              | Notes                                         |
|-------------------|-----------------------------------------------|
| GitHub account    | Free tier is fine                             |
| K8s cluster       | EKS, GKE, AKS, or a remote minikube           |
| kubectl access    | Export your kubeconfig (see Step 1)           |

This project assumes you have a remote K8s cluster. For local minikube, the `kubectl` steps still work if you expose the API server.

---

## Folder Structure

```
05_CICD_Build_Push_Deploy/
├── app/
│   ├── main.py
│   └── test_main.py         # Pytest tests for the API
├── Dockerfile
├── requirements.txt
├── k8s/
│   └── deployment.yaml      # Deployment with image placeholder
├── scripts/
│   └── update-image.sh      # Updates image tag in deployment YAML
├── .github/
│   └── workflows/
│       └── deploy.yaml      # The full CI/CD pipeline
├── Project_Guide.md
├── Step_by_Step.md
└── Code_Example.md
```

---

## What You'll Build — Step Summary

1. Set up GitHub Secrets for kubeconfig and registry access
2. Write the test suite (`test_main.py`)
3. Write the workflow file step by step
4. Push to main and watch the pipeline run
5. Verify the deployment updated in the cluster
6. Add a production environment with manual approval
7. Trigger a deploy, approve it, verify in prod

---

## 📂 Navigation

| | |
|---|---|
| Next | [Step_by_Step.md](./Step_by_Step.md) |
| Code | [Code_Example.md](./Code_Example.md) |
| All Projects | [04_Projects/](../) |
