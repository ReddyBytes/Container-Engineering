# Project 03: Deploy an App to Kubernetes

Docker Compose is great for a single machine. But what happens when you need your app to run on multiple machines, survive node failures, handle traffic spikes, and deploy new versions without downtime? That's Kubernetes. In this project you'll take the FastAPI app from Projects 01/02 and deploy it to a real Kubernetes cluster — running locally on minikube or kind.

---

## What You'll Build

A Kubernetes-native deployment of the FastAPI API that:

- Runs **3 replicas** for availability
- Defines **resource requests and limits** so the scheduler places pods correctly
- Has **liveness and readiness probes** so K8s knows when pods are actually ready
- Stores non-secret config in a **ConfigMap**
- Stores credentials in a **Secret**
- Is exposed via a **Service** (ClusterIP internally, NodePort for local access)
- Can be **scaled**, **updated**, and **rolled back** with single commands

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                        │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Namespace: default                                   │   │
│  │                                                       │   │
│  │  Service: myapi-svc (NodePort 30080)                 │   │
│  │       │                                               │   │
│  │       ├──▶ Pod: myapi-xxx-1 (port 8000)              │   │
│  │       ├──▶ Pod: myapi-xxx-2 (port 8000)              │   │
│  │       └──▶ Pod: myapi-xxx-3 (port 8000)              │   │
│  │                                                       │   │
│  │  ConfigMap: myapi-config                             │   │
│  │  Secret:    myapi-secret                             │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
         │ NodePort 30080
    localhost:30080 (minikube ip:30080)
         │
    curl / browser
```

---

## Skills Practiced

- Writing Deployment, Service, ConfigMap, and Secret YAML
- Using `kubectl apply -f` for declarative deployments
- Verifying pod status, events, and logs
- Scaling deployments up and down
- Performing a rolling update with zero downtime
- Rolling back a bad deployment
- Port forwarding for local access
- Understanding health probes (liveness vs readiness)

---

## Prerequisites

| Tool       | Version | Check command              |
|------------|---------|----------------------------|
| Docker     | 24+     | `docker --version`         |
| kubectl    | 1.28+   | `kubectl version --client` |
| minikube   | 1.32+   | `minikube version`         |

Install minikube: https://minikube.sigs.k8s.io/docs/start/

Or use kind (Kubernetes in Docker): https://kind.sigs.k8s.io/

This guide uses minikube. For kind, substitute `minikube service` with `kubectl port-forward`.

---

## Folder Structure

```
03_Deploy_App_to_Kubernetes/
├── app/
│   └── main.py              # FastAPI app (same as Project 01)
├── Dockerfile               # Multi-stage build
├── requirements.txt
├── k8s/
│   ├── configmap.yaml       # Non-secret app config
│   ├── secret.yaml          # DB credentials (base64)
│   ├── deployment.yaml      # 3-replica deployment with probes + limits
│   └── service.yaml         # ClusterIP + NodePort service
├── Project_Guide.md         # This file
├── Step_by_Step.md          # Numbered walkthrough
└── Code_Example.md          # Full K8s YAML
```

---

## What You'll Build — Step Summary

1. Push your image to Docker Hub (or load into minikube)
2. Write a ConfigMap for app config
3. Write a Secret for credentials
4. Write a Deployment with 3 replicas, resource limits, and health probes
5. Write a Service to expose the Deployment
6. Apply everything with `kubectl apply -f k8s/`
7. Verify pods are running and healthy
8. Access the app via minikube service or port-forward
9. Scale the Deployment to 5 replicas
10. Perform a rolling update to a new image tag
11. Roll back to the previous version

---

## 📂 Navigation

| | |
|---|---|
| Next | [Step_by_Step.md](./Step_by_Step.md) |
| Code | [Code_Example.md](./Code_Example.md) |
| All Projects | [04_Projects/](../) |
