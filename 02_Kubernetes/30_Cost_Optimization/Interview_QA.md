# Module 30 — Cost Optimization Interview Q&A

---

## Q1: What are the main drivers of high Kubernetes costs, and how do you identify them?

**Answer:**

The main cost drivers:

1. **Over-provisioned pods**: resource requests set much higher than actual usage. The scheduler reserves that space even if the pod uses a fraction. Identify with `kubectl top pods` vs `kubectl describe pod` (compare actual usage to requests).

2. **Idle or stale resources**: PVCs not attached to pods, namespaces with 0 active workloads, dev environments running 24/7. Identify with `kubectl get pvc -A | grep Released` and Kubecost idle cost reports.

3. **Wrong node sizing**: using 16-core nodes for workloads that could fit on 4-core nodes. Identify with node utilization metrics and Karpenter recommendations.

4. **No spot instances**: paying full on-demand price for workloads that could tolerate interruption. Check if batch jobs, CI/CD runners, or dev pods use spot.

5. **Cross-AZ traffic**: Kubernetes by default routes pod-to-pod traffic across AZs (which costs money). Identify with network cost tools in Kubecost.

Tools: `kubectl top`, Kubecost, OpenCost, VPA recommendations, cloud provider cost explorer.

---

## Q2: What is the difference between resource requests and limits in the context of cost?

**Answer:**

**Requests** determine scheduling and therefore node provisioning cost:
- The scheduler places pods based on requests
- If a pod requests `1 CPU`, that 1 CPU is "reserved" on the node even if the pod uses 10m
- Oversized requests directly cause oversized nodes (more cost)

**Limits** cap actual usage:
- A pod can't use more than its limit
- Limits don't affect scheduling (a node isn't "full" based on limits)
- Setting limits too low causes throttling (degraded performance)

Cost optimization insight: right-sizing requests is the highest-leverage cost action. Reducing a request from `cpu: 1` to `cpu: 100m` can allow 10 pods to fit on a node where only 1 did before — reducing node count by 10x.

VPA recommendations target request right-sizing. Set limits at 2-3x the request as buffer.

---

## Q3: What is Kubecost and what visibility does it provide that kubectl doesn't?

**Answer:**

kubectl shows you current resource usage (top pods, top nodes) but has no concept of cost — it doesn't know what an m5.large instance costs per hour.

Kubecost:
- Maps pod resource consumption to actual cloud costs using cloud provider pricing APIs
- Shows cost per namespace, deployment, label, team
- Calculates efficiency score (actual usage / requested) — 30% efficiency means 70% waste
- Shows idle cluster costs (nodes running with no pods)
- Provides right-sizing recommendations with projected savings
- Tracks cost over time (trending up? which team's costs changed?)
- Shows network transfer costs

Example insight only Kubecost can provide: "The machine-learning namespace cost $12,000 last month, up 300% from last month. The training-jobs deployment accounts for 80% of that. Their GPU node requests are 90% idle."

**OpenCost** is the CNCF open-source version of the core metrics — just the cost data API, no dashboard. Kubecost builds on it with a richer UI.

---

## Q4: How does Karpenter differ from Cluster Autoscaler in terms of cost optimization?

**Answer:**

**Cluster Autoscaler**:
- Works with pre-defined Node Groups (instance types fixed per group)
- Can only add nodes from configured groups
- Scaling decision: "does adding a node from group X fix the pending pod?"
- Doesn't consolidate — nodes stay around even if underutilized
- Slow to scale down (default 10-minute utilization wait)

**Karpenter**:
- Provisions any instance type dynamically (selects optimal per workload)
- When a pod is Pending, it evaluates requirements and picks the cheapest instance that fits
- **Consolidation**: actively moves pods to fill nodes, terminates emptied nodes
- Much faster (direct EC2 API, no node group constraints)
- Can split workloads: some pods on spot, some on on-demand, optimized per requirement

Cost example: Cluster Autoscaler might provision `m5.2xlarge` (8 vCPU) because that's the only group configured. Karpenter might provision `c5.large` (2 vCPU) because that's what the workload actually needs — 4x cheaper.

Karpenter's consolidation alone can reduce node count by 20-40% in clusters with variable workloads.

---

## Q5: Explain the spot instance pattern for Kubernetes and what workloads are suitable.

**Answer:**

Spot instances offer up to 90% discount over on-demand but can be terminated with ~2-minute notice when the cloud provider needs the capacity back.

Pattern:
1. Node group with spot instances, tagged with `capacity-type=spot`
2. Spot nodes tainted to prevent unintended workloads
3. Target workloads have matching tolerations + prefer spot via nodeAffinity
4. Apps designed for graceful shutdown (handle SIGTERM, drain connections in 120s)

**Suitable workloads**:
- Batch processing jobs (ML training, data pipelines) — interruption just delays completion
- CI/CD runners — job reruns if runner is killed
- Dev/staging environments — acceptable downtime
- Stateless services with >= 3 replicas — 1 termination doesn't break the service
- Queue workers — message goes back to queue on interruption

**Not suitable**:
- Databases and stateful services (data consistency on interruption is complex)
- Services with `replicas: 1` — one spot termination = full outage
- Latency-sensitive user-facing services without enough replicas

On GKE: preemptible or Spot VMs. On Azure: Spot VMs. On AWS: Spot instances (via managed node groups or Karpenter).

---

## Q6: How do you prevent runaway cloud costs in Kubernetes with multiple teams?

**Answer:**

Multi-layer controls:

1. **ResourceQuota per namespace/team**: caps total CPU, memory, storage, and pod count per team. A misconfigured deployment can't consume the entire cluster.

2. **LimitRange defaults**: sets default requests/limits so pods without explicit resource specs get reasonable defaults (not unlimited).

3. **Cost alerts**: Kubecost can alert when namespace cost exceeds a threshold (e.g., alert if team-backend costs > $5,000/day).

4. **Cost allocation labels**: require `team`, `product`, `environment` labels via Kyverno policy — makes cost attribution automatic.

5. **Quota for storage**: `requests.storage` quota prevents teams from creating unlimited PVCs.

6. **PR reviews for resource changes**: treat resource request increases as infrastructure changes requiring review, not just code changes.

7. **Regular cost reviews**: monthly or quarterly team cost review — show each team their spending trend and compare to baselines.

The key insight: teams optimize what they can see and are held accountable for. Make costs visible to the teams generating them.

---

## Q7: What is the efficiency score in Kubecost and what is a good target?

**Answer:**

Efficiency = actual CPU/memory usage ÷ requested CPU/memory.

Example: a pod requests 1 CPU and uses 100m CPU → efficiency = 10%.

A cluster with 50% efficiency means half the node capacity being paid for is unused.

Benchmarks:
- < 30%: significant waste, immediate right-sizing opportunity
- 30-50%: room for improvement, typical in dev-heavy environments
- 50-65%: reasonable for production (some headroom needed for spikes)
- 65-80%: well-optimized
- > 80%: potentially under-resourced — monitor for throttling and OOMKills

Target: 50-65% for production (enough headroom to absorb traffic spikes without immediate autoscaling). Dev environments can tolerate lower — they benefit more from spot + scale-to-zero.

Note: 100% efficiency would mean pods are constantly at their limits with no headroom — that's dangerous, not a goal.

---

## Q8: How do image sizes affect Kubernetes cost?

**Answer:**

Image size creates cost in multiple indirect ways:

1. **Slower pod starts**: large images take longer to pull on new nodes. During scale-out events, this delays workload readiness — meaning more nodes might be needed to handle load while new pods are still pulling.

2. **Node disk pressure**: large images consume node disk space. If node disk fills up, kubelet evicts pods (`DiskPressure` condition). You need larger disks or faster cleanup.

3. **Registry bandwidth**: pulling images from ECR/GCR/Docker Hub costs money for egress and bandwidth. A 2GB image pulled 1000 times per day = 2TB egress.

4. **Cache misses**: if images are too large to cache on nodes efficiently, every pod start requires a full pull.

Optimization:
- Multi-stage builds eliminate build-time dependencies from runtime images
- `python:3.11-slim` vs `python:3.11` saves ~800MB
- Distroless images (no shell, no package manager) save more and improve security
- Regularly prune old image layers from nodes: `crictl rmi --prune`

---

## Q9: What is Karpenter's consolidation feature and how does it save money?

**Answer:**

Consolidation is Karpenter's ability to actively reduce the number of nodes running in a cluster by moving pods around and terminating underutilized nodes.

How it works:
1. Karpenter continuously evaluates node utilization
2. If pods on an underutilized node can fit on other existing nodes, Karpenter cordons the node, evicts pods (which reschedule), and terminates the node
3. Also does "replace" consolidation: if a large expensive node's pods would fit on a cheaper smaller node, it replaces it

Example: after business hours, only 30% of pods are running. Karpenter consolidates from 20 nodes to 8 nodes by bin-packing pods. The other 12 nodes are terminated. When morning traffic returns, Karpenter scales back up.

Configuration:
```yaml
disruption:
  consolidationPolicy: WhenUnderutilized
  consolidateAfter: 30s
  budgets:
  - nodes: "10%"   # don't consolidate more than 10% of nodes simultaneously
```

The `budgets` setting ensures consolidation doesn't cause a flood of pod evictions that disrupts the service.

Cluster Autoscaler can also scale down, but it requires nodes to be empty — it doesn't move pods. Karpenter's proactive consolidation is much more aggressive and effective.

---

## Q10: How do you build a cost optimization culture in an engineering organization?

**Answer:**

Technical tools alone don't solve cost problems — culture does.

Key practices:

1. **Make costs visible**: show every team their monthly spend in Kubecost. "Out of sight, out of mind" doesn't work for cloud costs.

2. **Make teams responsible**: allocate costs to teams/products. When engineering teams see their product's cloud bill, they self-optimize.

3. **Set budgets per team**: monthly budgets with alerts. Getting an alert that you've used 80% of your budget in week 2 changes behavior.

4. **Celebrate efficiency wins**: when a team reduces their cost by 30%, make it visible to the organization.

5. **Include cost in architecture reviews**: "this design costs $X/month at Y scale" should be part of every design doc.

6. **Automate the easy wins**: auto-scaling, spot usage, and scheduled scale-down for dev environments shouldn't require manual intervention.

7. **Right-sizing as a quarterly ritual**: review VPA recommendations quarterly, update resource requests as workload patterns evolve.

The fundamental principle: cloud resources are like any other business expense. The engineers closest to the code have the most knowledge to optimize it — give them the visibility and accountability to do so.

---

## Q11: How do you implement showback and chargeback with OpenCost? What are the limitations?

**Answer:**

**OpenCost** is a CNCF project that provides a cost allocation API for Kubernetes. It queries cloud provider pricing APIs (or custom on-prem pricing), combines that with pod resource usage and node costs, and produces per-namespace, per-label, and per-deployment cost breakdowns.

**Implementation steps:**

```bash
# Install OpenCost
helm repo add opencost https://opencost.github.io/opencost-helm-chart
helm install opencost opencost/opencost \
  --namespace opencost \
  --create-namespace \
  --set opencost.exporter.cloudProviderApiKey="YOUR_KEY"

# Query cost allocation API
curl "http://opencost.opencost:9003/allocation?window=lastmonth&aggregate=namespace&accumulate=true"
```

The API returns JSON with cost broken down by namespace. Feed this into:
- A Grafana dashboard for visualization
- A weekly email report per team
- A finance system for actual chargeback transfers

**Showback** (information without billing): just display the costs to teams. No financial system integration needed. Requires team discipline to act on what they see.

**Chargeback** (actual billing): requires mapping Kubernetes namespaces/labels to cost centers in your finance system. A scheduled job reads OpenCost data weekly, converts to cost center allocations, and posts to your internal billing system.

**Limitations:**

1. **Shared infrastructure costs**: control plane, monitoring stack, load balancers — these have no natural workload owner and must be split proportionally or absorbed as overhead
2. **Label completeness**: pods without cost attribution labels end up in an "unallocated" bucket; enforce labeling policy upstream via Kyverno
3. **Spot price volatility**: spot instance prices change by the hour; OpenCost samples prices and averages, which may not match your actual bill perfectly
4. **Idle cost attribution**: deciding who pays for underutilized capacity requires a policy decision (by request, by actual usage, or shared overhead)
5. **Storage accuracy**: PVC costs are modeled but egress and NAT Gateway costs are harder to attribute to specific pods

---

## Q12: How do you optimize PersistentVolume costs in a Kubernetes cluster?

**Answer:**

PV costs are often invisible until the bill arrives. Block storage is 5–20x more expensive per GB than object storage. The main optimization levers:

**1. Delete unused PVCs immediately**

When a PVC is deleted with a `Delete` reclaim policy, the underlying volume is deleted. With `Retain`, it stays and keeps costing money. Detect and clean up:

```bash
# PVs in Released state (PVC deleted, volume still exists)
kubectl get pv -o json | \
  jq '.items[] | select(.status.phase=="Released") | {name:.metadata.name, size:.spec.capacity.storage}'

# Delete Released PVs after verifying they are no longer needed
kubectl delete pv <pv-name>
```

**2. Match storage class to workload**

```yaml
# Expensive: SSD for everything
storageClassName: gp3

# 70% cheaper: throughput-optimized HDD for non-latency-sensitive workloads
storageClassName: st1   # AWS throughput-optimized HDD

# Very cheap: object storage via a CSI driver (e.g., mountpoint-s3)
storageClassName: s3-csi
```

Databases need fast SSD (gp3). Log archives, ML datasets, and backups can use HDD or object storage at a fraction of the cost.

**3. Right-size PVC capacity**

Developers often request `50Gi` when the workload uses `5Gi`. Monitor actual usage:

```bash
# Check actual disk usage inside a pod
kubectl exec -it <pod> -- df -h /data
```

Use online expansion (most CSI drivers support it) to start small and grow on demand rather than pre-allocating.

**4. Use object storage instead of block PVCs**

For static assets, backups, ML datasets, audit logs — anything that does not need low-latency random I/O — object storage (S3, GCS) is 10–50x cheaper per GB. Use an SDK or a CSI-to-S3 driver rather than a PVC.

**5. Set lifecycle policies on snapshots**

VolumeSnapshots accrue costs. Automate deletion of old snapshots:

```bash
# AWS: EBS snapshot lifecycle policies
aws dlm create-lifecycle-policy \
  --description "Delete old K8s PV snapshots" \
  --state ENABLED \
  --execution-role-arn arn:aws:iam::...

# Or manage via Velero TTL (--ttl 720h deletes backups after 30 days)
```

---

## 📂 Navigation

| | Link |
|---|---|
| ⬅️ Prev | [Backup and DR](../29_Backup_and_DR/Interview_QA.md) |
| Theory | [Cost Optimization Theory](./Theory.md) |
| Cheatsheet | [Cost Optimization Cheatsheet](./Cheatsheet.md) |
| ➡️ Next | [Gateway API](../31_Gateway_API/Theory.md) |
