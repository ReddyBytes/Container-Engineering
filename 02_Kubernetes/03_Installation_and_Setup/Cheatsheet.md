# Module 03 — Installation and Setup Cheatsheet

## minikube Commands

```bash
# Install (macOS)
brew install minikube

# Start default cluster
minikube start

# Start with specific version and resources
minikube start --kubernetes-version=v1.29.0 --cpus=4 --memory=8192

# Start with a specific driver
minikube start --driver=docker       # Run K8s nodes as containers
minikube start --driver=hyperkit     # macOS hypervisor
minikube start --driver=virtualbox   # VirtualBox VM

# Check cluster status
minikube status

# Stop cluster (state is preserved)
minikube stop

# Start stopped cluster
minikube start

# Delete cluster (removes all data)
minikube delete

# SSH into the minikube node
minikube ssh

# Get minikube node IP (useful for NodePort access)
minikube ip

# Open the Kubernetes dashboard
minikube dashboard

# Manage addons
minikube addons list
minikube addons enable metrics-server
minikube addons enable ingress
minikube addons enable registry

# Tunnel to expose LoadBalancer services (run in separate terminal)
minikube tunnel
```

## kind Commands

```bash
# Install (macOS)
brew install kind

# Create a single-node cluster
kind create cluster

# Create a named cluster
kind create cluster --name dev

# Create a multi-node cluster
kind create cluster --config kind-config.yaml

# List clusters
kind get clusters

# Get kubeconfig for a named cluster
kind get kubeconfig --name dev

# Load a local Docker image into kind cluster
kind load docker-image my-image:tag --name dev

# Delete a cluster
kind delete cluster --name dev
```

## kubectl Installation

```bash
# macOS
brew install kubectl

# Linux (latest stable)
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/kubectl

# Verify installation
kubectl version --client

# Enable shell autocompletion (bash)
source <(kubectl completion bash)
echo "source <(kubectl completion bash)" >> ~/.bashrc

# Enable shell autocompletion (zsh)
source <(kubectl completion zsh)
echo "source <(kubectl completion zsh)" >> ~/.zshrc

# Set alias (widely used in the community)
alias k=kubectl
complete -F __start_kubectl k
```

## kubeconfig Management

```bash
# View full kubeconfig
kubectl config view

# View kubeconfig with decoded secrets (be careful with this)
kubectl config view --raw

# Show current context
kubectl config current-context

# List all contexts
kubectl config get-contexts

# Switch context
kubectl config use-context <context-name>

# Set default namespace for current context
kubectl config set-context --current --namespace=<namespace>

# Add a new cluster entry
kubectl config set-cluster my-cluster --server=https://1.2.3.4:6443

# Rename a context
kubectl config rename-context old-name new-name

# Delete a context
kubectl config delete-context my-context

# Merge two kubeconfig files
KUBECONFIG=~/.kube/config:~/new-cluster.yaml kubectl config view --flatten > /tmp/merged
mv /tmp/merged ~/.kube/config

# Override kubeconfig location
kubectl --kubeconfig=/path/to/config get pods
# Or set environment variable
export KUBECONFIG=/path/to/config
```

## Namespace Commands

```bash
# List namespaces
kubectl get namespaces
kubectl get ns          # short form

# Create a namespace
kubectl create namespace dev
kubectl create ns dev   # short form

# Delete a namespace (deletes ALL resources in it)
kubectl delete namespace dev

# Run command in specific namespace
kubectl get pods -n kube-system

# Run command in all namespaces
kubectl get pods -A
kubectl get pods --all-namespaces

# Set default namespace for session (current context)
kubectl config set-context --current --namespace=dev

# See which namespace is currently default
kubectl config get-contexts | grep "*"
```

## Quick Cluster Verification

```bash
# Full health check sequence
kubectl get nodes                          # all should be Ready
kubectl get pods -n kube-system            # all should be Running
kubectl get componentstatuses              # all should be Healthy

# Run a temporary test pod and delete it when done
kubectl run test --image=busybox --rm -it --restart=Never -- sh

# Check that DNS works (from inside a pod)
kubectl run dns-test --image=busybox --rm -it --restart=Never -- nslookup kubernetes.default
```

---

## Navigation

| File | Description |
|------|-------------|
| [Theory.md](./Theory.md) | Installation options and concepts |
| [Cheatsheet.md](./Cheatsheet.md) | You are here — quick reference |
| [Interview_QA.md](./Interview_QA.md) | Interview questions and answers |
| [Code_Example.md](./Code_Example.md) | Hands-on setup walkthrough |

**Previous:** [02_K8s_Architecture](../02_K8s_Architecture/Cheatsheet.md) |
**Next:** [04_Pods](../04_Pods/Theory.md)
