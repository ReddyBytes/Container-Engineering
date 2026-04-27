# 02 — Architecture: Deploy an App to Kubernetes

---

## 🗺️ System Overview

Kubernetes is a reconciliation engine. You describe the desired state — "I want 3 replicas of this container running with these resource limits" — and Kubernetes continuously compares that desired state to reality. If a pod crashes, Kubernetes creates a new one. If a node goes down, Kubernetes reschedules the pods to surviving nodes. You never imperatively tell it "start this container" — you declare what you want, and it figures out how.

---

## 🖥️ Cluster Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                        │
│                   (minikube, local)                          │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Namespace: default                                   │   │
│  │                                                       │   │
│  │  Service: myapi-svc (NodePort 30080)                 │   │
│  │       │                                               │   │
│  │       ├──▶ Pod: myapi-xxx-1 (port 8000)              │   │
│  │       ├──▶ Pod: myapi-xxx-2 (port 8000)              │   │
│  │       └──▶ Pod: myapi-xxx-3 (port 8000)              │   │
│  │                    │           │                      │   │
│  │             ConfigMap:      Secret:                   │   │
│  │             myapi-config    myapi-secret              │   │
│  │             (env vars)      (base64 creds)            │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
         │ NodePort 30080
    minikube_ip:30080
         │
    curl / browser
```

---

## 🔄 Request Flow

```
HTTP Request
     │
     ▼
minikube Node  port 30080
     │
     ▼  (NodePort → Service)
Service: myapi-svc  (ClusterIP + kube-proxy)
     │
     ├──▶  load balances (round-robin) across 3 pods
     │
     ▼  (Service → Pod)
Pod: myapi-xxx-1  port 8000
     │
     ▼
Uvicorn → FastAPI
     │
     └──▶ Response
```

---

## 🗂️ Kubernetes Resource Map

```
k8s/
├── configmap.yaml    →  ConfigMap: myapi-config
│                           APP_ENV, LOG_LEVEL, WORKERS
│                           injected as env vars via envFrom
│
├── secret.yaml       →  Secret: myapi-secret
│                           DB_USER, DB_PASSWORD, DB_NAME  (base64)
│                           injected as env vars via envFrom
│
├── deployment.yaml   →  Deployment: myapi
│                           replicas: 3
│                           strategy: RollingUpdate (maxSurge: 1, maxUnavailable: 0)
│                           container: myapi:1.0.0
│                           resources: requests (100m CPU, 128Mi) / limits (500m, 256Mi)
│                           readinessProbe: GET /health  (5s delay, 10s period)
│                           livenessProbe:  GET /health  (15s delay, 20s period)
│
└── service.yaml      →  Service: myapi-svc
                            type: NodePort
                            port: 8000 → targetPort: 8000 → nodePort: 30080
```

---

## 🔁 Rolling Update Flow

```
Current state: 3 pods running myapi:1.0.0

kubectl set image deployment/myapi myapi=YOUR_USERNAME/myapi:1.1.0
         │
         ▼
K8s creates 1 new pod (myapi:1.1.0)        ← maxSurge: 1
         │
         └── waits for readiness probe to pass
         │
         ▼
K8s terminates 1 old pod (myapi:1.0.0)    ← maxUnavailable: 0
         │   (old pod kept until new is ready — zero downtime)
         │
         └── repeat until all 3 pods run 1.1.0
```

---

## 🧱 Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Cluster | minikube | Local single-node Kubernetes |
| CLI | kubectl | Apply manifests, inspect state, exec into pods |
| Workload | Deployment | Manages the pod replica set |
| Networking | Service (NodePort) | Stable endpoint, load balancing |
| Config | ConfigMap | Non-secret env vars |
| Secrets | Secret (Opaque) | Base64-encoded sensitive values |
| App | FastAPI + Uvicorn | Same image as Projects 01/02 |

---

## 🔍 Probe Comparison

```
Readiness probe                     Liveness probe
───────────────                     ──────────────
Is the pod ready for traffic?       Is the pod still functioning?

Failure action:                     Failure action:
  Remove from Service endpoints       Restart the container

Use case:                           Use case:
  Slow startup, warming up cache      Hung process, deadlock, OOM

initialDelaySeconds: 5              initialDelaySeconds: 15
periodSeconds: 10                   periodSeconds: 20
```

Set liveness delay longer than readiness. If liveness fires before the app is up,
Kubernetes will restart it in a loop (CrashLoopBackOff).

---

⬅️ **Prev:** [02 — Multi-Container App with Compose](../02_Multi_Container_App_Compose/01_MISSION.md) &nbsp;&nbsp; ➡️ **Next:** [04 — Full Stack on K8s](../04_Full_Stack_on_K8s/01_MISSION.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
