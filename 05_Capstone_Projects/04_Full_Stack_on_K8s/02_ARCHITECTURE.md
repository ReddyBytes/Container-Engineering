# 04 — Architecture: Full-Stack App on Kubernetes

---

## ## The Big Picture

Imagine a restaurant. Customers walk in through the front door (Ingress). The
maitre d' (nginx routing rules) directs them: "Ordering food? Go to the kitchen
(backend). Looking for the menu? Go to the dining room display (frontend)." The
kitchen talks to the walk-in freezer (database) — nobody else does. Each part
has a job; none of them mix.

That separation — and the controlled communication between layers — is what you
are building here.

---

## ## Traffic Flow

```
Browser: GET http://app.local/api/items
                   |
                   v
        +--------------------+
        |  nginx Ingress     |  <-- reads the Host header (app.local)
        |  Controller Pod    |      and the URL path (/api/*)
        +--------------------+
                   |
     path: /api/*  |   path: /*
          +--------+-------+
          |                |
          v                v
  +-----------+     +-----------+
  | backend   |     | frontend  |
  | Service   |     | Service   |
  | ClusterIP |     | ClusterIP |
  +-----------+     +-----------+
          |
          v
  +-----------+
  | backend   |
  | Pod(s)    |  <-- 2 replicas, RollingUpdate
  | FastAPI   |
  +-----------+
          |
          v
  +-----------+
  | postgres  |
  | Service   |
  | (headless)|  <-- clusterIP: None
  +-----------+
          |
          v
  +-----------+
  | postgres-0|  <-- StatefulSet pod, stable name
  | StatefulSet|     postgres-0.postgres.fullstack.svc.cluster.local
  +-----------+
          |
          v
  +-----------+
  | PVC       |  <-- postgres-storage-postgres-0
  | 5Gi RWO   |      provisioned by the StorageClass
  +-----------+
```

---

## ## Tech Stack

| Layer    | Technology                    | Kubernetes Object         |
|----------|-------------------------------|---------------------------|
| Frontend | React + nginx                 | Deployment + Service      |
| Backend  | FastAPI (Python)              | Deployment + Service      |
| Database | PostgreSQL 16                 | StatefulSet + Service     |
| Storage  | PersistentVolumeClaim         | PVC via volumeClaimTemplate |
| Routing  | nginx-ingress controller      | Ingress resource          |
| Config   | Environment variables         | ConfigMap + Secret        |
| Isolation| Namespace                     | Namespace: `fullstack`    |

---

## ## Key Kubernetes Concepts in This Project

### StatefulSet vs Deployment

A **Deployment** treats all pods as interchangeable. Kill any pod, spin up a
replacement — they are identical. Fine for stateless web servers.

A **StatefulSet** gives each pod a stable, persistent identity:
- Pods are named `postgres-0`, `postgres-1`, ... (not random hashes)
- Each pod gets its own PVC (not shared)
- Pods start in order and terminate in reverse order
- The DNS name `postgres-0.postgres.fullstack.svc.cluster.local` is stable

Databases need StatefulSets because they store data locally. If you replaced
`postgres-0` with a random new pod, it would start with an empty database.

### Headless Service

A normal Service gets a virtual IP (ClusterIP). DNS for it returns that single
VIP, and kube-proxy load-balances connections to pods behind it.

A **Headless Service** (`clusterIP: None`) has no VIP. DNS for it returns the
actual pod IPs. Combined with a StatefulSet, each pod gets its own DNS record:

```
postgres-0.postgres.fullstack.svc.cluster.local  ->  pod IP of postgres-0
```

This stable DNS name is what the backend uses to connect to the database.

### Ingress with Path Rewriting

The Ingress annotation `nginx.ingress.kubernetes.io/rewrite-target: /$2`
strips the `/api` prefix before forwarding to the backend.

```
External request:  GET /api/items
                         |
                         v
Backend receives:  GET /items   (prefix stripped)
```

Without rewriting, the backend would need to handle `/api/items` as a path.
With rewriting, the backend is cleanly scoped to `/items`, `/health`, etc.

---

## ## Folder Structure

```
04_Full_Stack_on_K8s/
|
+-- frontend/
|   +-- Dockerfile              # Stage 1: Node build; Stage 2: nginx serve
|   +-- nginx.conf              # SPA fallback: unknown paths -> index.html
|   +-- src/
|       +-- App.jsx             # Fetches /api/items and renders a list
|
+-- backend/
|   +-- Dockerfile              # Multi-stage: deps + copy app
|   +-- app/
|   |   +-- main.py             # FastAPI: /health, /items (GET + POST)
|   +-- requirements.txt
|
+-- k8s/
|   +-- namespace.yaml
|   +-- backend-configmap.yaml  # DB_HOST, DB_PORT, LOG_LEVEL
|   +-- backend-secret.yaml     # DB_USER, DB_PASSWORD, DB_NAME (base64)
|   +-- backend-deployment.yaml # 2 replicas, RollingUpdate
|   +-- backend-service.yaml    # ClusterIP: 8000
|   +-- frontend-deployment.yaml# 2 replicas, RollingUpdate
|   +-- frontend-service.yaml   # ClusterIP: 80
|   +-- postgres-statefulset.yaml
|   +-- postgres-service.yaml   # Headless (clusterIP: None)
|   +-- ingress.yaml            # path-based routing + rewrite
|
+-- src/
    +-- starter.py
    +-- solution.py
```

---

## ## Data Flow: Creating an Item

```
Browser
  |  POST http://app.local/api/items
  |  {"name": "desk lamp", "price": 49.99}
  v
Ingress (nginx)
  |  strips /api prefix -> forwards to backend-svc:8000
  |  body: {"name": "desk lamp", "price": 49.99}
  v
backend Pod (FastAPI)
  |  validates request body (Pydantic model)
  |  connects to postgres-0.postgres.fullstack.svc.cluster.local:5432
  |  INSERT INTO items (name, price) VALUES (...)
  v
postgres-0 (StatefulSet)
  |  writes to /var/lib/postgresql/data/pgdata
  v
PVC (postgres-storage-postgres-0)
  |  backed by StorageClass -> local disk on minikube
  v
Response bubbles back:
  postgres -> backend -> ingress -> browser
  {"id": 1, "name": "desk lamp", "price": 49.99}
```

---

⬅️ **Prev:** [03 — Deploy App to Kubernetes](../03_Deploy_App_to_Kubernetes/03_GUIDE.md) &nbsp;&nbsp; ➡️ **Next:** [05 — CI/CD Build Push Deploy](../05_CICD_Build_Push_Deploy/01_MISSION.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
