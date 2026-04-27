# solution.py — Production K8s Cluster
#
# This file contains the full YAML content for all nine production components
# embedded as Python strings. Use this as a reference after attempting to
# write each YAML file yourself.
#
# Components:
#   1. namespaces.yaml
#   2. rbac/serviceaccounts.yaml
#   3. rbac/roles.yaml
#   4. rbac/clusterroles.yaml
#   5. rbac/bindings.yaml
#   6. quotas/resource-quotas.yaml
#   7. autoscaling/hpa.yaml
#   8. policies/network-policies.yaml
#   9. policies/pod-disruption-budget.yaml
#  10. affinity/deployment-with-affinity.yaml
#  11. argocd/application.yaml
#  12. helm/prometheus-values.yaml


NAMESPACES_YAML = """
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
"""


SERVICEACCOUNTS_YAML = """
# developer-sa: identity used by developers to deploy to dev
apiVersion: v1
kind: ServiceAccount
metadata:
  name: developer-sa
  namespace: dev
  labels:
    role-type: developer
---
# ops-sa: full cluster access for the platform/ops team
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ops-sa
  namespace: default
  labels:
    role-type: ops
---
# ci-sa: read-only access used by CI pipelines to verify rollout status
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ci-sa
  namespace: production
  labels:
    role-type: ci
"""


ROLES_YAML = """
# developer-role: deploy and manage workloads in dev.
# Deliberately excludes Secrets — credentials go through CI.
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: developer-role
  namespace: dev
rules:
  - apiGroups: [""]
    resources:
      - pods
      - pods/log
      - pods/exec
      - services
      - configmaps
      - endpoints
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: ["apps"]
    resources: [deployments, replicasets, statefulsets]
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: ["apps"]
    resources: [deployments/rollback]
    verbs: [create]
  - apiGroups: ["autoscaling"]
    resources: [horizontalpodautoscalers]
    verbs: [get, list, watch]
---
# staging-readonly: developers can observe staging but not modify it
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: staging-readonly
  namespace: staging
rules:
  - apiGroups: ["", "apps", "autoscaling"]
    resources: ["*"]
    verbs: [get, list, watch]
"""


CLUSTERROLES_YAML = """
# ops-clusterrole: full access across all namespaces.
# In production, scope this more narrowly.
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
# ci-readonly: used by CI pipelines to check rollout status.
# Never write access.
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: ci-readonly
  labels:
    role-type: ci
rules:
  - apiGroups: ["", "apps", "batch"]
    resources: [pods, pods/log, deployments, replicasets, services, endpoints]
    verbs: [get, list, watch]
"""


BINDINGS_YAML = """
# developer-sa gets developer-role in dev namespace
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
# developer-sa gets read-only in staging
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
# ops-sa gets full cluster access
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
# ci-sa gets read-only in production
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
"""


RESOURCE_QUOTAS_YAML = """
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
# LimitRange: applies default requests/limits to pods that don't specify them.
# Without this, pods with no resource spec bypass the ResourceQuota.
apiVersion: v1
kind: LimitRange
metadata:
  name: default-limits
  namespace: production
spec:
  limits:
    - type: Container
      default:
        cpu: "500m"
        memory: "256Mi"
      defaultRequest:
        cpu: "100m"
        memory: "128Mi"
      max:
        cpu: "2"
        memory: "2Gi"
"""


HPA_YAML = """
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: myapi-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: myapi
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70   # scale up when average pod CPU exceeds 70%
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 30   # react quickly to load spikes
      policies:
        - type: Pods
          value: 2                     # add at most 2 pods per scale event
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300  # wait 5 minutes before scaling down
      policies:
        - type: Pods
          value: 1                     # remove 1 pod at a time (prevents flapping)
          periodSeconds: 60
"""


NETWORK_POLICIES_YAML = """
# Step 1: deny everything. All subsequent policies carve out exceptions.
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all-default
  namespace: production
spec:
  podSelector: {}    # applies to ALL pods
  policyTypes: [Ingress, Egress]
---
# Allow frontend to receive from ingress-nginx and to call backend
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-ingress
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes: [Ingress, Egress]
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: ingress-nginx
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: backend
      ports:
        - protocol: TCP
          port: 8000
    - ports:                     # allow DNS for all pods
        - protocol: UDP
          port: 53
---
# Allow backend to receive from frontend and to connect to postgres
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes: [Ingress, Egress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8000
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: postgres
      ports:
        - protocol: TCP
          port: 5432
    - ports:
        - protocol: UDP
          port: 53
---
# Allow postgres to receive only from backend
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-backend-to-db
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: postgres
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: backend
      ports:
        - protocol: TCP
          port: 5432
"""


POD_DISRUPTION_BUDGET_YAML = """
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: myapi-pdb
  namespace: production
spec:
  minAvailable: 1    # at least 1 pod must stay running during voluntary disruptions
  selector:
    matchLabels:
      app: myapi
"""


DEPLOYMENT_WITH_AFFINITY_YAML = """
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
          # HARD rule: pod MUST land on a node labeled env=production
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
              - matchExpressions:
                  - key: env
                    operator: In
                    values: [production]
          # SOFT rule: prefer nodes labeled tier=app (does not block scheduling)
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              preference:
                matchExpressions:
                  - key: tier
                    operator: In
                    values: [app]
        # Spread replicas across nodes so no single node is a SPOF
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
"""


ARGOCD_APPLICATION_YAML = """
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapi-production
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io   # cleans up K8s resources on delete
spec:
  project: default
  source:
    repoURL: https://github.com/YOUR_USERNAME/YOUR_REPO.git
    targetRevision: main
    path: k8s/affinity    # directory containing K8s manifests
  destination:
    server: https://kubernetes.default.svc
    namespace: production
  syncPolicy:
    automated:
      prune: true       # delete K8s resources removed from git
      selfHeal: true    # revert manual kubectl changes automatically
    syncOptions:
      - CreateNamespace=true
      - ServerSideApply=true
"""


PROMETHEUS_VALUES_YAML = """
grafana:
  adminPassword: "admin123"    # change this in production
  persistence:
    enabled: true
    size: 5Gi
  defaultDashboardsEnabled: true

prometheus:
  prometheusSpec:
    retention: 7d
    storageSpec:
      volumeClaimTemplate:
        spec:
          accessModes: [ReadWriteOnce]
          resources:
            requests:
              storage: 10Gi
    scrapeInterval: "30s"
    resources:
      requests:
        cpu: "200m"
        memory: "512Mi"
      limits:
        cpu: "1"
        memory: "2Gi"

alertmanager:
  alertmanagerSpec:
    resources:
      requests:
        cpu: "50m"
        memory: "64Mi"
      limits:
        cpu: "200m"
        memory: "256Mi"

# Disable components unavailable in minikube single-node setup
kubeEtcd:
  enabled: false
kubeControllerManager:
  enabled: false
kubeScheduler:
  enabled: false
"""
