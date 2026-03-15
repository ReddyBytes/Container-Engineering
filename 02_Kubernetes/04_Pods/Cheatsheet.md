# Module 04 — Pods Cheatsheet

## Getting Pod Info

```bash
# List all pods in current namespace
kubectl get pods

# List with extra info (node, IP)
kubectl get pods -o wide

# List pods in all namespaces
kubectl get pods -A

# Watch pods live (refreshes on change)
kubectl get pods --watch
kubectl get pods -w

# List pods with labels shown
kubectl get pods --show-labels

# List pods filtered by label
kubectl get pods -l app=nginx
kubectl get pods -l app=nginx,version=1.0   # multiple labels (AND)

# Sort by creation time
kubectl get pods --sort-by=.metadata.creationTimestamp

# Get pod YAML (shows live configuration including K8s-added fields)
kubectl get pod <pod-name> -o yaml

# Get pod in JSON format
kubectl get pod <pod-name> -o json

# Quick status summary
kubectl get pod <pod-name> -o jsonpath='{.status.phase}'
```

## Creating and Deleting Pods

```bash
# Run a pod imperatively (testing only, avoid in production)
kubectl run my-pod --image=nginx:1.25

# Run a temporary pod and delete when shell exits
kubectl run debug --image=busybox --rm -it --restart=Never -- sh

# Run a pod with a command
kubectl run my-job --image=busybox --restart=Never -- echo "hello world"

# Create a pod from YAML
kubectl apply -f pod.yaml

# Delete a pod (graceful shutdown, default 30-second grace period)
kubectl delete pod my-pod

# Delete all pods matching a label
kubectl delete pods -l app=old-version

# Force delete a stuck pod (skips graceful shutdown)
kubectl delete pod my-pod --grace-period=0 --force

# Delete pod and wait until it's gone
kubectl delete pod my-pod --wait=true
```

## Inspecting and Debugging Pods

```bash
# Detailed info about a pod (events are the most useful part)
kubectl describe pod <pod-name>

# View container logs
kubectl logs <pod-name>

# Follow logs in real time
kubectl logs -f <pod-name>

# Logs for a specific container in a multi-container pod
kubectl logs <pod-name> -c <container-name>

# Previous container logs (after a crash/restart)
kubectl logs <pod-name> --previous
kubectl logs <pod-name> -p

# Last 100 lines of logs
kubectl logs <pod-name> --tail=100

# Logs since a time period
kubectl logs <pod-name> --since=1h
kubectl logs <pod-name> --since=30m

# Execute a command in a running pod
kubectl exec <pod-name> -- ls /app

# Open an interactive shell
kubectl exec -it <pod-name> -- /bin/bash
kubectl exec -it <pod-name> -- /bin/sh       # if bash is not available

# Exec into a specific container in multi-container pod
kubectl exec -it <pod-name> -c <container-name> -- /bin/sh

# Copy file from pod to local
kubectl cp <pod-name>:/path/in/pod ./local/path

# Copy file from local to pod
kubectl cp ./local/file <pod-name>:/path/in/pod
```

## Port Forwarding

```bash
# Forward local port 8080 to pod port 80
kubectl port-forward pod/<pod-name> 8080:80

# Forward to a service instead (traffic goes through the service)
kubectl port-forward service/<service-name> 8080:80

# Run in background
kubectl port-forward pod/<pod-name> 8080:80 &
```

## Resource Management

```bash
# Check resource usage of pods (requires metrics-server)
kubectl top pods

# Check resource usage of pods in all namespaces
kubectl top pods -A

# Check resource usage of a specific pod
kubectl top pod <pod-name>

# Check resource usage of containers in a pod
kubectl top pod <pod-name> --containers
```

## Pod Conditions and Status

```bash
# Check why a pod is pending (look at Events and Conditions)
kubectl describe pod <pending-pod>

# Common states and what they mean:
# Pending         - waiting for scheduling or image pull
# ContainerCreating - image pulling or volume mounting
# Running         - at least one container is running
# CrashLoopBackOff - container keeps crashing; K8s adds delay between restarts
# OOMKilled       - container exceeded memory limit
# ImagePullBackOff - can't pull the image (wrong name, no registry access)
# Terminating     - being deleted (stuck = node may be down, force delete if needed)
# Completed       - Job pod finished successfully
# Error           - container exited non-zero
```

---

## Navigation

| File | Description |
|------|-------------|
| [Theory.md](./Theory.md) | Pods explained |
| [Cheatsheet.md](./Cheatsheet.md) | You are here — quick reference |
| [Interview_QA.md](./Interview_QA.md) | Interview questions and answers |
| [Code_Example.md](./Code_Example.md) | Working YAML examples |

**Previous:** [03_Installation_and_Setup](../03_Installation_and_Setup/Cheatsheet.md) |
**Next:** [05_Deployments_and_ReplicaSets](../05_Deployments_and_ReplicaSets/Theory.md)
