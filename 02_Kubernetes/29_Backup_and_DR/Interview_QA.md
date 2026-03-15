# Module 29 — Backup and DR Interview Q&A

---

## Q1: What are the three things you need to back up in Kubernetes, and why?

**Answer:**

1. **etcd** — stores all Kubernetes cluster state (every object: Pods, Deployments, Secrets, RBAC rules, etc.). If etcd is lost, the cluster has no memory of what was running. Backed up with `etcdctl snapshot save`.

2. **Persistent Volumes** — the actual application data (database files, uploaded content, etc.). Kubernetes doesn't understand the data semantics — you need application-aware backup (Velero with volume snapshots, or database-level dumps). If PVs are lost, user data is gone.

3. **Kubernetes manifests** — the YAML definitions of your workloads. With GitOps, this is already in Git. Without GitOps, you might export them with `kubectl get all -o yaml` or use Velero to back up Kubernetes objects.

Together: etcd lets you restore cluster configuration, PV backups restore application data, and manifest backups (Git) let you rebuild from scratch if needed.

---

## Q2: What is Velero and what can it back up that etcd backup cannot?

**Answer:**

`etcdctl snapshot` captures cluster state — all the Kubernetes API objects. But it does NOT capture the data stored in Persistent Volumes (the actual bytes on the disk).

**Velero** addresses this gap:
- Backs up Kubernetes objects to object storage (S3, GCS, Azure Blob)
- Creates cloud volume snapshots (EBS snapshots, GCE PD snapshots) for PVs
- Can use restic/Kopia for file-level PV backup (for storage providers without snapshot support)
- Can restore to a different cluster (migration use case)
- Supports scheduling, TTL, namespace filtering

etcd backup: "what does Kubernetes think should exist?"
Velero: "what actually exists, including the data?"

For complete DR, you need both.

---

## Q3: What is the difference between RPO and RTO, and how do they influence backup strategy?

**Answer:**

**RPO (Recovery Point Objective)**: the maximum acceptable age of the data recovered after an incident. "How much data can we lose?"
- RPO of 1 hour → backup every hour (worst case: lose 59 minutes of data)
- RPO of 15 minutes → backup every 15 minutes
- RPO of 0 → synchronous replication (no loss)

**RTO (Recovery Time Objective)**: the maximum acceptable time to restore service after an incident. "How long can we be down?"
- RTO of 4 hours → manual restore acceptable
- RTO of 1 hour → need automated restore scripts and pre-provisioned infrastructure
- RTO of 15 minutes → need hot standby, automated failover

These drive architecture decisions:
- Small RPO → frequent backups, possibly continuous replication
- Small RTO → pre-provisioned DR infrastructure, tested runbooks, automation

For most businesses: RPO of 1 hour and RTO of 4 hours are common starting points. Critical systems (payment processing) might need RPO of minutes and RTO of minutes.

---

## Q4: Why is testing backups as important as taking them?

**Answer:**

An untested backup is an assumption, not a guarantee. Common failures discovered only during restore:

- Certificate paths in restore scripts are wrong (different on new cluster)
- IAM permissions allow writing to S3 but not reading (tested backup creation, not restore)
- etcd restore script uses wrong `--data-dir` path — overwrites live data instead of restoring
- The restore procedure works, but the applications don't start (missing secrets not in backup)
- Backup is corrupt or truncated (snapshot job ran out of disk space)
- Velero can backup objects but volume snapshots fail silently

The restore procedure also needs to be practiced. Under stress (during an actual outage), teams make mistakes they wouldn't make in a calm test.

**Testing cadence:**
- Monthly: restore to isolated cluster, verify application functionality
- Quarterly: full DR drill, measure actual RTO vs target
- After major changes: spot-check that backups still work

---

## Q5: Explain how Velero hooks work and why they matter for database backup consistency.

**Answer:**

Velero hooks are commands run inside pod containers before or after a backup operation. They're critical for databases because a file-level snapshot of a running database can be inconsistent — if a write is mid-transaction when the snapshot is taken, the backup captures a corrupted state.

Pre-backup hooks quiesce the application (stop writes, flush buffers, create a consistent checkpoint):
- **PostgreSQL**: `CHECKPOINT;` forces WAL flush
- **MySQL**: `FLUSH TABLES WITH READ LOCK;` prevents new writes temporarily
- **MongoDB**: `db.fsyncLock()` locks and flushes

Post-backup hooks reverse the quiesce:
- **MySQL**: `UNLOCK TABLES;`
- **MongoDB**: `db.fsyncUnlock()`

Without hooks, you might back up and restore a database that immediately shows corruption or inconsistency when the application starts. With proper hooks, you get a guaranteed-consistent backup.

Hooks are configured via pod annotations — no code changes required.

---

## Q6: What is the difference between active-active and active-passive multi-region Kubernetes?

**Answer:**

**Active-Passive (Cold/Warm Standby)**:
- Primary cluster handles all traffic
- DR cluster exists but handles no traffic (or minimal)
- On failure: update DNS to point to DR cluster, restore latest backup, bring up workloads
- Lower cost (DR cluster can be minimal)
- Higher RTO (time to restore and start workloads)
- Higher RPO (some data loss between last backup and failure)

**Active-Active**:
- Both clusters handle traffic (load balanced globally)
- Data is replicated synchronously or near-synchronously
- On failure: global load balancer redirects all traffic to surviving cluster
- Higher cost (full infrastructure in two regions)
- Lower RTO (seconds to minutes, just DNS change)
- Lower RPO (near-zero if synchronous replication)

For most applications: active-passive is sufficient and much cheaper. Financial or payment systems often require active-active due to business requirements.

The key challenge with active-active: **distributed data consistency**. If users can write to either region, how do you prevent conflicts? This requires careful database design (eventual consistency, CRDT, or a globally distributed database like CockroachDB, Spanner).

---

## Q7: How would you recover from accidental deletion of the `production` namespace?

**Answer:**

**Step 1: Assess scope**
```bash
kubectl get ns production  # confirm it's gone
```

**If using GitOps (ArgoCD/Flux)**:
```bash
# Redeploy from Git
argocd app sync myapp-production  # or let ArgoCD auto-sync
```
ArgoCD/Flux will recreate all resources from the Git manifests. Stateless apps recover in minutes.

**For persistent data** (if namespace had PVCs):
```bash
# Check if PVs still exist (they may be in Released state)
kubectl get pv

# If reclaim policy was Retain (recommended):
kubectl patch pv <pv-name> -p '{"spec":{"claimRef": null}}'  # release the PV
# Create new PVC that binds to this PV
```

**If PVs were deleted** (Reclaim policy: Delete):
```bash
# Restore from Velero backup
velero restore create recovery \
  --from-backup production-daily-backup \
  --include-namespaces production
```

**Lesson**: set `persistentVolumeReclaimPolicy: Retain` on StorageClasses for production data. This means deleting a PVC doesn't delete the underlying storage.

---

## Q8: How do you back up etcd in a managed Kubernetes cluster like EKS or GKE?

**Answer:**

In managed Kubernetes, the control plane (and etcd) is managed by the cloud provider. You don't have access to the etcd nodes, so you can't use `etcdctl snapshot` directly.

Instead:
- **EKS**: etcd is AWS-managed. AWS handles etcd reliability (multi-AZ). You don't backup etcd — you backup your workloads with Velero.
- **GKE**: same — GCP manages the control plane
- **AKS**: same — Azure manages the control plane

For managed clusters, the DR approach is:
1. **Manifests**: GitOps (Git is the backup)
2. **Application state (PVs)**: Velero with cloud volume snapshots
3. **Secrets**: External Secrets Operator pointing to AWS Secrets Manager/Vault
4. **Cluster configuration**: IaC (Terraform/Pulumi) to recreate the cluster

The cloud provider's SLA covers control plane availability. Your responsibility is application data.

---

## Q9: What is Velero's restic/Kopia integration and when would you use it?

**Answer:**

Velero's default PV backup uses **cloud provider volume snapshots** (EBS snapshot, GCE PD snapshot). This is fast and efficient but only works with cloud-native storage providers.

For storage that doesn't support snapshots (NFS, Ceph, local storage, some CSI drivers), Velero can use **file-level backup** via:
- **restic** (older, being phased out)
- **Kopia** (new default, faster and more efficient)

File-level backup mounts the PV and copies files directly to the backup destination, creating a file-level copy in your S3/GCS bucket.

Enable per-volume with an annotation:
```yaml
metadata:
  annotations:
    backup.velero.io/backup-volumes: my-pvc-volume
```

Tradeoffs:
- Works on any storage (advantage over snapshots)
- Slower than native snapshots (copies all files)
- Creates a point-in-time consistent copy of the files
- Restoring creates new PVs with the copied data

Use file-level backup when: running on-premises, using storage without snapshot support, or needing to migrate data across cloud providers.

---

## Q10: What is a backup retention policy and how would you configure it for a production system?

**Answer:**

Retention policy defines how long backups are kept before automatic deletion. Keeping all backups forever is expensive; deleting too aggressively means you can't recover from an old backup if needed.

Typical production retention policy (grandfather-father-son pattern):
- **Hourly**: keep 24 (last 24 hours)
- **Daily**: keep 7 (last week)
- **Weekly**: keep 4 (last month)
- **Monthly**: keep 12 (last year)

In Velero, TTL is set per schedule:
```bash
# Keep hourly backups for 24 hours
velero schedule create hourly-backup \
  --schedule="0 * * * *" \
  --ttl 24h

# Keep daily backups for 7 days
velero schedule create daily-backup \
  --schedule="0 2 * * *" \
  --ttl 168h   # 7 days

# Keep weekly backups for 30 days
velero schedule create weekly-backup \
  --schedule="0 3 * * 0" \
  --ttl 720h   # 30 days
```

Also consider storage costs: S3 Glacier/Coldline for older backups dramatically reduces costs while maintaining long-term recovery capability. Store recent backups in standard storage, move to archive storage after 30 days.

---

## Q11: How does GitOps serve as a form of disaster recovery?

**Answer:**

In a GitOps setup (Argo CD or Flux), every Kubernetes manifest — Deployments, Services, ConfigMaps, RBAC rules, Ingresses — is stored in a Git repository. The GitOps controller continuously reconciles the cluster to match the Git state. This has a natural DR implication: if you lose the cluster entirely, you can recreate it.

**Steps to recover a cluster using GitOps:**

1. Provision a new cluster (via Terraform, eksctl, or cloud console)
2. Install Argo CD or Flux and point it at your Git repository
3. The controller automatically creates every resource defined in Git
4. Your entire cluster configuration is restored without manual intervention

**Why this is powerful:**

- Git is your source of truth and your backup simultaneously
- Git history gives you point-in-time recovery — you can restore to any commit, letting you roll back accidental changes to cluster configuration
- It is vendor-agnostic: the same Git repo can recreate the workloads in any cloud or on-premises cluster

**What GitOps does NOT cover:**

GitOps restores Kubernetes object definitions but not the data inside PersistentVolumes. Your Git repo knows a PostgreSQL StatefulSet should exist with a 50Gi PVC — but the actual database rows live in the PVC, not in Git. You still need Velero or VolumeSnapshots for data recovery. GitOps covers the "rebuild the platform" layer; Velero covers the "restore the data" layer.

---

## Q12: How do you design a Kubernetes backup strategy around specific RTO and RPO targets?

**Answer:**

RTO and RPO targets directly dictate the infrastructure and tooling choices for your backup strategy.

**Example: RPO = 1 hour, RTO = 4 hours**

- Velero schedule: `--schedule="0 * * * *" --ttl 720h` (hourly backups, 30-day retention)
- VolumeSnapshot: daily cloud snapshots for PVCs
- Recovery: restore Velero backup to existing or new cluster within 4 hours
- RTO feasibility: 4 hours is achievable with documented runbooks and manual execution
- Testing: monthly restore drill to confirm 4-hour RTO is realistic

**Example: RPO = 15 minutes, RTO = 30 minutes**

- Velero schedule: every 15 minutes for critical namespaces
- Database: WAL archiving (PostgreSQL) or binlog streaming (MySQL) for near-zero data loss
- Cluster: warm standby in another region/AZ, already provisioned and running
- Recovery: automated failover script, not manual; Argo CD auto-sync on standby cluster
- RTO feasibility: 30 minutes is very tight — requires pre-automation and a warm cluster

**Example: RPO = 0, RTO = ~0**

- Active-active multi-region: both clusters serve traffic simultaneously
- Synchronous database replication (e.g., CockroachDB, Spanner)
- Global load balancer that routes away from failed region in seconds
- Cost: approximately 2x infrastructure

**The design process:**

1. Define RPO and RTO with business stakeholders — not engineers
2. Choose backup frequency to meet RPO (backup interval = RPO)
3. Choose standby infrastructure to meet RTO (cold vs warm vs hot standby)
4. Test the actual restore time to verify RTO is achievable
5. Adjust if measured RTO exceeds the target

---

## 📂 Navigation

| | Link |
|---|---|
| ⬅️ Prev | [Cluster Management](../28_Cluster_Management/Interview_QA.md) |
| Theory | [Backup and DR Theory](./Theory.md) |
| Cheatsheet | [Backup and DR Cheatsheet](./Cheatsheet.md) |
| ➡️ Next | [Cost Optimization](../30_Cost_Optimization/Theory.md) |
