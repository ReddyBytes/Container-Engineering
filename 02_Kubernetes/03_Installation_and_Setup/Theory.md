# Module 03 — Installation and Setup

## The Local vs. Production Question

Before you write a single line of Kubernetes YAML, you need a cluster to run it on. The options
range from a single-command local cluster on your laptop to a fully managed cloud service handling
thousands of nodes. Let's start with what you'll use most as a beginner: local development clusters.

---

## Local Development Options

### minikube

minikube is the most beginner-friendly way to run Kubernetes locally. It creates a single-node
cluster either in a VM (using VirtualBox, HyperKit, or Hyper-V) or in a Docker container.

**Best for**: Learning, trying out features, running the official Kubernetes tutorials.

**How it works**: minikube downloads a Kubernetes release and starts a VM (or container) with
both control plane and worker components running on the same machine. Everything — API server,
etcd, scheduler, kubelet — runs together on this single "node."

```bash
# Install minikube (macOS)
brew install minikube

# Start a cluster
minikube start

# Start with specific Kubernetes version
minikube start --kubernetes-version=v1.29.0

# Start with more resources
minikube start --cpus=4 --memory=8192

# Add additional nodes
minikube node add

# Stop the cluster (preserves state)
minikube stop

# Delete the cluster entirely
minikube delete
```

Minikube also comes with addons you can enable:

```bash
minikube addons list
minikube addons enable ingress          # nginx ingress controller
minikube addons enable metrics-server   # CPU/memory metrics
minikube addons enable dashboard        # web UI
minikube dashboard                      # open the dashboard
```

### kind (Kubernetes IN Docker)

kind runs Kubernetes nodes as Docker containers. It's fast to start (no VM overhead), great for
CI/CD pipelines, and supports multi-node clusters with a simple config file.

**Best for**: CI pipelines, testing controllers and operators, multi-node topology testing.

```bash
# Install kind (macOS)
brew install kind

# Create a single-node cluster
kind create cluster

# Create a named cluster
kind create cluster --name my-cluster

# Create a multi-node cluster with a config file
kind create cluster --config kind-config.yaml

# Load a local Docker image into kind (kind can't pull from local Docker daemon)
kind load docker-image my-app:local

# Delete a cluster
kind delete cluster --name my-cluster
```

Example `kind-config.yaml` for a multi-node cluster:

```yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
- role: worker
- role: worker
```

### k3d

k3d is k3s (a lightweight K8s distribution from Rancher) running in Docker. It starts even
faster than kind because k3s is a stripped-down Kubernetes.

**Best for**: Edge computing simulation, fast iteration, low-resource laptops.

```bash
# Install k3d (macOS)
brew install k3d

# Create a cluster
k3d cluster create my-cluster

# Create with multiple workers
k3d cluster create my-cluster --agents 2

# List clusters
k3d cluster list

# Delete
k3d cluster delete my-cluster
```

### Comparison

| Feature | minikube | kind | k3d |
|---------|----------|------|-----|
| Startup time | 2–3 min | 30–60 sec | 15–30 sec |
| Multi-node | Yes (addons) | Yes (config) | Yes (flags) |
| Resource usage | High (VM) | Medium | Low |
| CI-friendly | Possible | Yes | Yes |
| Addons/dashboard | Built-in | Manual | Manual |
| Best for | Learning | Testing | Speed |

---

## Production Options

### kubeadm

kubeadm is the official tool for bootstrapping production-grade Kubernetes clusters on bare metal
or cloud VMs. It handles the initial cluster setup but leaves ongoing operations to you.

```bash
# On control plane node
kubeadm init --pod-network-cidr=10.244.0.0/16

# Then copy the kubeconfig:
mkdir -p $HOME/.kube
cp /etc/kubernetes/admin.conf $HOME/.kube/config

# Install a CNI plugin (e.g., Flannel)
kubectl apply -f https://raw.githubusercontent.com/flannel-io/flannel/master/Documentation/kube-flannel.yml

# On worker nodes, join the cluster:
kubeadm join <control-plane-ip>:6443 --token <token> --discovery-token-ca-cert-hash sha256:<hash>
```

### Managed Kubernetes Services

Managed services handle the control plane for you — you never see the etcd nodes, you don't
upgrade the API server, the cloud provider handles HA and backups. You only manage worker nodes.

| Service | Provider | Notes |
|---------|----------|-------|
| EKS | AWS | Most widely deployed. Integrates with IAM, ALB, EBS |
| GKE | Google | Best autopilot mode. Easiest to get started |
| AKS | Azure | Good for Microsoft ecosystem |
| DigitalOcean K8s | DigitalOcean | Simple, affordable for small teams |
| Linode K8s | Akamai | Budget-friendly |

For new teams, **managed Kubernetes is almost always the right choice**. The control plane
complexity alone (HA etcd, certificate rotation, upgrades) can consume significant engineering time.

---

## kubectl: The Swiss Army Knife

kubectl (pronounced "kube-c-t-l", "kube-control", or "kube-cuddle" depending on who you ask) is
the primary command-line interface for Kubernetes. You use it for everything:

- Creating and updating resources (`kubectl apply`)
- Inspecting resources (`kubectl get`, `kubectl describe`)
- Debugging (`kubectl logs`, `kubectl exec`)
- Managing cluster config (`kubectl config`)

Install kubectl:

```bash
# macOS
brew install kubectl

# Linux
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl && sudo mv kubectl /usr/local/bin/

# Windows (winget)
winget install -e --id Kubernetes.kubectl

# Verify
kubectl version --client
```

---

## kubeconfig: How kubectl Knows Where to Connect

kubeconfig is a YAML file (default: `~/.kube/config`) that tells kubectl how to connect to
Kubernetes clusters. It contains three kinds of entries:

1. **clusters**: API server URLs and TLS certificates
2. **users**: credentials (certificates, tokens, exec plugins)
3. **contexts**: a named pairing of a cluster + a user + a default namespace

```yaml
# Simplified kubeconfig structure
apiVersion: v1
kind: Config

clusters:
- name: my-cluster
  cluster:
    server: https://192.168.99.100:8443
    certificate-authority-data: <base64-encoded-CA-cert>

users:
- name: my-user
  user:
    client-certificate-data: <base64-encoded-cert>
    client-key-data: <base64-encoded-key>

contexts:
- name: my-context
  context:
    cluster: my-cluster
    user: my-user
    namespace: default

current-context: my-context
```

When you run `kubectl get pods`, it reads the current context, finds the associated cluster and
user, and makes an HTTPS call to the cluster's API server using the user's credentials.

---

## Contexts: Switching Between Clusters

A context is just a bookmark — a named combination of cluster + user + namespace. Real-world
engineers work with multiple clusters daily (dev, staging, prod, different regions). Contexts
make switching easy.

```bash
# View all contexts
kubectl config get-contexts

# Switch to a different context
kubectl config use-context production

# See current context
kubectl config current-context

# Rename a context
kubectl config rename-context old-name new-name

# Set default namespace for the current context (avoids typing -n every time)
kubectl config set-context --current --namespace=my-team

# Merge multiple kubeconfig files
KUBECONFIG=~/.kube/config:~/.kube/cluster2.yaml kubectl config view --merge --flatten > ~/.kube/config
```

Tools like **kubectx** and **kubens** make context and namespace switching even faster:

```bash
# kubectx: switch contexts interactively
kubectx production

# kubens: switch default namespace interactively
kubens my-team
```

---

## Namespaces Introduction

A namespace is a virtual partition within a Kubernetes cluster. Resources in one namespace are
isolated from resources in another (from a naming, RBAC, and quota perspective — not a network
perspective by default).

Default namespaces in every cluster:

| Namespace | Purpose |
|-----------|---------|
| `default` | Where resources go if you don't specify a namespace |
| `kube-system` | Kubernetes system components (DNS, proxy, metrics-server) |
| `kube-public` | Publicly readable resources (cluster info ConfigMap) |
| `kube-node-lease` | Node heartbeat lease objects (for faster node failure detection) |

Common real-world usage:
- `dev`, `staging`, `production` — environment separation on one cluster
- `team-frontend`, `team-backend` — team isolation
- `monitoring`, `logging` — infrastructure tools

```bash
# Create a namespace
kubectl create namespace my-namespace

# Or with YAML (preferred)
kubectl apply -f - <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: my-namespace
EOF

# Run commands in a specific namespace
kubectl get pods -n my-namespace

# Run commands across all namespaces
kubectl get pods -A
```

---

## Verifying Your Cluster is Working

After setting up a cluster, run this quick check:

```bash
# Nodes should be Ready
kubectl get nodes

# System pods should be Running
kubectl get pods -n kube-system

# Create a test pod
kubectl run test --image=nginx --rm -it -- /bin/sh

# Inside the shell, try:
# curl localhost  → should return nginx HTML
# exit
```

If all nodes show `Ready` and system pods show `Running`, your cluster is healthy.

---

## Navigation

| File | Description |
|------|-------------|
| [Theory.md](./Theory.md) | You are here — installation options and concepts |
| [Cheatsheet.md](./Cheatsheet.md) | Quick reference commands |
| [Interview_QA.md](./Interview_QA.md) | Interview questions and answers |
| [Code_Example.md](./Code_Example.md) | Hands-on setup walkthrough |

**Previous:** [02_K8s_Architecture](../02_K8s_Architecture/Theory.md) |
**Next:** [04_Pods](../04_Pods/Theory.md)
