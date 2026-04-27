# Advanced Scheduling — Code Examples

All examples are production-quality with detailed comments explaining every decision.

---

## 1. NodeAffinity: Required and Preferred Node Placement

```yaml
# gpu-workload-deployment.yaml
# Deploy an ML inference service that must run on GPU nodes,
# with a soft preference for a specific availability zone.
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-inference
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ml-inference
  template:
    metadata:
      labels:
        app: ml-inference
    spec:
      affinity:
        nodeAffinity:
          # HARD rule: pod will not schedule on nodes without this label
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: accelerator          # node label key
                operator: In
                values:
                - nvidia-t4               # only T4 GPU nodes
                - nvidia-a100
              - key: node.kubernetes.io/capacity-type
                operator: NotIn
                values:
                - spot                    # never schedule ML inference on spot (2-min termination)

          # SOFT rule: prefer us-east-1a, but fall back to other AZs if needed
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 80                    # 0-100 — higher weight = stronger preference
            preference:
              matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - us-east-1a
          - weight: 20
            preference:
              matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - us-east-1b              # second choice

      containers:
      - name: inference-server
        image: myregistry/ml-inference:1.4.2
        resources:
          requests:
            cpu: "4"
            memory: 16Gi
            nvidia.com/gpu: "1"           # request 1 GPU — only nodes with GPU device plugin satisfy this
          limits:
            nvidia.com/gpu: "1"
```

```bash
# Label GPU nodes (typically done at node group creation, shown here manually)
kubectl label node gpu-node-01 accelerator=nvidia-t4
kubectl label node gpu-node-02 accelerator=nvidia-a100

# Verify pod placement — check which nodes were selected
kubectl get pods -o wide -n production -l app=ml-inference

# Debug a Pending pod — shows which predicates failed
kubectl describe pod ml-inference-xxx -n production | grep -A 20 "Events:"
```

---

## 2. Taints, Tolerations, and Dedicated Node Groups

```bash
# --- Step 1: Taint dedicated nodes ---

# GPU nodes: only GPU workloads allowed
kubectl taint node gpu-node-01 dedicated=gpu:NoSchedule
kubectl taint node gpu-node-02 dedicated=gpu:NoSchedule

# Spot nodes: prefer not to schedule here, but allow it
kubectl taint node spot-node-01 spot=true:PreferNoSchedule
kubectl taint node spot-node-02 spot=true:PreferNoSchedule

# Draining for maintenance: evict existing pods too
kubectl taint node worker-05 maintenance=true:NoExecute
# After maintenance, remove the taint:
kubectl taint node worker-05 maintenance=true:NoExecute-    # the trailing - removes the taint
```

```yaml
# dedicated-gpu-pod.yaml
# This pod can run on GPU nodes (toleration) AND is required to run there (nodeAffinity).
# Toleration alone is necessary but not sufficient — without the affinity, the pod
# could still land on a CPU node that happens to have no taint.
apiVersion: v1
kind: Pod
metadata:
  name: gpu-job
spec:
  tolerations:
  # This badge allows the pod to enter the GPU-dedicated node
  - key: dedicated
    operator: Equal
    value: gpu
    effect: NoSchedule

  # Tolerate spot instances with a time limit — evict after 90s if maintenance starts
  - key: maintenance
    operator: Exists
    effect: NoExecute
    tolerationSeconds: 90               # stay on node for 90s after taint is applied, then evict

  affinity:
    nodeAffinity:
      # Affinity ensures this pod GOES to GPU nodes, not just that it CAN
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: dedicated
            operator: In
            values: [gpu]

  containers:
  - name: gpu-job
    image: nvidia/cuda:12.0-runtime-ubuntu22.04
    resources:
      limits:
        nvidia.com/gpu: "1"
```

---

## 3. PodAntiAffinity: High-Availability Spread

```yaml
# ha-web-deployment.yaml
# 4 replicas of a web service spread across nodes (hard) and zones (soft).
# Hard anti-affinity on hostname guarantees no two replicas share a node.
# Soft spread across zones means a single AZ failure loses at most 1 replica.
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-frontend
  namespace: production
spec:
  replicas: 4
  selector:
    matchLabels:
      app: web-frontend
  template:
    metadata:
      labels:
        app: web-frontend
    spec:
      affinity:
        podAntiAffinity:
          # HARD: no two web-frontend pods on the same node — if only 3 nodes exist,
          # only 3 replicas will schedule (the 4th stays Pending until a node is added)
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: web-frontend         # match our own pods
            topologyKey: kubernetes.io/hostname    # "same node" scope

          # SOFT: try to spread across zones, but don't block scheduling if impossible
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchLabels:
                  app: web-frontend
              topologyKey: topology.kubernetes.io/zone  # "same AZ" scope

        # Co-locate with the Redis cache for lower latency (soft — don't fail if no cache nearby)
        podAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 50
            podAffinityTerm:
              labelSelector:
                matchLabels:
                  app: redis-cache
              topologyKey: kubernetes.io/hostname  # prefer same node as Redis

      containers:
      - name: web
        image: myregistry/web-frontend:2.1.0
        resources:
          requests:
            cpu: 200m
            memory: 256Mi
```

---

## 4. TopologySpreadConstraints: Even Distribution Across Zones

```yaml
# evenly-spread-deployment.yaml
# TopologySpreadConstraints gives precise control over pod distribution.
# This is better than anti-affinity when you want "balanced spread"
# rather than "never co-locate."
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-service
  namespace: production
spec:
  replicas: 9                             # 3 pods per zone with 3 zones = perfect spread
  selector:
    matchLabels:
      app: api-service
  template:
    metadata:
      labels:
        app: api-service
    spec:
      topologySpreadConstraints:

      # Constraint 1: spread evenly across availability zones (hard)
      - maxSkew: 1                        # max difference in pod count between any two zones
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule  # hard — block scheduling if constraint would be violated
        labelSelector:
          matchLabels:
            app: api-service
        # With 9 pods in 3 zones: 3-3-3 is fine (skew=0), but 4-4-1 would be rejected (skew=3)
        minDomains: 3                     # require at least 3 zones to exist before scheduling

      # Constraint 2: spread across nodes within each zone (soft)
      - maxSkew: 2                        # allow some imbalance within a zone
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: ScheduleAnyway # soft — schedule anyway if constraint can't be met
        labelSelector:
          matchLabels:
            app: api-service

      containers:
      - name: api
        image: myregistry/api-service:3.0.1
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
```

```bash
# Verify the spread — count pods per node and per zone
kubectl get pods -n production -l app=api-service -o wide

# View how pods are distributed across zones using a one-liner
kubectl get pods -n production -l app=api-service -o json | \
  jq -r '.items[] | "\(.spec.nodeName) \(.metadata.name)"' | sort
```

---

## 5. PriorityClasses: Critical Workloads Preempt Batch Jobs

```yaml
# priority-classes.yaml
# Define a hierarchy of workload priorities.
# When the cluster is under resource pressure, the scheduler evicts lower-priority
# pods to make room for higher-priority ones.
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: critical-production               # for stateless production services
value: 1000000                            # higher = more important
globalDefault: false                      # don't apply to all pods without a class
description: "Critical production services — will preempt batch and dev workloads"
preemptionPolicy: PreemptLowerPriority    # default: allowed to evict lower-priority pods
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: standard-production
value: 100000
globalDefault: true                       # applied to pods without an explicit priorityClassName
description: "Normal production workloads"
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: batch-low-priority
value: 1000                               # will be evicted to make room for critical/standard
globalDefault: false
description: "Batch jobs and CI runners — can be safely interrupted"
preemptionPolicy: Never                   # this class can never preempt others
```

```yaml
# critical-deployment.yaml — uses the high-priority class
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-processor
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: payment-processor
  template:
    metadata:
      labels:
        app: payment-processor
    spec:
      priorityClassName: critical-production   # if cluster is full, evict batch pods for this
      containers:
      - name: payment
        image: myregistry/payment-processor:5.2.0
        resources:
          requests:
            cpu: "1"
            memory: 1Gi
---
# batch-job.yaml — uses the low-priority class
apiVersion: batch/v1
kind: Job
metadata:
  name: nightly-report
spec:
  template:
    spec:
      priorityClassName: batch-low-priority    # safe to evict if critical workloads need room
      restartPolicy: OnFailure
      containers:
      - name: reporter
        image: myregistry/report-generator:1.0.0
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
```

```bash
# See current priority classes in the cluster
kubectl get priorityclasses

# See which priority class a pod is using
kubectl get pod payment-processor-xxx -n production \
  -o jsonpath='{.spec.priorityClassName}'

# When payment-processor can't schedule, look for evictions in events
kubectl get events -n production --sort-by='.lastTimestamp' | grep Preempt
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

⬅️ **Prev:** [Helm Charts](../26_Helm_Charts/Code_Example.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Cluster Management](../28_Cluster_Management/Code_Example.md)
🏠 **[Home](../../README.md)**
