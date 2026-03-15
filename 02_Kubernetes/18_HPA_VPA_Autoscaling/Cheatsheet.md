# HPA, VPA, and Autoscaling Cheatsheet

## Three Autoscaling Types

| Type | Scales | Based on | Requires |
|------|--------|----------|---------|
| HPA | Pod count (out/in) | CPU, memory, custom metrics | metrics-server |
| VPA | Pod size (up/down) | Actual resource usage | VPA controller |
| Cluster Autoscaler | Node count | Pending pods, idle nodes | Cloud node groups |
| KEDA | Pod count to zero+ | Events (queues, streams) | KEDA controller |

---

## kubectl Commands

```bash
# --- HPA ---

# List all HPAs
kubectl get hpa -n <namespace>
kubectl get hpa -A

# Describe an HPA (see current metrics, targets, events)
kubectl describe hpa <name> -n <namespace>

# Watch HPA scale in real time
kubectl get hpa <name> -n <namespace> -w

# Create an HPA imperatively (CPU target)
kubectl autoscale deployment <name> \
  --cpu-percent=70 \
  --min=2 \
  --max=20 \
  -n <namespace>

# Check current CPU utilization driving HPA
kubectl get hpa <name> -n <namespace> \
  -o jsonpath='{.status.currentMetrics}'

# Get HPA events (scale up/down events)
kubectl get events -n <namespace> | grep HorizontalPodAutoscaler

# Check metrics-server is working
kubectl top nodes
kubectl top pods -n <namespace>

# Get pod resource usage for HPA analysis
kubectl top pods -n <namespace> --sort-by=cpu

# --- VPA ---

# List all VPAs
kubectl get vpa -n <namespace>
kubectl get vpa -A

# Describe VPA (see recommendations)
kubectl describe vpa <name> -n <namespace>

# Get VPA recommendations in YAML
kubectl get vpa <name> -n <namespace> -o yaml

# Extract VPA recommendation for a container
kubectl get vpa <name> -n <namespace> \
  -o jsonpath='{.status.recommendation.containerRecommendations}'

# Check VPA controller logs
kubectl logs -n kube-system -l app=vpa-recommender -f

# --- Cluster Autoscaler ---

# Check Cluster Autoscaler logs (usually in kube-system)
kubectl logs -n kube-system -l app=cluster-autoscaler -f

# Check why a pod is Pending (Cluster Autoscaler trigger)
kubectl describe pod <pending-pod> -n <namespace>
# Look for: 0/3 nodes are available: insufficient cpu

# Annotate a node to prevent Cluster Autoscaler from removing it
kubectl annotate node <node-name> \
  cluster-autoscaler.kubernetes.io/scale-down-disabled=true

# --- KEDA ---

# List KEDA ScaledObjects
kubectl get scaledobjects -n <namespace>
kubectl get so -n <namespace>          # short form

# Describe a ScaledObject
kubectl describe scaledobject <name> -n <namespace>

# List KEDA TriggerAuthentication
kubectl get triggerauthentication -n <namespace>

# Check KEDA operator logs
kubectl logs -n keda -l app=keda-operator -f

# --- General Autoscaling Debugging ---

# Check if metrics-server is installed and healthy
kubectl get deployment metrics-server -n kube-system

# Test metrics-server is returning data
kubectl top nodes
kubectl top pods --all-namespaces

# See all events related to scaling
kubectl get events -A | grep -i "scale\|hpa\|autoscal" | \
  sort --key=1 --field-separator=' '

# Check resource utilization of all pods in a namespace
kubectl top pods -n <namespace> --containers

# View node capacity and allocatable resources
kubectl describe nodes | grep -A 5 "Allocatable:"
```

---

## HPA YAML Reference

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 50
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70   # 70% CPU target

    - type: Resource
      resource:
        name: memory
        target:
          type: AverageValue
          averageValue: 512Mi      # 512Mi per pod

  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300  # 5-minute cool-down
    scaleUp:
      stabilizationWindowSeconds: 60
```

## VPA YAML Reference

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: my-vpa
  namespace: production
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  updatePolicy:
    updateMode: "Off"    # Off | Initial | Auto | Recreate
  resourcePolicy:
    containerPolicies:
      - containerName: my-container
        minAllowed:
          cpu: 50m
          memory: 64Mi
        maxAllowed:
          cpu: 4
          memory: 8Gi
```

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Theory.md](./Theory.md) |
| Interview Q&A | [Interview_QA.md](./Interview_QA.md) |
| Module Home | [18_HPA_VPA_Autoscaling](../) |
