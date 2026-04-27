# Module 08 — Interview Q&A: Namespaces

---

**Q1: What is a Kubernetes namespace and what problem does it solve?**

A namespace is a virtual partition within a Kubernetes cluster that provides scoped resource
isolation. It solves several problems:
- **Name conflicts**: two teams can both have a deployment named "backend" in different namespaces
- **Access control**: RBAC permissions can be scoped to a namespace (give team A access to
  their namespace without touching team B's)
- **Resource management**: ResourceQuotas limit how much CPU/memory a namespace can consume
- **Organization**: logically separate environments (dev/staging) or teams on one cluster

---

**Q2: What are the four default namespaces and what are they for?**

- `default`: where resources go when you don't specify a namespace
- `kube-system`: Kubernetes system components (CoreDNS, kube-proxy, metrics-server, etcd)
- `kube-public`: publicly readable resources — contains the `cluster-info` ConfigMap that
  provides cluster discovery information, readable even without authentication
- `kube-node-lease`: stores lightweight Lease objects that kubelet updates as heartbeats.
  The Node controller watches these to detect node failures faster than polling node status.

---

**Q3: How do you access a service in a different namespace?**

Use the fully qualified DNS name format:
`<service-name>.<namespace>.svc.cluster.local`

For example, to call the `api` service in the `backend` namespace from a pod in any namespace:
```
http://api.backend.svc.cluster.local:8080
```

Within the same namespace, you can use just the service name:
```
http://api:8080
```

By default there are no network restrictions between namespaces — any pod can call any service.
Network Policies must be applied to restrict cross-namespace traffic.

---

**Q4: What is a ResourceQuota and how does it work?**

A ResourceQuota is a namespaced object that sets hard limits on the total resources that can
be consumed within a namespace. Once a quota is applied, Kubernetes enforces it for all
resource creation and updates. If a new pod would exceed the namespace's quota, the creation
is rejected with a "forbidden: exceeded quota" error.

ResourceQuota can limit: number of pods, total CPU requests and limits, total memory requests
and limits, number of secrets, configmaps, services, PVCs, and more.

One important side effect: once a quota is set, ALL pods in the namespace must have resource
requests and limits specified — otherwise they are rejected.

---

**Q5: What is the difference between ResourceQuota and LimitRange?**

**ResourceQuota** sets aggregate limits for the entire namespace — "this namespace can use
at most 8 CPUs in total." It doesn't care about individual pod sizes.

**LimitRange** sets constraints for individual pods and containers within a namespace:
- Default requests and limits (applied to pods that don't specify any)
- Minimum and maximum request/limit values (rejects pods outside the range)

They work together: LimitRange ensures every pod has resource requests set (so ResourceQuota
can account for them), and ResourceQuota ensures the namespace doesn't collectively exceed budget.

---

**Q6: What Kubernetes resources are NOT namespaced?**

Cluster-scoped resources exist once per cluster, not per namespace:
- `Node`: physical or virtual machines
- `PersistentVolume`: storage objects provisioned for the cluster
- `StorageClass`: describes storage types available cluster-wide
- `ClusterRole` and `ClusterRoleBinding`: RBAC rules that span namespaces
- `Namespace` itself
- `IngressClass`: defines which ingress controller handles ingress resources
- `CustomResourceDefinition (CRD)`: defines schemas for custom resources

Check with: `kubectl api-resources --namespaced=false`

---

**Q7: What happens when you delete a namespace?**

Kubernetes immediately sets the namespace to `Terminating` status and begins deleting all
resources inside it. The deletion propagates to all namespaced resources: pods, deployments,
services, secrets, configmaps, PVCs, etc. Note that PersistentVolumes (which are cluster-scoped)
are not deleted, but PersistentVolumeClaims (which are namespaced) are.

If any resource has a finalizer that prevents deletion (common with custom resources, Istio
resources, or stuck operators), the namespace can get stuck in `Terminating` indefinitely until
the finalizer is resolved.

---

**Q8: Can you rename a namespace?**

No. Namespace names are immutable. If you need to rename a namespace, you must:
1. Create a new namespace with the desired name
2. Migrate all resources to the new namespace (redeploy deployments, recreate configmaps/secrets,
   re-bind PVCs, update service references)
3. Delete the old namespace

This is one reason to choose namespace names carefully upfront.

---

**Q9: How do you set a default namespace so you don't have to type -n every time?**

```bash
kubectl config set-context --current --namespace=my-namespace
```

This modifies the active context in `~/.kube/config` to use the specified namespace as default
for all commands. To check the current default namespace:
```bash
kubectl config get-contexts | grep "*"
```

The tool `kubens` (from kubectx project) provides an interactive way to switch namespaces.

---

**Q10: Should you use one namespace per environment or one cluster per environment?**

Both approaches are used in practice, with trade-offs:

**Namespace-based separation** (dev, staging, prod in same cluster):
- Lower cost (one cluster)
- Potential noisy-neighbor risk (staging workloads affecting prod)
- Requires strict RBAC and network policies
- Good for small teams or cost-sensitive organizations

**Cluster-based separation** (dedicated cluster per environment):
- True isolation (a staging meltdown can't affect prod)
- Higher cost
- More operational overhead (multiple clusters to manage/upgrade)
- Industry standard for regulated industries or large organizations

Most mature organizations use separate clusters for production with shared clusters for
dev/staging, and use namespaces for team/service isolation within each cluster.

---

**Q11: What is a namespace's relationship to network isolation?**

By default, namespaces provide NO network isolation. Any pod in any namespace can send traffic
to any other pod or service in any namespace. Namespaces are a management boundary, not a
network boundary.

To add network isolation, you must apply **Network Policies** (module 20). Network Policies
are namespaced resources that define which pods/namespaces/IP ranges are allowed to connect.
Popular CNI plugins (Calico, Cilium) enforce these policies at the kernel level.

---

**Q12: How do you list all resources across all namespaces?**

```bash
# Specific resource type across all namespaces
kubectl get pods -A
kubectl get pods --all-namespaces

# Multiple resource types
kubectl get pods,services,deployments -A

# All resource types (slow but comprehensive)
kubectl get all -A
```

Note: `kubectl get all` doesn't actually get ALL resource types — it only shows pods,
services, deployments, replicasets, statefulsets, daemonsets, jobs, and cronjobs.
Custom resources and many built-in types (configmaps, secrets, pvcs) are excluded.

---

## 📂 Navigation

| File | Description |
|------|-------------|
| [Theory.md](./Theory.md) | Namespaces explained |
| [Cheatsheet.md](./Cheatsheet.md) | Quick reference commands |
| [Interview_QA.md](./Interview_QA.md) | You are here — interview questions |

---

⬅️ **Prev:** [ConfigMaps and Secrets](../07_ConfigMaps_and_Secrets/Interview_QA.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Ingress](../09_Ingress/Theory.md)
