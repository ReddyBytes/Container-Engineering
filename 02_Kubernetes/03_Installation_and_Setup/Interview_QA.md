# Module 03 — Interview Q&A: Installation and Setup

---

**Q1: What are the differences between minikube, kind, and k3d for local Kubernetes development?**

All three run Kubernetes locally for development and testing, but differ in approach:
- **minikube** creates a full single-node cluster in a VM (or Docker). It has the most built-in
  addons (dashboard, metrics-server, ingress) and is the best beginner choice.
- **kind** (Kubernetes IN Docker) runs K8s nodes as Docker containers. Faster startup than
  minikube, excellent for CI pipelines, and supports multi-node clusters via config file.
- **k3d** runs k3s (a lightweight K8s distribution) in Docker. The fastest startup, lowest
  resource usage, but uses k3s which strips some rarely-used features.

For learning: minikube. For CI testing: kind or k3d.

---

**Q2: What is kubeconfig and what does it contain?**

kubeconfig is a YAML file (default: `~/.kube/config`) that kubectl reads to know how to connect
to Kubernetes clusters. It contains three sections:
- **clusters**: API server URLs and the cluster's CA certificate for TLS verification
- **users**: authentication credentials (client certificates, tokens, or exec plugin commands)
- **contexts**: named pairings of a cluster + user + default namespace

The `current-context` field specifies which context is active. When you run any kubectl command,
it uses the active context's cluster and user settings.

---

**Q3: How do you switch between multiple Kubernetes clusters with kubectl?**

Using contexts. Each context maps a name to a cluster, user, and optional default namespace.
Commands:
```bash
kubectl config get-contexts         # list all contexts
kubectl config use-context staging  # switch to staging
kubectl config current-context      # show active context
```
Tools like `kubectx` provide an interactive TUI for faster switching. You can also set
`KUBECONFIG` environment variable to point to a specific kubeconfig file, or merge multiple
files with `KUBECONFIG=file1:file2 kubectl config view --flatten`.

---

**Q4: What is a Kubernetes namespace and why would you use one?**

A namespace is a virtual partition within a cluster that provides a scope for resource names,
RBAC policies, and resource quotas. You'd use namespaces to:
- Separate environments (dev, staging, prod) on the same cluster
- Isolate teams so each team only sees their resources
- Apply different resource quotas per team or environment
- Organize infrastructure tools (monitoring, logging) from application workloads

Resources with the same name can exist in different namespaces. However, cluster-scoped resources
(Nodes, PersistentVolumes, ClusterRoles) are not namespaced.

---

**Q5: What is kubeadm and when would you use it over a managed service?**

kubeadm is the official tool for bootstrapping production Kubernetes clusters on your own VMs
or bare metal. It initializes the control plane, generates certificates, and provides the join
command for worker nodes.

You'd choose kubeadm when:
- You need full control over the cluster configuration
- You're running on bare metal or private VMs
- Regulatory requirements prevent using cloud services
- You're studying for the CKA exam

For most teams, managed services (EKS, GKE, AKS) are a better choice because they handle the
control plane, HA etcd, certificate rotation, and version upgrades.

---

**Q6: How do you set a default namespace so you don't have to type -n every time?**

```bash
kubectl config set-context --current --namespace=my-namespace
```

This modifies the active context in kubeconfig to use `my-namespace` as the default. All
subsequent commands (without an explicit `-n` flag) will use that namespace. To see what's
currently set, run `kubectl config get-contexts`.

---

**Q7: What is the difference between `kubectl create` and `kubectl apply`?**

- `kubectl create` is imperative — it creates a new resource and fails if it already exists.
  Good for one-off resource creation but not idempotent.
- `kubectl apply` is declarative — it creates the resource if it doesn't exist, or updates it
  if it does. It stores the applied configuration as an annotation on the object for future
  diffing. This is the preferred approach for production workflows and GitOps.

Use `kubectl create` for quick testing; use `kubectl apply -f` for everything in production.

---

**Q8: How do you access a service running in minikube from your local browser?**

Three options:
1. **NodePort service**: minikube exposes NodePort services on the minikube IP.
   Run `minikube ip` to get the IP, then access `http://<minikube-ip>:<node-port>`.
2. **minikube service command**: `minikube service <service-name>` opens the service in your
   browser automatically and handles the IP/port.
3. **minikube tunnel**: for LoadBalancer services, run `minikube tunnel` in a separate terminal.
   It assigns a localhost IP to the LoadBalancer, making it accessible at `127.0.0.1`.

---

**Q9: What are the default namespaces in Kubernetes and what are they for?**

- `default`: resources created without specifying a namespace land here
- `kube-system`: Kubernetes system components (CoreDNS, kube-proxy, metrics-server, CNI plugins)
- `kube-public`: contains one ConfigMap (`cluster-info`) that is readable by all, including
  unauthenticated users — used for cluster discovery
- `kube-node-lease`: stores Lease objects for each node, which kubelet updates as heartbeats.
  The node controller uses these to detect node failures faster.

You should never deploy application workloads into `kube-system`.

---

**Q10: How does kubectl authenticate to the API server?**

kubectl supports multiple authentication methods, configured in kubeconfig:
- **Client certificates**: the most common for admin access — kubectl presents a TLS client
  certificate, the API server verifies it against the cluster CA
- **Bearer tokens**: a long-lived or short-lived token included in the HTTP Authorization header
- **OIDC tokens**: for enterprise SSO — kubectl fetches a JWT from an identity provider
- **Exec plugin**: runs an external command to fetch credentials (common with AWS: `aws eks
  get-token`). The cloud provider CLI returns a temporary token.

The API server then uses RBAC to determine what the authenticated identity is allowed to do.

---

## Navigation

| File | Description |
|------|-------------|
| [Theory.md](./Theory.md) | Installation options and concepts |
| [Cheatsheet.md](./Cheatsheet.md) | Quick reference commands |
| [Interview_QA.md](./Interview_QA.md) | You are here — interview questions |
| [Code_Example.md](./Code_Example.md) | Hands-on setup walkthrough |

**Previous:** [02_K8s_Architecture](../02_K8s_Architecture/Interview_QA.md) |
**Next:** [04_Pods](../04_Pods/Theory.md)
