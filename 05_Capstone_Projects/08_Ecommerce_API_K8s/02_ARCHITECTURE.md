# 08 — Architecture: E-Commerce API on Kubernetes

## The Big Picture

Imagine your API is a restaurant. A single chef (container) works fine on a slow Tuesday. But on Saturday night you need multiple chefs (replicas), a maitre d' at the door (Ingress), a waiter routing orders to the right station (Service), a separate pantry with its own lock (PostgreSQL with PVC), and a manager who calls in more staff when queues build up (HPA).

Every component in this diagram plays one of those roles.

---

## 1. Traffic Flow: Browser to Pod

```
                   Internet
                      │
                      ▼
          ┌─────────────────────┐
          │   Ingress (nginx)   │
          │  host: shop.local   │
          │  path: /api/*       │
          └──────────┬──────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │   app-service       │
          │   ClusterIP :80     │
          └──────────┬──────────┘
                     │
          ┌──────────┴──────────┐
          │   Deployment        │
          │   ecommerce-api     │
          │   replicas: 3       │
          ├─────────────────────┤
          │  pod-0  pod-1  pod-2│
          │  :8000  :8000  :8000│
          └──────────┬──────────┘
                     │  env from ConfigMap + Secret
                     │  DATABASE_URL → postgres-service:5432
                     ▼
          ┌─────────────────────┐
          │  postgres-service   │
          │  ClusterIP :5432    │
          └──────────┬──────────┘
                     │
          ┌──────────┴──────────┐
          │  Deployment         │
          │  postgres           │
          │  replicas: 1        │
          ├─────────────────────┤
          │       pod-0         │
          │   postgres:15       │
          └──────────┬──────────┘
                     │
          ┌──────────┴──────────┐
          │  PersistentVolume   │
          │  Claim: 5Gi         │
          │  /var/lib/postgresql│
          └─────────────────────┘

All resources live in namespace: ecommerce
```

---

## 2. Manifest Dependency Tree

Apply manifests in this order — each resource depends on the one above it being present first.

```
[1] Namespace
      │
      ▼
[2] ConfigMap  +  Secret
      │
      ▼
[3] PersistentVolumeClaim
      │
      ▼
[4] postgres Deployment
      │
      ▼
[5] postgres Service (ClusterIP)
      │
      ▼
[6] app Deployment
      │
      ▼
[7] app Service (ClusterIP)
      │
      ▼
[8] Ingress
      │
      ▼
[9] HorizontalPodAutoscaler  →  watches app Deployment
```

If you apply them out of order Kubernetes will still create the objects — but pods will crash-loop waiting for upstream dependencies (postgres, the secret) to exist first.

---

## 3. Resource Spec Table

| Workload | Container | CPU Request | CPU Limit | Memory Request | Memory Limit |
|---|---|---|---|---|---|
| ecommerce-api | app | 100m | 500m | 128Mi | 512Mi |
| postgres | db | 250m | 500m | 256Mi | 512Mi |

`100m` means 100 millicores — one tenth of a CPU core. Requests are what Kubernetes uses for scheduling; limits are the hard ceiling before the container is throttled or OOM-killed.

---

## 4. Rolling Update Strategy

A **rolling update** replaces pods one at a time so the service stays available throughout a deployment. Think of repainting a bridge while traffic is still flowing — you do one lane at a time.

```
Current state: 3 pods running v1
                 v1   v1   v1

maxSurge: 1       →  allow 1 extra pod above desired count during rollout
maxUnavailable: 0 →  never take a pod down before a new one is ready

Step 1:  v1   v1   v1  +  v2   (4 pods, 1 extra allowed by surge)
Step 2:  v1   v1   v2         (old v1 terminated after v2 Ready)
Step 3:  v1   v2   v2
Step 4:  v2   v2   v2         (rollout complete, back to 3 pods)
```

In the Deployment manifest this looks like:

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1        # ← at most 1 extra pod running during rollout
    maxUnavailable: 0  # ← zero downtime: never remove a pod before replacement is ready
```

---

## 5. HPA: Horizontal Pod Autoscaler

The **HPA** watches a metric (CPU utilisation by default) and adjusts the replica count of the Deployment automatically. The metrics-server addon on minikube provides the CPU data.

```
                  metrics-server
                       │
                  polls CPU usage
                       │
                       ▼
              ┌──────────────────┐
              │       HPA        │
              │  target: 50% CPU │
              │  min: 2          │
              │  max: 10         │
              └────────┬─────────┘
                       │
              scale decision every 15s
                       │
          ┌────────────┴────────────┐
          │  CPU < 50%              │  CPU > 50%
          ▼                         ▼
    scale down                 scale up
    (floor: 2 replicas)        (ceiling: 10 replicas)
          │                         │
          ▼                         ▼
   app Deployment            app Deployment
   replicas: 2               replicas: 4, 6, 8…
```

The HPA does not act instantly — there is a stabilisation window (default 5 minutes to scale down, faster to scale up) that prevents thrashing from momentary spikes.

---

⬅️ **Prev:** [07 — JWT Auth API Docker](../07_JWT_Auth_API_Docker/01_MISSION.md) &nbsp;&nbsp; ➡️ **Next:** [09 — Containerize RAG System](../09_RAG_System_Containerized/01_MISSION.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
