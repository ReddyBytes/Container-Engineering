# Module 01 — Kubernetes Basics Cheatsheet

## Cluster Inspection

```bash
# Check kubectl is installed and view its version
kubectl version --client

# View cluster info (API server URL)
kubectl cluster-info

# List all nodes in the cluster
kubectl get nodes

# List nodes with extra details (IP, OS, container runtime)
kubectl get nodes -o wide

# Describe a specific node (capacity, conditions, running pods)
kubectl describe node <node-name>
```

## Namespaces

```bash
# List all namespaces
kubectl get namespaces

# Short form
kubectl get ns

# List pods in a specific namespace
kubectl get pods -n kube-system

# List pods across ALL namespaces
kubectl get pods --all-namespaces
kubectl get pods -A           # short form
```

## Basic Resource Commands (works for most resource types)

```bash
# Get resources (pods, deployments, services, etc.)
kubectl get pods
kubectl get deployments
kubectl get services

# Get with more details
kubectl get pods -o wide

# Get as YAML (great for inspecting live configs)
kubectl get pod <pod-name> -o yaml

# Get as JSON
kubectl get pod <pod-name> -o json

# Watch live updates (re-runs every 2 seconds)
kubectl get pods --watch
kubectl get pods -w           # short form
```

## Applying and Deleting Resources

```bash
# Apply a YAML file (create or update)
kubectl apply -f my-resource.yaml

# Apply all YAML files in a directory
kubectl apply -f ./manifests/

# Delete a resource defined in a YAML file
kubectl delete -f my-resource.yaml

# Delete a specific pod by name
kubectl delete pod <pod-name>

# Force delete a stuck pod (use with caution)
kubectl delete pod <pod-name> --grace-period=0 --force
```

## Debugging Basics

```bash
# Show detailed info about a resource (events are at the bottom — read them!)
kubectl describe pod <pod-name>

# Tail logs from a pod's main container
kubectl logs <pod-name>

# Follow live logs
kubectl logs -f <pod-name>

# Logs from a specific container in a multi-container pod
kubectl logs <pod-name> -c <container-name>

# Open an interactive shell in a running pod
kubectl exec -it <pod-name> -- /bin/sh

# Run a one-off debug pod (busybox with network tools)
kubectl run debug --image=busybox --rm -it --restart=Never -- sh
```

## kubectl Configuration

```bash
# View current kubeconfig
kubectl config view

# See which context (cluster) you're currently talking to
kubectl config current-context

# List all contexts
kubectl config get-contexts

# Switch to a different context
kubectl config use-context <context-name>

# Set default namespace for current context
kubectl config set-context --current --namespace=<namespace>
```

## Helpful Output Flags

```bash
# Custom columns output
kubectl get pods -o custom-columns=NAME:.metadata.name,STATUS:.status.phase

# Sort by a field
kubectl get pods --sort-by=.metadata.creationTimestamp

# Filter by label
kubectl get pods -l app=nginx

# Show labels on resources
kubectl get pods --show-labels
```

---

## Navigation

| File | Description |
|------|-------------|
| [Theory.md](./Theory.md) | What is Kubernetes? Full explanation |
| [Cheatsheet.md](./Cheatsheet.md) | You are here — quick reference |
| [Interview_QA.md](./Interview_QA.md) | Interview questions and answers |

**Previous:** [01_Docker](../../01_Docker/) |
**Next:** [02_K8s_Architecture](../02_K8s_Architecture/Theory.md)
