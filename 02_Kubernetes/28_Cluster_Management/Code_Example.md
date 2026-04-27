# Cluster Management — Code Examples

All examples are production-quality with detailed comments explaining every decision.

---

## 1. Node Lifecycle: Cordon, Drain, and Uncordon

```bash
# --- Safely take a node out of service for maintenance ---

# Step 1: Cordon — prevent NEW pods from scheduling here.
# Existing pods keep running. Use this when you're about to start maintenance
# but don't need to move pods yet (e.g., waiting for a maintenance window).
kubectl cordon worker-03

# Verify the node is now SchedulingDisabled
kubectl get nodes worker-03
# Output: worker-03   Ready,SchedulingDisabled   ...

# Step 2: Drain — evict ALL pods from the node gracefully.
# The scheduler will recreate evicted pods on other nodes.
# --ignore-daemonsets: DaemonSet pods (like log agents) can't be evicted — skip them
# --delete-emptydir-data: allow eviction of pods using emptyDir (data will be lost)
# --grace-period=120: give each pod 120 seconds to finish in-flight requests
# --timeout=300s: abort drain if it takes more than 5 minutes (prevents hanging forever)
kubectl drain worker-03 \
  --ignore-daemonsets \
  --delete-emptydir-data \
  --grace-period=120 \
  --timeout=300s

# Verify the node is empty (DaemonSet pods are expected to remain)
kubectl get pods -A --field-selector=spec.nodeName=worker-03

# --- Perform maintenance here (OS patching, hardware replacement, etc.) ---

# Step 3: Uncordon — return the node to service.
# The node is now schedulable again. Pods that moved away do NOT auto-migrate back.
kubectl uncordon worker-03

# Confirm the node is Ready and schedulable
kubectl get nodes worker-03
# Output: worker-03   Ready   ...
```

```bash
# --- Remove a node from the cluster permanently ---
# Use this for hardware decommission or replacing a node entirely.

# 1. Add the replacement node first (kubeadm join, or managed node group scale-out)
# 2. Cordon and drain the old node
kubectl cordon old-worker-01
kubectl drain old-worker-01 --ignore-daemonsets --delete-emptydir-data

# 3. Confirm the node is empty
kubectl get pods -A --field-selector=spec.nodeName=old-worker-01

# 4. Delete the node object from the K8s API
kubectl delete node old-worker-01

# 5. Now terminate the underlying VM in your cloud console / Terraform
```

---

## 2. kubeadm Cluster Upgrade: Control Plane then Workers

```bash
# --- Pre-upgrade checklist ---
# 1. Verify current version
kubectl version --short
kubectl get nodes

# 2. Check what upgrade is available
kubeadm upgrade plan
# Output shows the target version and which components will change.
# Always read this output before proceeding.

# 3. Ensure etcd backup exists before starting (see Example 3 below)

# ========================
# PHASE 1: Control Plane
# ========================

# On the control plane node (as root):

# Unlock kubeadm to allow version change
apt-mark unhold kubeadm

# Install the new kubeadm version
apt-get update && apt-get install -y kubeadm=1.30.0-00

# Lock again to prevent accidental upgrades
apt-mark hold kubeadm

# Verify the new kubeadm version
kubeadm version

# Apply the control plane upgrade (upgrades API server, controller-manager, scheduler)
# This takes 2-5 minutes and briefly makes the API server unavailable
kubeadm upgrade apply v1.30.0

# Upgrade kubelet and kubectl on the control plane node
apt-mark unhold kubelet kubectl
apt-get install -y kubelet=1.30.0-00 kubectl=1.30.0-00
apt-mark hold kubelet kubectl

# Reload systemd and restart kubelet
systemctl daemon-reload && systemctl restart kubelet

# Verify control plane is upgraded
kubectl get nodes                         # control plane shows v1.30.0

# ========================
# PHASE 2: Worker Nodes (repeat for each worker, one at a time)
# ========================

# On the management machine: cordon and drain worker-01
kubectl cordon worker-01
kubectl drain worker-01 --ignore-daemonsets --delete-emptydir-data --grace-period=120

# On worker-01 (as root):
apt-mark unhold kubeadm
apt-get update && apt-get install -y kubeadm=1.30.0-00
apt-mark hold kubeadm
# kubeadm upgrade node (for workers, not "apply")
kubeadm upgrade node

apt-mark unhold kubelet kubectl
apt-get install -y kubelet=1.30.0-00 kubectl=1.30.0-00
apt-mark hold kubelet kubectl
systemctl daemon-reload && systemctl restart kubelet

# On the management machine: return worker-01 to service
kubectl uncordon worker-01

# Verify worker-01 is upgraded and Ready before moving to worker-02
kubectl get nodes worker-01               # should show v1.30.0, Ready
```

```bash
# --- Managed cluster upgrades (EKS, GKE, AKS) ---
# These handle the control plane upgrade automatically — you only manage node groups.

# EKS: upgrade the control plane first, then each node group
aws eks update-cluster-version \
  --name my-production-cluster \
  --kubernetes-version 1.30

# Poll until cluster update is complete
aws eks describe-cluster \
  --name my-production-cluster \
  --query 'cluster.status'               # waits for ACTIVE

# Upgrade the managed node group (rolling update — nodes are replaced one at a time)
aws eks update-nodegroup-version \
  --cluster-name my-production-cluster \
  --nodegroup-name general-workers \
  --kubernetes-version 1.30

# GKE: upgrade master, then node pool
gcloud container clusters upgrade my-cluster \
  --master \
  --cluster-version 1.30 \
  --zone us-east1-b

gcloud container clusters upgrade my-cluster \
  --node-pool default-pool \
  --cluster-version 1.30 \
  --zone us-east1-b
```

---

## 3. etcd Backup and Restore

```bash
# --- Take an etcd snapshot ---
# Run on the control plane node as root.
# etcdctl requires TLS client certificates to authenticate to etcd.

BACKUP_FILE="/backup/etcd-$(date +%Y%m%d-%H%M%S).db"

ETCDCTL_API=3 etcdctl snapshot save "$BACKUP_FILE" \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \          # CA that signed the etcd server cert
  --cert=/etc/kubernetes/pki/etcd/server.crt \        # client certificate for authentication
  --key=/etc/kubernetes/pki/etcd/server.key            # private key for the client cert

# Verify the snapshot is valid and contains data
ETCDCTL_API=3 etcdctl snapshot status "$BACKUP_FILE" --write-out=table
# Output shows: hash, revision, total keys, total size

# Upload to S3 for off-node storage (losing the control plane host loses local backups)
aws s3 cp "$BACKUP_FILE" s3://my-etcd-backups/$(basename "$BACKUP_FILE")

# Delete local copy to save disk space on the control plane
rm "$BACKUP_FILE"
```

```yaml
# etcd-backup-cronjob.yaml
# Automated hourly etcd backup to S3 running as a CronJob inside the cluster.
# Uses hostPath to access the etcd TLS certs from the control plane node.
apiVersion: batch/v1
kind: CronJob
metadata:
  name: etcd-backup
  namespace: kube-system
spec:
  schedule: "0 * * * *"                  # every hour at :00
  concurrencyPolicy: Forbid              # never run two backup jobs simultaneously
  successfulJobsHistoryLimit: 3          # keep logs from last 3 successful runs
  failedJobsHistoryLimit: 5              # keep logs from last 5 failed runs for debugging
  jobTemplate:
    spec:
      template:
        spec:
          hostNetwork: true              # use node's network to reach 127.0.0.1:2379
          nodeSelector:
            node-role.kubernetes.io/control-plane: ""  # must run on the control plane node
          tolerations:
          - key: node-role.kubernetes.io/control-plane
            operator: Exists
            effect: NoSchedule           # control plane nodes are usually tainted
          containers:
          - name: backup
            image: bitnami/etcd:3.5      # etcdctl is included in this image
            env:
            - name: AWS_DEFAULT_REGION
              value: us-east-1
            command:
            - /bin/sh
            - -c
            - |
              set -e
              BACKUP_FILE="/tmp/etcd-$(date +%Y%m%d-%H%M%S).db"
              ETCDCTL_API=3 etcdctl snapshot save "$BACKUP_FILE" \
                --endpoints=https://127.0.0.1:2379 \
                --cacert=/etc/kubernetes/pki/etcd/ca.crt \
                --cert=/etc/kubernetes/pki/etcd/server.crt \
                --key=/etc/kubernetes/pki/etcd/server.key
              aws s3 cp "$BACKUP_FILE" "s3://my-etcd-backups/$(basename $BACKUP_FILE)"
              echo "Backup complete: $(basename $BACKUP_FILE)"
            volumeMounts:
            - name: etcd-certs
              mountPath: /etc/kubernetes/pki/etcd
              readOnly: true
          restartPolicy: OnFailure
          volumes:
          - name: etcd-certs
            hostPath:
              path: /etc/kubernetes/pki/etcd  # read certs directly from the node filesystem
              type: Directory
```

```bash
# --- Restore from etcd snapshot (disaster recovery procedure) ---
# Only use this when the cluster is broken and etcd data is lost.

# Step 1: Stop the API server to prevent writes during restore
# (move the static pod manifest out of the manifests directory — kubelet stops it)
mv /etc/kubernetes/manifests/kube-apiserver.yaml /tmp/kube-apiserver.yaml.bak
# Wait a few seconds for the API server to stop
sleep 5

# Step 2: Download the backup from S3
aws s3 cp s3://my-etcd-backups/etcd-20240115-020000.db /tmp/etcd-restore.db

# Step 3: Restore snapshot to a new data directory
ETCDCTL_API=3 etcdctl snapshot restore /tmp/etcd-restore.db \
  --data-dir /var/lib/etcd-restore \
  --name master \
  --initial-cluster master=https://127.0.0.1:2380 \
  --initial-advertise-peer-urls https://127.0.0.1:2380

# Step 4: Update etcd manifest to point to restored directory
# Edit /etc/kubernetes/manifests/etcd.yaml and change:
#   --data-dir=/var/lib/etcd  →  --data-dir=/var/lib/etcd-restore
# Also update the hostPath volume to match

# Step 5: Restore the API server manifest to restart it
mv /tmp/kube-apiserver.yaml.bak /etc/kubernetes/manifests/kube-apiserver.yaml

# Step 6: Verify the cluster recovered
kubectl get nodes
kubectl get pods -A
```

---

## 4. Certificate Management and Rotation

```bash
# --- Check certificate expiry dates ---
# Run on the control plane node as root.
# Certificates managed by kubeadm expire in 1 year by default.
kubeadm certs check-expiration

# Sample output:
# CERTIFICATE                EXPIRES                  RESIDUAL TIME   CERTIFICATE AUTHORITY
# admin.conf                 Jan 15, 2025 02:00 UTC   178d            ca
# apiserver                  Jan 15, 2025 02:00 UTC   178d            ca
# etcd-healthcheck-client    Jan 15, 2025 02:00 UTC   178d            etcd-ca
# ...

# --- Renew all certificates at once ---
kubeadm certs renew all

# --- Renew individual certificates ---
kubeadm certs renew apiserver
kubeadm certs renew apiserver-kubelet-client
kubeadm certs renew front-proxy-client

# After renewal, restart the control plane components.
# kubelet detects the static pod spec hasn't changed, so kill the processes manually:
kill $(pidof kube-apiserver)
kill $(pidof kube-controller-manager)
kill $(pidof kube-scheduler)
# kubelet will restart them automatically within a few seconds.

# Verify renewed certificates
kubeadm certs check-expiration          # RESIDUAL TIME should now show ~365d

# Update kubeconfig if admin.conf was renewed
cp /etc/kubernetes/admin.conf ~/.kube/config
```

---

## 5. Multi-Cluster Access with kubeconfig

```bash
# --- Merge multiple kubeconfig files into one ---
# Useful for managing dev, staging, and production clusters from one machine.

# Each cluster's kubeconfig is exported from the cloud provider or kubeadm:
# EKS:
aws eks update-kubeconfig \
  --name production-cluster \
  --region us-east-1 \
  --alias production                    # human-readable context name

aws eks update-kubeconfig \
  --name staging-cluster \
  --region us-east-1 \
  --alias staging

# GKE:
gcloud container clusters get-credentials production-cluster \
  --zone us-east1-b \
  --project my-project

# Merge all kubeconfig files into a single flat config
KUBECONFIG=~/.kube/config:~/.kube/prod-config:~/.kube/staging-config \
  kubectl config view --flatten > ~/.kube/merged-config

mv ~/.kube/merged-config ~/.kube/config

# --- Switch between clusters ---
# List all contexts (one per cluster)
kubectl config get-contexts

# Output:
# CURRENT   NAME          CLUSTER       AUTHINFO   NAMESPACE
# *         production    production    admin      production
#           staging       staging       admin      staging

# Switch to staging cluster
kubectl config use-context staging

# Run a single command against a specific cluster without switching contexts
kubectl --context=production get nodes

# View which cluster you're currently targeting
kubectl config current-context

# --- Cluster health check commands ---
# These are useful as part of a post-upgrade verification checklist.

# Check all node versions and status
kubectl get nodes -o wide

# Check API server, controller-manager, and scheduler are healthy
kubectl get componentstatuses                # deprecated in newer K8s, use below instead
kubectl get --raw /healthz && echo "API server OK"
kubectl get --raw /readyz  && echo "API server ready"

# Check etcd health (from control plane node)
ETCDCTL_API=3 etcdctl endpoint health \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key

# Check recent cluster events for any warnings
kubectl get events -A \
  --sort-by='.lastTimestamp' \
  --field-selector type=Warning | tail -20

# Check resource pressure on all nodes
kubectl describe nodes | grep -A 5 "Conditions:"
# Look for MemoryPressure=True, DiskPressure=True, or PIDPressure=True
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

⬅️ **Prev:** [Advanced Scheduling](../27_Advanced_Scheduling/Code_Example.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Backup and DR](../29_Backup_and_DR/Code_Example.md)
🏠 **[Home](../../README.md)**
