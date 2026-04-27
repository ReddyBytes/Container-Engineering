# Module 08 — Namespaces Cheatsheet

## Basic Namespace Operations

```bash
# List all namespaces
kubectl get namespaces
kubectl get ns              # short form

# Create a namespace
kubectl create namespace my-namespace
kubectl create ns my-namespace

# Create from YAML
kubectl apply -f namespace.yaml

# Delete a namespace (deletes ALL resources inside it — irreversible!)
kubectl delete namespace my-namespace

# Describe a namespace (shows quotas and limits)
kubectl describe namespace my-namespace
```

## Working Within Namespaces

```bash
# List resources in a specific namespace
kubectl get pods -n my-namespace
kubectl get deployments -n my-namespace
kubectl get services -n my-namespace
kubectl get all -n my-namespace         # shows most resource types

# List resources across ALL namespaces
kubectl get pods -A
kubectl get pods --all-namespaces

# Create a resource in a specific namespace
kubectl apply -f my-deployment.yaml -n my-namespace
# (or set namespace in the YAML under metadata.namespace)

# Set default namespace for current context (avoids -n on every command)
kubectl config set-context --current --namespace=my-namespace

# Verify the default namespace
kubectl config get-contexts
# Look at the NAMESPACE column for the * (current) context

# Reset to default namespace
kubectl config set-context --current --namespace=default
```

## Cross-Namespace DNS

```bash
# Call a service in another namespace:
# Format: <service>.<namespace>.svc.cluster.local

# From inside a pod, test cross-namespace DNS
kubectl run dns-test \
  --image=busybox \
  --rm -it \
  --restart=Never \
  -- nslookup my-service.other-namespace.svc.cluster.local

# Curl a service in another namespace
kubectl run test \
  --image=curlimages/curl \
  --rm -it \
  --restart=Never \
  -- curl http://backend.production.svc.cluster.local:80/health
```

## Resource Quotas

```bash
# Create a ResourceQuota
kubectl apply -f resource-quota.yaml

# View current quota usage in a namespace
kubectl describe resourcequota -n my-namespace
# Shows: resource, used, hard (limit)

# Get quota as YAML
kubectl get resourcequota -n my-namespace -o yaml

# Check what happens when you exceed the quota
# Apply a deployment with more replicas than allowed → will see quota exceeded error
kubectl describe deployment my-app -n my-namespace
# Events: Error creating: pods "my-app-xxx" is forbidden: exceeded quota
```

## LimitRange

```bash
# Create a LimitRange
kubectl apply -f limitrange.yaml

# View limit ranges in a namespace
kubectl get limitrange -n my-namespace
kubectl describe limitrange -n my-namespace

# Verify a pod gets default limits applied (even if not specified in YAML)
kubectl get pod my-pod -n my-namespace -o yaml | grep -A 10 resources
```

## Namespace YAML Templates

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: team-backend
  labels:
    team: backend
    environment: production
---
# resource-quota.yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: backend-quota
  namespace: team-backend
spec:
  hard:
    pods: "20"
    requests.cpu: "4"
    requests.memory: 8Gi
    limits.cpu: "8"
    limits.memory: 16Gi
---
# limitrange.yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: backend-defaults
  namespace: team-backend
spec:
  limits:
  - type: Container
    default:
      cpu: "200m"
      memory: "256Mi"
    defaultRequest:
      cpu: "100m"
      memory: "128Mi"
```

## Namespace Selector for Network Policies

```bash
# Label a namespace (needed for network policies)
kubectl label namespace my-namespace team=backend

# Add multiple labels
kubectl label namespace my-namespace team=backend environment=prod

# Remove a label
kubectl label namespace my-namespace environment-

# View namespace labels
kubectl get namespace my-namespace --show-labels
```

## Debugging Namespace Issues

```bash
# Namespace stuck in Terminating state?
kubectl get namespace stuck-ns

# Check what resources are blocking deletion
kubectl api-resources --verbs=list --namespaced -o name | xargs -I{} \
  kubectl get {} -n stuck-ns 2>/dev/null | grep -v "No resources"

# Force remove finalizers (last resort — use carefully)
kubectl get namespace stuck-ns -o json \
  | python3 -c "import sys,json; d=json.load(sys.stdin); d['spec']['finalizers']=[]; print(json.dumps(d))" \
  | kubectl replace --raw /api/v1/namespaces/stuck-ns/finalize -f -
```

---

## 📂 Navigation

| File | Description |
|------|-------------|
| [Theory.md](./Theory.md) | Namespaces explained |
| [Cheatsheet.md](./Cheatsheet.md) | You are here — quick reference |
| [Interview_QA.md](./Interview_QA.md) | Interview questions and answers |

---

⬅️ **Prev:** [ConfigMaps and Secrets](../07_ConfigMaps_and_Secrets/Cheatsheet.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Ingress](../09_Ingress/Theory.md)
