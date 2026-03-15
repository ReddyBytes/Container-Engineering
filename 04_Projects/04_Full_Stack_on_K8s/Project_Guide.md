# Project 04: Full-Stack App on Kubernetes

You know how to deploy a single service to K8s. Now it's time to deploy the whole product: a React frontend, a FastAPI backend, and a PostgreSQL database — all running in Kubernetes, communicating securely, exposed to users via an Ingress controller that routes traffic based on URL path.

This is the project closest to what you'd actually ship to production.

---

## What You'll Build

A three-tier web application fully running on Kubernetes:

- **frontend** — React app served by nginx, responds to requests at `/`
- **backend** — FastAPI app with REST endpoints, handles requests at `/api`
- **database** — PostgreSQL in a StatefulSet (not a Deployment) with a PersistentVolumeClaim
- **ingress** — nginx-ingress controller routing `/api/*` → backend, `/*` → frontend

---

## Architecture

```
                     Internet
                        │
                        ▼
              ┌─────────────────┐
              │  Ingress (nginx) │
              │  host: app.local │
              └────────┬────────┘
                       │
          ┌────────────┴────────────┐
          │ /api/*                  │ /*
          ▼                         ▼
  ┌──────────────┐         ┌──────────────────┐
  │   backend    │         │    frontend       │
  │  Service     │         │    Service        │
  │  ClusterIP   │         │    ClusterIP      │
  └──────┬───────┘         └──────────────────┘
         │                         │
         │                    nginx (React SPA)
         │
         ▼
  ┌──────────────┐
  │   database   │
  │  Service     │
  │  (headless)  │
  └──────┬───────┘
         │
  ┌──────────────┐
  │ StatefulSet  │
  │  postgres-0  │
  │   PVC: 5Gi   │
  └──────────────┘

All resources live in the `fullstack` namespace.
```

---

## Skills Practiced

- Kubernetes Namespaces for logical isolation
- StatefulSet for stateful workloads (database)
- PersistentVolumeClaim for durable storage
- Headless Service for stable pod DNS
- Ingress resource and nginx-ingress controller
- Deploying multiple services independently
- URL path-based routing
- Building and pushing multi-service images

---

## Prerequisites

| Tool            | Version | Notes                                           |
|-----------------|---------|-------------------------------------------------|
| Docker          | 24+     | For building images                             |
| kubectl         | 1.28+   | Configured against minikube or kind             |
| minikube        | 1.32+   | Enable ingress addon (see Step 2)               |
| Node.js / npm   | 18+     | Only if building the React app locally          |

Enable the minikube Ingress addon:

```bash
minikube addons enable ingress
```

---

## Folder Structure

```
04_Full_Stack_on_K8s/
├── frontend/
│   ├── Dockerfile          # nginx serving React build output
│   ├── nginx.conf          # nginx config with /api proxy
│   └── src/App.jsx         # React app (calls /api/items)
├── backend/
│   ├── Dockerfile          # FastAPI multi-stage build
│   ├── app/main.py         # FastAPI app
│   └── requirements.txt
├── k8s/
│   ├── namespace.yaml
│   ├── frontend-deployment.yaml
│   ├── frontend-service.yaml
│   ├── backend-deployment.yaml
│   ├── backend-service.yaml
│   ├── backend-configmap.yaml
│   ├── backend-secret.yaml
│   ├── postgres-statefulset.yaml
│   ├── postgres-service.yaml
│   └── ingress.yaml
├── Project_Guide.md
├── Step_by_Step.md
└── Code_Example.md
```

---

## What You'll Build — Step Summary

1. Build and push the frontend and backend images
2. Create the `fullstack` namespace
3. Deploy PostgreSQL (StatefulSet + PVC + headless Service)
4. Deploy the backend (Deployment + Service + ConfigMap + Secret)
5. Deploy the frontend (Deployment + Service)
6. Install and configure the Ingress
7. Test the full stack end-to-end
8. Update one service independently without touching the others

---

## 📂 Navigation

| | |
|---|---|
| Next | [Step_by_Step.md](./Step_by_Step.md) |
| Code | [Code_Example.md](./Code_Example.md) |
| All Projects | [04_Projects/](../) |
