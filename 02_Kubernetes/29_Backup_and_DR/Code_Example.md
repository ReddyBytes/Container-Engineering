# Backup and Disaster Recovery — Code Examples

All examples are production-quality with detailed comments explaining every decision.

---

## 1. Velero: Install, Backup, and Restore

```bash
# --- Install Velero CLI ---
# macOS
brew install velero

# Linux
VELERO_VERSION=v1.13.0
curl -L https://github.com/vmware-tanzu/velero/releases/download/${VELERO_VERSION}/velero-${VELERO_VERSION}-linux-amd64.tar.gz \
  | tar xz -C /tmp
mv /tmp/velero-${VELERO_VERSION}-linux-amd64/velero /usr/local/bin/

# --- Create AWS credentials file for Velero ---
cat > /tmp/velero-credentials << 'EOF'
[default]
aws_access_key_id=AKIAIOSFODNN7EXAMPLE
aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
EOF

# --- Install Velero server components into the cluster ---
velero install \
  --provider aws \
  --plugins velero/velero-plugin-for-aws:v1.9.0 \
  --bucket my-velero-backups \            # S3 bucket to store backups
  --backup-location-config region=us-east-1 \
  --snapshot-location-config region=us-east-1 \
  --secret-file /tmp/velero-credentials

# Verify Velero is running and backup location is available
velero backup-location get
# Status should show: Available
```

```bash
# --- Create backups ---

# Full cluster backup (all namespaces, all resources)
velero backup create full-cluster-backup \
  --wait                                  # block until backup completes

# Namespace-scoped backup (production only)
velero backup create production-backup \
  --include-namespaces production \
  --wait

# Backup with volume snapshots (for PVCs)
velero backup create production-with-pvs \
  --include-namespaces production \
  --snapshot-volumes \                    # create EBS/GCE snapshots for PVCs
  --wait

# Backup specific resources by label (e.g., one application)
velero backup create payments-app-backup \
  --selector app=payments \               # only resources matching this label
  --wait

# Inspect a backup's contents before using it for restore
velero backup describe production-backup --details
velero backup logs production-backup

# --- Schedule regular backups ---
# Daily backup at 2am UTC, retained for 30 days
velero schedule create daily-production \
  --schedule="0 2 * * *" \
  --include-namespaces production,staging \
  --snapshot-volumes \
  --ttl 720h                              # 720h = 30 days

# List active schedules
velero schedule get
```

```bash
# --- Restore from backup ---

# List all available backups
velero backup get

# Restore an entire backup to the same cluster
velero restore create --from-backup production-backup \
  --wait

# Restore a specific namespace only
velero restore create restore-prod-only \
  --from-backup full-cluster-backup \
  --include-namespaces production \
  --wait

# Restore a namespace under a different name (e.g., for testing restore integrity)
velero restore create restore-to-test \
  --from-backup production-backup \
  --namespace-mappings production:production-restored \
  --wait

# Verify the restore succeeded
velero restore describe restore-prod-only
kubectl get pods -n production            # are pods running?
kubectl get pvc -n production             # are PVCs bound?

# Clean up a restore object (does not delete the restored resources)
velero restore delete restore-to-test
```

---

## 2. Velero Hooks: Consistent Database Backups

```yaml
# postgres-statefulset.yaml
# Pre/post backup hooks ensure the database is in a consistent state
# before Velero snapshots the volume. Without this, mid-transaction data
# can produce a snapshot that is valid but internally inconsistent.
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: production
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
      annotations:
        # Velero reads these annotations to run commands before/after backup
        pre.hook.backup.velero.io/container: postgres
        pre.hook.backup.velero.io/command: >
          ["/bin/bash", "-c",
          "psql -U $POSTGRES_USER -c 'CHECKPOINT;'"]
        # CHECKPOINT flushes all dirty buffers to disk — ensures consistent snapshot
        pre.hook.backup.velero.io/timeout: "60s"

        post.hook.backup.velero.io/container: postgres
        post.hook.backup.velero.io/command: >
          ["/bin/bash", "-c", "echo 'Velero backup snapshot complete'"]
        post.hook.backup.velero.io/timeout: "30s"
    spec:
      containers:
      - name: postgres
        image: postgres:15
        env:
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: username
        - name: POSTGRES_DB
          value: production_db
        volumeMounts:
        - name: postgres-data
          mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
  - metadata:
      name: postgres-data
    spec:
      accessModes: [ReadWriteOnce]
      storageClassName: gp3              # EBS gp3 — supports snapshots
      resources:
        requests:
          storage: 100Gi
```

```yaml
# mysql-backup-hooks.yaml — MySQL uses FLUSH TABLES WITH READ LOCK
# for a brief, consistent snapshot window
apiVersion: v1
kind: Pod
metadata:
  name: mysql
  namespace: production
  annotations:
    pre.hook.backup.velero.io/container: mysql
    pre.hook.backup.velero.io/command: >
      ["/bin/bash", "-c",
      "mysql -u root -p$MYSQL_ROOT_PASSWORD -e 'FLUSH TABLES WITH READ LOCK; SELECT SLEEP(5);' &"]
    # FLUSH TABLES WITH READ LOCK acquires a global read lock for consistency
    # The SLEEP(5) holds it open while Velero starts the snapshot

    post.hook.backup.velero.io/container: mysql
    post.hook.backup.velero.io/command: >
      ["/bin/bash", "-c",
      "mysql -u root -p$MYSQL_ROOT_PASSWORD -e 'UNLOCK TABLES;'"]
    # Release the lock immediately after Velero snapshot begins
spec:
  containers:
  - name: mysql
    image: mysql:8.0
```

---

## 3. etcd Backup with CronJob and S3 Upload

```yaml
# etcd-backup-cronjob.yaml
# Hourly etcd snapshots uploaded to S3.
# etcd holds ALL cluster state — losing it without a backup is catastrophic.
apiVersion: batch/v1
kind: CronJob
metadata:
  name: etcd-backup
  namespace: kube-system
spec:
  schedule: "0 * * * *"                  # every hour
  concurrencyPolicy: Forbid              # only one backup job at a time
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 5
  jobTemplate:
    spec:
      template:
        spec:
          hostNetwork: true              # needed to reach etcd at 127.0.0.1:2379
          nodeSelector:
            node-role.kubernetes.io/control-plane: ""  # must run on the control plane node
          tolerations:
          - key: node-role.kubernetes.io/control-plane
            operator: Exists
            effect: NoSchedule
          serviceAccountName: etcd-backup-sa
          containers:
          - name: backup
            image: bitnami/etcd:3.5
            env:
            - name: AWS_DEFAULT_REGION
              value: us-east-1
            - name: S3_BUCKET
              value: my-etcd-backups-prod
            command:
            - /bin/sh
            - -c
            - |
              set -e                                     # exit on any error
              TIMESTAMP=$(date +%Y%m%d-%H%M%S)
              BACKUP_FILE="/tmp/etcd-${TIMESTAMP}.db"

              # Take snapshot
              ETCDCTL_API=3 etcdctl snapshot save "$BACKUP_FILE" \
                --endpoints=https://127.0.0.1:2379 \
                --cacert=/certs/ca.crt \
                --cert=/certs/server.crt \
                --key=/certs/server.key

              # Verify snapshot integrity before uploading
              ETCDCTL_API=3 etcdctl snapshot status "$BACKUP_FILE" --write-out=table

              # Upload to S3 with date prefix for easy browsing and lifecycle policies
              aws s3 cp "$BACKUP_FILE" \
                "s3://${S3_BUCKET}/$(date +%Y/%m/%d)/$(basename $BACKUP_FILE)"

              echo "Backup complete: etcd-${TIMESTAMP}.db"
            volumeMounts:
            - name: etcd-certs
              mountPath: /certs
              readOnly: true
          restartPolicy: OnFailure
          volumes:
          - name: etcd-certs
            hostPath:
              path: /etc/kubernetes/pki/etcd
              type: Directory
```

```bash
# Manually verify the latest backup exists and is recent
aws s3 ls s3://my-etcd-backups-prod/ --recursive \
  | sort | tail -5

# Verify a backup file is a valid etcd snapshot
aws s3 cp s3://my-etcd-backups-prod/2024/01/15/etcd-20240115-020000.db /tmp/check.db
ETCDCTL_API=3 etcdctl snapshot status /tmp/check.db --write-out=table
# Shows: hash, revision, total keys, total size
# Any error here means the backup is corrupted — investigate immediately

rm /tmp/check.db
```

---

## 4. Disaster Recovery Runbook: Full Cluster Restore

```bash
# ================================================================
# DR RUNBOOK: Full Cluster Loss — Restore from Backup
# Estimated RTO: 60-90 minutes with a practiced team
# ================================================================

# --- Phase 1: Provision a new cluster (15-30 min) ---
# Use your existing Terraform/Pulumi IaC to recreate infrastructure.
# Replace CLUSTER_NAME and region as appropriate.

terraform init
terraform apply -target=module.eks_cluster   # or your cluster module

# Wait for the cluster to become Available
aws eks wait cluster-active --name my-production-cluster

# Update local kubeconfig to point to the new cluster
aws eks update-kubeconfig \
  --name my-production-cluster \
  --region us-east-1

kubectl get nodes                             # confirm nodes are Ready

# --- Phase 2: Install Velero on the new cluster (5 min) ---
velero install \
  --provider aws \
  --plugins velero/velero-plugin-for-aws:v1.9.0 \
  --bucket my-velero-backups \
  --backup-location-config region=us-east-1 \
  --snapshot-location-config region=us-east-1 \
  --secret-file /tmp/velero-credentials

# Wait for Velero to connect to S3 and list backups
velero backup-location get                    # Status: Available

# --- Phase 3: List and pick the restore point (2 min) ---
velero backup get
# Pick the most recent successful backup before the disaster
# NAME                    STATUS      CREATED                    ...
# production-2024-01-15   Completed   2024-01-15 02:00:14 +0000  ...

# --- Phase 4: Restore (10-20 min depending on data volume) ---
velero restore create dr-restore-$(date +%Y%m%d) \
  --from-backup production-2024-01-15 \
  --wait

velero restore describe dr-restore-20240115

# --- Phase 5: Verify the restore (10 min) ---
kubectl get pods -A                           # all pods should be Running/Completed
kubectl get pvc -A                            # all PVCs should be Bound
kubectl get svc -A                            # all Services present

# Run smoke tests against the restored environment
# (These are application-specific — document them in your runbook)

# --- Phase 6: DNS cutover (5 min) ---
# Update your DNS record (Route53 / Cloud DNS) to point to the new cluster's
# load balancer endpoint.
NEW_LB=$(kubectl get svc ingress-nginx-controller -n ingress-nginx \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "New LB endpoint: $NEW_LB"
# Update Route53 ALIAS record to $NEW_LB
```

---

## 5. Backup Testing: Verify Restores Actually Work

```bash
# ================================================================
# Monthly backup verification procedure.
# A backup is worthless if you've never tested restoring from it.
# Run against a SEPARATE test cluster — never against production.
# ================================================================

# Step 1: Switch to the test cluster context
kubectl config use-context test-cluster

# Step 2: Restore the most recent production backup into the test cluster
LATEST_BACKUP=$(velero backup get --output json | \
  jq -r '.items | map(select(.status.phase == "Completed")) |
  sort_by(.metadata.creationTimestamp) | last | .metadata.name')

echo "Testing restore of backup: $LATEST_BACKUP"

velero restore create "test-$(date +%Y%m%d)" \
  --from-backup "$LATEST_BACKUP" \
  --include-namespaces production \
  --namespace-mappings production:production-restored \
  --wait

# Step 3: Verify the restore
kubectl get pods -n production-restored          # pods should be Running
kubectl get pvc -n production-restored           # PVCs should be Bound

# Step 4: Run application smoke tests
# Document and run your app-specific health checks here
# Example: check the payments API returns 200
kubectl port-forward -n production-restored svc/payments-api 8080:80 &
sleep 5
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health
# Expected: 200

# Step 5: Record results and clean up
echo "Restore test completed: $(date)"
echo "Pods running: $(kubectl get pods -n production-restored --no-headers | grep -c Running)"
echo "PVCs bound: $(kubectl get pvc -n production-restored --no-headers | grep -c Bound)"

# Clean up the test namespace
kubectl delete namespace production-restored

# Step 6: Alert if backup is stale (automate this as a monitoring check)
BACKUP_AGE_HOURS=$(( ($(date +%s) - $(date -d "$BACKUP_DATE" +%s)) / 3600 ))
if [ "$BACKUP_AGE_HOURS" -gt 2 ]; then
  echo "WARNING: Latest backup is ${BACKUP_AGE_HOURS} hours old — expected < 2 hours"
  # Send alert to PagerDuty / Slack
fi
```

---

## 📂 Navigation

**In this folder:**
| File | |
|---|---|
| [Theory.md](./Theory.md) | Full explanation |
| [Cheatsheet.md](./Cheatsheet.md) | Quick reference |
| [Interview_QA.md](./Interview_QA.md) | Interview prep |
| **Code_Example.md** | you are here |

⬅️ **Prev:** [Cluster Management](../28_Cluster_Management/Code_Example.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Cost Optimization](../30_Cost_Optimization/Code_Example.md)
🏠 **[Home](../../README.md)**
