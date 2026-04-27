# K8s Architecture — Code Examples

All examples are production-quality with detailed comments explaining every decision.

---

## 1. Inspecting Every Control Plane Component

```bash
# ── All control plane pods live in kube-system ─────────────────────────────────
kubectl get pods -n kube-system

# Expected output includes:
#   etcd-<node>                    — the cluster database
#   kube-apiserver-<node>          — the REST API front door
#   kube-controller-manager-<node> — reconciliation loops
#   kube-scheduler-<node>          — pod placement decisions
#   coredns-<hash>                 — cluster DNS
#   kube-proxy-<hash>              — per-node network rules

# ── Inspect the API server specifically ───────────────────────────────────────
kubectl describe pod kube-apiserver-<node-name> -n kube-system
# Look for: --etcd-servers, --service-cluster-ip-range, --tls-cert-file

# ── Check the scheduler is making decisions ───────────────────────────────────
kubectl logs kube-scheduler-<node-name> -n kube-system | tail -20
# You'll see lines like: "Successfully assigned default/my-pod to node-2"

# ── Watch controller manager reconciliations ──────────────────────────────────
kubectl logs kube-controller-manager-<node-name> -n kube-system | grep -i "reconcil" | tail -10

# ── Check node details — what kubelet reports ─────────────────────────────────
kubectl get nodes -o wide              # OS, container runtime version, internal IP
kubectl describe node <node-name>      # Allocated resources, conditions, running pods
```

---

## 2. Tracing a Pod's Journey Through the Architecture

This example creates a pod and uses kubectl to observe each architectural step.

```yaml
# trace-pod.yaml
# A minimal pod to watch flow through: API server → etcd → scheduler → kubelet
apiVersion: v1
kind: Pod
metadata:
  name: trace-demo
  labels:
    purpose: architecture-demo
spec:
  containers:
  - name: app
    image: nginx:1.25
    resources:
      requests:
        cpu: "50m"
        memory: "32Mi"
      limits:
        cpu: "100m"
        memory: "64Mi"
```

```bash
# Step 1: Submit to API server — it validates, authorizes, and writes to etcd
kubectl apply -f trace-pod.yaml

# Step 2: Pod starts in Pending state — no node assigned yet (scheduler hasn't run)
kubectl get pod trace-demo             # STATUS: Pending

# Step 3: Scheduler assigns the pod to a node (watch it happen)
kubectl get events --sort-by=.lastTimestamp | grep trace-demo
# You'll see: "Successfully assigned default/trace-demo to <node>"

# Step 4: kubelet on that node pulls the image and starts the container
kubectl get pod trace-demo --watch     # Watch: Pending → ContainerCreating → Running

# Step 5: See exactly which node was chosen by the scheduler
kubectl get pod trace-demo -o wide     # NODE column shows the assigned node

# Step 6: Read the full pod spec K8s has stored — includes all scheduler additions
kubectl get pod trace-demo -o yaml | grep -A 3 "nodeName\|schedulerName\|phase"

# Step 7: kubelet's health reporting — see conditions the kubelet sets
kubectl describe pod trace-demo | grep -A 10 "Conditions:"
# PodScheduled: True | Initialized: True | Ready: True | ContainersReady: True

# Clean up
kubectl delete pod trace-demo
```

---

## 3. etcd — The Source of Truth

```bash
# ── etcd runs as a static pod managed directly by kubelet ─────────────────────
kubectl get pod etcd-<node-name> -n kube-system -o yaml | grep -A 5 "command:"
# You'll see: --data-dir, --listen-client-urls, --advertise-client-urls

# ── etcd health check (run from inside the etcd pod) ─────────────────────────
kubectl exec -it etcd-<node-name> -n kube-system -- \
  etcdctl \
    --endpoints=https://127.0.0.1:2379 \
    --cacert=/etc/kubernetes/pki/etcd/ca.crt \
    --cert=/etc/kubernetes/pki/etcd/server.crt \
    --key=/etc/kubernetes/pki/etcd/server.key \
    endpoint health
# Output: https://127.0.0.1:2379 is healthy: successfully committed proposal

# ── Check cluster member list (important for HA: should be 3 or 5) ────────────
kubectl exec -it etcd-<node-name> -n kube-system -- \
  etcdctl \
    --endpoints=https://127.0.0.1:2379 \
    --cacert=/etc/kubernetes/pki/etcd/ca.crt \
    --cert=/etc/kubernetes/pki/etcd/server.crt \
    --key=/etc/kubernetes/pki/etcd/server.key \
    member list

# ── Backup etcd — the most critical operational task ──────────────────────────
# If etcd is lost without a backup, the cluster config is gone permanently
ETCDCTL_API=3 etcdctl \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot save /backup/etcd-snapshot-$(date +%Y%m%d-%H%M).db

# Verify the snapshot is valid
ETCDCTL_API=3 etcdctl snapshot status /backup/etcd-snapshot-*.db
```

---

## 4. Scheduler: Watching Filtering and Scoring Decisions

```yaml
# node-affinity-demo.yaml
# Shows the scheduler's filtering phase: only schedule to nodes with SSD storage
apiVersion: v1
kind: Pod
metadata:
  name: ssd-required-pod
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:  # Hard filter — no SSD = not scheduled
        nodeSelectorTerms:
        - matchExpressions:
          - key: storage-type                          # Node label to match
            operator: In
            values:
            - ssd                                      # Only nodes labeled storage-type=ssd
      preferredDuringSchedulingIgnoredDuringExecution: # Soft score — prefer us-east-1a
      - weight: 10                                     # Weight in scoring phase (1-100)
        preference:
          matchExpressions:
          - key: topology.kubernetes.io/zone
            operator: In
            values:
            - us-east-1a
  containers:
  - name: app
    image: nginx:1.25
    resources:
      requests:
        cpu: "100m"
        memory: "64Mi"
      limits:
        cpu: "200m"
        memory: "128Mi"
```

```bash
# Label a node to make it eligible (simulating SSD node)
kubectl label node <node-name> storage-type=ssd

# Apply — scheduler runs filter (must have ssd label) then score (prefer us-east-1a)
kubectl apply -f node-affinity-demo.yaml

# See which node was chosen
kubectl get pod ssd-required-pod -o wide

# Remove the label from all nodes to see Pending state (no node passes the filter)
kubectl label node <node-name> storage-type-            # Removes the label
kubectl delete pod ssd-required-pod
kubectl apply -f node-affinity-demo.yaml
kubectl get pod ssd-required-pod                        # STATUS: Pending — no eligible nodes

# Check the scheduling failure reason
kubectl describe pod ssd-required-pod | grep -A 5 "Events:"
# "0/N nodes are available: N node(s) didn't match Pod's node affinity/selector."

# Clean up
kubectl delete pod ssd-required-pod
kubectl label node <node-name> storage-type-
```

---

## 5. kubelet and kube-proxy — Node-Level Components

```bash
# ── kubelet runs as a systemd service, not a pod ──────────────────────────────
# (Run on a worker node directly — SSH into the node first)
systemctl status kubelet               # Shows kubelet PID, uptime, last restart
journalctl -u kubelet -n 50            # Last 50 log lines from kubelet

# Common kubelet log patterns:
# "Successfully pulled image" — image downloaded from registry
# "Created container"        — containerd created the container process
# "Started container"        — container PID 1 is running
# "Killing container"        — graceful termination signal sent

# ── Check what kubelet reports for node resources ─────────────────────────────
kubectl describe node <node-name> | grep -A 10 "Capacity:\|Allocatable:"
# Capacity:    — raw hardware (CPU cores, RAM, pods limit)
# Allocatable: — capacity minus what's reserved for system (kubelet, OS overhead)

# ── kube-proxy manages iptables rules for Services ────────────────────────────
kubectl get pods -n kube-system -l k8s-app=kube-proxy
kubectl logs -n kube-system -l k8s-app=kube-proxy | tail -20

# See the actual iptables rules kube-proxy created (run on the node)
iptables -t nat -L KUBE-SERVICES -n --line-numbers | head -30
# Each Service gets a chain here — traffic to the ClusterIP is redirected to pod IPs

# ── Check which container runtime kubelet is using ────────────────────────────
kubectl get node <node-name> -o jsonpath='{.status.nodeInfo.containerRuntimeVersion}'
# Output: containerd://1.7.x  or  cri-o://1.x.x
```

---

## 📂 Navigation

**In this folder:**
| File | |
|---|---|
| [📖 Theory.md](./Theory.md) | Full explanation |
| [⚡ Cheatsheet.md](./Cheatsheet.md) | Quick reference |
| [🎯 Interview_QA.md](./Interview_QA.md) | Interview prep |
| 💻 **Code_Example.md** | ← you are here |

⬅️ **Prev:** [What is Kubernetes](../01_What_is_Kubernetes/Code_Example.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Installation and Setup](../03_Installation_and_Setup/Code_Example.md)
🏠 **[Home](../../README.md)**
