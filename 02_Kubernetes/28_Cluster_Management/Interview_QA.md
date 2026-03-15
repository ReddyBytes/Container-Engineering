# Module 28 — Cluster Management Interview Q&A

---

## Beginner Questions

---

**Q1: How do you upgrade a Kubernetes cluster?**

**Answer:**

The most important rule: **upgrade the control plane before upgrading worker nodes.**

For kubeadm-based clusters, the process is:

1. **Upgrade kubeadm** on the control plane node
2. Run `kubeadm upgrade plan` to see what's available
3. Run `kubeadm upgrade apply v1.30.0` — this upgrades kube-apiserver, kube-controller-manager, kube-scheduler
4. **Upgrade kubelet and kubectl** on the control plane node, restart kubelet
5. For each worker node, one at a time:
   - `kubectl cordon <worker>` — no new pods
   - `kubectl drain <worker>` — evict existing pods
   - Install new kubeadm, run `kubeadm upgrade node`
   - Install new kubelet and kubectl, restart kubelet
   - `kubectl uncordon <worker>` — return to service

For managed clusters (EKS, GKE, AKS), you use the cloud provider's CLI or console — they handle control plane upgrades for you and have automated node group upgrade options.

Key constraint: Kubernetes skew policy allows workers to be at most 2 minor versions behind the API server, but never ahead. So always upgrade control plane first.

---

**Q2: What is `kubectl drain` and when do you use it?**

**Answer:**

`kubectl drain` evicts all running pods from a node and marks the node as unschedulable (cordons it). It's the step you perform before taking a node out of service for maintenance.

```bash
kubectl drain worker-03 \
  --ignore-daemonsets \       # DaemonSet pods can't be evicted — skip them
  --delete-emptydir-data \    # allow eviction of pods using emptyDir storage
  --grace-period=120          # give pods 120 seconds to shut down gracefully
```

Key behaviors:
- Drain respects **PodDisruptionBudgets** — it won't evict a pod if doing so would drop below the PDB's minimum availability
- DaemonSet pods are skipped by default (they'd just be recreated)
- Evicted pods are rescheduled by their Deployment/ReplicaSet controllers on other nodes

After maintenance, `kubectl uncordon <node>` returns the node to schedulable state. Running drain implies cordon, so you don't need to cordon separately before draining.

---

**Q3: What is the difference between `kubectl cordon` and `kubectl drain`?**

**Answer:**

**`kubectl cordon <node>`**: marks the node as unschedulable (adds the `node.kubernetes.io/unschedulable:NoSchedule` taint). New pods will not be scheduled there. Existing pods keep running.

**`kubectl drain <node>`**: evicts all running pods from the node AND cordons it. After drain, the node is both unschedulable and empty (except DaemonSet pods).

Use cordon when: you want to prevent new pods from landing but don't need existing pods gone yet.

Use drain when: you need the node completely empty — for hardware maintenance, OS upgrade, or node replacement.

After both operations: `kubectl uncordon <node>` makes the node schedulable again.

---

## Intermediate Questions

---

**Q4: How do you backup etcd and why is it critical?**

**Answer:**

etcd stores every piece of Kubernetes cluster state: all Pods, Deployments, Services, Secrets, ConfigMaps, RBAC rules, CRDs, and more. If etcd is lost without a backup, **the entire cluster configuration is permanently gone**. Worker nodes lose their assignments and the cluster effectively dies.

Taking a snapshot:

```bash
ETCDCTL_API=3 etcdctl snapshot save /backup/etcd.db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key

# Verify it's valid
ETCDCTL_API=3 etcdctl snapshot status /backup/etcd.db --write-out=table
```

Best practices:
- Schedule automated hourly backups (CronJob or external automation)
- Copy backups off the control plane node to external storage (S3, GCS)
- Keep multiple generations (7+ days)
- Periodically test restores in a non-production environment

On managed clusters (EKS, GKE, AKS), the cloud provider manages etcd — use Velero for application-level backup instead.

---

**Q5: What is node cordon vs drain — and what is uncordon?**

**Answer:**

These three commands form the standard node maintenance lifecycle:

| Command | Effect | When to use |
|---------|--------|-------------|
| `kubectl cordon <node>` | Marks node unschedulable. New pods won't land here. Existing pods keep running. | Before maintenance that requires no new pods |
| `kubectl drain <node>` | Evicts all pods AND cordons. Node becomes empty. | Before maintenance requiring an empty node |
| `kubectl uncordon <node>` | Removes unschedulable mark. Node accepts new pods again. | After maintenance is complete |

Drain respects PodDisruptionBudgets — if evicting a pod would violate the PDB, drain waits or fails. Use `--timeout=300s` to fail after 5 minutes instead of waiting indefinitely.

---

**Q6: How do you rotate TLS certificates in a kubeadm cluster?**

**Answer:**

kubeadm certificates expire in 1 year by default. If they expire, the API server becomes inaccessible.

```bash
# Check when each certificate expires
kubeadm certs check-expiration

# Renew all certificates at once
kubeadm certs renew all

# Renew a specific certificate
kubeadm certs renew apiserver
```

After renewal, the control plane components need to restart to load the new certificates. For kubeadm static pods, you can kill the process — kubelet will restart it automatically:

```bash
kill $(pidof kube-apiserver)
kill $(pidof kube-controller-manager)
kill $(pidof kube-scheduler)
```

Also update kubeconfig files: `kubeadm init phase kubeconfig all` regenerates them.

**Prevention tip**: running `kubeadm upgrade` automatically renews certificates as part of the upgrade process. If you upgrade at least once per year, certificates stay current without manual rotation.

---

**Q7: What happens to running workloads when the Kubernetes API server goes down?**

**Answer:**

The API server going down does NOT kill running pods. Here's what happens to each component:

- **kubelet**: continues running and monitoring pods based on last known state. If a container crashes, kubelet restarts it. Does not need the API server for this.
- **kube-proxy**: keeps existing iptables/IPVS rules. Existing network traffic continues routing correctly.
- **Controller-manager**: offline — no scaling, no healing failed deployments, no processing of new events
- **Scheduler**: offline — no new pods can be placed
- **kubectl**: all commands fail — you cannot view or change anything
- **HPA/VPA**: cannot scale — they depend on the API server

In summary: **existing workloads keep running, but you cannot make any changes and failed replicas won't be replaced** until the API server recovers.

For HA control planes (3 API server instances behind a load balancer), the other instances take over automatically. For single-control-plane clusters, restoring etcd from backup is your recovery path.

---

**Q8: How does etcd quorum work and what happens if you lose it?**

**Answer:**

etcd uses the Raft consensus protocol: a write is only committed when a majority of etcd members acknowledge it. This majority is called the quorum.

| etcd members | Quorum required | Tolerated failures |
|-------------|----------------|-------------------|
| 1 | 1 | 0 (no HA) |
| 3 | 2 | 1 |
| 5 | 3 | 2 |

If quorum is lost (too many members fail), etcd enters read-only mode: existing cluster state is readable but no writes are accepted. The Kubernetes API server cannot process any mutating requests — creates, updates, and deletes all fail.

To recover from quorum loss:
1. If enough members can be restored (hardware repaired, VMs restarted), etcd may recover automatically once quorum is re-established
2. For severe cases: restore from snapshot to a new etcd cluster using `etcdctl snapshot restore`
3. For single-member etcd (development only): the `--force-new-cluster` flag can revive a single-member cluster from an existing data directory

Always run 3 or 5 etcd members in production. Never run 2 or 4 — even numbers don't improve fault tolerance but do increase write latency.

---

## Advanced Questions

---

**Q9: What is a zero-downtime cluster upgrade strategy?**

**Answer:**

Zero-downtime upgrades require both application design and operational process:

**Application requirements:**
- `replicas >= 2` for every Deployment — single-replica apps go down during node drain
- Proper `PodDisruptionBudgets` — prevents drain from taking down too many replicas at once
- `readinessProbe` and `livenessProbe` — ensures traffic only goes to healthy instances
- Graceful shutdown handling — containers handle SIGTERM and finish in-flight requests

**Upgrade process:**
1. Upgrade control plane with a HA API server setup (3 replicas behind a load balancer) — rolling restart of API servers, zero downtime
2. Upgrade worker nodes one at a time:
   - Cordon + drain (PDBs ensure minimum availability is maintained)
   - Upgrade node
   - Uncordon + verify workloads reschedule and become Ready before moving to next node
3. Monitor at each step — check `kubectl get pods -A` for pods stuck in Pending or CrashLoopBackOff

**For managed clusters**: EKS, GKE, and AKS support managed node group upgrades that do this automatically — they surge a new node, drain the old one, and terminate it, respecting PDBs.

**Pitfalls:**
- Not setting PDBs — drain can evict all replicas of a service simultaneously
- Skipping more than 1 minor version in one upgrade — not supported, must upgrade one minor at a time
- Not leaving time between worker node upgrades — rush all nodes at once and you may lose quorum

---

**Q10: How do you handle etcd quorum loss in a production cluster?**

**Answer:**

Etcd quorum loss is a serious incident. Response depends on severity:

**Scenario 1: One member failed in a 3-member cluster (quorum maintained)**

The cluster continues functioning. Add a new member to restore redundancy:
```bash
# Remove the failed member
etcdctl member remove <member-id>
# Add a new member
etcdctl member add <new-name> --peer-urls=https://<new-ip>:2380
# Then join the new member to the cluster
```

**Scenario 2: Two members failed in a 3-member cluster (quorum lost)**

etcd is read-only. Options:
1. **Restore the failed members**: if VMs can be restarted, etcd may recover with existing data
2. **Restore from snapshot**: the cleanest recovery path

```bash
# Stop API server on all control plane nodes
# Restore snapshot on each etcd member
ETCDCTL_API=3 etcdctl snapshot restore /backup/etcd.db \
  --name <member-name> \
  --initial-cluster <member1>=https://<ip1>:2380,<member2>=... \
  --initial-advertise-peer-urls https://<my-ip>:2380 \
  --data-dir /var/lib/etcd-restore

# Update etcd manifests to use --initial-cluster-state=existing
# Restart API servers
```

**Prevention:**
- Automate hourly etcd snapshots to external storage
- Run 3-member etcd across 3 different AZs — a single AZ failure won't lose quorum
- Monitor etcd leader elections and DB size in Grafana
- Alert at 75% of the 8GB storage limit — run `etcdctl defrag` before hitting it

---

**Q11: How do multi-cluster setups work with GitOps?**

**Answer:**

GitOps multi-cluster management uses Git as the single source of truth for what should be deployed on every cluster. The workflow:

1. All cluster configuration (application manifests, Helm values, Kustomize overlays) lives in Git
2. A GitOps agent (ArgoCD or Flux) runs in each cluster (or in a central management cluster)
3. The agent continuously reconciles the cluster state with the desired state in Git
4. Any drift — someone manually applies a change to the cluster — is automatically corrected

**ArgoCD multi-cluster approach:**

A single ArgoCD instance in a management cluster manages multiple target clusters:

```bash
# Register target clusters
argocd cluster add production-us-east
argocd cluster add production-eu-west

# Create an Application targeting a specific cluster
argocd app create my-app \
  --repo https://github.com/myorg/app \
  --path charts/myapp \
  --dest-server https://production-us-east.example.com \
  --dest-namespace production
```

**App of Apps pattern**: a parent ArgoCD Application that itself deploys other Applications. One repo entry manages 50+ clusters.

**Flux multi-cluster approach:**

Flux uses a "hub and spoke" model — run Flux on every cluster, each pointing to its own subdirectory in the Git repo:

```
git-repo/
  clusters/
    production-us-east/
      apps.yaml
      infrastructure.yaml
    production-eu-west/
      apps.yaml
```

**Benefits:**
- Every change is auditable (Git history)
- Cluster state can be recovered by re-running the GitOps reconciliation
- Environment differences (dev/staging/prod) are explicit in Git
- Rollback = revert a commit

**Challenges:**
- Secrets management — don't commit secrets to Git (use Sealed Secrets, External Secrets Operator, or Vault)
- Bootstrapping — the first GitOps agent must be installed somehow
- Drift detection takes seconds to minutes — not instant

---

**Q12: How do you monitor cluster health at scale?**

**Answer:**

A production cluster monitoring stack typically consists of:

**Metrics collection:**
- **kube-state-metrics**: exposes object-level Kubernetes metrics (deployment desired/ready replicas, pod phase, PVC binding state, node conditions). Essential for alerting on deployment failures and capacity.
- **node-exporter**: system-level node metrics (CPU, memory, disk, network). Runs as a DaemonSet.
- **metrics-server**: in-cluster resource metrics for `kubectl top` and HPA. Lightweight, not for long-term storage.

**Key alerts to configure:**
| Alert | Condition |
|-------|-----------|
| Node NotReady | `kube_node_status_condition{condition="Ready",status="true"} == 0` |
| Pod CrashLoopBackOff | `kube_pod_container_status_waiting_reason{reason="CrashLoopBackOff"} > 0` |
| Deployment not fully available | `kube_deployment_status_replicas_available < kube_deployment_spec_replicas` |
| etcd DB size > 75% | etcd DB approaching 8GB limit |
| Certificate expiry < 30 days | `kubeadm certs check-expiration` output |
| PVC not bound | `kube_persistentvolumeclaim_status_phase{phase="Pending"} > 0` |

**node-problem-detector**: DaemonSet that watches kernel logs and system logs for known issues (OOM kills, disk errors, CNI failures) and surfaces them as Kubernetes Node conditions and events. Essential for catching hardware or OS issues that don't show up in standard metrics.

**Cluster-level visibility tools:**
- **Grafana dashboards**: standard dashboards for Kubernetes are available from the `kube-prometheus-stack` Helm chart
- **k9s**: real-time terminal dashboard for interactive debugging
- **Lens**: desktop GUI for multi-cluster visibility

---

## 📂 Navigation

⬅️ **Prev:** [Advanced Scheduling](../27_Advanced_Scheduling/Interview_QA.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Backup and DR](../29_Backup_and_DR/Theory.md)

| | Link |
|---|---|
| Theory | [Theory.md](./Theory.md) |
| Cheatsheet | [Cheatsheet.md](./Cheatsheet.md) |
