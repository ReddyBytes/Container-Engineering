# Module 28 — Cluster Management Cheatsheet

## Node Lifecycle Commands

```bash
# --- Cordon: prevent new pod scheduling (existing pods stay) ---
kubectl cordon <node-name>
kubectl uncordon <node-name>       # return to schedulable

# --- Drain: evict all pods safely ---
kubectl drain <node-name> \
  --ignore-daemonsets \            # skip DaemonSet pods
  --delete-emptydir-data \         # allow pods using emptyDir to be evicted
  --grace-period=120 \             # seconds for graceful termination
  --timeout=300s                   # give up after 5 minutes

# --- Force drain (bypasses PDBs — use only in emergencies) ---
kubectl drain <node-name> \
  --ignore-daemonsets \
  --force \
  --disable-eviction

# --- Check node status ---
kubectl get nodes
kubectl describe node <node-name>
kubectl get nodes -o wide          # shows IPs and OS info

# --- Node resource usage (requires metrics-server) ---
kubectl top nodes
kubectl top node <node-name>

# --- List pods on a specific node ---
kubectl get pods -A --field-selector=spec.nodeName=<node-name>

# --- Node labels and taints ---
kubectl label node <node> key=value
kubectl label node <node> key-                      # remove label
kubectl taint node <node> key=value:NoSchedule
kubectl taint node <node> key=value:NoSchedule-     # remove taint
```

---

## kubeadm Cluster Upgrade

```bash
# --- Control Plane ---

# 1. Check available versions and upgrade plan
kubeadm upgrade plan

# 2. Upgrade kubeadm binary
apt-mark unhold kubeadm
apt-get update && apt-get install -y kubeadm=1.30.0-00
apt-mark hold kubeadm

# 3. Apply the upgrade (upgrades API server, controller-manager, scheduler)
kubeadm upgrade apply v1.30.0

# 4. Upgrade kubelet and kubectl
apt-mark unhold kubelet kubectl
apt-get install -y kubelet=1.30.0-00 kubectl=1.30.0-00
apt-mark hold kubelet kubectl
systemctl daemon-reload
systemctl restart kubelet

# 5. Verify control plane
kubectl get nodes

# --- Worker Nodes (repeat for each node, one at a time) ---

# From management machine:
kubectl cordon <worker-node>
kubectl drain <worker-node> --ignore-daemonsets --delete-emptydir-data

# On the worker node:
apt-mark unhold kubeadm
apt-get install -y kubeadm=1.30.0-00
kubeadm upgrade node
apt-mark unhold kubelet kubectl
apt-get install -y kubelet=1.30.0-00 kubectl=1.30.0-00
systemctl daemon-reload && systemctl restart kubelet

# From management machine:
kubectl uncordon <worker-node>
kubectl get nodes   # verify version and Ready status
```

---

## etcd Backup and Restore

```bash
# --- BACKUP ---

# Take a snapshot
ETCDCTL_API=3 etcdctl snapshot save \
  /backup/etcd-$(date +%Y%m%d-%H%M%S).db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key

# Verify the snapshot
ETCDCTL_API=3 etcdctl snapshot status \
  /backup/etcd.db \
  --write-out=table

# Check etcd DB size and health
ETCDCTL_API=3 etcdctl endpoint status \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  --write-out=table

# --- RESTORE ---

# 1. Stop the API server (static pod — move manifest out)
mv /etc/kubernetes/manifests/kube-apiserver.yaml /tmp/kube-apiserver.yaml.bak

# 2. Restore snapshot to new directory
ETCDCTL_API=3 etcdctl snapshot restore \
  /backup/etcd.db \
  --data-dir /var/lib/etcd-restore

# 3. Update etcd manifest to point to restored directory
# Edit: /etc/kubernetes/manifests/etcd.yaml
# Change: --data-dir=/var/lib/etcd-restore

# 4. Start API server again
mv /tmp/kube-apiserver.yaml.bak /etc/kubernetes/manifests/kube-apiserver.yaml

# 5. Verify cluster is back
kubectl get nodes
kubectl get pods -A

# --- etcd defrag (reduce DB size after deletions) ---
ETCDCTL_API=3 etcdctl defrag \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key
```

---

## Certificate Management

```bash
# Check all certificate expiry dates
kubeadm certs check-expiration

# Renew all certificates
kubeadm certs renew all

# Renew specific certificates
kubeadm certs renew apiserver
kubeadm certs renew apiserver-kubelet-client
kubeadm certs renew etcd-server
kubeadm certs renew etcd-healthcheck-client
kubeadm certs renew front-proxy-client

# After renewal: restart control plane components
# (for static pods, kubelet auto-restarts them after process is killed)
kill $(pidof kube-apiserver)
kill $(pidof kube-controller-manager)
kill $(pidof kube-scheduler)

# Regenerate kubeconfig files after cert renewal
kubeadm init phase kubeconfig all
```

---

## Managed Cluster Upgrades

```bash
# --- EKS ---
# Upgrade control plane
aws eks update-cluster-version \
  --name <cluster-name> \
  --kubernetes-version 1.30

# Check upgrade status
aws eks describe-update \
  --name <cluster-name> \
  --update-id <update-id>

# Upgrade node group
aws eks update-nodegroup-version \
  --cluster-name <cluster-name> \
  --nodegroup-name <ng-name> \
  --kubernetes-version 1.30

# --- GKE ---
# Upgrade control plane
gcloud container clusters upgrade <cluster> \
  --master --cluster-version 1.30

# Upgrade node pool
gcloud container clusters upgrade <cluster> \
  --node-pool <pool-name> \
  --cluster-version 1.30

# --- AKS ---
az aks upgrade \
  --resource-group <rg> \
  --name <cluster> \
  --kubernetes-version 1.30
```

---

## Cluster Health and Debugging

```bash
# --- Recent events (best first debugging step) ---
kubectl get events -A --sort-by='.lastTimestamp' | tail -50
kubectl get events -n <namespace> --sort-by='.lastTimestamp'

# --- API server health ---
kubectl get --raw /healthz
kubectl get --raw /readyz
kubectl get --raw /livez

# --- Component status ---
kubectl get componentstatuses    # deprecated in 1.19+ but still works
kubectl get cs

# --- Node conditions ---
kubectl describe node <node> | grep -A 15 "Conditions:"

# --- Pod resource usage ---
kubectl top pods -A --sort-by=cpu
kubectl top pods -A --sort-by=memory

# --- etcd health ---
ETCDCTL_API=3 etcdctl endpoint health \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key

# --- kubelet status (SSH to the node first) ---
systemctl status kubelet
journalctl -u kubelet -n 100 --no-pager
```

---

## Resource Cleanup

```bash
# Delete failed and completed pods
kubectl delete pods -A --field-selector=status.phase==Failed
kubectl delete pods -A --field-selector=status.phase==Succeeded

# Delete completed jobs
kubectl delete jobs -A --field-selector=status.successful=1

# Find pods in problematic states
kubectl get pods -A | grep -E "Evicted|OOMKilled|Error|CrashLoopBackOff"

# Find unused PVCs (not bound)
kubectl get pvc -A | grep -v Bound

# Old ReplicaSets with 0 desired and 0 ready
kubectl get rs -A -o json | \
  jq '.items[] | select(.spec.replicas==0) | {name:.metadata.name, ns:.metadata.namespace}'

# Prune unused container images on a node (crictl)
crictl rmi --prune
```

---

## kubectl Context and Multi-Cluster

```bash
# List all contexts
kubectl config get-contexts
kubectl config current-context

# Switch context
kubectl config use-context <context-name>

# One-off command with different context
kubectl --context=production get pods -n my-app

# Rename or delete a context
kubectl config rename-context old-name new-name
kubectl config delete-context old-context

# View full kubeconfig
kubectl config view
kubectl config view --minify   # current context only

# Merge kubeconfigs
KUBECONFIG=~/.kube/config:~/.kube/prod-config \
  kubectl config view --flatten > ~/.kube/merged-config
```

---

## k9s Quick Reference

```bash
# Launch k9s
k9s
k9s --context production
k9s -n production              # start in specific namespace

# Key bindings inside k9s:
# :pods / :nodes / :deployments  — navigate to resource type
# /                              — search/filter
# d                              — describe resource
# l                              — show logs
# e                              — edit resource
# ctrl-d                         — delete resource
# ctrl-k                         — kill pod
# y                              — show YAML
# ESC                            — go back
```

---

## When to Use What

| Situation | Command |
|-----------|---------|
| Prevent new pods on a node | `kubectl cordon` |
| Empty a node for maintenance | `kubectl drain` |
| Return node to service | `kubectl uncordon` |
| Upgrade cluster | `kubeadm upgrade` (control plane first) |
| Backup cluster state | `etcdctl snapshot save` |
| Recover from total cluster loss | `etcdctl snapshot restore` |
| Check cert expiry | `kubeadm certs check-expiration` |
| Renew certs | `kubeadm certs renew all` |
| Manage multiple clusters | `kubectl config use-context` |

---

## 📂 Navigation

⬅️ **Prev:** [Advanced Scheduling](../27_Advanced_Scheduling/Interview_QA.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Backup and DR](../29_Backup_and_DR/Theory.md)

| | Link |
|---|---|
| Theory | [Theory.md](./Theory.md) |
| Interview Q&A | [Interview_QA.md](./Interview_QA.md) |
