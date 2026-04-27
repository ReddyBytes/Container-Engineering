# Service Accounts — Code Examples

All examples are production-quality with detailed comments explaining every decision.

---

## 1. Full RBAC Setup — Service Account, Role, and RoleBinding

```yaml
# myapp-rbac.yaml
# Complete RBAC configuration for an application that needs to read ConfigMaps and list Pods
# Rule: create one Service Account per application, grant only what it needs

---
# Step 1: Create a dedicated Service Account for this application
apiVersion: v1
kind: ServiceAccount
metadata:
  name: myapp-sa
  namespace: production
automountServiceAccountToken: false      # ← disable auto-mount at SA level; pods opt-in explicitly

---
# Step 2: Define a Role — what actions are allowed on what resources
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: myapp-role
  namespace: production                  # ← Role is namespace-scoped; use ClusterRole for cluster-wide
rules:
- apiGroups: [""]                        # ← "" means the core API group (Pods, ConfigMaps, Services)
  resources: ["configmaps"]
  verbs: ["get", "list", "watch"]        # ← read-only; never grant "create", "update", "delete" unless needed
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["pods/log"]               # ← sub-resources need their own rule
  verbs: ["get"]

---
# Step 3: Bind the Role to the Service Account
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: myapp-rolebinding
  namespace: production
subjects:                                # ← who gets the permissions
- kind: ServiceAccount
  name: myapp-sa
  namespace: production                  # ← namespace is required for ServiceAccount subjects
roleRef:                                 # ← what permissions to grant (immutable after creation)
  kind: Role
  name: myapp-role
  apiGroup: rbac.authorization.k8s.io

---
# Step 4: Pod that uses the dedicated Service Account
apiVersion: v1
kind: Pod
metadata:
  name: myapp
  namespace: production
spec:
  serviceAccountName: myapp-sa          # ← use the dedicated SA, not the default
  automountServiceAccountToken: true    # ← opt-in here (overrides the SA-level false)
  containers:
  - name: app
    image: myapp:1.0
    resources:
      requests:
        cpu: "100m"
        memory: "128Mi"
      limits:
        cpu: "500m"
        memory: "256Mi"
```

```bash
kubectl apply -f myapp-rbac.yaml

# Verify the Service Account exists
kubectl get serviceaccount myapp-sa -n production

# Check what permissions the SA has (impersonation test)
kubectl auth can-i list pods \
  --as=system:serviceaccount:production:myapp-sa \
  -n production
# yes

kubectl auth can-i delete pods \
  --as=system:serviceaccount:production:myapp-sa \
  -n production
# no ← correct; we only granted list/get/watch

# List all permissions the SA has (audit view)
kubectl auth can-i --list \
  --as=system:serviceaccount:production:myapp-sa \
  -n production
```

---

## 2. Disabling Auto-Mount — Reducing Attack Surface

```yaml
# no-api-access.yaml
# Most application pods do not need to call the Kubernetes API at all
# For these pods, disable auto-mount to reduce the attack surface
# If a container is compromised, the attacker has no K8s API token

---
# Service Account for a standard web app that never calls the K8s API
apiVersion: v1
kind: ServiceAccount
metadata:
  name: web-app-sa
  namespace: production
automountServiceAccountToken: false      # ← default: no token injected into pods using this SA

---
# Deployment: all pods inherit the SA's automount=false setting
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      serviceAccountName: web-app-sa
      # automountServiceAccountToken not set here — inherits SA-level false
      # You can also set it explicitly on the pod to override the SA setting:
      # automountServiceAccountToken: false
      containers:
      - name: web
        image: mywebapp:2.1
        resources:
          requests:
            cpu: "200m"
            memory: "256Mi"
          limits:
            cpu: "1"
            memory: "512Mi"
```

```bash
kubectl apply -f no-api-access.yaml

# Confirm no token is mounted in the pod
kubectl exec -n production \
  $(kubectl get pod -n production -l app=web-app -o name | head -1) \
  -- ls /var/run/secrets/kubernetes.io/serviceaccount/ 2>&1
# ls: cannot access '/var/run/secrets/kubernetes.io/serviceaccount/': No such file or directory

# Compare with a pod that HAS auto-mount enabled
kubectl exec -n production myapp \
  -- ls /var/run/secrets/kubernetes.io/serviceaccount/
# ca.crt  namespace  token    ← these exist in a pod with auto-mount enabled
```

---

## 3. ClusterRole for Cluster-Wide Read Access (Monitoring Agent)

```yaml
# monitoring-sa.yaml
# A monitoring agent (like Prometheus) needs to list pods, services, and nodes
# across ALL namespaces — so we need a ClusterRole + ClusterRoleBinding

---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: prometheus-sa
  namespace: monitoring                  # ← SA lives in the monitoring namespace

---
# ClusterRole: permissions that apply cluster-wide (not namespace-scoped)
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: prometheus-cluster-role
rules:
- apiGroups: [""]
  resources:
  - nodes
  - nodes/proxy                          # ← needed to scrape kubelet /metrics/cadvisor
  - services
  - endpoints
  - pods
  verbs: ["get", "list", "watch"]
- apiGroups: ["extensions", "networking.k8s.io"]
  resources: ["ingresses"]
  verbs: ["get", "list", "watch"]
- nonResourceURLs:
  - "/metrics"                           # ← needed to scrape the /metrics endpoint directly
  - "/metrics/cadvisor"
  verbs: ["get"]

---
# ClusterRoleBinding: bind the ClusterRole to the SA across the whole cluster
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: prometheus-cluster-role-binding
subjects:
- kind: ServiceAccount
  name: prometheus-sa
  namespace: monitoring                  # ← SA namespace must match here
roleRef:
  kind: ClusterRole                      # ← note: ClusterRole, not Role
  name: prometheus-cluster-role
  apiGroup: rbac.authorization.k8s.io
```

```bash
kubectl apply -f monitoring-sa.yaml

# Verify the SA can list pods in any namespace
kubectl auth can-i list pods \
  --as=system:serviceaccount:monitoring:prometheus-sa \
  --all-namespaces
# yes

# Verify the SA cannot create or delete (read-only)
kubectl auth can-i delete pods \
  --as=system:serviceaccount:monitoring:prometheus-sa \
  -n production
# no
```

---

## 4. IRSA — Pod Accesses AWS S3 Without Stored Credentials

```yaml
# irsa-setup.yaml
# IRSA (IAM Roles for Service Accounts) on Amazon EKS
# The pod gets temporary AWS credentials automatically via projected token exchange
# No AWS access keys or secrets stored in the cluster

---
# Step 1: Annotate the Service Account with the IAM Role ARN
# The IAM Role must have a trust policy allowing this K8s SA to assume it
# (trust policy configured in AWS IAM, not in K8s)
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-reader-sa
  namespace: production
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/MyS3ReaderRole
    # ← the EKS Pod Identity Webhook injects AWS_WEB_IDENTITY_TOKEN_FILE
    # and AWS_ROLE_ARN env vars into pods using this SA
    eks.amazonaws.com/token-expiration: "86400"  # ← token TTL in seconds (default 86400 = 24h)
automountServiceAccountToken: true       # ← must be true so the projected token is mounted

---
# Step 2: Pod that reads from S3 — the AWS SDK picks up credentials automatically
apiVersion: v1
kind: Pod
metadata:
  name: s3-reader
  namespace: production
spec:
  serviceAccountName: s3-reader-sa       # ← use the IRSA-annotated SA
  containers:
  - name: reader
    image: amazon/aws-cli:2.15.0
    command: ["/bin/sh", "-c"]
    args:
    - |
      # The AWS SDK finds credentials automatically via the projected token
      # No AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY needed
      aws s3 ls s3://my-data-bucket/
      sleep 3600
    resources:
      requests:
        cpu: "100m"
        memory: "128Mi"
      limits:
        cpu: "500m"
        memory: "256Mi"
```

```bash
# Verify IRSA annotation is present
kubectl get serviceaccount s3-reader-sa -n production -o yaml | grep "role-arn"

# Check the projected token and env vars injected by the EKS webhook
kubectl exec s3-reader -n production -- env | grep AWS
# AWS_ROLE_ARN=arn:aws:iam::123456789012:role/MyS3ReaderRole
# AWS_WEB_IDENTITY_TOKEN_FILE=/var/run/secrets/eks.amazonaws.com/serviceaccount/token

# Confirm S3 access works without any stored credentials
kubectl logs s3-reader -n production
```

---

## 5. Inspecting and Debugging Service Account Tokens

```bash
# --- Inspect a projected token (short-lived, Kubernetes 1.21+) ---

# Get the token from inside a running pod
kubectl exec -n production myapp \
  -- cat /var/run/secrets/kubernetes.io/serviceaccount/token

# Decode the JWT manually (the middle section is base64url-encoded JSON)
kubectl exec -n production myapp \
  -- cat /var/run/secrets/kubernetes.io/serviceaccount/token \
  | cut -d'.' -f2 \
  | base64 -d 2>/dev/null \
  | python3 -m json.tool
# {
#   "iss": "https://kubernetes.default.svc",
#   "sub": "system:serviceaccount:production:myapp-sa",   ← identity used in RBAC
#   "aud": ["https://kubernetes.default.svc"],
#   "exp": 1710000000,                                     ← expiry (short-lived)
#   "iat": 1709996400,
#   "kubernetes.io": {
#     "namespace": "production",
#     "pod": {"name": "myapp-7d4f9b-xxx", "uid": "..."},  ← bound to specific pod
#     "serviceaccount": {"name": "myapp-sa", "uid": "..."}
#   }
# }

# --- Generate a temporary token for debugging (without running a pod) ---

# Short-lived token (default 1 hour)
kubectl create token myapp-sa -n production

# Longer-lived token for a CI/CD script
kubectl create token myapp-sa -n production --duration=8h

# --- Create a long-lived static token (legacy approach, avoid if possible) ---
# Only use this when an external system cannot use projected tokens
kubectl apply -f - <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: myapp-sa-static-token
  namespace: production
  annotations:
    kubernetes.io/service-account.name: myapp-sa   # ← link to the SA
type: kubernetes.io/service-account-token
EOF

# Read the static token
kubectl get secret myapp-sa-static-token -n production \
  -o jsonpath='{.data.token}' | base64 -d

# --- Audit all service account permissions in a namespace ---
kubectl get rolebindings,clusterrolebindings -n production -o wide | grep myapp-sa
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

⬅️ **Prev:** [Network Policies](../20_Network_Policies/Code_Example.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Monitoring and Logging](../22_Monitoring_and_Logging/Code_Example.md)
🏠 **[Home](../../README.md)**
