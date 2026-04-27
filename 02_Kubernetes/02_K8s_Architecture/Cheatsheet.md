# Module 02 — Kubernetes Architecture Cheatsheet

## Inspecting Cluster Components

```bash
# View all control plane components (in kube-system namespace)
kubectl get pods -n kube-system

# Check API server, etcd, scheduler, controller-manager status
kubectl get componentstatuses
# or
kubectl get cs

# Describe a specific component pod
kubectl describe pod kube-apiserver-<node-name> -n kube-system

# Check the Kubernetes version of the API server
kubectl version

# View API server audit logs (location varies by setup)
# kubeadm: /var/log/kubernetes/audit.log
```

## Nodes

```bash
# List all nodes
kubectl get nodes

# Detailed node view (IP, OS, container runtime, K8s version)
kubectl get nodes -o wide

# Describe a node (capacity, allocatable, conditions, events)
kubectl describe node <node-name>

# Show node resource usage (requires metrics-server)
kubectl top nodes

# Cordon a node (prevent new pods from scheduling)
kubectl cordon <node-name>

# Uncordon a node (allow scheduling again)
kubectl uncordon <node-name>

# Drain a node (evict all pods, cordon the node)
# Use before maintenance or node removal
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data

# Label a node
kubectl label node <node-name> disktype=ssd

# Remove a label from a node
kubectl label node <node-name> disktype-

# Taint a node (repel pods that don't tolerate the taint)
kubectl taint nodes <node-name> key=value:NoSchedule

# Remove a taint
kubectl taint nodes <node-name> key=value:NoSchedule-
```

## etcd Operations (run on control plane node)

```bash
# Check etcd cluster health
ETCDCTL_API=3 etcdctl endpoint health \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key

# List all etcd members
ETCDCTL_API=3 etcdctl member list \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key

# Take an etcd snapshot backup
ETCDCTL_API=3 etcdctl snapshot save /backup/snapshot.db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key

# Verify snapshot
ETCDCTL_API=3 etcdctl snapshot status /backup/snapshot.db --write-out=table
```

## API Server Exploration

```bash
# List all available API groups and versions
kubectl api-versions

# List all available resource types
kubectl api-resources

# List resource types that are namespaced
kubectl api-resources --namespaced=true

# List resource types that are NOT namespaced (cluster-scoped)
kubectl api-resources --namespaced=false

# Explain a resource's fields (great for learning YAML structure)
kubectl explain pod
kubectl explain pod.spec
kubectl explain pod.spec.containers
kubectl explain deployment.spec.strategy
```

## Watching and Events

```bash
# Watch events in real time (great for debugging scheduling issues)
kubectl get events --sort-by=.lastTimestamp
kubectl get events -w

# Events in a specific namespace
kubectl get events -n kube-system

# Events for a specific resource
kubectl describe pod <pod-name>  # events section at bottom

# View all events across namespaces sorted by time
kubectl get events -A --sort-by=.lastTimestamp
```

## Checking Logs of Control Plane Components

```bash
# In kubeadm clusters, control plane components run as pods
kubectl logs kube-apiserver-<node> -n kube-system
kubectl logs kube-scheduler-<node> -n kube-system
kubectl logs kube-controller-manager-<node> -n kube-system
kubectl logs etcd-<node> -n kube-system

# On the node directly (for kubelet — not a pod)
journalctl -u kubelet -f
journalctl -u kubelet --since "5 min ago"

# Container runtime logs
journalctl -u containerd -f
```

---

## 📂 Navigation

| File | Description |
|------|-------------|
| [Theory.md](./Theory.md) | Architecture overview |
| [Architecture_Deep_Dive.md](./Architecture_Deep_Dive.md) | Component deep dives |
| [Cheatsheet.md](./Cheatsheet.md) | You are here — quick reference |
| [Interview_QA.md](./Interview_QA.md) | Interview questions and answers |

**Previous:** [01_What_is_Kubernetes](../01_What_is_Kubernetes/Cheatsheet.md) |
**Next:** [03_Installation_and_Setup](../03_Installation_and_Setup/Theory.md)
