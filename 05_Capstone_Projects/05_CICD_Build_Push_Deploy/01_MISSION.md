# 05 — CI/CD: Build, Push, Deploy

**Difficulty:** 🟠 Minimal Hints

---

## 🎯 The Mission

Think of a deployment pipeline as a series of gates on an assembly line. Raw code
enters at one end. A test gate rejects it if anything is broken. A build gate
produces a versioned artifact. A delivery gate pushes that artifact to a warehouse
(container registry). A final gate installs it in the factory (the Kubernetes
cluster). And for the most sensitive environment — production — a human must press
an "approve" button before the last gate opens.

Your job: build that assembly line using **GitHub Actions**.

---

## What You Will Build

A GitHub Actions workflow with five stages, triggered on every push to `main`:

1. **Test** — run the app's pytest suite inside Docker
2. **Build** — create a multi-platform image (amd64 + arm64) tagged with the git commit SHA
3. **Push** — push to **GitHub Container Registry** (GHCR), free and built into GitHub
4. **Deploy to staging** — update the K8s deployment to use the new image tag and wait for rollout
5. **Deploy to production** — same, but gated behind a manual approval in the GitHub UI

No manual steps after the initial setup. Every push either deploys or tells you
exactly why it did not.

---

## Why This Matters

Manual deployments do not scale. They create incidents:

- "I forgot to push the image before applying the manifest."
- "I applied the manifest to prod but meant to apply to staging."
- "I deployed at 2am and nobody knows what changed."

A CI/CD pipeline eliminates all three. Every deployment is:
- **Tested** — broken code never ships
- **Immutable** — the image tag is the git SHA, so you always know what is running
- **Auditable** — the GitHub Actions log is the deployment record
- **Reproducible** — anyone with repo access can trigger the exact same pipeline

---

## ## Skills Practiced

- GitHub Actions workflow syntax (jobs, steps, `needs`, `environment`)
- Docker Buildx for **multi-platform** builds (amd64 + arm64)
- Authenticating to GHCR with the built-in `GITHUB_TOKEN`
- Storing `kubeconfig` as a GitHub Secret
- Running `kubectl` from a GitHub Actions runner
- **Manual approval gates** with GitHub Environments
- Image tag strategies: SHA (immutable) vs `latest` (mutable)

---

## Prerequisites

| Tool           | Notes                                          |
|----------------|------------------------------------------------|
| GitHub account | Free tier is fine                              |
| K8s cluster    | EKS, GKE, AKS, or a remote minikube instance  |
| kubectl access | Export your kubeconfig (see Guide Step 1)      |

This project assumes a remote cluster. The kubectl steps work with local
minikube if its API server is accessible from the internet (use `ngrok` or
similar if needed).

---

## Folder Structure You Will Create

```
05_CICD_Build_Push_Deploy/
├── app/
│   ├── main.py              # FastAPI app
│   └── test_main.py         # Pytest test suite
├── Dockerfile               # Multi-stage: builder + runtime
├── requirements.txt
├── k8s/
│   └── deployment.yaml      # Deployment with image placeholder
├── scripts/
│   └── update-image.sh      # Alternative: sed-based image update
├── .github/
│   └── workflows/
│       └── deploy.yaml      # The full CI/CD pipeline
└── src/
    ├── starter.py
    └── solution.py
```

---

⬅️ **Prev:** [04 — Full-Stack on K8s](../04_Full_Stack_on_K8s/01_MISSION.md) &nbsp;&nbsp; ➡️ **Next:** [06 — Production K8s Cluster](../06_Production_K8s_Cluster/01_MISSION.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
