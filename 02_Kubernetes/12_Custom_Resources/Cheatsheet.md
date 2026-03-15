# Custom Resources Cheatsheet

## Core Concepts

| Term | Meaning |
|------|---------|
| CRD | CustomResourceDefinition — registers a new API type |
| CR | Custom Resource — an instance of a CRD |
| Operator | CRD + custom controller that automates app lifecycle |
| Controller | A reconcile loop watching resource state |
| Reconcile | Bring actual state in line with desired state |

---

## kubectl Commands

```bash
# --- Discovering CRDs ---

# List all CRDs in the cluster
kubectl get crds

# List CRDs with short info
kubectl get crds -o wide

# Describe a specific CRD (see schema, versions, scope)
kubectl describe crd <crd-name>

# Example: describe cert-manager's Certificate CRD
kubectl describe crd certificates.cert-manager.io

# --- Working with Custom Resources ---

# List instances of a custom resource (using plural name)
kubectl get <plural-name>
kubectl get certificates -n my-namespace
kubectl get kafkas -n kafka

# List custom resources across all namespaces
kubectl get certificates -A

# Describe a custom resource instance
kubectl describe certificate my-cert -n my-namespace

# Get CR in YAML format
kubectl get certificate my-cert -n my-namespace -o yaml

# Apply a custom resource
kubectl apply -f my-postgres-cluster.yaml

# Delete a custom resource
kubectl delete certificate my-cert -n my-namespace

# --- Managing CRDs ---

# Apply a CRD manifest
kubectl apply -f my-crd.yaml

# Delete a CRD (WARNING: deletes all instances too!)
kubectl delete crd widgets.example.com

# List all API resources (includes CRDs)
kubectl api-resources

# List API resources filtered to a specific group
kubectl api-resources --api-group=cert-manager.io

# See all available API versions
kubectl api-versions | grep cert-manager

# --- Operator Management ---

# Check if an operator is running
kubectl get pods -n cert-manager
kubectl get pods -n prometheus-operator

# Check operator logs
kubectl logs -n cert-manager -l app=cert-manager -f

# View events for a custom resource (operator actions)
kubectl describe certificate my-cert -n my-namespace
# Look for Events: section at the bottom

# Check operator RBAC (what the operator is allowed to do)
kubectl get clusterroles | grep cert-manager
kubectl describe clusterrole cert-manager-controller-certificates

# --- Kubebuilder / controller-runtime development ---

# Initialize a new operator project (requires kubebuilder CLI)
kubebuilder init --domain example.com --repo github.com/myorg/myoperator

# Create a new API/CRD
kubebuilder create api --group widgets --version v1 --kind Widget

# Generate CRD manifests from Go structs
make manifests

# Run the operator locally (against current kubeconfig context)
make run

# Install CRDs into the cluster
make install

# Deploy operator to cluster
make deploy IMG=my-registry/my-operator:tag

# --- Checking Status ---

# See if a CRD is established (healthy)
kubectl get crd certificates.cert-manager.io \
  -o jsonpath='{.status.conditions[?(@.type=="Established")].status}'

# Watch a custom resource for status changes
kubectl get certificate my-cert -n my-namespace -w
```

---

## CRD Scope Quick Reference

| Scope | kubectl usage | Notes |
|-------|---------------|-------|
| `Namespaced` | `kubectl get myresource -n <ns>` | Instances belong to a namespace |
| `Cluster` | `kubectl get myresource` | Instances are cluster-wide, like Nodes |

---

## Common Operators Reference

```bash
# cert-manager - TLS certificates
kubectl get certificates -A
kubectl get clusterissuers
kubectl get certificaterequests -A

# prometheus-operator - monitoring
kubectl get prometheus -A
kubectl get servicemonitors -A
kubectl get prometheusrules -A

# ArgoCD - GitOps
kubectl get applications -n argocd
kubectl get appprojects -n argocd

# Strimzi - Kafka
kubectl get kafka -A
kubectl get kafkatopics -A
kubectl get kafkausers -A
```

---

## Operator Maturity Levels

| Level | What the operator can do |
|-------|--------------------------|
| 1 - Basic Install | Install and configure the app |
| 2 - Seamless Upgrades | Manage version upgrades |
| 3 - Full Lifecycle | Backup, restore, failure recovery |
| 4 - Deep Insights | Metrics, alerts, dashboards |
| 5 - Auto Pilot | Auto-scaling, self-tuning |

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Theory.md](./Theory.md) |
| Interview Q&A | [Interview_QA.md](./Interview_QA.md) |
| Module Home | [12_Custom_Resources](../) |
