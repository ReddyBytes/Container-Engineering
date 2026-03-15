# Module 27 — Advanced Scheduling Interview Q&A

---

## Beginner Questions

---

**Q1: What is pod scheduling in Kubernetes?**

**Answer:**

Pod scheduling is the process by which Kubernetes decides which node each pod should run on. When you create a pod (or a Deployment creates pods), they don't magically appear on nodes — the **kube-scheduler** evaluates every available node and picks the best one.

The default scheduling process has three phases:

1. **Filter** — eliminate nodes that cannot run the pod at all (not enough CPU/memory, node is NotReady, has a taint the pod doesn't tolerate, etc.)
2. **Score** — rank the remaining nodes using scoring algorithms (spread pods evenly, prefer nodes with more free resources, etc.)
3. **Bind** — assign the pod to the highest-scoring node

Without any scheduling hints from you, the scheduler makes sensible choices based on resource availability. But for production workloads — GPU nodes, high-availability spread, dedicated infrastructure — you need to give the scheduler explicit guidance.

---

**Q2: What is a nodeSelector and how do you use it?**

**Answer:**

`nodeSelector` is the simplest way to constrain which nodes a pod can be scheduled on. It specifies a set of key=value label pairs, and the pod will only be scheduled on nodes that have all of those labels.

```yaml
# Step 1: Label the node
kubectl label node worker-03 disktype=ssd

# Step 2: Use nodeSelector in the pod spec
spec:
  nodeSelector:
    disktype: ssd
```

The pod will only schedule on nodes with the `disktype=ssd` label. If no such node has capacity, the pod stays Pending.

`nodeSelector` is intentionally simple — it only supports exact label matching with implicit AND (all labels must match). For more complex rules like "prefer SSD but run anywhere if none available," or "not equal" conditions, you need `nodeAffinity`.

---

**Q3: What are taints and tolerations?**

**Answer:**

Taints and tolerations work together to repel pods from nodes.

**A taint** is applied to a node and says: "Pods that do not tolerate this taint will not be scheduled here." It has three parts:
- **key**: a label key (e.g., `gpu`)
- **value**: a label value (e.g., `nvidia`)
- **effect**: what happens to pods that don't tolerate it (`NoSchedule`, `PreferNoSchedule`, or `NoExecute`)

```bash
# Taint a node so only GPU pods run there
kubectl taint node gpu-node-01 gpu=nvidia:NoSchedule
```

**A toleration** is added to a pod and says: "I can tolerate this taint." The pod is then allowed (but not necessarily scheduled) on tainted nodes.

```yaml
spec:
  tolerations:
    - key: gpu
      operator: Equal
      value: nvidia
      effect: NoSchedule
```

The difference from nodeAffinity: taints are node-side (the node rejects by default) while nodeAffinity is pod-side (the pod requests certain nodes). Taints affect all pods — only pods with matching tolerations are allowed.

---

## Intermediate Questions

---

**Q4: What is the difference between nodeAffinity and nodeSelector?**

**Answer:**

Both constrain which nodes a pod can run on, but they differ significantly in expressiveness:

**nodeSelector** — simple key=value matching only:
- Only supports exact equality
- All specified labels must match (AND only)
- No soft preferences — it's always a hard requirement

**nodeAffinity** — rich expression-based constraints:
- Supports operators: `In`, `NotIn`, `Exists`, `DoesNotExist`, `Gt`, `Lt`
- Multiple terms with OR between `nodeSelectorTerms`, AND within `matchExpressions`
- Two types:
  - `requiredDuringSchedulingIgnoredDuringExecution` — hard requirement (pod stays Pending if not satisfied)
  - `preferredDuringSchedulingIgnoredDuringExecution` — soft preference (scheduler tries to satisfy it, but schedules elsewhere if needed)

Example that nodeSelector cannot express: "must run on amd64 OR arm64 architecture, but NOT on spot instances":

```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
        - matchExpressions:
            - key: kubernetes.io/arch
              operator: In
              values: [amd64, arm64]
            - key: node.kubernetes.io/capacity-type
              operator: NotIn
              values: [spot]
```

For new workloads, prefer `nodeAffinity`. `nodeSelector` is kept for simplicity and backward compatibility.

---

**Q5: What are the three taint effects and when do you use each?**

**Answer:**

- **`NoSchedule`**: new pods without a matching toleration will NOT be scheduled on this node. Already running pods are unaffected. Use this when you want to stop new general workloads from landing on a dedicated node, without disrupting existing workloads.

- **`PreferNoSchedule`**: the scheduler will try to avoid placing untolerated pods here, but will if there's no better option. Use this for soft dedications — you'd prefer only specific pods, but you can accept others in a pinch.

- **`NoExecute`**: new pods without toleration won't schedule, AND existing running pods without toleration are **evicted**. This is the most powerful effect. Use it for: node maintenance (immediately evict everything), node health issues, or marking a node for rapid draining. You can add `tolerationSeconds` to give running pods a grace period before eviction.

```bash
# NoSchedule — stop new pods
kubectl taint node worker-01 maintenance=true:NoSchedule

# NoExecute — evict everything with 60 second grace
kubectl taint node worker-01 maintenance=true:NoExecute

# Add a toleration for a pod that should survive NoExecute for 5 minutes
tolerations:
  - key: maintenance
    effect: NoExecute
    tolerationSeconds: 300
```

---

**Q6: What is pod affinity and pod anti-affinity?**

**Answer:**

Pod affinity and anti-affinity define scheduling constraints based on where **other pods** are running, rather than node properties.

**PodAffinity** — "schedule this pod near pods matching these labels":
- Use case: co-locate a service with its local cache (same node = lower latency)

**PodAntiAffinity** — "do not schedule this pod near pods matching these labels":
- Use case: spread replicas across nodes or availability zones for high availability

Both use a `topologyKey` to define the scope of "near":
- `kubernetes.io/hostname` — same node
- `topology.kubernetes.io/zone` — same availability zone
- `topology.kubernetes.io/region` — same region

```yaml
# Anti-affinity: ensure replicas spread across nodes
affinity:
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchLabels:
            app: my-service
        topologyKey: kubernetes.io/hostname
```

With `required` anti-affinity, if you have 4 replicas and only 3 nodes, the 4th pod stays Pending — hard constraint. With `preferred`, the scheduler spreads as much as possible but doesn't block when nodes are exhausted.

---

**Q7: What is TopologySpreadConstraints and how does it differ from PodAntiAffinity?**

**Answer:**

Both spread pods across topology domains, but with different precision:

**PodAntiAffinity** with `required` creates a pairwise constraint: each pod refuses to be on the same topology domain as another matching pod. With 4 pods and 3 nodes, the 4th pod is Pending forever — it cannot be scheduled on any node that already has one.

**TopologySpreadConstraints** controls spread more precisely using `maxSkew` — the maximum difference in pod count allowed between any two topology domains:

```yaml
topologySpreadConstraints:
  - maxSkew: 1                    # max difference between any two zones
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: DoNotSchedule   # hard — or ScheduleAnyway for soft
    labelSelector:
      matchLabels:
        app: my-service
```

With `maxSkew: 1` across 3 zones and 6 pods: 2-2-2 is valid (skew=0), 3-2-1 is valid (skew=2 — exceeds maxSkew so it's blocked), 6-0-0 would never happen.

TopologySpreadConstraints is the modern, more precise approach. It also handles the case where you have more replicas than nodes gracefully — it just balances as evenly as possible instead of blocking.

---

**Q8: What are PriorityClasses and how does preemption work?**

**Answer:**

**PriorityClasses** assign a numeric priority value to pods (higher = more important). Kubernetes uses priority in two ways:

1. **Scheduling order**: when multiple pods are pending, higher-priority pods are scheduled first
2. **Preemption**: if a high-priority pod cannot be scheduled because nodes are full, the scheduler evicts lower-priority pods to make room

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000
preemptionPolicy: PreemptLowerPriority   # default
globalDefault: false
description: "For critical production services"
```

Kubernetes has built-in system classes: `system-cluster-critical` (2000000000) and `system-node-critical` (2000001000) — used for CoreDNS, kube-proxy, etc.

Important caveats:
- Preemption terminates running pods — it's disruptive
- Use PodDisruptionBudgets on important workloads to limit preemption impact
- Set `preemptionPolicy: Never` if you want a pod to be scheduled first among pending pods but not evict running ones
- Non-preempting priority is useful for batch jobs that should schedule ahead of other batch jobs but shouldn't disturb production workloads

---

## Advanced Questions

---

**Q9: What is the difference between a scheduler extender and the scheduler plugin framework?**

**Answer:**

Both allow you to extend or replace scheduling logic, but they work very differently:

**Scheduler Extender** (older approach):
- An external webhook that the scheduler calls during certain phases (filter, score, bind, preempt)
- The main scheduler makes HTTP calls to your extender
- Simple to build and deploy independently
- High latency — HTTP round-trips for every scheduling decision
- Limited integration — you can only hook into specific phases, not add new ones

**Scheduler Plugin Framework** (modern approach, Kubernetes Scheduling Framework):
- Compile scheduling logic directly into the scheduler binary as plugins
- Plugins implement well-defined Go interfaces for each scheduling phase: `PreFilter`, `Filter`, `PostFilter`, `PreScore`, `Score`, `Reserve`, `Permit`, `PreBind`, `Bind`, `PostBind`
- Zero HTTP overhead — runs in-process
- Full access to all scheduling data
- Can replace or extend any phase
- Used by Volcano, Kueue, and other advanced scheduling systems

The scheduler plugin framework is the recommended approach for any serious custom scheduling. Extenders are simpler for quick prototypes but have performance limitations at scale.

---

**Q10: How do you schedule pods across availability zones for high availability?**

**Answer:**

Three complementary approaches, often used together:

**1. TopologySpreadConstraints (recommended)**
```yaml
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: ScheduleAnyway   # soft — don't block if unbalanced
    labelSelector:
      matchLabels:
        app: my-service
```

**2. PodAntiAffinity (hard enforcement)**
```yaml
affinity:
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchLabels:
            app: my-service
        topologyKey: topology.kubernetes.io/zone
```
Warning: with `required`, if you have more replicas than zones, pods will be Pending.

**3. Node Group / Node Pool per Zone**
In cloud environments, configure multiple node groups — one per AZ. Combine with the above constraints. This ensures even if one AZ has more capacity, pods still spread.

**Important prerequisite**: nodes must be labeled with `topology.kubernetes.io/zone`. Cloud providers (EKS, GKE, AKS) do this automatically. For self-managed clusters, label nodes manually or via the cloud provider node group configuration.

---

**Q11: What is the Descheduler and when would you use it?**

**Answer:**

The Kubernetes Descheduler is a separate tool (not part of core Kubernetes) that runs periodically and evicts pods to trigger re-scheduling. The scheduler only places pods when they are first created — it does not rebalance running pods. Over time, this leads to suboptimal placement:

- Nodes added after pods were scheduled are underutilized
- Node labels changed, making some placements suboptimal
- Some nodes have many pods while newer nodes are mostly empty
- Pods that should be anti-affined ended up on the same node due to race conditions

The Descheduler has pluggable strategies:

| Strategy | What it does |
|----------|-------------|
| `RemoveDuplicates` | Evicts pods so no two replicas of the same ReplicaSet are on the same node |
| `LowNodeUtilization` | Evicts pods from over-utilized nodes and lets them reschedule on under-utilized ones |
| `RemovePodsViolatingInterPodAntiAffinity` | Evicts pods that violate anti-affinity rules |
| `RemovePodsViolatingNodeAffinity` | Evicts pods on nodes that no longer match their affinity rules |
| `TopologySpreadConstraint` | Evicts pods that violate spread constraints |

You deploy it as a CronJob or Deployment. It runs, finds violations, evicts the offending pods, and the scheduler re-places them following current rules.

Use the Descheduler when: your cluster has long-lived pods and you want to ensure optimal placement is maintained over time, not just at initial scheduling.

---

**Q12: What is topology spread with `whenUnsatisfiable: DoNotSchedule` vs `ScheduleAnyway`?**

**Answer:**

These control what happens when the Descheduler or scheduler cannot satisfy the `maxSkew` constraint:

**`DoNotSchedule`** (hard constraint):
- The pod stays Pending if scheduling it would exceed `maxSkew`
- Use when even placement is critical for correctness (e.g., a distributed system that requires exactly equal shards per zone)
- Risk: pods can get stuck Pending if the cluster doesn't have the right capacity distribution

**`ScheduleAnyway`** (soft constraint):
- The pod is scheduled even if it would exceed `maxSkew`, but the scheduler still prefers balanced placement
- The scheduler uses the spread as a scoring factor — it scores nodes that maintain better balance higher
- Use for most production HA scenarios — you want good spread, but you don't want pods to be Pending just because one zone has one extra pod

**Recommended practice**: start with `ScheduleAnyway` for most workloads. Switch to `DoNotSchedule` only for specific systems where strict balance is a correctness requirement, and ensure you have adequate node capacity in each zone to avoid Pending pods.

---

## 📂 Navigation

⬅️ **Prev:** [Helm Charts](../26_Helm_Charts/Interview_QA.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Cluster Management](../28_Cluster_Management/Theory.md)

| | Link |
|---|---|
| Theory | [Advanced Scheduling Theory](./Theory.md) |
| Cheatsheet | [Advanced Scheduling Cheatsheet](./Cheatsheet.md) |
