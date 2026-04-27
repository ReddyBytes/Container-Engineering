# Module 03 — Code Examples: Installation and Setup

## Step 1: Install minikube and kubectl

```bash
# macOS with Homebrew
brew install minikube kubectl

# Verify both are installed
minikube version
kubectl version --client

# Expected output:
# minikube version: v1.32.0
# Client Version: v1.29.0
```

## Step 2: Start Your First Cluster

```bash
# Start minikube with Docker driver (no VM needed)
minikube start --driver=docker --cpus=2 --memory=4096

# You should see:
# * minikube v1.32.0 on Darwin
# * Using the docker driver
# * Starting control plane node minikube
# * Pulling base image ...
# * Preparing Kubernetes v1.29.0 on Docker 24.0.7 ...
# * Done! kubectl is now configured to use "minikube" cluster

# Confirm the cluster is running
minikube status
# Output:
# minikube
# type: Control Plane
# host: Running
# kubelet: Running
# apiserver: Running
# kubeconfig: Configured
```

## Step 3: Verify kubectl Can Talk to the Cluster

```bash
# Check nodes — you should see one node in Ready state
kubectl get nodes

# NAME       STATUS   ROLES           AGE   VERSION
# minikube   Ready    control-plane   2m    v1.29.0

# Check system pods are running
kubectl get pods -n kube-system

# View cluster info
kubectl cluster-info
```

## Step 4: Run Your First Pod

```bash
# Run a simple nginx pod imperatively (for quick testing)
kubectl run my-nginx --image=nginx:1.25

# Watch it start up
kubectl get pods --watch
# NAME       READY   STATUS    RESTARTS   AGE
# my-nginx   0/1     Pending   0          2s
# my-nginx   0/1     ContainerCreating   0   3s
# my-nginx   1/1     Running   0          5s

# Describe the pod to see what happened
kubectl describe pod my-nginx

# View the logs
kubectl logs my-nginx

# Access the nginx server (port-forward locally)
kubectl port-forward pod/my-nginx 8080:80
# Now visit http://localhost:8080 in your browser

# Clean up
kubectl delete pod my-nginx
```

## Step 5: Understand the kubeconfig File

```bash
# View your kubeconfig
kubectl config view

# The output looks like this (simplified):
# apiVersion: v1
# clusters:
# - cluster:
#     certificate-authority: /home/user/.minikube/ca.crt
#     server: https://192.168.49.2:8443
#   name: minikube
# contexts:
# - context:
#     cluster: minikube
#     user: minikube
#   name: minikube
# current-context: minikube
# users:
# - name: minikube
#   user:
#     client-certificate: /home/user/.minikube/profiles/minikube/client.crt
#     client-key: /home/user/.minikube/profiles/minikube/client.key

# View the actual file
cat ~/.kube/config

# The --raw flag decodes base64 values (careful — shows actual secrets)
kubectl config view --raw
```

## Step 6: Context Switching

```bash
# Imagine you have three clusters: minikube, staging, production
# List all contexts
kubectl config get-contexts

# CURRENT   NAME         CLUSTER      AUTHINFO   NAMESPACE
# *         minikube     minikube     minikube   default
#           staging      staging      staging    default
#           production   production   prod-user  production

# Switch to staging
kubectl config use-context staging

# Confirm the switch
kubectl config current-context
# staging

# Switch back to minikube
kubectl config use-context minikube

# Set default namespace for current context
# (avoids having to type -n my-namespace on every command)
kubectl config set-context --current --namespace=development

# Verify
kubectl config get-contexts
# CURRENT   NAME       CLUSTER    AUTHINFO   NAMESPACE
# *         minikube   minikube   minikube   development
```

## Step 7: Working with kind (Kubernetes IN Docker)

```bash
# Install kind
brew install kind

# Create a simple single-node cluster
kind create cluster --name local-dev

# Create a multi-node cluster using a config file
cat > kind-multinode.yaml << 'EOF'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
- role: worker
- role: worker
EOF

kind create cluster --name multi-node --config kind-multinode.yaml

# Verify nodes
kubectl get nodes
# NAME                       STATUS   ROLES           AGE
# multi-node-control-plane   Ready    control-plane   90s
# multi-node-worker          Ready    <none>          60s
# multi-node-worker2         Ready    <none>          60s

# kind clusters use a separate kubeconfig context automatically
kubectl config get-contexts
# CURRENT   NAME                   CLUSTER                ...
# *         kind-multi-node        kind-multi-node
#           kind-local-dev         kind-local-dev
#           minikube               minikube

# Switch between them
kubectl config use-context kind-local-dev
kubectl config use-context minikube

# Load a locally-built Docker image into kind
docker build -t my-app:v1 .
kind load docker-image my-app:v1 --name local-dev

# Delete a kind cluster
kind delete cluster --name multi-node
kind delete cluster --name local-dev
```

## Step 8: Create a Namespace and Deploy Into It

```yaml
# Save as: namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: my-app             # Name of the namespace
  labels:
    team: backend           # Optional labels for organizing
    environment: dev
```

```bash
# Create the namespace
kubectl apply -f namespace.yaml

# Verify
kubectl get namespaces

# Deploy something into the new namespace
kubectl run test-pod \
  --image=nginx:1.25 \
  --namespace=my-app

# Check it's there
kubectl get pods -n my-app

# Set my-app as default namespace so you don't need -n
kubectl config set-context --current --namespace=my-app
kubectl get pods   # same result, no -n needed

# List resources across ALL namespaces at once
kubectl get pods -A
```

## Step 9: Useful kubectl Aliases and Shortcuts

```bash
# Add to your ~/.bashrc or ~/.zshrc:

# Short alias
alias k=kubectl

# Context and namespace switching (requires kubectx and kubens)
# brew install kubectx

# Quick pod listing across all namespaces
alias kga='kubectl get all -A'

# Watch pods
alias kw='kubectl get pods --watch'

# Describe pod shortcut
alias kdp='kubectl describe pod'

# Logs follow
alias kl='kubectl logs -f'

# Apply file
alias kaf='kubectl apply -f'

# Delete file
alias kdf='kubectl delete -f'
```

---

## 📂 Navigation

| File | Description |
|------|-------------|
| [Theory.md](./Theory.md) | Installation options and concepts |
| [Cheatsheet.md](./Cheatsheet.md) | Quick reference commands |
| [Interview_QA.md](./Interview_QA.md) | Interview questions and answers |
| [Code_Example.md](./Code_Example.md) | You are here — hands-on setup walkthrough |

**Previous:** [02_K8s_Architecture](../02_K8s_Architecture/Theory.md) |
**Next:** [04_Pods](../04_Pods/Theory.md)
