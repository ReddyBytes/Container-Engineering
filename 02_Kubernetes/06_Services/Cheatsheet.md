# Module 06 — Services Cheatsheet

## Getting Service Info

```bash
# List services in current namespace
kubectl get services
kubectl get svc            # short form

# List with extra info (cluster IP, external IP, ports)
kubectl get svc -o wide

# List services in all namespaces
kubectl get svc -A

# Detailed info about a service (shows endpoints, selector, events)
kubectl describe svc my-service

# Get service as YAML
kubectl get svc my-service -o yaml

# See which pods are backing a service (the Endpoints object)
kubectl get endpoints my-service
kubectl get ep my-service   # short form

# Filter services by label
kubectl get svc -l app=backend
```

## Creating Services

```bash
# Expose a deployment as a ClusterIP service
kubectl expose deployment my-app --port=80 --target-port=8080

# Expose as NodePort
kubectl expose deployment my-app --type=NodePort --port=80 --target-port=8080

# Expose as LoadBalancer
kubectl expose deployment my-app --type=LoadBalancer --port=80 --target-port=8080

# Create from YAML (recommended)
kubectl apply -f service.yaml

# Quick ClusterIP service creation
kubectl create service clusterip my-service --tcp=80:8080

# Quick NodePort service creation
kubectl create service nodeport my-service --tcp=80:8080 --node-port=30080
```

## Testing Services

```bash
# Port-forward a service to your local machine for testing
kubectl port-forward svc/my-service 8080:80
# Now: curl http://localhost:8080

# Run a temporary pod to test service connectivity from inside the cluster
kubectl run test --image=busybox --rm -it --restart=Never -- sh
# Inside the shell:
# wget -qO- http://my-service
# wget -qO- http://my-service.default.svc.cluster.local

# Test DNS resolution from inside the cluster
kubectl run dns-test --image=busybox --rm -it --restart=Never -- \
  nslookup my-service.default.svc.cluster.local

# Check service endpoints (pod IPs backing the service)
kubectl get endpoints my-service

# Watch endpoints change as pods scale up/down
kubectl get endpoints my-service --watch
```

## minikube — Accessing NodePort and LoadBalancer Services

```bash
# Get the URL for a NodePort or LoadBalancer service in minikube
minikube service my-service --url

# Open in browser
minikube service my-service

# For LoadBalancer services, create a tunnel
minikube tunnel
# Then get the external IP
kubectl get svc my-service
```

## Service DNS Names

```bash
# Service DNS format:
# <service>.<namespace>.svc.cluster.local
# From same namespace: just use <service>
# From different namespace: use <service>.<namespace>

# Examples:
# backend.default.svc.cluster.local
# postgres.database.svc.cluster.local

# Check DNS from inside a running pod
kubectl exec -it my-pod -- nslookup kubernetes.default
kubectl exec -it my-pod -- curl http://my-service/health
```

## Deleting Services

```bash
# Delete by name
kubectl delete service my-service
kubectl delete svc my-service

# Delete from YAML
kubectl delete -f service.yaml

# Delete all services with a label
kubectl delete svc -l app=my-app
```

## Troubleshooting Services

```bash
# Problem: service has no endpoints (no pods matching selector)
kubectl describe svc my-service
# Look for "Endpoints: <none>" — means no pods matched the selector

# Check what labels the service selects
kubectl get svc my-service -o jsonpath='{.spec.selector}'

# Check what labels the pods have
kubectl get pods --show-labels

# Problem: service type is LoadBalancer but EXTERNAL-IP is <pending>
kubectl get svc my-service
# In minikube: run "minikube tunnel" in separate terminal
# In cloud: wait for the cloud LB to provision (1-2 minutes)

# Check kube-proxy logs for routing issues
kubectl logs -n kube-system -l k8s-app=kube-proxy
```

---

## Navigation

| File | Description |
|------|-------------|
| [Theory.md](./Theory.md) | Services explained |
| [Cheatsheet.md](./Cheatsheet.md) | You are here — quick reference |
| [Interview_QA.md](./Interview_QA.md) | Interview questions and answers |
| [Code_Example.md](./Code_Example.md) | Working YAML examples |

**Previous:** [05_Deployments_and_ReplicaSets](../05_Deployments_and_ReplicaSets/Cheatsheet.md) |
**Next:** [07_ConfigMaps_and_Secrets](../07_ConfigMaps_and_Secrets/Theory.md)
