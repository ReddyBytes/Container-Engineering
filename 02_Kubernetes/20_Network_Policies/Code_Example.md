# Network Policies — Code Examples

## Scenario: Three-Tier Application (Frontend → Backend → Database)

### Application Layout

```
Namespace: production
Pods:
  - frontend (app: frontend, tier: web)
  - backend  (app: backend, tier: api)
  - database (app: postgres, tier: db)

External traffic enters via the ingress-nginx namespace.
Backend needs to call an external payments API at 203.0.113.42/32.
```

---

## Step 1: Default Deny-All (Apply First)

```yaml
# Block ALL ingress and egress for every pod in the namespace.
# This is the starting point. Add allow rules on top of this.

apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: production
spec:
  podSelector: {}        # {} = selects ALL pods in this namespace
  policyTypes:
    - Ingress
    - Egress
  # No ingress or egress rules = deny everything
```

---

## Step 2: Allow DNS Egress (Without This, Nothing Works)

```yaml
# After default-deny, pods cannot resolve DNS.
# Allow all pods to query kube-dns in kube-system.
# ALWAYS apply this immediately after default-deny.

apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns-egress
  namespace: production
spec:
  podSelector: {}          # applies to all pods in production namespace
  policyTypes:
    - Egress
  egress:
    - ports:
        - protocol: UDP
          port: 53          # DNS over UDP (most queries)
        - protocol: TCP
          port: 53          # DNS over TCP (large responses, zone transfers)
      # No 'to' field means: to anywhere on port 53
      # More restrictive version would add:
      # to:
      #   - namespaceSelector:
      #       matchLabels:
      #         kubernetes.io/metadata.name: kube-system
```

---

## Step 3: Allow Ingress to Frontend (from Ingress Controller)

```yaml
# Frontend accepts HTTP/HTTPS traffic only from the ingress-nginx namespace.
# No other pod can initiate connections to the frontend.

apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-ingress-to-frontend
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: frontend         # applies to frontend pods only
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              # kube-system automatically has this label (K8s 1.21+)
              kubernetes.io/metadata.name: ingress-nginx
          # Optional: also restrict by pod label within that namespace
          podSelector:
            matchLabels:
              app.kubernetes.io/name: ingress-nginx
      ports:
        - protocol: TCP
          port: 3000          # frontend app port
```

---

## Step 4: Allow Frontend → Backend

```yaml
# Backend accepts traffic only from the frontend.
# Any other pod trying to reach the backend API is blocked.

apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: backend            # applies to backend pods
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend   # only allow from frontend pods
              # (same namespace = no namespaceSelector needed)
      ports:
        - protocol: TCP
          port: 8080          # backend REST API port
```

---

## Step 5: Allow Backend Egress to Frontend (Optional) and to Database

```yaml
# Allow backend pods to initiate connections to:
# 1. The database (port 5432)
# 2. The external payments API (specific IP)

apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-egress
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
    - Egress
  egress:
    # Allow connections to the database pod
    - to:
        - podSelector:
            matchLabels:
              app: postgres     # target: database pods
      ports:
        - protocol: TCP
          port: 5432

    # Allow connections to external payments API
    - to:
        - ipBlock:
            cidr: 203.0.113.42/32    # specific external IP
      ports:
        - protocol: TCP
          port: 443                  # HTTPS only

    # Allow connections to the Redis cache pod
    - to:
        - podSelector:
            matchLabels:
              app: redis
      ports:
        - protocol: TCP
          port: 6379
```

---

## Step 6: Allow Backend → Database (Database Ingress)

```yaml
# Database only accepts connections from the backend.
# Absolutely nothing else can reach the database.

apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-backend-to-database
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: postgres           # applies to database pods
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: backend    # only backend can connect to the DB
      ports:
        - protocol: TCP
          port: 5432
  # No egress rules = database cannot initiate outbound connections
  # (the default-deny-all policy covers egress for database pods)
```

---

## Step 7: Allow Monitoring Access (Cross-Namespace)

```yaml
# Allow Prometheus in the monitoring namespace to scrape metrics
# from all pods in the production namespace on port 9090.

apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-prometheus-scraping
  namespace: production
spec:
  podSelector: {}              # applies to ALL pods in production
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: monitoring
          podSelector:
            matchLabels:
              app: prometheus  # only Prometheus pods, not everything in monitoring
      ports:
        - protocol: TCP
          port: 9090           # Prometheus metrics endpoint
```

---

## Step 8: Complete deny-all-egress Except DNS (Strict Mode)

```yaml
# Lock down the database completely: no egress at all,
# except DNS (so it can resolve hostnames in connection strings).

apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-strict-egress
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: postgres
  policyTypes:
    - Egress
  egress:
    # Only allow DNS - nothing else
    - ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
    # If the database needs to call backup storage:
    # - to:
    #     - ipBlock:
    #         cidr: <backup-storage-ip>/32
    #   ports:
    #     - protocol: TCP
    #       port: 443
```

---

## Testing the Policies

```bash
# Deploy a test busybox pod
kubectl run nettest \
  --image=busybox:1.36 \
  --rm -it \
  --restart=Never \
  -n production \
  -- sh

# From inside nettest (this pod has no labels — should be blocked):

# Try to reach database directly (should fail)
nc -zv postgres-service 5432
# Expected: connection refused or timeout

# Try to reach backend directly (should fail)
wget -qO- --timeout=5 http://backend-service:8080
# Expected: timeout

# Test from frontend pod — should reach backend
kubectl exec -it \
  $(kubectl get pods -n production -l app=frontend -o jsonpath='{.items[0].metadata.name}') \
  -n production \
  -- wget -qO- http://backend-service:8080/health
# Expected: 200 OK

# Test from backend pod — should reach database
kubectl exec -it \
  $(kubectl get pods -n production -l app=backend -o jsonpath='{.items[0].metadata.name}') \
  -n production \
  -- nc -zv postgres-service 5432
# Expected: connection succeeded

# Test that frontend CANNOT reach database (should be blocked)
kubectl exec -it \
  $(kubectl get pods -n production -l app=frontend -o jsonpath='{.items[0].metadata.name}') \
  -n production \
  -- nc -zv postgres-service 5432 -w 3
# Expected: timeout

# Verify DNS still works from any pod (if allow-dns-egress is applied)
kubectl exec -it \
  $(kubectl get pods -n production -l app=backend -o jsonpath='{.items[0].metadata.name}') \
  -n production \
  -- nslookup kubernetes.default.svc.cluster.local
# Expected: successful resolution
```

---

## Summary of All Policies in This Example

```
default-deny-all           → Blocks everything for all pods
allow-dns-egress           → All pods can resolve DNS
allow-ingress-to-frontend  → Frontend receives traffic from ingress-nginx
allow-frontend-to-backend  → Backend receives traffic from frontend only
backend-egress             → Backend can reach DB, Redis, and external payments API
allow-backend-to-database  → Database receives traffic from backend only
allow-prometheus-scraping  → All pods accept metrics scraping from monitoring namespace
database-strict-egress     → Database can only egress to DNS
```

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Theory.md](./Theory.md) |
| Cheatsheet | [Cheatsheet.md](./Cheatsheet.md) |
| Interview Q&A | [Interview_QA.md](./Interview_QA.md) |
| Module Home | [20_Network_Policies](../) |
