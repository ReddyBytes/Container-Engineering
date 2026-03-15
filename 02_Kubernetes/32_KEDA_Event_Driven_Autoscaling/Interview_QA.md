# KEDA — Interview Q&A

---

**Q1: What is KEDA and why would you use it over standard HPA?**

KEDA (Kubernetes Event Driven Autoscaling) is a CNCF-graduated project that extends Kubernetes autoscaling to support external event sources. Standard HPA can only scale based on CPU utilization, memory utilization, or custom metrics that you expose yourself. This works for latency-sensitive web services, but it breaks down completely for event-driven workloads. If you have queue workers reading from SQS, they spend most of their time waiting — low CPU, but potentially thousands of messages backed up. HPA would scale them down while work piles up. KEDA solves this by connecting the scaling decision directly to the queue depth, Kafka consumer lag, Prometheus metrics, or any of 50+ other triggers. Additionally, KEDA can scale to zero replicas when there are no events, which is impossible with standard HPA (minimum of 1).

---

**Q2: Explain how KEDA interacts with HPA. Does it replace it?**

KEDA does not replace HPA — it manages an HPA resource on your behalf and feeds it external metrics through the KEDA Metrics Adapter. When you create a `ScaledObject`, KEDA creates a corresponding HPA that references a custom metric (e.g., `External/keda-sqs-my-queue`). The KEDA Metrics Adapter serves this metric value to the Kubernetes Metrics API, which the HPA then uses to calculate the desired replica count. For scale-to-zero specifically, KEDA bypasses HPA and controls the Deployment's replica count directly, because HPA has a hard minimum of 1. Once traffic returns, KEDA scales the Deployment to 1, which brings HPA back into control for 1 → N scaling.

---

**Q3: What is the difference between ScaledObject and ScaledJob?**

`ScaledObject` targets a long-running workload like a Deployment or StatefulSet. It adjusts the replica count up and down based on the metric — pods stay alive and continuously poll for work. This is appropriate when the time to process each item is short (seconds) and you want continuous throughput.

`ScaledJob` creates Kubernetes Job objects — each scale event results in a new batch of Jobs being created, each running to completion before being cleaned up. This is appropriate when each unit of work is long-running (minutes or hours), when you want strict isolation between processing runs, or when you need to track completion status of each work item. For example, video transcoding jobs are better modeled as ScaledJob — each video gets its own pod that runs to completion, rather than a long-running worker that processes videos sequentially.

---

**Q4: How does KEDA scale to zero, and what are the trade-offs?**

When `minReplicaCount: 0` is set in a ScaledObject, KEDA monitors the trigger source directly. When the source returns an empty/zero value (empty queue, no consumer lag) and the `cooldownPeriod` has elapsed, KEDA bypasses HPA and sets the Deployment's replica count to 0. When a new event arrives, KEDA detects it on the next poll cycle (`pollingInterval`, default 30s) and scales the Deployment to 1 pod. Once running, HPA takes over for scaling beyond 1.

The trade-off is cold start latency. Scaling from 0 → 1 takes: polling interval (up to 30s) + pod scheduling time + container startup time = typically 30-60 seconds. For asynchronous workloads like batch processing or background jobs, this is acceptable. For user-facing request handlers, the cold start is usually unacceptable and you should keep `minReplicaCount: 1`.

---

**Q5: You have a Kafka consumer that is falling behind. How would you configure KEDA to autoscale it?**

Use the `kafka` scaler, which measures consumer group lag:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: kafka-consumer-scaler
spec:
  scaleTargetRef:
    name: kafka-consumer-deployment
  minReplicaCount: 1
  maxReplicaCount: 50
  triggers:
  - type: kafka
    metadata:
      bootstrapServers: kafka.kafka.svc:9092
      consumerGroup: my-consumer-group
      topic: orders
      lagThreshold: "100"      # target: 100 messages of lag per pod
      offsetResetPolicy: latest
```

With `lagThreshold: "100"`, KEDA calculates `desired replicas = current_lag / 100`. If lag is 500, KEDA targets 5 pods. If lag is 2000, it targets 20 pods (capped at maxReplicaCount). As consumers catch up and lag decreases, KEDA scales down. The `consumerGroup` is critical — KEDA measures lag for that specific consumer group, not the total topic offset.

---

**Q6: What is TriggerAuthentication and why is it a separate resource?**

`TriggerAuthentication` separates credential management from the scaling logic. Without it, you would embed secret references directly in the ScaledObject, which has several problems: different teams manage secrets vs scaling configurations, secrets cannot be easily reused across multiple ScaledObjects, and access control becomes harder.

With TriggerAuthentication, a security team can create and manage the authentication resource (which references Kubernetes Secrets), while developers just reference it by name in their ScaledObject. Multiple ScaledObjects can share one TriggerAuthentication. There is also `ClusterTriggerAuthentication` for cluster-scoped credentials that any namespace can reference. In 2024 on AWS EKS, the recommended approach is IRSA (IAM Roles for Service Accounts) — annotate the Kubernetes ServiceAccount with an IAM role ARN and KEDA uses that role automatically, with no static credentials at all.

---

**Q7: Can you have multiple triggers in one ScaledObject? How does KEDA resolve them?**

Yes. KEDA evaluates all triggers independently and scales to the **maximum** replica count recommended by any trigger. This is an OR logic: "scale if ANY trigger says so, to the highest value any trigger recommends."

Example: If your SQS trigger says "you need 8 pods" and your Prometheus error rate trigger says "you need 15 pods", KEDA targets 15 pods. The rationale is that multiple triggers represent different dimensions of load, and you need enough pods to handle all of them.

A common pattern is pairing a queue scaler (for throughput) with a Prometheus scaler (for error rate or latency) — the system scales up proactively for queue depth, but also defensively if latency or error rates spike.

---

**Q8: How does the `cooldownPeriod` field affect scaling behavior?**

`cooldownPeriod` controls how long KEDA waits after the trigger value drops to zero before scaling down to zero replicas. It does NOT affect scaling down between non-zero replica counts (that is controlled by the HPA's `stabilizationWindowSeconds`).

Example: `cooldownPeriod: 300` means KEDA waits 5 minutes after the queue empties before scaling to 0. This prevents rapid scale-to-zero/scale-up cycles if messages arrive in bursts with short gaps between them. Without it, your workers might constantly cold-start. The right value depends on your message arrival pattern — for steady queues, 60-120 seconds is often fine; for bursty queues, 300-600 seconds prevents thrashing.

---

**Q9: What is a ScaledJob's scaling strategy? What options exist?**

ScaledJob has a `scalingStrategy.strategy` field with three options:

- **`default`**: Creates new Jobs based on the difference between current pending messages and currently running jobs. Simple, predictable behavior.
- **`accurate`**: Queries the trigger more carefully to count pending-but-not-yet-running jobs. Better for high-throughput scenarios where the queue drains faster than new jobs start.
- **`eager`**: Creates Jobs as fast as possible when load spikes, accepting some over-provisioning. Use when minimizing latency matters more than efficiency.

The default strategy is correct for most batch use cases. Use `accurate` when you notice KEDA creating duplicate jobs, and `eager` when messages must be processed as immediately as possible regardless of cost.

---

**Q10: How would you use KEDA to only run pods during business hours?**

Use the `cron` scaler. It does not measure an external metric — it simply sets a desired replica count during a time window:

```yaml
triggers:
- type: cron
  metadata:
    timezone: America/Chicago
    start: "0 7 * * 1-5"      # 7 AM Mon-Fri
    end: "0 19 * * 1-5"       # 7 PM Mon-Fri
    desiredReplicas: "5"
```

Outside business hours, the trigger returns 0 and KEDA scales to `minReplicaCount` (which you set to 0 for scale-to-zero). During business hours, KEDA targets 5 replicas, and if you also have a queue scaler, it will scale beyond 5 if the queue demands it (KEDA takes the max of all triggers). This pattern is common for reporting workers, batch jobs, and internal tools that only need to run during work hours, saving significant compute cost overnight and on weekends.

---

**Q11: KEDA is described as a "CNCF graduated" project. What does that mean?**

CNCF (Cloud Native Computing Foundation) has three maturity levels: Sandbox, Incubating, and Graduated. Graduation is the highest level and indicates the project is production-ready, has a healthy community of contributors and adopters, follows security best practices, and meets CNCF's governance standards. Projects like Kubernetes, Prometheus, and Envoy are also graduated. KEDA graduated in 2023. For organizations evaluating third-party Kubernetes tooling, "CNCF graduated" is a meaningful signal that the project has been vetted, is not going to disappear, and is widely deployed in production. It does not mean it is part of core Kubernetes — it is still a separately installed add-on.

---

## 📂 Navigation

| | |
|---|---|
| Previous | [31_Gateway_API](../31_Gateway_API/) |
| Next | [33_Karpenter_Node_Autoprovisioning](../33_Karpenter_Node_Autoprovisioning/) |
| Up | [02_Kubernetes](../) |

**Files in this module:**
- [Theory.md](./Theory.md) — Concepts and architecture
- [Cheatsheet.md](./Cheatsheet.md) — Quick reference
- [Interview_QA.md](./Interview_QA.md) — Common interview questions
- [Code_Example.md](./Code_Example.md) — Working YAML examples
