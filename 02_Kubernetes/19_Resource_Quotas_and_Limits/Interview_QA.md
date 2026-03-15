# Resource Quotas and Limits — Interview Q&A

---

## Beginner

---

**Q1: What are resource requests and limits in Kubernetes?**

Every container in a pod can specify two resource numbers for CPU and memory:

A **request** is the amount of CPU or memory that the container is guaranteed. The Kubernetes scheduler uses requests to decide where to place a pod — it only schedules a pod on a node that has enough unallocated resources to satisfy all requests. A container is guaranteed to receive its requested resources.

A **limit** is the maximum the container is allowed to use. If a container exceeds its CPU limit, it is throttled (runs slower but keeps running). If it exceeds its memory limit, it is OOMKilled — the kernel terminates the process and Kubernetes restarts the container.

Think of requests as a reserved desk at work (guaranteed to you) and limits as the maximum desk space you are allowed to spread across (go beyond it and your stuff gets cleared off).

---

**Q2: What is OOMKilled?**

OOMKilled (Out Of Memory Killed) is what happens when a container exceeds its memory limit. The Linux kernel's Out-Of-Memory killer selects the process that went over the limit and terminates it with signal 9 (SIGKILL). Kubernetes sees the container exit and restarts it.

You can identify it with:
```bash
kubectl describe pod <name> -n <namespace>
# Look for: State: Terminated, Reason: OOMKilled, Exit Code: 137
```

Exit code 137 is always OOMKill (128 + 9 for SIGKILL). Common causes are a memory limit set too low, a memory leak in the application, or a spike in data being processed. The fix is to increase the memory limit, fix the leak, or reduce the amount of data the container loads at once.

---

**Q3: What is the difference between resource requests and limits — which one affects scheduling?**

Only **requests** affect scheduling. The scheduler looks at each node's total allocatable resources minus the sum of all existing pod requests, and only places the new pod on a node where there is enough headroom.

**Limits** do not affect scheduling. A pod with a CPU limit of 4 cores can be placed on a node with only 2 allocatable cores — as long as the request (e.g., 100m) fits. The limit only comes into play at runtime.

This means a pod could theoretically be scheduled on a node where its limit is unachievable. Memory limits are enforced immediately (OOMKill). CPU limits are enforced through throttling. Neither is a scheduling constraint.

---

**Q4: What are the three QoS classes and how are they assigned?**

Kubernetes automatically assigns every pod one of three QoS classes based on its resource configuration:

1. **Guaranteed**: Every container in the pod has both requests and limits set, and requests equal limits for both CPU and memory. These pods are evicted last under memory pressure.

2. **Burstable**: At least one container has a request or limit set, but they are not all equal (or not all set). These pods can use more resources than requested when available, but are evicted before Guaranteed pods under pressure.

3. **BestEffort**: No container in the pod has any requests or limits. These pods use whatever is left over and are evicted first under memory pressure.

You cannot set the QoS class directly — Kubernetes derives it from your resource spec. For production, always set requests and limits to get at least Burstable class.

---

**Q5: What is CPU throttling?**

CPU throttling happens when a container tries to use more CPU than its limit. The Linux kernel's CFS (Completely Fair Scheduler) enforces the limit by pausing the container's CPU access after its burst quota is used up.

Unlike OOMKill, the container is not terminated — it just runs more slowly. The container continues processing, but latency increases. An application that normally handles 100 requests per second might handle only 20 when severely throttled.

CPU throttling is often invisible without monitoring. Signs include: high response latency with low reported CPU utilization, or the Prometheus metric `container_cpu_cfs_throttled_seconds_total` increasing steadily.

---

## Intermediate

---

**Q6: What are QoS classes and how do they affect pod eviction?**

QoS (Quality of Service) classes determine which pods are evicted first when a node runs low on memory. Kubernetes has three classes:

- **BestEffort** (no resources set): evicted first. These pods have made no promises about their resource needs, so Kubernetes has no information to protect them.
- **Burstable** (partial or unequal requests/limits): evicted second. Among Burstable pods, those using the most memory above their requests are evicted first.
- **Guaranteed** (requests equal limits, all containers, CPU and memory): evicted last. These pods have accurate resource declarations and are treated as stable workloads.

For a payment service or any customer-facing application, use Guaranteed class by setting requests equal to limits. This ensures the pod survives node memory pressure caused by poorly-configured neighbor pods.

---

**Q7: What is a LimitRange vs a ResourceQuota? When do you use each?**

A **LimitRange** governs individual containers and pods within a namespace. It sets default requests and limits (so pods without resource specs get sane defaults), and enforces minimum and maximum values per container. It is applied per-pod at admission time.

A **ResourceQuota** governs the entire namespace's total aggregate consumption. It caps the total CPU requests, memory requests, number of pods, PVCs, services, and other objects across all pods combined. It enforces namespace-level budgets.

**When to use each**: Use LimitRange to ensure every pod in the namespace has meaningful defaults and to prevent any single container from requesting enormous resources. Use ResourceQuota to give each team or namespace a fixed budget that cannot be exceeded regardless of how many pods they run.

They are complementary — use both together. LimitRange ensures good individual pod hygiene; ResourceQuota ensures the team stays within their infrastructure budget.

---

**Q8: How does CPU throttling work technically?**

Kubernetes sets CPU limits using Linux CFS (Completely Fair Scheduler) bandwidth control. The kernel divides time into periods (default 100ms). Each container is allocated a quota of CPU time within each period proportional to its limit. For example, a container with a 500m limit gets 50ms of CPU time per 100ms period.

If the container exhausts its 50ms quota before the 100ms period ends, it is paused ("throttled") for the remainder of the period. The next period, it gets its quota again. This repeating pause-and-resume creates the latency spikes that characterize CPU throttling.

The metric `container_cpu_cfs_throttled_periods_total` in Prometheus counts how many times this throttling occurred. A ratio of throttled to total periods above ~25% is a sign that CPU limits need to be raised.

---

**Q9: What happens when a namespace exceeds its ResourceQuota?**

When a pod creation request would push the namespace over its ResourceQuota, the Kubernetes API server rejects the request immediately at admission time. The developer sees an error like:

```
Error from server (Forbidden): error when creating "deployment.yaml":
pods "my-app-7d9f4b" is forbidden: exceeded quota: team-quota,
requested: requests.cpu=500m, used: requests.cpu=9.7, limited: requests.cpu=10
```

The pod is simply not created. No partial creation occurs. The developer must either reduce their resource requests, delete existing resources to free up quota, or ask a cluster administrator to increase the quota limit.

This rejection is different from a pod being scheduled and failing — it is a hard API-level gate. `kubectl apply` or `kubectl create` will fail with this error.

---

## Advanced

---

**Q10: How do you right-size container resource requests and limits?**

Right-sizing is an iterative process:

1. **Start with VPA in `Off` mode**: Deploy the application and let the Vertical Pod Autoscaler observe actual resource usage over several days under representative load. Run `kubectl describe vpa <name>` to see recommendations for each container.

2. **Use `kubectl top pods --containers`**: Observe actual CPU and memory usage under different load scenarios (normal, peak, burst).

3. **Set requests slightly above average usage**: Requests should reflect typical usage — not peak, not minimum. This gives the scheduler accurate placement information.

4. **Set limits at peak usage plus a 20-30% buffer**: Limits should allow for traffic spikes without triggering OOMKill or excessive throttling. For memory, be more generous — OOMKill is more disruptive than CPU throttling.

5. **Monitor in production**: Set Prometheus alerts for `container_cpu_cfs_throttled_seconds_total` (CPU throttling) and `kube_pod_container_status_last_terminated_reason{reason="OOMKilled"}` (memory kills). Adjust limits when alerts fire.

---

**Q11: What tools help with resource recommendations?**

Several tools automate or assist with resource right-sizing:

- **VPA (Vertical Pod Autoscaler)** in `Off` mode: The most integrated option. Runs inside Kubernetes and generates per-container recommendations based on observed usage history. `kubectl describe vpa <name>` shows the recommendations. Use `Off` mode in production to get recommendations without automatic evictions.

- **Goldilocks** (by Fairwinds): An open-source tool that runs VPA in recommendation mode across all namespaces and presents the results in a web dashboard. Great for visualizing right-sizing opportunities across a whole cluster.

- **Robusta KRR** (Kubernetes Resource Recommender): An open-source CLI tool that connects to Prometheus and generates resource recommendations based on historical metrics. Does not require VPA to be installed.

- **Prometheus + Grafana**: Manual approach — build dashboards showing actual CPU/memory usage vs requests/limits per container. Identify containers that are consistently over-provisioned or under-provisioned.

- **Cloud provider tools**: AWS Compute Optimizer, GKE Autopilot suggestions, and Azure Advisor can recommend resource changes for managed Kubernetes workloads.

---

**Q12: What happens when a namespace exceeds its ResourceQuota for object counts (not just CPU/memory)?**

ResourceQuota can limit not just CPU and memory, but the count of Kubernetes objects:

```yaml
pods: "50"
services: "20"
secrets: "50"
configmaps: "50"
services.loadbalancers: "5"
```

When any of these counts are exceeded, the API server rejects new object creation of that type with the same `exceeded quota` error. This prevents accidental runaway object creation — for example:

- A CronJob with a bug that creates thousands of Jobs before anyone notices
- A Helm chart that creates dozens of Secrets per install, filling up etcd
- A load balancer for every microservice that inflates cloud costs

Object count quotas are especially important for limiting expensive resources like LoadBalancer services (which create cloud load balancers that cost money per hour) and PersistentVolumeClaims (which provision real storage). They are also useful as a safety net against automation bugs.

---

**Q13: A pod is being OOMKilled repeatedly. Walk through how you would investigate and fix it.**

Step-by-step investigation:

1. **Confirm it is OOMKilled**:
   ```bash
   kubectl describe pod <name> -n <namespace>
   # Look for: Reason: OOMKilled, Exit Code: 137
   ```

2. **Check logs from the previous run** (before the kill):
   ```bash
   kubectl logs <pod> --previous
   ```
   Look for memory-related errors, queries loading large datasets, or unbounded caches.

3. **Check current memory usage**:
   ```bash
   kubectl top pod <name> --containers
   ```
   Compare usage to the configured limit.

4. **Check the current limit**:
   ```bash
   kubectl get pod <name> -o jsonpath='{.spec.containers[0].resources}'
   ```

5. **Determine the cause**:
   - If usage steadily increases over time: likely a memory leak. Fix the code.
   - If usage spikes on specific requests or operations: the operation loads too much data at once. Add pagination, streaming, or chunking.
   - If usage is consistently near the limit but not leaking: the limit is simply too low. Increase it.

6. **Fix**:
   - Increase the memory limit in the Deployment spec.
   - Use VPA in `Off` mode for a week to get a data-driven recommendation.
   - If the app is genuinely leaking memory, instrument it with a memory profiler (pprof for Go, heapdump for JVM, memory-profiler for Python).

---

## 📂 Navigation

⬅️ **Prev:** [HPA/VPA Autoscaling](../18_HPA_VPA_Autoscaling/Interview_QA.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Network Policies](../20_Network_Policies/Theory.md)

| | Link |
|---|---|
| Theory | [Theory.md](./Theory.md) |
| Cheatsheet | [Cheatsheet.md](./Cheatsheet.md) |
| Module Home | [19_Resource_Quotas_and_Limits](../) |
