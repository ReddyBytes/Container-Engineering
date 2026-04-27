# 08 — Deploy E-Commerce API to Kubernetes

## 🎯 Mission

You have a working e-commerce API and a Docker image sitting on your machine. Right now it runs — but only because you're manually starting containers, managing environment variables in a `.env` file, and hoping nothing crashes overnight.

Think of Kubernetes as hiring a building manager for your apartment complex. You don't call individual tenants when a pipe bursts — the manager handles restarts, load balancing, and scaling automatically. Your job is to write the lease agreements (manifests) and hand over the keys.

In this project you'll take the E-Commerce FastAPI (from Python-DSA-API-Mastery Project 14) from a Docker Compose setup and promote it to a proper Kubernetes deployment: health-checked, autoscaling, with persistent storage for PostgreSQL — the way an engineering team would actually ship it.

---

## 🏆 What You Will Build

- A dedicated Kubernetes **namespace** isolating all resources
- **ConfigMap** and **Secret** manifests replacing your `.env` file
- A **PostgreSQL Deployment** backed by a **PersistentVolumeClaim** so data survives pod restarts
- An **App Deployment** with liveness/readiness probes and resource limits
- **Services** wiring the app and postgres together inside the cluster
- An **Ingress** resource routing external HTTP traffic to the API
- A **HorizontalPodAutoscaler** that scales the API from 2 to 10 replicas under load

---

## 🛠 Skills Practiced

| Skill | Where You Use It |
|---|---|
| Deployment + ReplicaSet | App and PostgreSQL workloads |
| Service (ClusterIP) | Internal DNS-based communication |
| Ingress | External traffic routing |
| PersistentVolumeClaim | PostgreSQL durable storage |
| ConfigMap + Secret | Externalised configuration |
| Liveness + Readiness probes | Health checks on the API |
| Resource requests + limits | CPU/memory guardrails |
| HorizontalPodAutoscaler | Autoscaling driven by CPU metrics |
| Rolling update strategy | Zero-downtime deployments |

---

## 📋 Prerequisites

| Requirement | Notes |
|---|---|
| K8s basics (Projects 02–04) | Pods, Deployments, Services, Ingress, PVCs |
| E-Commerce API containerized | Docker image built and available locally |
| minikube or kind running | `kubectl cluster-info` returns a valid endpoint |
| metrics-server enabled | Required for HPA — `minikube addons enable metrics-server` |
| Ingress addon enabled | `minikube addons enable ingress` |

---

## ⚙️ Difficulty and Time Estimate

**Difficulty:** 🟡 Partially Guided — hints point you in the right direction, full answers are revealed below each step.

**Estimated time:** 5 hours

- 30 min — prerequisite check and image prep
- 1 h — namespace, ConfigMap, Secret, postgres manifests
- 1 h — app Deployment with probes + Service
- 45 min — Ingress manifest and cluster verification
- 45 min — HPA setup and load test
- 1 h — debugging and extension challenges

---

## 🗺 What is Next

When you finish this project you will have covered the full lifecycle of a real containerised application: build, push, deploy, configure, expose, scale. The techniques here — probes, HPAs, PVCs, Ingress — transfer directly to production clusters on EKS, GKE, or AKS.

---

⬅️ **Prev:** [07 — JWT Auth API Docker](../07_JWT_Auth_API_Docker/01_MISSION.md) &nbsp;&nbsp; ➡️ **Next:** [09 — Containerize RAG System](../09_RAG_System_Containerized/01_MISSION.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
