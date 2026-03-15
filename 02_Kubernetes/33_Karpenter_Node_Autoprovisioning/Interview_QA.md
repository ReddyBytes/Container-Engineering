# Karpenter — Interview Q&A

---

**Q1: What are the main limitations of Cluster Autoscaler that Karpenter addresses?**

Cluster Autoscaler has three fundamental architectural constraints. First, it works with fixed Auto Scaling Groups — if you need a new instance type, you must pre-provision a new ASG in advance. Karpenter has no ASGs; it calls EC2 directly and can provision any instance type at decision time. Second, CA is slow: the polling cycle, ASG expansion, and instance registration take 2-3 minutes. Karpenter launches nodes in ~30 seconds by talking directly to the EC2 API. Third, CA's consolidation is passive — it will scale down empty nodes eventually, but it does not proactively bin-pack underutilized nodes. Karpenter's consolidation loop continuously evaluates whether running pods can be moved to fewer nodes and terminates the redundant ones.

---

**Q2: Explain the difference between NodePool and EC2NodeClass.**

`NodePool` contains the scheduling logic — what constraints apply to nodes Karpenter can provision (allowed instance families, capacity types like spot/on-demand, architecture, zones) and how consolidation should behave. It is intentionally cloud-agnostic in structure.

`EC2NodeClass` contains AWS-specific infrastructure configuration — which AMI family to use, which VPC subnets (selected by tag), which security groups, IAM instance role, EBS volume configuration, and instance metadata settings. It is separated so the scheduling logic can be understood and modified without needing to know AWS details, and so multiple NodePools can share one EC2NodeClass.

The separation also reflects team responsibility: a platform/SRE team manages EC2NodeClass (it touches VPC, IAM, and AMIs), while a cluster admin can manage NodePools (scheduling policy) separately.

---

**Q3: How does Karpenter select which instance type to launch for a pending pod?**

Karpenter takes a constraint-satisfaction approach. Given a pending pod, it reads all of the pod's scheduling requirements: resource requests/limits, nodeSelector, nodeAffinity, tolerations, topology spread constraints, and pod affinity/anti-affinity rules. It then evaluates every instance type allowed by the matching NodePool(s) and filters out any that cannot satisfy the pod's requirements. From the remaining candidates, Karpenter uses a bin-packing algorithm to select the instance type that fits the pod (and any other pending pods that could be co-scheduled) at the lowest cost. This means Karpenter naturally avoids over-provisioning — if a pod needs 1 vCPU and 2 GiB, it will select a `t3.medium` rather than launching an `m5.4xlarge`.

---

**Q4: What is Karpenter consolidation and how does WhenEmptyOrUnderutilized work?**

Consolidation is Karpenter's proactive cluster right-sizing mechanism. It runs continuously and looks for opportunities to reduce the number of nodes without disrupting workloads.

`WhenEmptyOrUnderutilized` evaluates nodes in two ways: first, it identifies nodes with no running pods (ignoring DaemonSets) and terminates them. Second — and more powerfully — it identifies underutilized nodes where all running pods could be moved to other existing nodes with available capacity. For each candidate node, Karpenter checks whether evicting all its pods would violate any PodDisruptionBudgets. If not, it evicts the pods, waits for them to be rescheduled on existing nodes, and then terminates the empty node.

Disruption budgets (`budgets.nodes: "10%"`) control how aggressively this runs, preventing too many nodes from being consolidated simultaneously. This is critical in production — you want consolidation to save money, not cause an outage.

---

**Q5: How does Karpenter handle AWS Spot instance interruptions?**

Karpenter watches an SQS queue that receives EC2 Spot interruption notices (configured during installation). When AWS signals a 2-minute interruption warning, Karpenter:

1. Marks the node as unschedulable immediately (no new pods will be scheduled there)
2. Begins gracefully evicting pods from the node (respecting PDBs and terminationGracePeriodSeconds)
3. Simultaneously, Karpenter detects the now-pending pods and provisions a replacement node (either Spot from a different pool, or on-demand if the `on-demand` capacity type is in the NodePool)
4. Once the pods reschedule and the node is empty, Karpenter allows AWS to terminate it

This is significantly better than Cluster Autoscaler's Spot handling, where interruptions often caused pod disruptions with no proactive mitigation.

---

**Q6: What is the `do-not-disrupt` annotation and when would you use it?**

The `karpenter.sh/do-not-disrupt: "true"` annotation on a pod tells Karpenter never to evict that pod for consolidation or any other voluntary disruption. A node running a pod with this annotation will not be consolidated, even if it is otherwise underutilized.

Use cases:
- Long-running batch jobs that cannot be safely interrupted mid-execution (e.g., a 4-hour ML training run)
- Pods with no PDB defined but that would be disruptive to restart (e.g., a stateful singleton)
- During maintenance windows when you want to prevent unexpected pod restarts
- Testing: pin a pod to a specific node to debug a node-level issue

The trade-off is that nodes hosting do-not-disrupt pods become "sticky" — they will not be consolidated until those pods complete or the annotation is removed.

---

**Q7: How would you configure Karpenter to use Graviton (arm64) instances for cost savings?**

You add `arm64` to the `kubernetes.io/arch` requirement in your NodePool, and include Graviton instance families (m7g, c7g, r7g for Graviton 3; m8g, c8g for Graviton 4):

```yaml
requirements:
- key: kubernetes.io/arch
  operator: In
  values: ["amd64", "arm64"]
- key: karpenter.k8s.aws/instance-family
  operator: In
  values: ["m7g", "c7g", "m6i", "c6i"]
```

Karpenter will then choose arm64 or amd64 instances based on cost and availability. For this to work, your container images must be built as multi-architecture images (supporting both `linux/amd64` and `linux/arm64`). Build them with `docker buildx build --platform linux/amd64,linux/arm64`. Most public images (nginx, postgres, redis) are already multi-arch. Your own application images need to be explicitly built that way.

---

**Q8: A developer is running a long database migration job overnight. They are worried Karpenter will evict it during consolidation. How do you protect it?**

Two complementary approaches:

First, annotate the pod to prevent eviction:
```yaml
metadata:
  annotations:
    karpenter.sh/do-not-disrupt: "true"
```

Second, if this is a critical workload, create a PodDisruptionBudget:
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
spec:
  minAvailable: 1
  selector:
    matchLabels:
      job-name: db-migration
```

The annotation is the primary protection — it explicitly opts the pod out of voluntary disruptions. The PDB is a safety net for any scenario where the annotation might not apply (e.g., node failure). In practice, for a Job (which creates pods by design to run to completion), the `do-not-disrupt` annotation is the simplest and most direct protection.

---

**Q9: What does the `limits` field in a NodePool do?**

`limits` in a NodePool sets a ceiling on the total compute resources Karpenter will provision from that NodePool. Once the total vCPUs or memory across all Karpenter-managed nodes from that pool reaches the limit, Karpenter will not launch any more nodes from it (pods will remain pending).

```yaml
limits:
  cpu: 1000        # stop at 1000 vCPUs total
  memory: 4000Gi   # stop at 4 TiB memory total
```

This is a cost protection mechanism. Without limits, a runaway workload (autoscaling bug, accidental deployment of thousands of pods) could cause Karpenter to provision an unlimited number of nodes. Setting reasonable limits prevents unexpected cloud bills while still allowing normal autoscaling. The limits are per-NodePool, so you can set different ceilings for spot vs on-demand pools.

---

**Q10: Karpenter v1.0 was released in 2024. What does v1.0 stability mean for production use?**

Karpenter v1.0 means the API is stable — the `karpenter.sh/v1` API version for `NodePool` and `NodeClaim` resources will not have breaking changes. Before v1.0 (when resources were in `v1beta1`), operators had to handle API migrations during upgrades. With v1.0, you can upgrade Karpenter without rewriting your NodePool manifests.

Practically, v1.0 signals production readiness from the project maintainers. AWS uses Karpenter in EKS managed clusters internally, it is the recommended node autoscaler in AWS's own EKS best practices guide, and it is the default autoscaler in EKS Auto Mode (announced at re:Invent 2024). The CNCF graduation track is also in progress. For new EKS clusters started in 2024 or later, Karpenter is the default recommendation over Cluster Autoscaler.

---

**Q11: How do multiple NodePools interact? Can a pod be scheduled on nodes from different NodePools?**

Multiple NodePools can exist simultaneously and a pod can be scheduled on a node from any matching NodePool. Karpenter evaluates all NodePools against the pod's requirements and uses the one that produces the lowest-cost node matching all constraints.

A common pattern is to have:
- A `spot-general` NodePool for most workloads (cost-optimized)
- An `on-demand-critical` NodePool for databases and stateful services (stable)
- A `gpu` NodePool with GPU instance types and a taint (only used by pods that tolerate it)

Pods use `nodeSelector` or `nodeAffinity` to target a specific pool, or they let Karpenter pick the cheapest matching pool. Taints+tolerations are the primary mechanism for "dedicated" pools — taint the NodePool's nodes and only pods with matching tolerations will land there.

---

## 📂 Navigation

| | |
|---|---|
| Previous | [32_KEDA_Event_Driven_Autoscaling](../32_KEDA_Event_Driven_Autoscaling/) |
| Next | [34_eBPF_and_Cilium](../34_eBPF_and_Cilium/) |
| Up | [02_Kubernetes](../) |

**Files in this module:**
- [Theory.md](./Theory.md) — Concepts and architecture
- [Cheatsheet.md](./Cheatsheet.md) — Quick reference
- [Interview_QA.md](./Interview_QA.md) — Common interview questions
- [Code_Example.md](./Code_Example.md) — Working YAML examples
