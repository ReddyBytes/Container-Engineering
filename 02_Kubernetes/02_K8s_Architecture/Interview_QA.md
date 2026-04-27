# Module 02 — Interview Q&A: Kubernetes Architecture

---

**Q1: Describe the main components of the Kubernetes control plane.**

The control plane consists of:
- **kube-apiserver**: the REST API front door; all cluster operations flow through it
- **etcd**: the distributed key-value store that holds all cluster state
- **kube-scheduler**: assigns pending pods to nodes using filtering and scoring
- **kube-controller-manager**: runs control loops (ReplicaSet, Deployment, Node, etc.)
- **cloud-controller-manager**: integrates with cloud provider APIs for load balancers, volumes, etc.

The API server is the only component that communicates directly with etcd. All other components
interact through the API server.

---

**Q2: What is etcd and why is it critical to Kubernetes?**

etcd is a distributed key-value store built on the Raft consensus algorithm. It is the single
source of truth for all Kubernetes cluster state — every object (pods, deployments, secrets,
configmaps) is stored here. If etcd is lost without a backup, the entire cluster configuration
is gone. This makes etcd backup the most important operational task. In production, etcd is
typically run as a 3-node cluster to tolerate one node failure while maintaining consensus.

---

**Q3: How does the Kubernetes scheduler decide where to place a pod?**

The scheduler runs two phases:
1. **Filtering**: eliminates nodes that cannot run the pod (insufficient resources, wrong labels,
   failing taints, missing topology requirements)
2. **Scoring**: ranks the remaining nodes by multiple criteria (resource availability, affinity
   preferences, spread requirements) and assigns a weighted score

The pod is assigned to the highest-scoring node by writing the `nodeName` field to the pod object
in etcd. The scheduler itself does not start the container — kubelet handles that.

---

**Q4: What is the reconciliation loop and which components use it?**

The reconciliation loop is a control pattern: continuously compare desired state (from the API
server) to actual state, and take action when they differ. Almost every Kubernetes component
uses it:
- Controller manager controllers (ReplicaSet, Deployment, Node, etc.)
- The scheduler (watches for unscheduled pods)
- kubelet (watches for pods assigned to its node)

This loop is idempotent — running it multiple times is safe. It also means K8s is self-healing
by design: controllers keep comparing and correcting indefinitely.

---

**Q5: What is kubelet and what is its role?**

kubelet is an agent running on every worker node. It:
- Watches the API server for pods assigned to its node
- Tells the container runtime (containerd) to pull images and start containers
- Runs health probes (liveness, readiness, startup) against running containers
- Reports container and node status back to the API server

kubelet only manages containers it knows about — containers started outside of Kubernetes are
invisible to it.

---

**Q6: What is kube-proxy and how does it implement Service routing?**

kube-proxy runs on every node and programs network routing rules so that traffic sent to a
Service's virtual IP (ClusterIP) gets forwarded to one of the backend pods. In the default
iptables mode, it writes DNAT rules in the iptables PREROUTING chain. When a packet hits
the ClusterIP, iptables randomly selects a pod IP and rewrites the packet destination.

In IPVS mode, it uses the Linux kernel's IPVS load balancer, which uses hash tables for O(1)
lookup — better performance at large scale (thousands of services).

---

**Q7: What is the difference between the control plane and worker nodes?**

The **control plane** hosts the management components — API server, etcd, scheduler, controller
manager. It makes decisions about the cluster but does not run application workloads (in most
setups). The **worker nodes** are where application pods actually run. They host kubelet,
kube-proxy, and a container runtime. Worker nodes register themselves with the control plane
and receive instructions from it.

---

**Q8: How does kubectl communicate with the cluster?**

kubectl reads a kubeconfig file (default: `~/.kube/config`) that contains the API server URL,
TLS certificates for authentication, and context definitions. Each context maps to a cluster,
a user (credentials), and a default namespace. kubectl makes HTTPS REST calls to the API server
using the credentials in the active context. You can see exactly what HTTP calls it makes with
the `--v=8` verbosity flag.

---

**Q9: What happens when a node fails in Kubernetes?**

1. The kubelet on the failed node stops sending heartbeats to the API server
2. The Node controller (in controller manager) marks the node `NotReady` after ~40 seconds
3. After the pod eviction timeout (default 5 minutes), the Node controller evicts all pods
   from the failed node by setting their status to `Terminating`
4. The ReplicaSet controller notices the replicas are below the desired count and creates
   replacement pods on healthy nodes
5. The scheduler assigns the new pods to healthy nodes and they start running there

Total recovery time is typically 5–10 minutes unless you reduce the eviction timeout.

---

**Q10: What are admission controllers?**

Admission controllers are plugins in the API server request pipeline that run after authentication
and authorization but before the object is written to etcd. There are two types:
- **Mutating**: can modify the request (e.g., inject sidecar containers, add default resource limits)
- **Validating**: can approve or reject the request (e.g., require certain labels, enforce naming
  conventions)

They run in order: mutating webhooks run first (so validators see the final object). Important
examples: LimitRanger, ResourceQuota, PodSecurity, and custom webhooks for tools like Istio,
Kyverno, and OPA/Gatekeeper.

---

**Q11: What is a static pod?**

A static pod is a pod defined by a YAML file in a directory on the node (typically
`/etc/kubernetes/manifests/`) that kubelet manages directly, without involving the API server
to schedule it. The control plane components themselves — kube-apiserver, kube-scheduler,
kube-controller-manager, and etcd — run as static pods in kubeadm-managed clusters. Static
pods always have the node name appended to their name (e.g., `kube-apiserver-master-node`).

---

**Q12: What is the difference between the API server and the controller manager?**

The API server is a stateless gateway — it validates, authenticates, and persists objects to
etcd, and exposes a REST API. It has no business logic about what should exist.

The controller manager contains the business logic — it watches the API server for changes and
reconciles actual state to desired state. For example, when you create a Deployment, the API
server stores it; the controller manager notices it and creates ReplicaSets and Pods.

---

## 📂 Navigation

| File | Description |
|------|-------------|
| [Theory.md](./Theory.md) | Architecture overview |
| [Architecture_Deep_Dive.md](./Architecture_Deep_Dive.md) | Component deep dives |
| [Cheatsheet.md](./Cheatsheet.md) | Quick reference commands |
| [Interview_QA.md](./Interview_QA.md) | You are here — interview questions |

**Previous:** [01_What_is_Kubernetes](../01_What_is_Kubernetes/Interview_QA.md) |
**Next:** [03_Installation_and_Setup](../03_Installation_and_Setup/Theory.md)
