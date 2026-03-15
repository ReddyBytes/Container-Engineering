# RBAC — Code Examples

## Scenario: Securing a Kubernetes Operator

We have an app called `inventory-api` that runs in the `shop` namespace. It needs to:
- Read pods and services in its own namespace
- Read ConfigMaps in its own namespace
- NOT touch anything else

We also want a global read-only role for monitoring tools.

---

## 1. ServiceAccount for the Application

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: inventory-api-sa          # dedicated identity for this app
  namespace: shop
  labels:
    app: inventory-api
# Pods using this SA will have their token mounted automatically.
# Set automountServiceAccountToken: false if you don't need it.
```

---

## 2. Role — Specific Permissions (Namespaced)

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: inventory-api-role
  namespace: shop                 # this role only applies in the 'shop' namespace
rules:
  - apiGroups: [""]               # "" = core API group (pods, services, configmaps)
    resources: ["pods", "services", "endpoints"]
    verbs: ["get", "list", "watch"]   # read-only access to these resources

  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["get", "list", "watch"]   # read configmaps but NOT create/update/delete

  - apiGroups: ["apps"]           # apps group covers deployments, replicasets, etc.
    resources: ["deployments", "replicasets"]
    verbs: ["get", "list", "watch"]
```

---

## 3. RoleBinding — Grant the Role to the ServiceAccount

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: inventory-api-rolebinding
  namespace: shop                 # binding is scoped to the 'shop' namespace
subjects:
  - kind: ServiceAccount
    name: inventory-api-sa        # the service account we created above
    namespace: shop               # must specify namespace for ServiceAccount subjects
roleRef:
  kind: Role                      # can be Role or ClusterRole
  name: inventory-api-role        # the role defined above
  apiGroup: rbac.authorization.k8s.io
```

---

## 4. Deployment Using the ServiceAccount

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inventory-api
  namespace: shop
spec:
  replicas: 2
  selector:
    matchLabels:
      app: inventory-api
  template:
    metadata:
      labels:
        app: inventory-api
    spec:
      serviceAccountName: inventory-api-sa  # use the dedicated SA, not 'default'
      automountServiceAccountToken: true     # set to false if the app doesn't call K8s API
      containers:
        - name: api
          image: my-registry/inventory-api:1.0.0
          ports:
            - containerPort: 8080
```

---

## 5. ClusterRole — Read-Only Access Cluster-Wide (for Monitoring)

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: cluster-read-only
  # Optional: aggregate into the built-in 'view' ClusterRole
  labels:
    rbac.authorization.k8s.io/aggregate-to-view: "true"
rules:
  - apiGroups: [""]
    resources: ["pods", "services", "nodes", "namespaces",
                "persistentvolumes", "configmaps", "endpoints",
                "events", "resourcequotas"]
    verbs: ["get", "list", "watch"]

  - apiGroups: ["apps"]
    resources: ["deployments", "daemonsets", "statefulsets",
                "replicasets"]
    verbs: ["get", "list", "watch"]

  - apiGroups: ["batch"]
    resources: ["jobs", "cronjobs"]
    verbs: ["get", "list", "watch"]

  - apiGroups: ["metrics.k8s.io"]
    resources: ["nodes", "pods"]
    verbs: ["get", "list"]       # needed by monitoring tools like Prometheus
```

---

## 6. ClusterRoleBinding — Bind to Monitoring ServiceAccount

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: monitoring-read-only
subjects:
  - kind: ServiceAccount
    name: prometheus              # ServiceAccount in the monitoring namespace
    namespace: monitoring
  - kind: ServiceAccount
    name: grafana-agent           # multiple subjects can share one binding
    namespace: monitoring
roleRef:
  kind: ClusterRole
  name: cluster-read-only         # the ClusterRole we defined above
  apiGroup: rbac.authorization.k8s.io
```

---

## 7. ServiceAccount for Monitoring Namespace

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: prometheus
  namespace: monitoring
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: grafana-agent
  namespace: monitoring
```

---

## 8. Testing Permissions with kubectl auth can-i

```bash
# Test that inventory-api can read pods in the 'shop' namespace
kubectl auth can-i get pods \
  --as=system:serviceaccount:shop:inventory-api-sa \
  -n shop
# Expected: yes

# Test that inventory-api CANNOT delete pods (should be denied)
kubectl auth can-i delete pods \
  --as=system:serviceaccount:shop:inventory-api-sa \
  -n shop
# Expected: no

# Test that inventory-api cannot read pods in OTHER namespaces
kubectl auth can-i get pods \
  --as=system:serviceaccount:shop:inventory-api-sa \
  -n production
# Expected: no

# Test that prometheus can list pods cluster-wide
kubectl auth can-i list pods \
  --as=system:serviceaccount:monitoring:prometheus
# Expected: yes (cluster-wide ClusterRoleBinding)

# Test that prometheus CANNOT delete anything
kubectl auth can-i delete deployments \
  --as=system:serviceaccount:monitoring:prometheus
# Expected: no

# List ALL permissions for inventory-api in the shop namespace
kubectl auth can-i --list \
  --as=system:serviceaccount:shop:inventory-api-sa \
  -n shop
```

---

## 9. Deny All — Explicit Denial Pattern (No Access Role)

Kubernetes RBAC is deny-by-default: if there is no rule granting something, it is denied. You rarely need an explicit deny role, but if you want to revoke a group member's access, you can bind them to an empty role:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: no-access
  namespace: restricted
rules: []   # empty rules = no permissions granted; everything is denied
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: locked-out-binding
  namespace: restricted
subjects:
  - kind: User
    name: contractor-bob
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: no-access
  apiGroup: rbac.authorization.k8s.io
```

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Theory.md](./Theory.md) |
| Cheatsheet | [Cheatsheet.md](./Cheatsheet.md) |
| Interview Q&A | [Interview_QA.md](./Interview_QA.md) |
| Module Home | [11_RBAC](../) |
