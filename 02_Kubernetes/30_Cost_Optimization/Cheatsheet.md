# Module 30 — Cost Optimization Cheatsheet

## Cost Drivers at a Glance

| Driver | Impact | Fix |
|---|---|---|
| Over-provisioned CPU/memory | Wasted node capacity | VPA recommendations + right-sizing |
| Idle pods/namespaces | Paying for nothing | Scale to zero, delete stale environments |
| Unused PVCs | Storage bill | Regular cleanup, lifecycle policies |
| Over-sized nodes | Under-utilization | Karpenter, right-size node groups |
| No spot instances | Missed 60-90% discount | Spot for batch/dev/fault-tolerant workloads |
| No resource quotas | Runaway spending | Namespace quotas per team |
| Large images | Slow pulls, more disk | Multi-stage builds, distroless images |

---

## kubectl top: Usage vs Requests

```bash
# Pod CPU and memory usage
kubectl top pods -n production
kubectl top pods -A --sort-by=cpu
kubectl top pods -A --sort-by=memory

# Node usage
kubectl top nodes

# Install kube-capacity for requests vs limits vs usage
kubectl krew install resource-capacity
kubectl resource-capacity --pods --util
kubectl resource-capacity -n production --pods
```

---

## VPA Recommendations (No changes, just advise)

```yaml
# Recommendation-only VPA
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: myapp-vpa
  namespace: production
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: myapp
  updatePolicy:
    updateMode: "Off"    # Off = no changes, just recommendations
  resourcePolicy:
    containerPolicies:
    - containerName: "*"
      minAllowed:
        cpu: 10m
        memory: 50Mi
      maxAllowed:
        cpu: "4"
        memory: 4Gi
```

```bash
# View VPA recommendations
kubectl describe vpa myapp-vpa -n production
# Look for: Target, LowerBound, UpperBound recommendations
```

---

## Kubecost / OpenCost

```bash
# Install Kubecost
helm repo add kubecost https://kubecost.github.io/cost-analyzer/
helm install kubecost kubecost/cost-analyzer \
  -n kubecost --create-namespace

# Access dashboard
kubectl port-forward deployment/kubecost-cost-analyzer 9090 -n kubecost

# Install OpenCost (CNCF open-source)
helm repo add opencost https://opencost.github.io/opencost-helm-chart
helm install opencost opencost/opencost -n opencost --create-namespace
```

---

## Karpenter

```bash
# Karpenter NodePool with spot + on-demand mix
```

```yaml
apiVersion: karpenter.sh/v1beta1
kind: NodePool
metadata:
  name: default
spec:
  template:
    metadata:
      labels:
        managed-by: karpenter
    spec:
      nodeClassRef:
        name: default
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values: ["spot", "on-demand"]
      - key: karpenter.k8s.aws/instance-category
        operator: In
        values: ["c", "m", "r"]
      - key: karpenter.k8s.aws/instance-cpu
        operator: In
        values: ["2", "4", "8", "16"]
  limits:
    cpu: 500
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenUnderutilized
    consolidateAfter: 30s
    budgets:
    - nodes: "10%"    # max % of nodes disrupted at once
```

---

## Namespace Resource Quotas

```yaml
# ResourceQuota — per namespace limits
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-quota
  namespace: team-backend
spec:
  hard:
    requests.cpu: "20"
    requests.memory: 40Gi
    limits.cpu: "40"
    limits.memory: 80Gi
    pods: "100"
    persistentvolumeclaims: "30"
    requests.storage: 500Gi
    count/services: "20"

---
# LimitRange — default per-container limits
apiVersion: v1
kind: LimitRange
metadata:
  name: default-limits
  namespace: team-backend
spec:
  limits:
  - type: Container
    default:
      cpu: 200m
      memory: 256Mi
    defaultRequest:
      cpu: 50m
      memory: 64Mi
    max:
      cpu: "4"
      memory: 4Gi
```

---

## Spot Instance Pattern

```yaml
spec:
  tolerations:
  - key: node.kubernetes.io/capacity-type
    operator: Equal
    value: spot
    effect: NoSchedule

  affinity:
    nodeAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 80
        preference:
          matchExpressions:
          - key: node.kubernetes.io/capacity-type
            operator: In
            values: [spot]

  terminationGracePeriodSeconds: 120  # handle spot termination
  priorityClassName: low-priority     # allow preemption by important work
```

---

## Cleanup Commands

```bash
# Unused PVCs (Released state)
kubectl get pvc -A | grep Released
kubectl delete pvc <name> -n <namespace>

# Completed/failed pods
kubectl delete pods -A --field-selector=status.phase==Succeeded
kubectl delete pods -A --field-selector=status.phase==Failed

# Old ReplicaSets with 0 replicas
kubectl get rs -A | awk '$3 == 0 {print $1, $2}' | \
  while read ns name; do kubectl delete rs $name -n $ns; done

# Dev namespaces not used recently (use Kubecost to identify)
kubectl delete namespace stale-feature-branch-env

# Find large PVCs
kubectl get pvc -A -o json | \
  jq '.items[] | {name:.metadata.name, ns:.metadata.namespace,
  size:.spec.resources.requests.storage}' | sort
```

---

## Cost Labels

```yaml
metadata:
  labels:
    team: platform
    product: api-gateway
    environment: production
    cost-center: engineering
    managed-by: terraform
```

---

## Image Optimization

```bash
# Check image sizes
docker images --format "{{.Size}}\t{{.Repository}}:{{.Tag}}" | sort -rh | head -20

# Scan for unnecessary packages
docker run --rm wagoodman/dive myapp:latest

# Compare base images
# python:3.11        → 1.0 GB
# python:3.11-slim   → 200 MB
# python:3.11-alpine → 60 MB
# distroless/python3 → 55 MB
```

---

## Cost Optimization Quick Wins

```
Week 1 (measure):
[ ] Install Kubecost or OpenCost
[ ] Run kubectl top pods -A --sort-by=cpu
[ ] Check for pods with requests >> actual usage
[ ] List unused PVCs: kubectl get pvc -A | grep Released

Week 2 (right-size):
[ ] Deploy VPA in Off mode for top 10 most expensive deployments
[ ] Apply VPA recommendations (conservative — use Target, not LowerBound)
[ ] Delete unused PVCs
[ ] Scale down dev environments outside business hours

Month 1 (automate):
[ ] Enable Karpenter or tune Cluster Autoscaler
[ ] Add spot nodes to non-critical node groups
[ ] Apply ResourceQuota to all team namespaces
[ ] Set up cost alerts (alert if namespace cost > threshold)
```

---

## 📂 Navigation

| | Link |
|---|---|
| ⬅️ Prev | [Backup and DR](../29_Backup_and_DR/Interview_QA.md) |
| Theory | [Cost Optimization Theory](./Theory.md) |
| Interview Q&A | [Cost Optimization Interview Q&A](./Interview_QA.md) |
| ➡️ Next | [Gateway API](../31_Gateway_API/Theory.md) |
