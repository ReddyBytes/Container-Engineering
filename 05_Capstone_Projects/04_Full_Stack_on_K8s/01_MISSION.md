# 04 — Full-Stack App on Kubernetes

**Difficulty:** 🟠 Minimal Hints

---

## 🎯 The Mission

Think of Kubernetes as a city. Each building is a container. Some buildings serve
the public (frontend), some process business logic in the back office (backend),
and some are underground vaults that store critical data (database). The city
has a traffic controller at the gate — an **Ingress** — that reads the address on
every incoming request and routes it to the right building.

Your job in this project: design and build the whole city from scratch.

---

## What You Will Build

A three-tier web application running entirely on Kubernetes:

- **Frontend** — React app served by nginx, responds to requests at `/`
- **Backend** — FastAPI app with REST endpoints, handles requests at `/api`
- **Database** — PostgreSQL in a **StatefulSet** with a **PersistentVolumeClaim**
- **Ingress** — nginx-ingress controller routing `/api/*` to the backend and `/*` to the frontend

All resources live in a dedicated `fullstack` **Namespace**.

```
                     Internet
                        |
                        v
              +-----------------+
              |  Ingress (nginx) |
              |  host: app.local |
              +--------+--------+
                       |
          +------------+-----------+
          | /api/*                 | /*
          v                        v
  +--------------+        +------------------+
  |   backend    |        |    frontend       |
  |  Service     |        |    Service        |
  | (ClusterIP)  |        |   (ClusterIP)     |
  +------+-------+        +------------------+
         |                        |
         |                   nginx (React SPA)
         v
  +--------------+
  |   database   |
  |  Service     |
  |  (headless)  |
  +------+-------+
         |
  +--------------+
  | StatefulSet  |
  |  postgres-0  |
  |   PVC: 5Gi   |
  +--------------+
```

---

## Why This Matters

This is the pattern closest to what you actually ship to production. Mastering it
means you can take any web application — regardless of language or framework —
and deploy it on Kubernetes with proper isolation, persistence, and routing.

The three key ideas this project teaches:

1. **Separation of concerns** — frontend, backend, and database are independent
   deployable units. Update one without touching the others.
2. **Stateful vs stateless workloads** — databases need stable identity and
   persistent storage. Kubernetes handles these differently from web servers.
3. **Path-based routing** — a single external IP handles all traffic; the
   Ingress decides who gets what.

---

## ## Skills Practiced

- Kubernetes **Namespaces** for logical isolation
- **StatefulSet** for stateful workloads (database)
- **PersistentVolumeClaim** for durable storage
- **Headless Service** for stable pod DNS
- **Ingress** resource and nginx-ingress controller
- Deploying multiple services independently
- URL path-based routing
- Building and pushing multi-service Docker images

---

## Prerequisites

| Tool          | Version | Notes                                     |
|---------------|---------|-------------------------------------------|
| Docker        | 24+     | For building images                       |
| kubectl       | 1.28+   | Configured against minikube or kind       |
| minikube      | 1.32+   | Enable ingress addon (see Guide Step 2)   |
| Node.js / npm | 18+     | Only if building the React app locally    |

Enable the minikube Ingress addon before starting:

```bash
minikube addons enable ingress
```

---

## Folder Structure You Will Create

```
04_Full_Stack_on_K8s/
├── frontend/
│   ├── Dockerfile          # nginx serving React build output
│   ├── nginx.conf          # nginx config with SPA fallback
│   └── src/App.jsx         # React app (calls /api/items)
├── backend/
│   ├── Dockerfile          # FastAPI multi-stage build
│   ├── app/main.py         # FastAPI application
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
└── src/
    ├── starter.py
    └── solution.py
```

---

⬅️ **Prev:** [03 — Deploy App to Kubernetes](../03_Deploy_App_to_Kubernetes/03_GUIDE.md) &nbsp;&nbsp; ➡️ **Next:** [05 — CI/CD Build Push Deploy](../05_CICD_Build_Push_Deploy/01_MISSION.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
