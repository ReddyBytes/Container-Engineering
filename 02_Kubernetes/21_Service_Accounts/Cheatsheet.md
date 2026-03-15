# Module 21 — Service Accounts Cheatsheet

## Core Concepts at a Glance

| Concept | Description |
|---|---|
| User Account | For humans (kubectl users) — not stored in K8s |
| Service Account | For pods/processes — stored as K8s objects |
| Default SA | Auto-created per namespace; auto-mounted in every pod |
| Projected token | Short-lived JWT (K8s 1.21+), rotated by kubelet |
| IRSA | AWS EKS: link SA to IAM Role for cloud API access |
| Workload Identity | GKE: link SA to GCP Service Account |

---

## Essential Commands

```bash
# List service accounts in a namespace
kubectl get serviceaccounts -n <namespace>
kubectl get sa -n <namespace>                    # short form

# Create a service account
kubectl create serviceaccount <name> -n <namespace>

# Describe a service account
kubectl describe sa <name> -n <namespace>

# Generate a token for a service account (K8s 1.24+)
kubectl create token <sa-name> -n <namespace>
kubectl create token <sa-name> --duration=24h -n <namespace>

# Check permissions of a service account
kubectl auth can-i <verb> <resource> \
  --as=system:serviceaccount:<namespace>:<sa-name> \
  -n <namespace>

# Example: can myapp-sa list pods in production?
kubectl auth can-i list pods \
  --as=system:serviceaccount:production:myapp-sa \
  -n production

# Delete a service account
kubectl delete serviceaccount <name> -n <namespace>
```

---

## Service Account YAML

```yaml
# Basic service account
apiVersion: v1
kind: ServiceAccount
metadata:
  name: myapp-sa
  namespace: production

---
# Service account with auto-mount disabled
apiVersion: v1
kind: ServiceAccount
metadata:
  name: myapp-sa
  namespace: production
automountServiceAccountToken: false

---
# Service account with IRSA annotation (AWS EKS)
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-reader-sa
  namespace: production
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/MyRole

---
# Service account with Workload Identity (GKE)
apiVersion: v1
kind: ServiceAccount
metadata:
  name: gcs-reader-sa
  namespace: production
  annotations:
    iam.gke.io/gcp-service-account: mysa@my-project.iam.gserviceaccount.com
```

---

## Using a Service Account in a Pod

```yaml
spec:
  serviceAccountName: myapp-sa          # use named SA
  automountServiceAccountToken: false   # disable if not needed
  containers:
  - name: app
    image: myapp:1.0
```

---

## RBAC Binding Pattern

```yaml
# 1. Role — what can be done
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: myapp-role
  namespace: production
rules:
- apiGroups: [""]
  resources: ["configmaps", "pods"]
  verbs: ["get", "list", "watch"]

---
# 2. RoleBinding — who can do it
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: myapp-rolebinding
  namespace: production
subjects:
- kind: ServiceAccount
  name: myapp-sa
  namespace: production
roleRef:
  kind: Role
  name: myapp-role
  apiGroup: rbac.authorization.k8s.io
```

---

## Token Locations Inside a Pod

```
/var/run/secrets/kubernetes.io/serviceaccount/
├── token       ← JWT token (rotated by kubelet)
├── ca.crt      ← cluster CA certificate
└── namespace   ← current namespace
```

---

## Long-Lived Token Secret (legacy / explicit)

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: myapp-token
  annotations:
    kubernetes.io/service-account.name: myapp-sa
type: kubernetes.io/service-account-token
```

---

## Best Practice Checklist

- [ ] One Service Account per application, not sharing the `default`
- [ ] `automountServiceAccountToken: false` on pods that don't call the API
- [ ] Use projected tokens (K8s 1.21+) not long-lived secret-based tokens
- [ ] Bind only the minimum required verbs/resources via Role/RoleBinding
- [ ] Use IRSA or Workload Identity for cloud provider API access
- [ ] Audit SA permissions with `kubectl auth can-i --list`
- [ ] Do not give `cluster-admin` or broad ClusterRoles to application SAs

---

## Common Identity String Format

```
system:serviceaccount:<namespace>:<serviceaccount-name>
```

Example: `system:serviceaccount:production:myapp-sa`

This is what RBAC uses as the subject identity.

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Service Accounts Theory](./Theory.md) |
| Interview Q&A | [Service Accounts Interview Q&A](./Interview_QA.md) |
| Next Module | [22 — Monitoring and Logging](../22_Monitoring_and_Logging/Theory.md) |
