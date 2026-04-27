# Module 04 — Code Examples: Pods

## Example 1: Simple Single-Container Pod

```yaml
# simple-pod.yaml
# A basic nginx pod — the "hello world" of Kubernetes
apiVersion: v1
kind: Pod
metadata:
  name: simple-nginx                     # Name of the pod (must be unique in namespace)
  namespace: default                     # Which namespace to create it in
  labels:
    app: nginx                           # Labels are key-value pairs used for selection
    environment: learning
spec:
  containers:
  - name: nginx                          # Name of the container (used in logs, exec)
    image: nginx:1.25                    # Image name and tag (always pin the tag!)
    ports:
    - containerPort: 80                  # Informational — does NOT expose the port externally
    resources:
      requests:
        memory: "64Mi"                   # Minimum memory guaranteed
        cpu: "100m"                      # 100 millicores = 0.1 CPU core
      limits:
        memory: "128Mi"                  # Hard cap — OOMKilled if exceeded
        cpu: "200m"                      # Throttled if exceeded
```

```bash
# Apply it
kubectl apply -f simple-pod.yaml

# Check it's running
kubectl get pod simple-nginx

# See details (IP, node, etc.)
kubectl get pod simple-nginx -o wide

# Access it locally
kubectl port-forward pod/simple-nginx 8080:80
# Visit http://localhost:8080

# Clean up
kubectl delete pod simple-nginx
```

---

## Example 2: Multi-Container Pod (App + Log Sidecar)

```yaml
# multi-container-pod.yaml
# Main app writes logs to a shared volume; sidecar reads and outputs them
apiVersion: v1
kind: Pod
metadata:
  name: app-with-sidecar
  labels:
    app: my-app
spec:
  containers:

  # Main application container
  - name: app
    image: busybox:1.36
    command: ["/bin/sh", "-c"]
    args:
    - |
      while true; do
        echo "[$(date)] App is running - writing log" >> /var/log/app/app.log
        sleep 5
      done
    volumeMounts:
    - name: log-volume                   # Mount the shared volume
      mountPath: /var/log/app            # At this path in the container

  # Sidecar container — reads logs and prints to stdout (where kubectl logs reads from)
  - name: log-reader
    image: busybox:1.36
    command: ["/bin/sh", "-c"]
    args:
    - |
      tail -f /var/log/app/app.log       # Follow the log file written by the main app
    volumeMounts:
    - name: log-volume                   # Same volume name — they share it
      mountPath: /var/log/app

  # Shared volume (emptyDir = lives as long as the pod, created fresh each time)
  volumes:
  - name: log-volume
    emptyDir: {}                         # Empty directory created on the node for this pod
```

```bash
kubectl apply -f multi-container-pod.yaml

# Watch the main app logs
kubectl logs -f app-with-sidecar -c app

# Watch the sidecar reading those logs
kubectl logs -f app-with-sidecar -c log-reader

# Execute into a specific container
kubectl exec -it app-with-sidecar -c app -- /bin/sh

# Clean up
kubectl delete pod app-with-sidecar
```

---

## Example 3: Pod with Resource Requests and Limits

```yaml
# resource-pod.yaml
# Demonstrating resource requests and limits
apiVersion: v1
kind: Pod
metadata:
  name: resource-demo
spec:
  containers:
  - name: memory-hungry-app
    image: polinux/stress                # Stress testing tool
    command: ["stress"]
    args:
    - "--vm"
    - "1"                               # 1 worker process
    - "--vm-bytes"
    - "64M"                             # Allocate 64MB (within limits)
    - "--vm-hang"
    - "1"
    resources:
      requests:
        memory: "32Mi"                   # Minimum memory needed
        cpu: "100m"
      limits:
        memory: "128Mi"                  # Max allowed: if app uses >128Mi, OOMKilled
        cpu: "500m"
```

```bash
kubectl apply -f resource-pod.yaml

# Check actual resource usage (requires metrics-server)
kubectl top pod resource-demo

# See resource requests/limits in describe
kubectl describe pod resource-demo | grep -A 5 "Limits\|Requests"

# Try using MORE memory than the limit to see OOMKill
# Edit the pod args to use "256M" instead of "64M"
# The pod will get OOMKilled and show OOMKilled exit code in describe

kubectl delete pod resource-demo
```

---

## Example 4: Pod with Environment Variables from ConfigMap and Secret

```yaml
# configmap.yaml — non-sensitive configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  DATABASE_HOST: "postgres.default.svc.cluster.local"   # DB hostname
  DATABASE_PORT: "5432"
  LOG_LEVEL: "info"
  FEATURE_FLAG_NEW_UI: "true"
---
# secret.yaml — sensitive data (values are base64 encoded, NOT encrypted)
apiVersion: v1
kind: Secret
metadata:
  name: app-secret
type: Opaque
data:
  # echo -n "mysecretpassword" | base64
  DATABASE_PASSWORD: bXlzZWNyZXRwYXNzd29yZA==
  # echo -n "myapikey123" | base64
  API_KEY: bXlhcGlrZXkxMjM=
---
# pod-with-config.yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-config
spec:
  containers:
  - name: app
    image: busybox:1.36
    command: ["/bin/sh", "-c"]
    args:
    - |
      echo "DB Host: $DATABASE_HOST"
      echo "DB Port: $DATABASE_PORT"
      echo "Log Level: $LOG_LEVEL"
      echo "DB Password: $DATABASE_PASSWORD"
      sleep 3600

    env:
    # Individual values from ConfigMap
    - name: DATABASE_HOST
      valueFrom:
        configMapKeyRef:
          name: app-config             # ConfigMap name
          key: DATABASE_HOST           # Key within that ConfigMap

    - name: DATABASE_PORT
      valueFrom:
        configMapKeyRef:
          name: app-config
          key: DATABASE_PORT

    # Individual value from Secret
    - name: DATABASE_PASSWORD
      valueFrom:
        secretKeyRef:
          name: app-secret             # Secret name
          key: DATABASE_PASSWORD       # Key within the Secret

    # Load ALL keys from a ConfigMap as environment variables at once
    envFrom:
    - configMapRef:
        name: app-config               # This loads DATABASE_HOST, DATABASE_PORT,
                                       # LOG_LEVEL, and FEATURE_FLAG_NEW_UI all at once
    - secretRef:
        name: app-secret               # Loads all secret keys too
```

```bash
# Apply all resources
kubectl apply -f configmap.yaml
kubectl apply -f pod-with-config.yaml

# Check the env vars inside the running pod
kubectl exec app-with-config -- env | grep -E "DATABASE|LOG_LEVEL|API_KEY"

# View pod logs to see the echo output
kubectl logs app-with-config

# Clean up
kubectl delete pod app-with-config
kubectl delete configmap app-config
kubectl delete secret app-secret
```

---

## Example 5: Pod with Liveness and Readiness Probes

```yaml
# pod-with-probes.yaml
apiVersion: v1
kind: Pod
metadata:
  name: probed-pod
spec:
  containers:
  - name: web-server
    image: nginx:1.25
    ports:
    - containerPort: 80

    # Startup probe: gives the app time to start (runs before liveness/readiness)
    startupProbe:
      httpGet:
        path: /healthz                 # HTTP endpoint to call
        port: 80
      failureThreshold: 30             # Allow up to 30 failed checks before restarting
      periodSeconds: 10                # Check every 10 seconds
      # Total startup time allowed: 30 * 10 = 300 seconds

    # Liveness probe: if this fails repeatedly, restart the container
    livenessProbe:
      httpGet:
        path: /                        # Check if nginx returns 200
        port: 80
      initialDelaySeconds: 10          # Wait 10s after startup before first check
      periodSeconds: 15                # Check every 15 seconds
      failureThreshold: 3              # Restart after 3 consecutive failures
      timeoutSeconds: 5                # HTTP request must complete within 5s

    # Readiness probe: if this fails, remove pod from Service endpoints (no traffic)
    readinessProbe:
      httpGet:
        path: /
        port: 80
      initialDelaySeconds: 5
      periodSeconds: 10
      failureThreshold: 3
      successThreshold: 1              # How many consecutive successes to be "ready" again
```

```bash
kubectl apply -f pod-with-probes.yaml

# Watch the pod start up
kubectl get pod probed-pod --watch

# See probe status in describe
kubectl describe pod probed-pod | grep -A 15 "Liveness\|Readiness\|Startup"

# Clean up
kubectl delete pod probed-pod
```

---

## 📂 Navigation

| File | Description |
|------|-------------|
| [Theory.md](./Theory.md) | Pods explained |
| [Cheatsheet.md](./Cheatsheet.md) | Quick reference commands |
| [Interview_QA.md](./Interview_QA.md) | Interview questions and answers |
| [Code_Example.md](./Code_Example.md) | You are here — working YAML examples |

**Previous:** [03_Installation_and_Setup](../03_Installation_and_Setup/Code_Example.md) |
**Next:** [05_Deployments_and_ReplicaSets](../05_Deployments_and_ReplicaSets/Theory.md)
