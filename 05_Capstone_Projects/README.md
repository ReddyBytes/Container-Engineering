# 🐳 Container Engineering — Capstone Projects

> Docker and Kubernetes tutorials teach you the commands. Projects prove you can use them.

10 real deployments — from your first Dockerfile to a horizontally-scaled AI agent on Kubernetes. Each project produces a running system you can show to anyone.

---

## How This Series Works

Every project follows the **Mission Briefing Format**:

```
01_MISSION.md      — What you are building and why it matters
02_ARCHITECTURE.md — System design, diagrams, tech stack
03_GUIDE.md        — Step-by-step build with hints and answers
src/starter.py     — Scaffolded code to get you started
src/solution.py    — Full reference solution
04_RECAP.md        — What you built, what to extend
```

Difficulty progression:

```
🟢 Fully Guided     — Every step: concept → hint → full answer
🟡 Partially Guided — Steps explained, you write the code/YAML
🟠 Minimal Hints    — Requirements + one hint per step
🔴 Build Yourself   — Spec + acceptance criteria, solution at end
```

---

## Projects

### Track 1 — Docker Fundamentals

| # | Project | Difficulty | Core Skills |
|---|---------|------------|-------------|
| 01 | [Dockerize a Python App](./01_Dockerize_a_Python_App/01_MISSION.md) | 🟢 Guided | Multi-stage Dockerfile, .dockerignore, HEALTHCHECK, Docker Hub |
| 02 | [Multi-Container App with Compose](./02_Multi_Container_App_Compose/01_MISSION.md) | 🟡 Partial | docker-compose, named volumes, bridge networks, Redis cache |
| 03 | [Deploy App to Kubernetes](./03_Deploy_App_to_Kubernetes/01_MISSION.md) | 🟠 Hints | Deployment, Service, ConfigMap, liveness/readiness probes |

### Track 2 — Kubernetes in Depth

| # | Project | Difficulty | Core Skills |
|---|---------|------------|-------------|
| 04 | [Full-Stack App on K8s](./04_Full_Stack_on_K8s/01_MISSION.md) | 🟠 Hints | StatefulSet, PVC, Ingress, multi-service wiring |
| 05 | [CI/CD Build-Push-Deploy](./05_CICD_Build_Push_Deploy/01_MISSION.md) | 🟠 Hints | GitHub Actions, Docker Hub push, SHA tagging, rollout |
| 06 | [Production K8s Cluster](./06_Production_K8s_Cluster/01_MISSION.md) | 🔴 Self | RBAC, NetworkPolicy, ResourceQuota, HPA, PodDisruptionBudget |

### Track 3 — Real System Deployments

| # | Project | Difficulty | Core Skills |
|---|---------|------------|-------------|
| 07 | [JWT Auth API — Docker](./07_JWT_Auth_API_Docker/01_MISSION.md) | 🟢 Guided | Multi-stage build, Compose + Postgres, Docker secrets, push |
| 08 | [E-Commerce API — Kubernetes](./08_Ecommerce_API_K8s/01_MISSION.md) | 🟡 Partial | K8s Deployment + PVC + Ingress + HPA for a full REST API |
| 09 | [RAG System — Containerized](./09_RAG_System_Containerized/01_MISSION.md) | 🟠 Hints | ChromaDB HTTP mode, multi-container RAG, shared volumes |
| 10 | [AI Agent — K8s Microservice](./10_AI_Agent_K8s_Microservice/01_MISSION.md) | 🔴 Self | K8s Secrets for API keys, HPA, Prometheus metrics, probes |

---

## Learning Paths

**Path A — Complete Beginner**
```
01 → 02 → 03 → 04 → 06
Focus: Docker → Compose → K8s fundamentals
```

**Path B — Deploy Your Projects**
```
01 → 02 → 07 → 08
Focus: containerize real apps from your portfolio
```

**Path C — Production Engineer**
```
03 → 04 → 05 → 06 → 08 → 10
Focus: CI/CD, production K8s, scaling, observability
```

**Path D — AI Infrastructure**
```
01 → 02 → 09 → 10
Focus: containerize and deploy AI/RAG systems
```

---

## Prerequisites by Track

| Track | What you need first |
|---|---|
| Track 1 | Docker installed, basic Python |
| Track 2 | Track 1 done, minikube or kind, kubectl |
| Track 3 | Track 1-2 done + the underlying app (from Python/AI capstones) |

---

## 📂 Navigation

| | |
|---|---|
| Back to Container-Engineering | [README.md](../README.md) |
| Docker Fundamentals | [01_Docker/](../01_Docker/) |
| Kubernetes | [02_Kubernetes/](../02_Kubernetes/) |
| Docker to K8s | [03_Docker_to_K8s/](../03_Docker_to_K8s/) |
