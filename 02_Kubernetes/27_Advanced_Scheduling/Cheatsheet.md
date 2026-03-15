# Module 27 — Advanced Scheduling Cheatsheet

## Scheduling Concepts Summary

| Feature | What it does | Hard/Soft |
|---|---|---|
| NodeSelector | Pod only on nodes with matching labels | Hard |
| NodeAffinity (required) | Rich node matching with operators | Hard |
| NodeAffinity (preferred) | Prefer certain nodes, fallback ok | Soft |
| PodAffinity | Schedule near matching pods | Both |
| PodAntiAffinity | Avoid scheduling near matching pods | Both |
| Taints + Tolerations | Nodes repel pods without toleration | Hard/Soft |
| PriorityClass | Preempt lower-priority pods | — |
| TopologySpreadConstraints | Even distribution across domains | Both |

---

## Node Labels Commands

```bash
# List all node labels
kubectl get nodes --show-labels

# Add a label to a node
kubectl label node <node-name> key=value
kubectl label node worker-01 disk=ssd
kubectl label node gpu-node accelerator=nvidia

# Remove a label
kubectl label node <node-name> key-
kubectl label node worker-01 disk-

# Get nodes with a specific label
kubectl get nodes -l disk=ssd
kubectl get nodes -l accelerator=nvidia
```

---

## NodeSelector

```yaml
spec:
  nodeSelector:
    disk: ssd
    accelerator: nvidia   # AND of all labels required
```

---

## NodeAffinity

```yaml
spec:
  affinity:
    nodeAffinity:
      # Hard constraint
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: node-type
            operator: In
            values: [worker, high-mem]
          - key: node-type
            operator: NotIn
            values: [spot]
          - key: ssd
            operator: Exists           # label exists, any value

      # Soft preference
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 80   # 1-100; higher = stronger preference
        preference:
          matchExpressions:
          - key: zone
            operator: In
            values: [us-east-1a]
      - weight: 20
        preference:
          matchExpressions:
          - key: zone
            operator: In
            values: [us-east-1b]
```

---

## PodAntiAffinity (Most Common Use Case)

```yaml
# Hard: each pod on a different node
spec:
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchLabels:
            app: myapp
        topologyKey: kubernetes.io/hostname

---
# Soft: prefer different nodes (recommended for most apps)
spec:
  affinity:
    podAntiAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchLabels:
              app: myapp
          topologyKey: kubernetes.io/hostname
```

---

## PodAffinity (Co-location)

```yaml
# Schedule app pod near its cache pod (same node)
spec:
  affinity:
    podAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchLabels:
              app: redis-cache
          topologyKey: kubernetes.io/hostname
```

---

## Taints and Tolerations

```bash
# Taint effects: NoSchedule | PreferNoSchedule | NoExecute
kubectl taint node <node> key=value:effect
kubectl taint node worker-01 dedicated=gpu:NoSchedule
kubectl taint node spot-01 spot=true:PreferNoSchedule
kubectl taint node worker-01 maintenance=true:NoExecute

# Remove taint
kubectl taint node worker-01 dedicated:NoSchedule-
```

```yaml
# Toleration in pod spec
spec:
  tolerations:
  - key: dedicated
    operator: Equal        # Equal | Exists
    value: gpu
    effect: NoSchedule

  - key: maintenance
    operator: Exists       # any value
    effect: NoExecute
    tolerationSeconds: 300  # evict after 5 minutes
```

---

## PriorityClass

```yaml
# Create priority class
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000
globalDefault: false
preemptionPolicy: PreemptLowerPriority   # default
description: "Critical workloads"

---
# Use in pod
spec:
  priorityClassName: high-priority
```

```bash
# List priority classes
kubectl get priorityclasses
```

---

## TopologySpreadConstraints

```yaml
spec:
  topologySpreadConstraints:
  # Spread across availability zones
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: DoNotSchedule    # Hard
    labelSelector:
      matchLabels:
        app: myapp

  # Spread across nodes (soft)
  - maxSkew: 2
    topologyKey: kubernetes.io/hostname
    whenUnsatisfiable: ScheduleAnyway   # Soft
    labelSelector:
      matchLabels:
        app: myapp
    minDomains: 3  # require at least 3 zones
```

---

## Common topologyKey Values

| topologyKey | Scope |
|---|---|
| `kubernetes.io/hostname` | Individual node |
| `topology.kubernetes.io/zone` | Availability zone |
| `topology.kubernetes.io/region` | Cloud region |
| Custom label | Any custom grouping |

---

## Quick Reference: HA Web App Pattern

```yaml
spec:
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchLabels:
            app: myapp
        topologyKey: kubernetes.io/hostname
  topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: ScheduleAnyway
    labelSelector:
      matchLabels:
        app: myapp
  priorityClassName: high-priority
```

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Advanced Scheduling Theory](./Theory.md) |
| Interview Q&A | [Advanced Scheduling Interview Q&A](./Interview_QA.md) |
| Next Module | [28 — Cluster Management](../28_Cluster_Management/Theory.md) |
