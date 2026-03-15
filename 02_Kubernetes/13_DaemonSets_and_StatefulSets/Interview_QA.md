# DaemonSets and StatefulSets — Interview Q&A

---

**Q1: What is a DaemonSet and when would you use it?**

A DaemonSet ensures that exactly one copy of a pod runs on every (or selected) node in the cluster. When new nodes join, the pod is automatically scheduled on them. When nodes are removed, the pods are garbage collected. DaemonSets are used for infrastructure concerns that must be present on every node: log collectors (Fluentd, Fluent Bit), monitoring agents (Prometheus Node Exporter, Datadog Agent), network plugins (Calico, Cilium), storage drivers, and security agents (Falco).

---

**Q2: What is a StatefulSet and how is it different from a Deployment?**

A StatefulSet manages pods that require stable identity and state. Unlike Deployments, StatefulSets provide:
1. **Stable pod names**: pods are named `<name>-0`, `<name>-1`, not random suffixes
2. **Stable DNS**: each pod gets a predictable hostname via a headless service
3. **Stable storage**: each pod gets its own PVC from a VolumeClaimTemplate that persists across pod rescheduling
4. **Ordered operations**: pods start in order (0 before 1 before 2) and terminate in reverse order

Deployments are for stateless workloads where any replica is interchangeable. StatefulSets are for stateful workloads where each replica has a distinct role (primary, replica) and its own data.

---

**Q3: What is a headless service and why do StatefulSets need one?**

A headless service has `clusterIP: None`. Unlike regular services that provide a single virtual IP (VIP) and load-balance traffic, a headless service returns the individual pod IPs directly from DNS. StatefulSets need a headless service because clients often need to address specific pods — for example, always connecting to `postgres-0` (the primary) for writes and distributing reads across `postgres-1` and `postgres-2`. The headless service enables the stable DNS name pattern `<pod>.<service>.<namespace>.svc.cluster.local`.

---

**Q4: What happens to PVCs when you delete a StatefulSet?**

PVCs created by a StatefulSet's `volumeClaimTemplates` are NOT automatically deleted when the StatefulSet is deleted. This is intentional — it protects data from accidental loss. You must manually delete PVCs if you intend to clean up the storage. This is a common operational gotcha: teams delete a StatefulSet thinking they are doing a clean teardown, but GB or TB of storage volumes remain and continue incurring cost.

---

**Q5: What is the `partition` field in a StatefulSet update strategy?**

The `partition` field in a StatefulSet's RollingUpdate strategy enables canary-style rollouts. Setting `partition: N` means only pods with ordinal >= N will be updated to the new version. Pods with ordinal < N keep the old version. For example, in a 3-replica StatefulSet with `partition: 2`, only pod-2 gets the new version. This lets you test the new version on one replica before committing to a full rollout.

---

**Q6: How does a DaemonSet handle node taints?**

By default, DaemonSets do NOT schedule on tainted nodes. To schedule on tainted nodes (like control-plane nodes), add a matching `toleration` to the DaemonSet pod spec. Kubernetes system DaemonSets like `kube-proxy` include tolerations for standard control-plane taints like `node-role.kubernetes.io/control-plane:NoSchedule`. You can also use `nodeSelector` to limit a DaemonSet to only nodes with specific labels — useful for running GPU monitoring only on GPU nodes.

---

**Q7: Can you run only one DaemonSet pod on a subset of nodes?**

Yes, in two ways:
1. **nodeSelector**: Add a label to target nodes and use `nodeSelector` in the DaemonSet spec. Only nodes with matching labels will host the pod.
2. **nodeName**: Directly specify nodes (rarely used in practice).
3. **Affinity rules**: More expressive node selection using `nodeAffinity` in the pod spec.

This is useful for running a specialized DaemonSet (e.g., GPU monitoring) only on GPU-enabled nodes labeled `gpu: "true"`.

---

**Q8: What is the difference between `OnDelete` and `RollingUpdate` for DaemonSets?**

`RollingUpdate` (default) automatically updates DaemonSet pods one node at a time when the spec changes — controlling how many nodes can be updating simultaneously via `maxUnavailable`. `OnDelete` does nothing automatically; DaemonSet pods are only updated when they are manually deleted. `OnDelete` is useful when you need precise control over which nodes are updated and when — for example, coordinating DaemonSet updates with node maintenance windows.

---

**Q9: Why should you prefer managed database services over running databases in StatefulSets?**

Running production databases in StatefulSets requires operational expertise that most teams underestimate:
- Backup and restore requires custom automation (CronJobs, scripts)
- Failover requires careful coordination (which pod is primary?)
- Upgrades require careful management of ordinal order and data compatibility
- Storage management, IOPS provisioning, and snapshot management are manual
- Monitoring and alerting require additional operator setup

Managed services (AWS RDS, Cloud SQL, Azure Database) handle all of this automatically. StatefulSets are appropriate for teams with deep database expertise, specific compliance requirements, or infrastructure-as-code where a managed service isn't available — such as self-hosted Kafka, ZooKeeper, or Elasticsearch clusters.

---

**Q10: How does a StatefulSet ensure pods start in order?**

A StatefulSet's controller only creates pod N+1 after pod N is in Running and Ready state. This is enforced by the `podManagementPolicy` setting. The default is `OrderedReady`. You can set `podManagementPolicy: Parallel` to bypass this and start all pods simultaneously, which is faster for apps that don't actually need startup ordering but still want stable identities.

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Theory.md](./Theory.md) |
| Cheatsheet | [Cheatsheet.md](./Cheatsheet.md) |
| Code Example | [Code_Example.md](./Code_Example.md) |
| Module Home | [13_DaemonSets_and_StatefulSets](../) |
