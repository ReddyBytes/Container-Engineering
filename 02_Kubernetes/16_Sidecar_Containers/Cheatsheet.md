# Sidecar Containers Cheatsheet

## Patterns Quick Reference

| Pattern | Sidecar Role | Example |
|---------|-------------|---------|
| Log Shipper | Read app logs, forward to central store | Fluent Bit → Elasticsearch |
| Service Mesh | Intercept all network traffic | Envoy (Istio) |
| Config Reloader | Watch config, reload app | config-reloader |
| TLS Terminator | Handle HTTPS, forward HTTP to app | Nginx, Envoy |
| Auth Proxy | Handle OAuth/OIDC, forward authenticated requests | oauth2-proxy |
| Ambassador | Proxy app's outbound connections | redis-proxy |
| Adapter | Transform app output to standard format | log-adapter |

---

## kubectl Commands

```bash
# --- Multi-Container Pod Inspection ---

# List containers in a pod
kubectl get pod <pod-name> -n <namespace> \
  -o jsonpath='{.spec.containers[*].name}'

# List init containers in a pod
kubectl get pod <pod-name> -n <namespace> \
  -o jsonpath='{.spec.initContainers[*].name}'

# Get all container names and images
kubectl get pod <pod-name> -n <namespace> \
  -o jsonpath='{range .spec.containers[*]}{.name}: {.image}{"\n"}{end}'

# Describe pod (shows all containers, init containers, their status)
kubectl describe pod <pod-name> -n <namespace>

# --- Logs from Specific Containers ---

# Get logs from the main app container
kubectl logs <pod-name> -n <namespace>

# Get logs from a specific named container
kubectl logs <pod-name> -c <container-name> -n <namespace>

# Get logs from the sidecar
kubectl logs <pod-name> -c log-shipper -n <namespace>

# Follow logs from a specific container
kubectl logs <pod-name> -c <container-name> -n <namespace> -f

# Get logs from all containers in a pod
kubectl logs <pod-name> --all-containers=true -n <namespace>

# Get previous container logs (after a crash/restart)
kubectl logs <pod-name> -c <container-name> --previous -n <namespace>

# --- Exec into Specific Containers ---

# Exec into main app container (default is first container)
kubectl exec -it <pod-name> -n <namespace> -- bash

# Exec into a specific named container
kubectl exec -it <pod-name> -c <container-name> -n <namespace> -- sh

# Run a command in the sidecar
kubectl exec <pod-name> -c log-shipper -n <namespace> -- \
  cat /var/log/app.log

# --- Init Container Debugging ---

# Get logs from an init container
kubectl logs <pod-name> -c init-myinit -n <namespace>

# Check init container exit status
kubectl get pod <pod-name> -n <namespace> -o yaml | \
  grep -A 10 initContainerStatuses

# Describe pod to see init container state
kubectl describe pod <pod-name> -n <namespace>
# Look for: Init Containers: section

# --- Checking Volume Sharing ---

# See shared volumes between containers
kubectl get pod <pod-name> -n <namespace> -o jsonpath='{.spec.volumes}'

# Check if a volume is mounted correctly
kubectl exec -it <pod-name> -c main-app -- ls /var/log
kubectl exec -it <pod-name> -c log-shipper -- ls /var/log

# --- Istio Sidecar Management ---

# Check if Istio sidecar injection is enabled for a namespace
kubectl get namespace <ns> --show-labels
# Look for: istio-injection=enabled

# Enable Istio sidecar injection for a namespace
kubectl label namespace <ns> istio-injection=enabled

# Disable Istio sidecar injection for a namespace
kubectl label namespace <ns> istio-injection=disabled

# Check if a pod has the Istio proxy sidecar
kubectl get pod <pod-name> -n <ns> \
  -o jsonpath='{.spec.containers[*].name}'
# Should include 'istio-proxy'

# View Istio proxy logs for a pod
kubectl logs <pod-name> -c istio-proxy -n <ns>

# Check Istio proxy config
kubectl exec <pod-name> -c istio-proxy -n <ns> -- \
  pilot-agent request GET config_dump

# --- Native Sidecar (K8s 1.29+) ---

# Check if a container in initContainers has restartPolicy: Always
kubectl get pod <pod-name> -n <namespace> -o yaml | \
  grep -A 5 initContainers
```

---

## Init Container vs Sidecar Container

```yaml
# Init container — runs before app, exits when done
initContainers:
  - name: wait-for-db
    image: busybox
    command: ['sh', '-c', 'until nc -z db-service 5432; do sleep 2; done']

# Regular sidecar — runs alongside app (K8s < 1.29)
containers:
  - name: log-shipper
    image: fluent/fluent-bit:2.2.0

# Native sidecar — init container with restartPolicy: Always (K8s 1.29+)
initContainers:
  - name: log-shipper
    image: fluent/fluent-bit:2.2.0
    restartPolicy: Always       # runs before AND alongside app, restarts if crashes
```

---

## Shared Volume Pattern

```yaml
volumes:
  - name: shared-logs
    emptyDir: {}               # ephemeral shared storage

containers:
  - name: app
    volumeMounts:
      - name: shared-logs
        mountPath: /var/log/app
  - name: log-shipper
    volumeMounts:
      - name: shared-logs
        mountPath: /var/log/app   # same path — both containers share logs
        readOnly: true
```

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Theory.md](./Theory.md) |
| Interview Q&A | [Interview_QA.md](./Interview_QA.md) |
| Module Home | [16_Sidecar_Containers](../) |
