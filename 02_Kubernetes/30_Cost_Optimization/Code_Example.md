# Cost Optimization — Code Examples

All examples are production-quality with detailed comments explaining every decision.

---

## 1. VPA Recommendations: Right-Size Pod Resources

```yaml
# vpa-recommendation-mode.yaml
# VPA in "Off" mode: observes actual CPU and memory usage and generates
# recommendations without making any changes to running pods.
# Use this for a week or two before changing any resource requests.
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: payments-api-vpa
  namespace: production
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: payments-api                    # the Deployment to analyze
  updatePolicy:
    updateMode: "Off"                     # Off = never change pods, only recommend
    # Other modes:
    # "Auto"    — restart pods and apply recommendations automatically
    # "Initial" — apply recommendations only at pod creation, not after
```

```bash
# Install VPA (requires metrics-server to already be running)
kubectl apply -f https://github.com/kubernetes/autoscaler/releases/latest/download/vertical-pod-autoscaler.yaml

# Apply the VPA object
kubectl apply -f vpa-recommendation-mode.yaml

# After 24-48 hours of traffic, view the recommendations
kubectl describe vpa payments-api-vpa -n production

# Key section in the output:
# Recommendation:
#   Container Recommendations:
#     Container Name: api
#       Lower Bound:    cpu: 50m       memory: 128Mi    <- minimum safe setting
#       Target:         cpu: 200m      memory: 512Mi    <- recommended request
#       Upper Bound:    cpu: 500m      memory: 1Gi      <- include for spikes

# Compare VPA target against current requests
kubectl get pod -n production -l app=payments-api -o json | \
  jq '.items[0].spec.containers[0].resources'
# If requests are "cpu: 4, memory: 4Gi" but VPA target is "cpu: 200m, memory: 512Mi"
# you have 20x over-provisioned CPU — that's directly wasted node capacity
```

```bash
# --- Find over-provisioned pods across the cluster ---
# Compare actual usage (kubectl top) against configured requests

# Sort all pods by CPU usage descending
kubectl top pods -A --sort-by=cpu | head -20

# Sort by memory
kubectl top pods -A --sort-by=memory | head -20

# For a specific pod: compare actual vs requested
POD=payments-api-abc123
NS=production

echo "=== Actual usage ==="
kubectl top pod "$POD" -n "$NS"

echo "=== Configured requests ==="
kubectl get pod "$POD" -n "$NS" \
  -o jsonpath='{.spec.containers[*].resources.requests}' | jq .

# If actual CPU is 80m but request is 2000m, that pod is reserving 25x what it uses.
# A node with 16 CPUs could theoretically run 200 of these pods but K8s only sees
# capacity for 8 (because requests, not actual usage, drive scheduling).
```

---

## 2. Namespace ResourceQuota and LimitRange: Guardrails for Teams

```yaml
# team-backend-quota.yaml
# ResourceQuota caps the total resources a namespace can consume.
# This prevents one team from starving others on shared infrastructure.
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-backend-quota
  namespace: team-backend
spec:
  hard:
    requests.cpu: "20"                   # total CPU cores reserved by all pods in namespace
    requests.memory: 40Gi               # total memory reserved
    limits.cpu: "40"                    # total CPU limits (burst ceiling)
    limits.memory: 80Gi
    pods: "100"                         # max number of pods (prevents pod storm attacks)
    persistentvolumeclaims: "30"        # max PVC count
    requests.storage: 1Ti              # total storage across all PVCs
    services.loadbalancers: "3"         # max external load balancers (expensive on cloud)
    services.nodeports: "5"
---
# team-backend-limitrange.yaml
# LimitRange sets per-container defaults AND max values.
# Without this, a pod with no resource requests gets 0 requests (unlimited scheduling weight)
# and can starve other pods on the same node.
apiVersion: v1
kind: LimitRange
metadata:
  name: team-backend-limits
  namespace: team-backend
spec:
  limits:
  - type: Container
    # Applied when a container has no requests or limits specified
    defaultRequest:
      cpu: 100m                         # default CPU request if none specified
      memory: 128Mi                     # default memory request
    default:
      cpu: 200m                         # default CPU limit
      memory: 256Mi
    # Hard ceiling: a container cannot request/limit more than this
    max:
      cpu: "8"                          # no single container gets more than 8 cores
      memory: 16Gi
    # Minimum — prevents requesting 0 which bypasses quota accounting
    min:
      cpu: 10m
      memory: 32Mi
  - type: PersistentVolumeClaim
    max:
      storage: 100Gi                    # no single PVC can be larger than 100GB
    min:
      storage: 1Gi
```

```bash
# Apply quotas and limits to the namespace
kubectl apply -f team-backend-quota.yaml
kubectl apply -f team-backend-limitrange.yaml

# Check current quota usage for a namespace
kubectl describe resourcequota team-backend-quota -n team-backend
# Shows Used vs Hard for each resource — useful for capacity planning

# Check limit range in effect
kubectl describe limitrange team-backend-limits -n team-backend
```

---

## 3. Spot Instances: Batch Workloads on Discounted Capacity

```yaml
# batch-job-spot.yaml
# This Job runs on spot instances (60-90% cheaper than on-demand).
# It tolerates the spot taint (permission to use spot nodes),
# and uses node affinity to prefer spot but fall back to on-demand.
# The termination grace period gives the job time to checkpoint before eviction.
apiVersion: batch/v1
kind: Job
metadata:
  name: nightly-etl-job
  namespace: data-processing
spec:
  completions: 10                        # run 10 tasks total
  parallelism: 5                         # run 5 at a time
  backoffLimit: 3                        # retry failed pods up to 3 times
  template:
    spec:
      priorityClassName: batch-low-priority   # allow preemption by critical workloads

      tolerations:
      # Spot nodes are tainted to repel regular workloads — batch jobs tolerate it
      - key: "karpenter.sh/interruption"   # Karpenter's spot interruption taint
        operator: "Exists"
        effect: "NoSchedule"
      - key: "node.kubernetes.io/capacity-type"
        operator: "Equal"
        value: "spot"
        effect: "NoSchedule"

      affinity:
        nodeAffinity:
          # PREFER spot (cheaper), fall back to on-demand if no spot is available
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            preference:
              matchExpressions:
              - key: karpenter.sh/capacity-type
                operator: In
                values: [spot]

      # Give the job 120 seconds to save a checkpoint when spot is reclaimed
      terminationGracePeriodSeconds: 120

      containers:
      - name: etl-worker
        image: myregistry/etl-worker:2.3.0
        resources:
          requests:
            cpu: "2"
            memory: 4Gi
          limits:
            cpu: "4"
            memory: 8Gi
        # Implement SIGTERM handler in your code to save a checkpoint
        # when the spot instance receives a 2-minute warning
        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "/app/save-checkpoint.sh"]
      restartPolicy: OnFailure
```

```bash
# Label on-demand vs spot nodes for visibility
kubectl get nodes -L karpenter.sh/capacity-type,node.kubernetes.io/instance-type

# Watch the cost difference: spot nodes show "spot" in the capacity-type label
# Check actual spot savings in your cloud billing console or Kubecost
```

---

## 4. Karpenter NodePool: Intelligent Autoprovisioning

```yaml
# karpenter-nodepool.yaml
# Karpenter selects the optimal (cheapest) instance type for each pending pod
# and provisions it directly — no pre-configured node groups needed.
# It also consolidates nodes when workloads could fit on fewer machines.
apiVersion: karpenter.sh/v1beta1
kind: NodePool
metadata:
  name: default
spec:
  template:
    metadata:
      labels:
        managed-by: karpenter            # label for easy identification
    spec:
      nodeClassRef:
        apiVersion: karpenter.k8s.aws/v1beta1
        kind: EC2NodeClass
        name: default

      requirements:
      # Allow both spot and on-demand — Karpenter picks based on availability/price
      - key: karpenter.sh/capacity-type
        operator: In
        values: ["spot", "on-demand"]
      # Only use compute, memory, and general-purpose instance families
      - key: karpenter.k8s.aws/instance-category
        operator: In
        values: ["c", "m", "r"]
      # Exclude tiny instances that can't fit typical workloads
      - key: karpenter.k8s.aws/instance-size
        operator: NotIn
        values: ["nano", "micro", "small"]
      # Only amd64 (x86) for compatibility
      - key: kubernetes.io/arch
        operator: In
        values: ["amd64"]

  # Hard cap on total cluster CPU to prevent runaway scaling
  limits:
    cpu: 500                             # max 500 vCPUs across all Karpenter nodes
    memory: 2000Gi

  # Consolidation: Karpenter moves pods to defragment and delete underused nodes
  disruption:
    consolidationPolicy: WhenUnderutilized   # consolidate when nodes are underused
    consolidateAfter: 30s                     # wait 30s of underutilization before acting
    expireAfter: 720h                         # replace nodes older than 30 days (OS patch rotation)
---
# karpenter-ec2nodeclass.yaml
# Defines the AWS-specific settings for nodes Karpenter provisions
apiVersion: karpenter.k8s.aws/v1beta1
kind: EC2NodeClass
metadata:
  name: default
spec:
  amiFamily: Bottlerocket                # security-hardened, minimal OS (faster startup)
  role: KarpenterNodeRole                # IAM role with ECR pull + SSM permissions
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster # auto-discover subnets tagged for this cluster
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  blockDeviceMappings:
  - deviceName: /dev/xvda
    ebs:
      volumeSize: 40Gi
      volumeType: gp3                    # gp3 is cheaper and faster than gp2
      encrypted: true
```

```bash
# Watch Karpenter in action
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -f | grep -E "provisioned|terminated"

# See currently running Karpenter-managed nodes
kubectl get nodes -L karpenter.sh/capacity-type,karpenter.sh/nodepool \
  --selector karpenter.sh/nodepool=default

# Force consolidation check (normally automatic)
kubectl -n karpenter patch configmap karpenter-global-settings \
  --type merge -p '{"data":{"featureGates.drift":"true"}}'
```

---

## 5. Cleanup: Find and Delete Unused Resources

```bash
# --- Find released PVCs (volume exists but no pod claims it) ---
# A "Released" PVC still incurs storage costs. These accumulate silently.
kubectl get pvc -A -o json | jq -r '
  .items[]
  | select(.status.phase == "Released" or .status.phase == "Lost")
  | "\(.metadata.namespace)/\(.metadata.name) — \(.spec.resources.requests.storage)"
'

# Review and delete stale PVCs
kubectl delete pvc stale-data-pvc -n team-a

# --- Find Deployments scaled to 0 that still exist ---
# These waste nothing in resources, but do generate etcd churn and confusion.
kubectl get deployments -A \
  --field-selector=status.replicas=0 \
  -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,CREATED:.metadata.creationTimestamp \
  | sort -k3

# --- Clean up completed Job pods ---
# Completed pods take up no CPU or memory but do count against the pod limit quota.
kubectl delete pods -A --field-selector=status.phase==Succeeded
kubectl delete pods -A --field-selector=status.phase==Failed

# --- Find namespaces with no running pods (candidate for deletion) ---
# Loop through all non-system namespaces and check for running pods
for ns in $(kubectl get ns --no-headers \
  | grep -vE "kube-|argocd|velero|monitoring|default" \
  | awk '{print $1}'); do
  pod_count=$(kubectl get pods -n "$ns" --no-headers 2>/dev/null | wc -l)
  if [ "$pod_count" -eq 0 ]; then
    echo "Empty namespace: $ns"
  fi
done

# --- Identify images pulling from expensive registries vs cached ones ---
# Large image pulls = slower autoscaling and higher bandwidth costs
kubectl get pods -A -o json | jq -r '
  .items[].spec.containers[].image
' | sort | uniq -c | sort -rn | head -20
# Look for large images pulled from DockerHub (rate limited + slow)
# vs images already in ECR/GCR (fast, free egress within same region)
```

```yaml
# cost-labels-deployment.yaml
# Apply cost allocation labels to every workload.
# Kubecost and OpenCost aggregate by these labels to produce per-team cost reports.
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payments-api
  namespace: production
  labels:
    team: payments-backend              # which engineering team owns this
    product: checkout                   # which product / business unit
    environment: production             # separate prod vs dev costs clearly
    cost-center: "engineering-platform" # maps to a finance cost center code
spec:
  selector:
    matchLabels:
      app: payments-api
  template:
    metadata:
      labels:
        app: payments-api
        team: payments-backend          # labels must be on pods too — Kubecost reads pod labels
        product: checkout
        environment: production
        cost-center: "engineering-platform"
    spec:
      containers:
      - name: api
        image: myregistry/payments-api:4.1.0
        resources:
          requests:
            cpu: 200m                   # right-sized from VPA recommendation
            memory: 512Mi
          limits:
            cpu: 500m
            memory: 1Gi
```

```bash
# Install Kubecost for cost visibility
helm repo add kubecost https://kubecost.github.io/cost-analyzer/
helm install kubecost kubecost/cost-analyzer \
  --namespace kubecost \
  --create-namespace

# Access the Kubecost dashboard
kubectl port-forward deployment/kubecost-cost-analyzer 9090 -n kubecost
# Open http://localhost:9090 — shows per-namespace and per-team cost breakdowns

# Or use OpenCost (CNCF open-source, no dashboard):
helm install opencost opencost/opencost \
  --namespace opencost \
  --create-namespace

# Query OpenCost API for cost by namespace
kubectl port-forward -n opencost service/opencost 9003:9003 &
curl "http://localhost:9003/allocation?window=7d&aggregate=namespace&step=1d" | jq .
```

---

## 📂 Navigation

**In this folder:**
| File | |
|---|---|
| [Theory.md](./Theory.md) | Full explanation |
| [Cheatsheet.md](./Cheatsheet.md) | Quick reference |
| [Interview_QA.md](./Interview_QA.md) | Interview prep |
| **Code_Example.md** | you are here |

⬅️ **Prev:** [Backup and DR](../29_Backup_and_DR/Code_Example.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Gateway API](../31_Gateway_API/Code_Example.md)
🏠 **[Home](../../README.md)**
