# Module 29 — Backup and DR Cheatsheet

## What to Back Up

| Component | Tool | Frequency |
|---|---|---|
| etcd (cluster state) | etcdctl snapshot | Hourly |
| Persistent Volumes | Velero + volume snapshots | Daily (or per app SLA) |
| K8s manifests | Git (GitOps) | Every commit |
| Application databases | App-level (pg_dump, mysqldump) + Velero | Hourly to daily |

---

## Velero Commands

```bash
# --- INSTALL ---
velero install \
  --provider aws \
  --plugins velero/velero-plugin-for-aws:v1.8.0 \
  --bucket my-velero-backups \
  --backup-location-config region=us-east-1 \
  --snapshot-location-config region=us-east-1 \
  --secret-file ./credentials

# --- BACKUP ---
# Full cluster backup
velero backup create full-backup

# Namespace backup
velero backup create ns-backup --include-namespaces production

# Backup with PV snapshots
velero backup create full-with-data \
  --include-namespaces production \
  --snapshot-volumes

# Exclude specific resources
velero backup create ns-backup \
  --include-namespaces production \
  --exclude-resources pods,events

# --- SCHEDULE ---
velero schedule create daily-backup \
  --schedule="0 2 * * *" \
  --include-namespaces production \
  --ttl 720h    # keep 30 days

velero schedule get
velero schedule delete daily-backup

# --- INSPECT ---
velero backup get                                  # list all backups
velero backup describe <backup-name> --details     # full details
velero backup logs <backup-name>                   # backup job logs

# --- RESTORE ---
velero restore create --from-backup <backup-name>

# Restore specific namespace
velero restore create \
  --from-backup <backup-name> \
  --include-namespaces production

# Restore to different namespace
velero restore create \
  --from-backup <backup-name> \
  --namespace-mappings production:production-test

velero restore get                                 # list restores
velero restore describe <restore-name>
velero restore logs <restore-name>
```

---

## etcd Backup and Restore

```bash
# --- BACKUP ---
ETCDCTL_API=3 etcdctl snapshot save /tmp/etcd-backup.db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key

# Verify
ETCDCTL_API=3 etcdctl snapshot status /tmp/etcd-backup.db

# --- RESTORE ---
# 1. Stop API server
mv /etc/kubernetes/manifests/kube-apiserver.yaml /tmp/

# 2. Restore snapshot
ETCDCTL_API=3 etcdctl snapshot restore /tmp/etcd-backup.db \
  --data-dir /var/lib/etcd-restore

# 3. Update etcd manifest: --data-dir=/var/lib/etcd-restore

# 4. Restart API server
mv /tmp/kube-apiserver.yaml /etc/kubernetes/manifests/
```

---

## Velero Hooks (Database Consistency)

```yaml
# Add to Pod annotations for pre/post backup commands
metadata:
  annotations:
    # Pre-backup: flush/checkpoint before snapshot
    pre.hook.backup.velero.io/container: postgres
    pre.hook.backup.velero.io/command: >
      ["/bin/bash", "-c",
      "psql -U $POSTGRES_USER -c 'CHECKPOINT;'"]
    pre.hook.backup.velero.io/timeout: 60s

    # Post-backup: cleanup
    post.hook.backup.velero.io/container: postgres
    post.hook.backup.velero.io/command: >
      ["/bin/bash", "-c", "echo backup_done"]
```

---

## RPO and RTO Reference

| Metric | Definition | Example |
|---|---|---|
| RPO | Max acceptable data loss | "1 hour" = backup every hour |
| RTO | Max acceptable downtime | "4 hours" = restore in < 4h |

| RPO Target | Backup approach |
|---|---|
| 24 hours | Daily backups |
| 1 hour | Hourly Velero schedule |
| 15 minutes | DB WAL archiving, frequent snapshots |
| Near-zero | Synchronous replication, active-active |

---

## DR Runbook Template

```bash
# 1. DETECT: Declare disaster
# 2. ASSESS: What failed? (node / AZ / region / data)

# 3. RESTORE CLUSTER (if full cluster loss)
terraform apply -target=module.cluster   # or cloud console
aws eks update-kubeconfig --name new-cluster --region us-west-2

# 4. RESTORE KUBERNETES STATE
# Option A: GitOps (redeploy from Git)
kubectl apply -k environments/production/

# Option B: Velero restore
velero restore create dr-restore \
  --from-backup production-daily-backup

# 5. RESTORE PERSISTENT DATA
velero restore create dr-data-restore \
  --from-backup production-daily-backup \
  --include-namespaces production

# 6. VERIFY
kubectl get pods -n production
kubectl get pvc -n production
# Run smoke tests

# 7. UPDATE DNS
aws route53 change-resource-record-sets ...  # point to new cluster

# 8. DECLARE RECOVERY COMPLETE
# Document RTO: time from step 1 to step 7
```

---

## Backup Testing Checklist

```
Monthly:
[ ] Restore latest backup to isolated test cluster
[ ] Verify all pods come up healthy
[ ] Run application smoke tests on restored cluster
[ ] Measure and document RTO

Quarterly:
[ ] Full DR drill: simulate region failure
[ ] Test full restore procedure end-to-end
[ ] Update runbook with any procedure changes

Ongoing:
[ ] Alert fires if backup older than 2 hours
[ ] Backup size monitored (detect backup failures)
[ ] Test restores after major cluster changes
```

---

## 📂 Navigation

| | Link |
|---|---|
| ⬅️ Prev | [Cluster Management](../28_Cluster_Management/Interview_QA.md) |
| Theory | [Backup and DR Theory](./Theory.md) |
| Interview Q&A | [Backup and DR Interview Q&A](./Interview_QA.md) |
| ➡️ Next | [Cost Optimization](../30_Cost_Optimization/Theory.md) |
