# Code Examples: Production Kubernetes Cluster

---

## k8s/namespaces.yaml

```yaml
# k8s/namespaces.yaml
# Five namespaces: three environment tiers + monitoring + GitOps tooling.

apiVersion: v1
kind: Namespace
metadata:
  name: dev
  labels:
    environment: dev
    managed-by: ops
---
apiVersion: v1
kind: Namespace
metadata:
  name: staging
  labels:
    environment: staging
    managed-by: ops
---
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    environment: production
    managed-by: ops
---
apiVersion: v1
kind: Namespace
metadata:
  name: monitoring
  labels:
    purpose: observability
---
apiVersion: v1
kind: Namespace
metadata:
  name: argocd
  labels:
    purpose: gitops
```

---

## k8s/rbac/serviceaccounts.yaml

```yaml
# k8s/rbac/serviceaccounts.yaml
# ServiceAccounts are identities that pods and CI systems use.
# Human users typically authenticate via OIDC/certificates.
# These SAs represent the team identities for demonstrating RBAC.

apiVersion: v1
kind: ServiceAccount
metadata:
  name: developer-sa
  namespace: dev
  labels:
    role-type: developer
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ops-sa
  namespace: default
  labels:
    role-type: ops
---
# The CI service account needs read-only access to check rollout status.
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ci-sa
  namespace: production
  labels:
    role-type: ci
```

---

## k8s/rbac/roles.yaml

```yaml
# k8s/rbac/roles.yaml
# Role: namespace-scoped permissions.
# (Use ClusterRole for cluster-wide resources like nodes, PVs.)

# Developer role: deploy and manage workloads in dev.
# Deliberately excludes Secrets (developers use CI for that).
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: developer-role
  namespace: dev
rules:
  # Core resources (pods, services, configmaps)
  - apiGroups: [""]
    resources:
      - pods
      - pods/log
      - pods/exec
      - services
      - configmaps
      - endpoints
    verbs:
      - get
      - list
      - watch
      - create
      - update
      - patch
      - delete

  # Deployments, ReplicaSets, StatefulSets
  - apiGroups: ["apps"]
    resources:
      - deployments
      - replicasets
      - statefulsets
    verbs:
      - get
      - list
      - watch
      - create
      - update
      - patch
      - delete

  # Allow checking rollout status
  - apiGroups: ["apps"]
    resources:
      - deployments/rollback
    verbs:
      - create

  # HPA — developers can adjust scaling
  - apiGroups: ["autoscaling"]
    resources:
      - horizontalpodautoscalers
    verbs:
      - get
      - list
      - watch

---
# Staging role: read-only (developers observe, don't modify staging)
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: staging-readonly
  namespace: staging
rules:
  - apiGroups: ["", "apps", "autoscaling"]
    resources: ["*"]
    verbs: ["get", "list", "watch"]
```

---

## k8s/rbac/clusterroles.yaml

```yaml
# k8s/rbac/clusterroles.yaml
# ClusterRoles: permissions that span all namespaces or cover cluster-level resources.

# Ops ClusterRole: full access everywhere.
# In practice, scope this more narrowly. Full * access is for demonstration.
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: ops-clusterrole
  labels:
    role-type: ops
rules:
  - apiGroups: ["*"]
    resources: ["*"]
    verbs: ["*"]

---
# CI read-only ClusterRole: used by CI pipelines to verify rollout status.
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: ci-readonly
  labels:
    role-type: ci
rules:
  - apiGroups: ["", "apps", "batch"]
    resources:
      - pods
      - pods/log
      - deployments
      - replicasets
      - services
      - endpoints
    verbs:
      - get
      - list
      - watch
```

---

## k8s/rbac/bindings.yaml

```yaml
# k8s/rbac/bindings.yaml
# RoleBinding: attaches a Role to a subject (user, group, or service account)
# within a specific namespace.
# ClusterRoleBinding: attaches a ClusterRole across all namespaces.

# Developer gets developer-role in dev namespace
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: developer-dev-binding
  namespace: dev
subjects:
  - kind: ServiceAccount
    name: developer-sa
    namespace: dev
roleRef:
  kind: Role
  name: developer-role
  apiGroup: rbac.authorization.k8s.io

---
# Developer gets read-only in staging namespace
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: developer-staging-readonly-binding
  namespace: staging
subjects:
  - kind: ServiceAccount
    name: developer-sa
    namespace: dev
roleRef:
  kind: Role
  name: staging-readonly
  apiGroup: rbac.authorization.k8s.io

---
# Ops gets full cluster access
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: ops-binding
subjects:
  - kind: ServiceAccount
    name: ops-sa
    namespace: default
roleRef:
  kind: ClusterRole
  name: ops-clusterrole
  apiGroup: rbac.authorization.k8s.io

---
# CI service account gets read-only access in production
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: ci-binding
  namespace: production
subjects:
  - kind: ServiceAccount
    name: ci-sa
    namespace: production
roleRef:
  kind: ClusterRole
  name: ci-readonly
  apiGroup: rbac.authorization.k8s.io
```

---

## k8s/quotas/resource-quotas.yaml

```yaml
# k8s/quotas/resource-quotas.yaml
# ResourceQuota sets hard limits on what a namespace can consume.
# If a pod would exceed the quota, it's rejected at admission.

# Dev: generous limits for experimentation
apiVersion: v1
kind: ResourceQuota
metadata:
  name: dev-quota
  namespace: dev
spec:
  hard:
    requests.cpu: "4"
    requests.memory: "8Gi"
    limits.cpu: "8"
    limits.memory: "16Gi"
    pods: "20"
    services: "10"
    persistentvolumeclaims: "5"

---
# Staging: moderate limits
apiVersion: v1
kind: ResourceQuota
metadata:
  name: staging-quota
  namespace: staging
spec:
  hard:
    requests.cpu: "8"
    requests.memory: "16Gi"
    limits.cpu: "16"
    limits.memory: "32Gi"
    pods: "30"
    services: "15"
    persistentvolumeclaims: "10"

---
# Production: tighter limits to prevent runaway resource consumption
apiVersion: v1
kind: ResourceQuota
metadata:
  name: production-quota
  namespace: production
spec:
  hard:
    requests.cpu: "16"
    requests.memory: "32Gi"
    limits.cpu: "32"
    limits.memory: "64Gi"
    pods: "50"
    services: "20"
    persistentvolumeclaims: "20"

---
# LimitRange: sets default resource requests/limits for pods that don't specify them.
# Without this, pods with no requests/limits bypass the ResourceQuota.
apiVersion: v1
kind: LimitRange
metadata:
  name: default-limits
  namespace: production
spec:
  limits:
    - type: Container
      default:          # Applied if a container has no limits specified
        cpu: "500m"
        memory: "256Mi"
      defaultRequest:   # Applied if a container has no requests specified
        cpu: "100m"
        memory: "128Mi"
      max:              # No single container can exceed these
        cpu: "2"
        memory: "2Gi"
```

---

## k8s/autoscaling/hpa.yaml

```yaml
# k8s/autoscaling/hpa.yaml
# HorizontalPodAutoscaler: automatically adjusts replica count
# based on CPU utilization (or custom metrics).
#
# Requires: kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/...
# On minikube: minikube addons enable metrics-server

apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: myapi-hpa
  namespace: production
spec:
  # The Deployment to scale
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: myapi

  # Replica bounds: never drop below 2, never exceed 10
  minReplicas: 2
  maxReplicas: 10

  metrics:
    # Scale up when average CPU across all pods exceeds 70%
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70

    # Optionally also scale on memory (uncomment to enable)
    # - type: Resource
    #   resource:
    #     name: memory
    #     target:
    #       type: Utilization
    #       averageUtilization: 80

  behavior:
    # Scale up quickly when under load
    scaleUp:
      stabilizationWindowSeconds: 30   # Wait 30s before scaling up again
      policies:
        - type: Pods
          value: 2                     # Add up to 2 pods at a time
          periodSeconds: 60

    # Scale down slowly to avoid flapping
    scaleDown:
      stabilizationWindowSeconds: 300  # Wait 5 minutes before scaling down
      policies:
        - type: Pods
          value: 1                     # Remove 1 pod at a time
          periodSeconds: 60
```

---

## k8s/policies/network-policies.yaml

```yaml
# k8s/policies/network-policies.yaml
# NetworkPolicies control which pods can communicate with each other.
# Without any NetworkPolicy, all pods in a cluster can reach all other pods.
# The pattern here: deny everything by default, then allow only specific paths.

# Default deny: reject all ingress AND egress for pods in the namespace.
# This is the baseline. Other policies below add exceptions.
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all-default
  namespace: production
spec:
  podSelector: {}    # Applies to ALL pods in the namespace
  policyTypes:
    - Ingress
    - Egress

---
# Allow frontend pods to receive external traffic (from the Ingress controller)
# and to send requests to the backend.
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-ingress
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes:
    - Ingress
    - Egress
  ingress:
    # Allow traffic from the nginx ingress controller
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: ingress-nginx
  egress:
    # Allow frontend to call the backend
    - to:
        - podSelector:
            matchLabels:
              app: backend
      ports:
        - protocol: TCP
          port: 8000
    # Allow DNS resolution (all pods need this)
    - ports:
        - protocol: UDP
          port: 53

---
# Allow backend pods to receive from frontend and to connect to Postgres.
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8000
  egress:
    # Backend can connect to Postgres
    - to:
        - podSelector:
            matchLabels:
              app: postgres
      ports:
        - protocol: TCP
          port: 5432
    # Allow DNS
    - ports:
        - protocol: UDP
          port: 53

---
# Allow Postgres to receive connections from the backend only.
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-backend-to-db
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: postgres
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: backend
      ports:
        - protocol: TCP
          port: 5432
```

---

## k8s/policies/pod-disruption-budget.yaml

```yaml
# k8s/policies/pod-disruption-budget.yaml
# PodDisruptionBudget (PDB) limits voluntary disruptions to pods.
# "Voluntary disruption" = node drain, cluster upgrade, node maintenance.
# "Involuntary" = hardware failure (PDB doesn't apply to those).
#
# This PDB ensures at least 1 myapi pod is always running during disruptions.
# If you have 3 replicas and someone drains a node, K8s will evict at most
# 2 pods (leaving 1 running), reschedule them, then continue the drain.

apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: myapi-pdb
  namespace: production
spec:
  # minAvailable: the minimum number of pods that must be running.
  # Use an integer (1) or percentage ("33%").
  # With 3 replicas, minAvailable: 2 means maxUnavailable is 1.
  minAvailable: 1

  # Alternatively, use maxUnavailable:
  # maxUnavailable: 1

  selector:
    matchLabels:
      app: myapi
```

---

## k8s/affinity/deployment-with-affinity.yaml

```yaml
# k8s/affinity/deployment-with-affinity.yaml
# Node affinity: schedule production pods on nodes labeled env=production.
# In a real multi-node cluster, you'd have dedicated production nodes
# (possibly with taints to prevent dev pods from landing on them).
#
# Label your node first:
#   kubectl label node <NODE_NAME> env=production tier=app

apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapi
  namespace: production
spec:
  replicas: 2
  selector:
    matchLabels:
      app: myapi
  template:
    metadata:
      labels:
        app: myapi
    spec:
      affinity:
        nodeAffinity:
          # requiredDuringSchedulingIgnoredDuringExecution:
          #   HARD rule: pod MUST be scheduled on a matching node.
          #   "IgnoredDuringExecution" = if the label is removed after scheduling,
          #   the pod is NOT evicted.
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
              - matchExpressions:
                  - key: env
                    operator: In
                    values:
                      - production

          # preferredDuringSchedulingIgnoredDuringExecution:
          #   SOFT rule: try to schedule here, but don't block if no match.
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100      # Higher weight = stronger preference
              preference:
                matchExpressions:
                  - key: tier
                    operator: In
                    values:
                      - app

        # Pod anti-affinity: spread replicas across nodes.
        # Prevents all pods landing on the same node (single point of failure).
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchLabels:
                    app: myapi
                topologyKey: kubernetes.io/hostname

      containers:
        - name: myapi
          image: YOUR_USERNAME/myapi:1.0.0
          ports:
            - containerPort: 8000
          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "500m"
              memory: "256Mi"
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 10
```

---

## k8s/argocd/application.yaml

```yaml
# k8s/argocd/application.yaml
# ArgoCD Application manifest.
# Apply this after ArgoCD is installed.
# ArgoCD will poll the Git repo every 3 minutes and apply any changes.
#
# Update the repoURL to point to your actual repository.

apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapi-production
  namespace: argocd
  # finalizers ensure ArgoCD cleans up K8s resources when you delete this Application
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default

  source:
    # Your Git repository containing K8s manifests
    repoURL: https://github.com/YOUR_USERNAME/YOUR_REPO.git
    # The branch to track
    targetRevision: main
    # The directory within the repo that contains the K8s manifests
    path: k8s/affinity

  destination:
    # Deploy to the local cluster (where ArgoCD is running)
    server: https://kubernetes.default.svc
    namespace: production

  syncPolicy:
    # automated: ArgoCD syncs automatically when it detects a diff
    automated:
      # prune: delete K8s resources that were removed from Git
      prune: true
      # selfHeal: if someone makes a manual kubectl change, ArgoCD reverts it
      selfHeal: true

    syncOptions:
      # Create the namespace if it doesn't exist
      - CreateNamespace=true
      # Apply server-side apply (better conflict handling)
      - ServerSideApply=true
```

---

## helm/prometheus-values.yaml

```yaml
# helm/prometheus-values.yaml
# Custom values for the kube-prometheus-stack Helm chart.
# Install with:
#   helm install monitoring prometheus-community/kube-prometheus-stack \
#     --namespace monitoring \
#     --values helm/prometheus-values.yaml

grafana:
  # Change this in production!
  adminPassword: "admin123"

  # Persist Grafana config and dashboards
  persistence:
    enabled: true
    size: 5Gi

  # Default dashboards to install
  defaultDashboardsEnabled: true

prometheus:
  prometheusSpec:
    # How long to retain metrics data
    retention: 7d

    # Storage for Prometheus metrics
    storageSpec:
      volumeClaimTemplate:
        spec:
          accessModes:
            - ReadWriteOnce
          resources:
            requests:
              storage: 10Gi

    # Scrape interval — how often Prometheus collects metrics
    scrapeInterval: "30s"

    # Resource limits for the Prometheus pod
    resources:
      requests:
        cpu: "200m"
        memory: "512Mi"
      limits:
        cpu: "1"
        memory: "2Gi"

alertmanager:
  alertmanagerSpec:
    # Resource limits for AlertManager
    resources:
      requests:
        cpu: "50m"
        memory: "64Mi"
      limits:
        cpu: "200m"
        memory: "256Mi"

# Disable components you don't need (saves resources on minikube)
kubeEtcd:
  enabled: false

kubeControllerManager:
  enabled: false

kubeScheduler:
  enabled: false
```

---

## 📂 Navigation

| | |
|---|---|
| Guide | [Project_Guide.md](./Project_Guide.md) |
| Steps | [Step_by_Step.md](./Step_by_Step.md) |
| All Projects | [04_Projects/](../) |
