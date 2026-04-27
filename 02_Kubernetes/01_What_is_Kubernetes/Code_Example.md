# What is Kubernetes — Code Examples

All examples are production-quality with detailed comments explaining every decision.

---

## 1. Declarative vs Imperative: Seeing the Difference

The core philosophy of Kubernetes is declaring desired state, not issuing step-by-step commands.

```bash
# ── IMPERATIVE approach (Docker-style thinking) ───────────────────────────────
# You manually tell each machine what to do. If one crashes, you repeat manually.
docker run -d --name nginx-1 nginx:1.25
docker run -d --name nginx-2 nginx:1.25
docker run -d --name nginx-3 nginx:1.25
# If nginx-2 crashes at 3AM → nobody restarts it until someone notices

# ── DECLARATIVE approach (Kubernetes) ─────────────────────────────────────────
# You write a manifest describing desired state once. K8s enforces it forever.
kubectl apply -f deployment.yaml
# K8s ensures 3 replicas exist at all times — you never ssh into servers again
```

```yaml
# deployment.yaml
# This single file replaces all the docker run commands above AND adds
# self-healing, rolling updates, and rollback for free.
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx                          # Name of this Deployment object
  namespace: default                   # Logical partition within the cluster
spec:
  replicas: 3                          # Desired state: 3 pods at all times
  selector:
    matchLabels:
      app: nginx                       # Which pods this Deployment owns
  template:
    metadata:
      labels:
        app: nginx                     # Label applied to every pod it creates
    spec:
      containers:
      - name: nginx
        image: nginx:1.25              # Always pin the tag — "latest" is a trap
        resources:
          requests:
            cpu: "100m"                # Minimum CPU guaranteed to this container
            memory: "64Mi"             # Minimum memory guaranteed
          limits:
            cpu: "200m"                # Throttled if it tries to use more
            memory: "128Mi"            # OOMKilled if it exceeds this
```

```bash
# Apply the desired state
kubectl apply -f deployment.yaml

# K8s immediately starts reconciling: creates 3 pods, schedules them to nodes
kubectl get pods -l app=nginx

# Kill one pod manually — K8s self-heals within seconds
kubectl delete pod <pod-name>
kubectl get pods -l app=nginx     # Observe a new pod replacing it automatically
```

---

## 2. Your First kubectl Commands — Navigating the Cluster

```bash
# ── Cluster health check ───────────────────────────────────────────────────────
kubectl cluster-info                   # Shows API server and CoreDNS endpoints
kubectl get nodes                      # Lists all nodes and their status
kubectl get nodes -o wide              # Adds OS, kernel version, container runtime

# ── Listing resources ──────────────────────────────────────────────────────────
kubectl get pods                       # Pods in the default namespace
kubectl get pods -n kube-system        # Pods in the kube-system namespace
kubectl get pods -A                    # All pods in all namespaces
kubectl get all                        # Pods, services, deployments, replicasets

# ── Inspecting a resource in detail ───────────────────────────────────────────
kubectl describe pod <pod-name>        # Full details: events, conditions, mounts
kubectl describe node <node-name>      # Node capacity, allocatable resources, pods

# ── Viewing raw YAML of any object ─────────────────────────────────────────────
kubectl get pod <pod-name> -o yaml     # The full spec K8s has stored in etcd
kubectl get deployment nginx -o yaml   # See every field including defaults K8s added

# ── Real-time watching ─────────────────────────────────────────────────────────
kubectl get pods --watch               # Stream updates as pod status changes
kubectl get events --sort-by=.lastTimestamp   # Cluster events, newest last
```

---

## 3. Demonstrating Self-Healing

Self-healing is the most fundamental K8s promise. This example makes it visible.

```yaml
# self-healing-demo.yaml
# A Deployment with 3 replicas of a simple web server
apiVersion: apps/v1
kind: Deployment
metadata:
  name: resilient-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: resilient-app
  template:
    metadata:
      labels:
        app: resilient-app
    spec:
      containers:
      - name: web
        image: nginx:1.25
        resources:
          requests:
            cpu: "50m"
            memory: "32Mi"
          limits:
            cpu: "100m"
            memory: "64Mi"
```

```bash
kubectl apply -f self-healing-demo.yaml

# Confirm 3 pods are running
kubectl get pods -l app=resilient-app

# Force delete a pod — simulates a crash or node eviction
kubectl delete pod -l app=resilient-app --field-selector=status.phase=Running \
  | head -1

# Watch K8s react — a new pod appears within 2-5 seconds
kubectl get pods -l app=resilient-app --watch

# Scale up to 10 replicas by changing the desired state
kubectl scale deployment resilient-app --replicas=10

# Scale back down — K8s terminates excess pods gracefully
kubectl scale deployment resilient-app --replicas=3

# Clean up
kubectl delete deployment resilient-app
```

---

## 4. Exposing an Application — Service Discovery

Kubernetes gives every set of pods a stable DNS name and virtual IP — even as pods come and go.

```yaml
# web-app-with-service.yaml
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
      - name: web
        image: nginx:1.25
        ports:
        - containerPort: 80             # Informational — does not open a host port
---
apiVersion: v1
kind: Service
metadata:
  name: web-app-svc                     # DNS name inside the cluster
spec:
  selector:
    app: web-app                        # Route to pods with this label
  ports:
  - port: 80                            # Port exposed by the Service
    targetPort: 80                      # Port on the pod to forward to
  type: ClusterIP                       # Internal-only (default); use LoadBalancer for external
```

```bash
kubectl apply -f web-app-with-service.yaml

# The Service gets a stable virtual IP (ClusterIP)
kubectl get service web-app-svc

# Port-forward to test locally without a cloud load balancer
kubectl port-forward service/web-app-svc 8080:80
# Open http://localhost:8080 in your browser

# Show DNS name used by other pods: web-app-svc.default.svc.cluster.local
kubectl run curl-test --image=curlimages/curl --restart=Never --rm -it \
  -- curl http://web-app-svc.default.svc.cluster.local

# Clean up
kubectl delete -f web-app-with-service.yaml
```

---

## 5. When NOT to Use Kubernetes — A Quick Sanity Check

```bash
# ── Check if K8s complexity is justified ───────────────────────────────────────
# Count your services: if you have 1-3, Docker Compose wins on simplicity
cat docker-compose.yml | grep "^  [a-z]" | wc -l

# Estimate operational overhead: K8s needs at minimum
#   - A control plane (3 nodes for HA)
#   - Worker nodes
#   - Networking (CNI plugin)
#   - Storage (CSI plugin)
#   - Load balancer (cloud LB or MetalLB on bare metal)
#   - Certificate management
#   - Monitoring (Prometheus + Grafana or equivalent)

# For a startup or single-service app, a managed PaaS or Docker Compose is better:
docker compose up -d                   # Zero infrastructure overhead

# K8s is worth it when you have:
# 1. Multiple services needing independent scaling
# 2. High availability requirements (no single points of failure)
# 3. Team > 3 people with separate deployment cadences
# 4. Need for rolling updates, canaries, or automated rollbacks

# Managed K8s reduces the overhead if you do need it:
# AWS:   eksctl create cluster --name my-cluster --region us-east-1
# GCP:   gcloud container clusters create my-cluster --num-nodes=3
# Azure: az aks create -g myGroup -n myAKS --node-count 3
```

---

## 📂 Navigation

**In this folder:**
| File | |
|---|---|
| [📖 Theory.md](./Theory.md) | Full explanation |
| [⚡ Cheatsheet.md](./Cheatsheet.md) | Quick reference |
| [🎯 Interview_QA.md](./Interview_QA.md) | Interview prep |
| 💻 **Code_Example.md** | ← you are here |

⬅️ **Prev:** [Home](../../README.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [K8s Architecture](../02_K8s_Architecture/Code_Example.md)
🏠 **[Home](../../README.md)**
