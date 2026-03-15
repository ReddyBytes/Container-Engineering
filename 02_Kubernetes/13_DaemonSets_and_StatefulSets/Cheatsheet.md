# DaemonSets and StatefulSets Cheatsheet

## Core Differences

| Feature | DaemonSet | StatefulSet | Deployment |
|---------|-----------|-------------|------------|
| Pod count | One per node | Fixed, ordered | Flexible replicas |
| Pod names | Random | Predictable (pod-0, pod-1) | Random |
| Storage | Shared or host-path | Per-pod PVC (stable) | Shared PVC |
| DNS | Normal | Stable per-pod DNS | Normal |
| Startup order | No | Ordered (0, 1, 2...) | No |
| Use case | Node agents | Stateful apps | Stateless apps |

---

## kubectl Commands

```bash
# --- DaemonSet Commands ---

# List all DaemonSets in a namespace
kubectl get daemonsets -n <namespace>
kubectl get ds -n <namespace>          # short form

# List DaemonSets across all namespaces
kubectl get ds -A

# Describe a DaemonSet
kubectl describe ds <name> -n <namespace>

# Check DaemonSet rollout status
kubectl rollout status ds/<name> -n <namespace>

# See which nodes are running (or missing) the DaemonSet pod
kubectl get pods -o wide -l <daemonset-selector> -n <namespace>

# Manually trigger a rollout (after editing)
kubectl rollout restart ds/<name> -n <namespace>

# Rollback a DaemonSet
kubectl rollout undo ds/<name> -n <namespace>

# Pause a DaemonSet rollout
kubectl rollout pause ds/<name> -n <namespace>

# Resume a DaemonSet rollout
kubectl rollout resume ds/<name> -n <namespace>

# View DaemonSet rollout history
kubectl rollout history ds/<name> -n <namespace>

# Prevent a DaemonSet from scheduling on specific node (using node taint)
kubectl taint nodes <node-name> key=value:NoSchedule

# --- StatefulSet Commands ---

# List all StatefulSets
kubectl get statefulsets -n <namespace>
kubectl get sts -n <namespace>         # short form

# Describe a StatefulSet
kubectl describe sts <name> -n <namespace>

# Check StatefulSet rollout status
kubectl rollout status sts/<name> -n <namespace>

# Scale a StatefulSet
kubectl scale sts <name> --replicas=5 -n <namespace>

# Restart a StatefulSet (rolling restart)
kubectl rollout restart sts/<name> -n <namespace>

# Rollback a StatefulSet
kubectl rollout undo sts/<name> -n <namespace>

# List pods belonging to a StatefulSet (ordered by name)
kubectl get pods -l app=<label> -n <namespace> --sort-by=.metadata.name

# List PVCs created by a StatefulSet (VolumeClaimTemplates)
kubectl get pvc -n <namespace> -l app=<label>

# Exec into a specific StatefulSet pod
kubectl exec -it <sts-name>-0 -n <namespace> -- bash

# Delete a StatefulSet WITHOUT deleting its pods (orphan)
kubectl delete sts <name> --cascade=orphan -n <namespace>

# Delete a StatefulSet AND its pods
kubectl delete sts <name> -n <namespace>

# WARNING: PVCs are NOT deleted automatically — clean up manually:
kubectl delete pvc -l app=<label> -n <namespace>

# --- Checking Pod DNS for StatefulSets ---
# From inside the cluster, test DNS resolution:
# nslookup <sts-name>-0.<service-name>.<namespace>.svc.cluster.local

# --- Headless Service ---

# Verify a service is headless
kubectl get svc <name> -n <namespace> -o jsonpath='{.spec.clusterIP}'
# Output: None  (if headless)

# --- Node Management for DaemonSets ---

# Add a label to a node (for nodeSelector matching)
kubectl label nodes <node-name> role=worker

# Remove a label from a node
kubectl label nodes <node-name> role-

# Check which nodes have a specific label
kubectl get nodes -l role=worker

# Drain a node (DaemonSet pods are not evicted by default)
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data
```

---

## DaemonSet Update Strategies

```yaml
spec:
  updateStrategy:
    type: RollingUpdate      # or OnDelete
    rollingUpdate:
      maxUnavailable: 1      # max nodes updating at once
```

## StatefulSet Update Strategies

```yaml
spec:
  updateStrategy:
    type: RollingUpdate      # or OnDelete
    rollingUpdate:
      partition: 2           # only update pods with ordinal >= 2 (canary)
```

---

## StatefulSet Pod DNS Pattern

```
<pod-name>.<service-name>.<namespace>.svc.cluster.local
postgres-0.postgres.default.svc.cluster.local
postgres-1.postgres.default.svc.cluster.local
```

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Theory.md](./Theory.md) |
| Interview Q&A | [Interview_QA.md](./Interview_QA.md) |
| Code Example | [Code_Example.md](./Code_Example.md) |
| Module Home | [13_DaemonSets_and_StatefulSets](../) |
