# HPA, VPA, and Autoscaling — Interview Q&A

---

## Beginner

---

**Q1: What is the HPA and what does it do?**

The HPA (Horizontal Pod Autoscaler) is a Kubernetes controller that automatically adjusts the number of pod replicas in a Deployment, StatefulSet, or ReplicaSet based on observed metrics. When your application gets more traffic or CPU load, the HPA adds more pods. When the load drops, it removes pods to save resources.

The "horizontal" in the name means it scales by changing the number of pods — scaling out (more pods) or scaling in (fewer pods). Instead of manually running `kubectl scale deployment` at 2 AM when traffic spikes, the HPA handles it automatically based on real-time metrics.

---

**Q2: What is the difference between HPA and VPA?**

HPA and VPA solve different parts of the same problem — right-sizing your application's resource usage:

| Aspect | HPA | VPA |
|---|---|---|
| What it scales | Number of pod replicas | CPU/memory requests and limits per pod |
| Direction | Horizontal (out/in) | Vertical (up/down) |
| Pod restarts? | No — adds/removes pods | Yes (in Auto mode) — evicts and recreates pods |
| Best for | Stateless services with variable traffic | Workloads with hard-to-predict resource needs |
| Can scale to zero? | No (minimum 1) | N/A — manages single pod sizing |

**Analogy**: HPA is like opening more checkout lanes at a supermarket when it gets busy. VPA is like training the cashiers to work faster.

For most production web services, HPA is the right tool. VPA is valuable for batch jobs, ML workloads, or any service where the right CPU/memory allocation is unclear.

---

**Q3: What are the three types of autoscaling in Kubernetes?**

1. **HPA (Horizontal Pod Autoscaler)**: Scales the number of pod replicas based on observed metrics (CPU, memory, or custom metrics). More pods = more capacity.

2. **VPA (Vertical Pod Autoscaler)**: Adjusts the CPU and memory requests/limits of individual pods based on actual observed usage. Same number of pods, but each pod is sized more accurately. Requires pod restarts in Auto mode.

3. **Cluster Autoscaler**: Adds nodes to the cluster when pods are Pending due to insufficient capacity, and removes underutilized nodes. Operates at the infrastructure level, not the pod level.

---

**Q4: What is the Metrics Server and why does HPA need it?**

The Metrics Server is a cluster-wide aggregator of resource usage data. It scrapes CPU and memory usage from the `kubelet` on each node and exposes this data through the Kubernetes Metrics API (`metrics.k8s.io`).

The HPA reads from the Metrics API to get current CPU and memory utilization for the pods it monitors. Without the Metrics Server running, the HPA cannot get these numbers — it will show `<unknown>` for current metrics and will stop making scaling decisions. You can verify the Metrics Server is working with:

```bash
kubectl top nodes
kubectl top pods -n <namespace>
```

If these commands fail, the Metrics Server is not running or not healthy. It must be installed separately on most clusters (it is not included by default in `kubeadm` clusters, but is pre-installed on EKS, GKE, and AKS).

---

## Intermediate

---

**Q5: How does HPA calculate how many replicas to create?**

The HPA uses this formula:

```
desiredReplicas = ceil(currentReplicas × (currentMetricValue / desiredMetricValue))
```

Example: You have 4 pods, target CPU is 50%, current average CPU across pods is 80%.

```
desiredReplicas = ceil(4 × (80 / 50)) = ceil(6.4) = 7
```

The HPA would scale up to 7 pods. As those pods absorb the load, CPU per pod drops, and the HPA eventually stabilizes. When multiple metrics are specified (e.g., both CPU and memory), the HPA computes desired replicas for each metric and uses the highest number — always erring on the side of more capacity.

---

**Q6: What metrics can HPA use beyond CPU and memory?**

HPA supports four metric types:

| Metric Type | Source | Example use case |
|---|---|---|
| `Resource` | CPU or memory from Metrics Server | Standard web services |
| `Pods` | Custom per-pod metric from a custom metrics API | Requests per second per pod |
| `Object` | A metric from a specific Kubernetes object | Message queue depth |
| `External` | Metrics from outside Kubernetes | AWS SQS queue length, Datadog metric |

For `Pods`, `Object`, and `External` metrics, you need a custom metrics adapter installed — for example, the **Prometheus Adapter** (exposes Prometheus metrics to HPA) or **KEDA** (supports dozens of event sources natively).

---

**Q7: What is the Metrics Server?**

The Metrics Server is a lightweight, in-cluster component that collects resource utilization data (CPU and memory) from each node's kubelet and exposes it through the `metrics.k8s.io` API. It is the required backend for `kubectl top` commands and for HPA and VPA to function.

Key facts about the Metrics Server:
- It is **not** a long-term metrics store — it only keeps the most recent snapshot of data (no historical data)
- For historical metrics and alerting, use Prometheus
- It aggregates data from all nodes every 15 seconds
- It must be installed separately on most self-managed clusters

---

**Q8: What is the scale-down stabilization window and why does it exist?**

The stabilization window is a delay that prevents the HPA from scaling down immediately after a metric drops. By default, the HPA waits 5 minutes (300 seconds) after a scale-down condition is met before reducing replicas.

This exists to prevent "thrashing" — a pattern where the HPA scales down, then a new traffic spike hits, then it scales back up, scales down again in a loop. This rapid oscillation wastes resources and can cause latency spikes.

You can customize the window per direction:

```yaml
behavior:
  scaleDown:
    stabilizationWindowSeconds: 300   # 5 minutes — conservative
  scaleUp:
    stabilizationWindowSeconds: 60    # 1 minute — responsive
```

Scale-up uses a shorter window because responding quickly to new load is more important than avoiding brief over-provisioning.

---

## Advanced

---

**Q9: Can HPA and VPA be used together? What is the safe combination?**

Yes, but with an important constraint: **do not run HPA on CPU with VPA in Auto mode on CPU at the same time**. They will fight each other:

1. VPA increases CPU requests (because observed usage is high)
2. Higher CPU requests change the utilization percentage even if actual usage is unchanged
3. HPA sees utilization drop and scales down replicas
4. Fewer replicas mean higher per-pod load, VPA increases requests again
5. The loop continues, causing constant pod evictions and replica changes

Safe combinations:
- **HPA on CPU + VPA on memory only**: Set VPA's `controlledResources: ["memory"]` so VPA only manages memory sizing.
- **HPA on custom metrics + VPA in Auto**: VPA handles right-sizing the pods; HPA scales on business metrics (queue depth, requests per second) that are not affected by resource request changes.
- **VPA in `Off` mode + HPA on CPU**: VPA gives you sizing recommendations you apply manually; HPA handles the actual scaling.

---

**Q10: What is KEDA and how does it extend HPA?**

KEDA (Kubernetes Event-Driven Autoscaling) is an open-source component that extends Kubernetes autoscaling with event-driven triggers. It works by creating a custom HPA object under the hood, but adds support for dozens of event sources that native HPA cannot handle natively.

The two key advantages KEDA offers over native HPA:

1. **Scale to zero**: Native HPA cannot go below 1 replica. KEDA can scale a Deployment to 0 when there is no work, and back up to N when events arrive. This is critical for cost efficiency in event-driven architectures.

2. **Rich event sources**: KEDA has built-in scalers for Kafka (consumer group lag), RabbitMQ (queue depth), AWS SQS, Azure Service Bus, Redis, Prometheus metrics, cron schedules, and many more.

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: kafka-consumer-scaler
spec:
  scaleTargetRef:
    name: kafka-consumer-deployment
  minReplicaCount: 0      # scale to zero when no messages
  maxReplicaCount: 50
  triggers:
    - type: kafka
      metadata:
        topic: orders
        consumerGroup: order-processor
        lagThreshold: "100"
```

---

**Q11: How do you avoid thrashing with HPA?**

Thrashing happens when the HPA over-reacts to short metric spikes and scales up, then scales back down, creating a continuous cycle. Strategies to prevent it:

1. **Tune the stabilization window**: Increase `scaleDown.stabilizationWindowSeconds` (default 300s). For spiky workloads, use 600s or more.

2. **Use scale policies to limit the rate of change**:
   ```yaml
   behavior:
     scaleDown:
       policies:
         - type: Pods
           value: 2           # remove at most 2 pods per 60 seconds
           periodSeconds: 60
   ```

3. **Set a sensible target utilization**: Targeting 90% CPU leaves very little headroom. Use 70-80% to allow normal variation without triggering scale-up on every small spike.

4. **Set appropriate minReplicas**: Do not set `minReplicas: 1` for production traffic. Keep enough base capacity to handle normal load so the HPA is not constantly scaling from 1.

5. **Use `averageValue` instead of `Utilization` for memory**: Memory can jump on startup (JVM warm-up, caches) and trigger false scale-ups. An absolute `averageValue` target for memory is often more stable.

---

**Q12: What is the Cluster Proportional Autoscaler and when would you use it?**

The Cluster Proportional Autoscaler (CPA) is a different autoscaling tool that scales a Deployment proportionally to the size of the cluster (number of nodes or total CPU cores), not based on the workload's own metrics.

It is designed for cluster add-ons and infrastructure components whose required replicas scale with cluster size, not with application traffic:

- **CoreDNS**: A cluster with 10 nodes needs 2 DNS replicas; a cluster with 500 nodes needs many more.
- **kube-proxy**: Node-level networking components.
- **Ingress controllers**: More nodes means more traffic surface, more instances needed.

The CPA uses a ConfigMap to define a step-function (ladder):

```json
{
  "coresToReplicas": [[1,1],[16,2],[64,3],[512,5]],
  "nodesToReplicas": [[1,1],[16,2],[64,3]]
}
```

This is distinct from HPA (which scales based on pod metrics) and Cluster Autoscaler (which scales nodes). CPA is specifically for cluster infrastructure components that need to grow with the cluster itself.

---

**Q13: What happens when there is no Metrics Server installed?**

Without the Metrics Server, HPA enters a degraded state. It cannot obtain current metrics and will emit events like `unable to fetch metrics from resource metrics API`. The HPA stops making scaling decisions and keeps the current replica count frozen. The HPA status will show `<unknown>` for current metric values.

VPA recommendations also stop working because the VPA recommender cannot get resource usage data. `kubectl top nodes` and `kubectl top pods` commands will fail.

The fix is to install the Metrics Server:
```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

For clusters with self-signed certificates (like local `kubeadm` clusters), you may also need to add `--kubelet-insecure-tls` to the Metrics Server deployment args.

---

## 📂 Navigation

⬅️ **Prev:** [Jobs and CronJobs](../17_Jobs_and_CronJobs/Interview_QA.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Resource Quotas and Limits](../19_Resource_Quotas_and_Limits/Theory.md)

| | Link |
|---|---|
| Theory | [Theory.md](./Theory.md) |
| Cheatsheet | [Cheatsheet.md](./Cheatsheet.md) |
| Module Home | [18_HPA_VPA_Autoscaling](../) |
