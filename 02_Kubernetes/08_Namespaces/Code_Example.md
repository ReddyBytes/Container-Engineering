# Namespaces — Code Examples

All examples are production-quality with detailed comments explaining every decision.

---

## 1. Creating and Switching Between Namespaces

```bash
# ── Create namespaces for a multi-team cluster ────────────────────────────────
kubectl create namespace team-frontend
kubectl create namespace team-backend
kubectl create namespace monitoring

# Or declaratively (preferred in production — can be committed to git)
kubectl apply -f - <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: team-frontend
  labels:
    team: frontend                     # Labels enable namespace selectors in NetworkPolicy
    environment: production
---
apiVersion: v1
kind: Namespace
metadata:
  name: team-backend
  labels:
    team: backend
    environment: production
EOF

# ── List all namespaces in the cluster ────────────────────────────────────────
kubectl get namespaces                 # Short alias: kubectl get ns

# ── Switch default namespace for your context ─────────────────────────────────
kubectl config set-context --current --namespace=team-backend
# Now all commands default to team-backend without -n flag

kubectl get pods                       # Equivalent to: kubectl get pods -n team-backend

# ── Reset to default namespace ────────────────────────────────────────────────
kubectl config set-context --current --namespace=default

# ── Query across all namespaces at once ───────────────────────────────────────
kubectl get pods -A                    # All pods in all namespaces
kubectl get deployments -A             # All deployments cluster-wide
kubectl get all -n team-frontend       # Everything in one namespace
```

---

## 2. Deploying Isolated Workloads Per Namespace

Same resource names can coexist in different namespaces — no collision.

```yaml
# frontend-stack.yaml
# Deploy to team-frontend namespace
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend-api                    # Same name as the team-backend deployment below
  namespace: team-frontend             # Scoped to this namespace — no conflict
spec:
  replicas: 2
  selector:
    matchLabels:
      app: backend-api
      team: frontend
  template:
    metadata:
      labels:
        app: backend-api
        team: frontend
    spec:
      containers:
      - name: api
        image: nginx:1.25              # Placeholder — would be the frontend's backend service
        resources:
          requests:
            cpu: "100m"
            memory: "64Mi"
          limits:
            cpu: "200m"
            memory: "128Mi"
---
# backend-stack.yaml
# Completely separate deployment — same name, different namespace
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend-api                    # Same name — safe because different namespace
  namespace: team-backend
spec:
  replicas: 3                          # Different replica count
  selector:
    matchLabels:
      app: backend-api
      team: backend
  template:
    metadata:
      labels:
        app: backend-api
        team: backend
    spec:
      containers:
      - name: api
        image: nginx:1.25
        resources:
          requests:
            cpu: "200m"
            memory: "128Mi"
          limits:
            cpu: "500m"
            memory: "256Mi"
```

```bash
kubectl apply -f frontend-stack.yaml
kubectl apply -f backend-stack.yaml

# Both deployments named "backend-api" exist independently
kubectl get deployment backend-api -n team-frontend
kubectl get deployment backend-api -n team-backend

# No collision — they are entirely separate objects
kubectl describe deployment backend-api -n team-frontend | grep -i "namespace\|replicas"
kubectl describe deployment backend-api -n team-backend  | grep -i "namespace\|replicas"
```

---

## 3. ResourceQuota — Preventing Noisy Neighbors

```yaml
# team-backend-quota.yaml
# Prevents team-backend from consuming all cluster resources
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-backend-quota
  namespace: team-backend              # Quota only applies within this namespace
spec:
  hard:
    pods: "20"                         # Maximum 20 pods total in this namespace
    requests.cpu: "4"                  # Total CPU requests across all pods: 4 cores
    requests.memory: 8Gi               # Total memory requests: 8 GB
    limits.cpu: "8"                    # Total CPU limits: 8 cores
    limits.memory: 16Gi                # Total memory limits: 16 GB
    configmaps: "20"                   # Max ConfigMap objects
    secrets: "30"                      # Max Secret objects
    services: "10"                     # Max Service objects
    persistentvolumeclaims: "5"        # Max PVC objects
---
# Once a quota is set, pods without resource requests are REJECTED
# This enforces good resource hygiene across the team
apiVersion: v1
kind: LimitRange
metadata:
  name: team-backend-limits
  namespace: team-backend
spec:
  limits:
  - type: Container
    default:                           # Applied to containers that don't specify limits
      cpu: "200m"
      memory: "256Mi"
    defaultRequest:                    # Applied to containers that don't specify requests
      cpu: "100m"
      memory: "128Mi"
    max:                               # Hard cap — any container requesting more is rejected
      cpu: "2"
      memory: "2Gi"
    min:                               # Minimum allowed — prevents zero-resource containers
      cpu: "50m"
      memory: "64Mi"
```

```bash
kubectl apply -f team-backend-quota.yaml

# View current quota usage
kubectl describe resourcequota team-backend-quota -n team-backend
# Shows: used vs hard limits for each resource type

kubectl get limitrange -n team-backend

# Try deploying a pod without resource limits — rejected if quota is set
kubectl run no-limits --image=nginx -n team-backend
# Error: pods "no-limits" is forbidden: failed quota: team-backend-quota:
#   must specify limits.cpu, limits.memory, requests.cpu, requests.memory

# With limits — accepted
kubectl run with-limits --image=nginx -n team-backend \
  --requests='cpu=100m,memory=64Mi' \
  --limits='cpu=200m,memory=128Mi'

kubectl delete pod with-limits -n team-backend
```

---

## 4. Cross-Namespace DNS Communication

```yaml
# cross-ns-demo.yaml
# Service in team-backend that team-frontend needs to reach
apiVersion: v1
kind: Service
metadata:
  name: data-api                       # DNS name within the cluster
  namespace: team-backend              # Lives in team-backend
spec:
  selector:
    app: backend-api
    team: backend
  ports:
  - port: 80
    targetPort: 80
```

```bash
kubectl apply -f cross-ns-demo.yaml

# ── DNS name format for cross-namespace service access ────────────────────────
# Pattern: <service-name>.<namespace>.svc.cluster.local
# Full name: data-api.team-backend.svc.cluster.local

# From WITHIN team-frontend, call team-backend's service:
kubectl run dns-test \
  --image=curlimages/curl \
  --namespace=team-frontend \          # Running in team-frontend
  --restart=Never \
  --rm -it \
  -- curl http://data-api.team-backend.svc.cluster.local   # Reaching into team-backend

# Short form ONLY works within the same namespace:
# curl http://data-api               ← works from team-backend
# curl http://data-api               ← FAILS from team-frontend (resolves to wrong namespace)
# curl http://data-api.team-backend  ← also works (without .svc.cluster.local)

# Check which resources are cluster-scoped (not namespaced)
kubectl api-resources --namespaced=false | head -20
# Includes: Node, PersistentVolume, ClusterRole, StorageClass, Namespace itself

# Check which resources are namespaced
kubectl api-resources --namespaced=true | head -20
# Includes: Pod, Deployment, Service, ConfigMap, Secret, ServiceAccount
```

---

## 5. Stuck Namespace — Diagnosing and Forcing Removal

```bash
# ── A namespace can get stuck in "Terminating" state ─────────────────────────
# This happens when a custom resource has a finalizer that never completes
kubectl delete namespace stuck-namespace

# Check if it's stuck
kubectl get namespace stuck-namespace
# STATUS: Terminating   (has been for > 5 minutes)

# Diagnose: find resources still lingering inside
kubectl api-resources --verbs=list --namespaced -o name \
  | xargs -I {} kubectl get {} -n stuck-namespace 2>/dev/null \
  | grep -v "No resources"             # Shows what is preventing deletion

# Check for finalizers on the namespace object itself
kubectl get namespace stuck-namespace -o jsonpath='{.spec.finalizers}'

# ── Force remove finalizers (last resort — verify resources are truly gone) ───
# This bypasses the normal cleanup and directly removes the finalizer from etcd
kubectl get namespace stuck-namespace -o json \
  | python3 -c "import sys,json; d=json.load(sys.stdin); d['spec']['finalizers']=[]; print(json.dumps(d))" \
  | kubectl replace --raw /api/v1/namespaces/stuck-namespace/finalize -f -

# Alternative using jq (if installed)
kubectl get namespace stuck-namespace -o json \
  | jq '.spec.finalizers = []' \
  | kubectl replace --raw /api/v1/namespaces/stuck-namespace/finalize -f -

# Verify it's gone
kubectl get namespace stuck-namespace
# Error from server (NotFound): namespaces "stuck-namespace" not found
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

⬅️ **Prev:** [ConfigMaps and Secrets](../07_ConfigMaps_and_Secrets/Code_Example.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Ingress](../09_Ingress/Code_Example.md)
🏠 **[Home](../../README.md)**
