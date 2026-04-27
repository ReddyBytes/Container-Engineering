# 01 — Deploy an App to Kubernetes

> Difficulty: 🟠 Minimal Hints

---

## 🎯 The Mission

Docker Compose is great for a single machine. But what happens when you need your app to run on multiple machines, survive a node failure, handle a traffic spike, and deploy a new version without taking the service down? That is what **Kubernetes** is built for.

Think of Compose as a skilled chef who can manage a small kitchen solo. Kubernetes is the head chef who coordinates an entire brigade — routing orders, replacing anyone who goes home sick, adjusting staff count for a busy service, and training new staff on the fly without closing the restaurant.

In this project you will take the FastAPI app from Projects 01 and 02 and deploy it to a real Kubernetes cluster running locally on minikube.

---

## 🏗️ What You'll Build

A Kubernetes-native deployment that:

- Runs **3 replicas** for availability — one pod dying does not take down the service
- Defines **resource requests and limits** so the scheduler places pods correctly and bad pods cannot starve the node
- Has **liveness and readiness probes** so Kubernetes knows when pods are actually ready for traffic
- Stores non-secret config in a **ConfigMap**
- Stores credentials in a **Secret**
- Is exposed via a **Service** (NodePort for local access)
- Can be **scaled**, **rolling-updated**, and **rolled back** with single commands

---

## 🛠️ Skills Practiced

| Skill | Why it matters |
|---|---|
| Deployment, Service, ConfigMap, Secret YAML | Core Kubernetes primitives |
| `kubectl apply -f` | Declarative, idempotent deployments |
| Readiness vs liveness probes | Traffic routing and self-healing |
| Resource requests and limits | Scheduler placement and noisy-neighbor protection |
| Rolling updates | Zero-downtime deploys |
| Rollback | Fast recovery from bad deploys |
| Port forwarding | Local cluster access without LoadBalancer |

---

## 📋 Prerequisites

| Tool | Version | Check command |
|---|---|---|
| Docker | 24+ | `docker --version` |
| kubectl | 1.28+ | `kubectl version --client` |
| minikube | 1.32+ | `minikube version` |

Install minikube: https://minikube.sigs.k8s.io/docs/start/

Or use kind (Kubernetes in Docker): https://kind.sigs.k8s.io/ — substitute `minikube service` with `kubectl port-forward`.

---

## 🗺️ Step Summary

1. Start minikube and push (or load) your image
2. Write `k8s/configmap.yaml` — non-secret app config
3. Write `k8s/secret.yaml` — base64-encoded credentials
4. Write `k8s/deployment.yaml` — 3 replicas, resource limits, probes
5. Write `k8s/service.yaml` — NodePort service on 30080
6. Apply everything with `kubectl apply -f k8s/`
7. Verify pods are running and healthy
8. Access the app via minikube service or port-forward
9. Scale to 5 replicas
10. Perform a rolling update to a new image tag
11. Roll back to the previous version

---

⬅️ **Prev:** [02 — Multi-Container App with Compose](../02_Multi_Container_App_Compose/01_MISSION.md) &nbsp;&nbsp; ➡️ **Next:** [04 — Full Stack on K8s](../04_Full_Stack_on_K8s/01_MISSION.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
