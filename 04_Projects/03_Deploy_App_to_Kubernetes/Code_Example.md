# Code Examples: Deploy an App to Kubernetes

All four files go in the `k8s/` directory. Apply them all with `kubectl apply -f k8s/`.

---

## k8s/configmap.yaml

```yaml
# k8s/configmap.yaml
# ConfigMap stores non-sensitive configuration as key-value pairs.
# The Deployment references this with envFrom.configMapRef,
# which injects every key as an environment variable in the pod.

apiVersion: v1
kind: ConfigMap
metadata:
  name: myapi-config
  # Labels help you select and filter resources.
  labels:
    app: myapi
    environment: development
data:
  # Application settings — these become env vars in the container.
  APP_ENV: "development"
  LOG_LEVEL: "info"
  WORKERS: "1"
  # These aren't secret, so ConfigMap is appropriate.
  # If they were passwords/tokens, use a Secret instead.
```

---

## k8s/secret.yaml

```yaml
# k8s/secret.yaml
# Secrets store sensitive data, base64-encoded.
# Note: base64 is encoding, not encryption.
# In production use Sealed Secrets, Vault, or External Secrets Operator.
#
# To generate base64 values:
#   echo -n "myvalue" | base64

apiVersion: v1
kind: Secret
metadata:
  name: myapi-secret
  labels:
    app: myapi
# type: Opaque is the generic secret type.
# Other types: kubernetes.io/tls, kubernetes.io/dockerconfigjson, etc.
type: Opaque
data:
  # echo -n "appuser" | base64 = YXBwdXNlcg==
  DB_USER: YXBwdXNlcg==
  # echo -n "supersecret" | base64 = c3VwZXJzZWNyZXQ=
  DB_PASSWORD: c3VwZXJzZWNyZXQ=
  # echo -n "appdb" | base64 = YXBwZGI=
  DB_NAME: YXBwZGI=
```

---

## k8s/deployment.yaml

```yaml
# k8s/deployment.yaml
# A Deployment describes the desired state for your application pods.
# Kubernetes continuously reconciles the actual state to match this.

apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapi
  labels:
    app: myapi
spec:
  # Run 3 pod replicas. If one crashes, K8s creates a replacement.
  replicas: 3

  # The selector tells the Deployment which pods it owns.
  # Must match spec.template.metadata.labels.
  selector:
    matchLabels:
      app: myapi

  strategy:
    type: RollingUpdate
    rollingUpdate:
      # How many pods above the desired count can exist during an update.
      # With maxSurge: 1 and 3 replicas, up to 4 pods exist briefly.
      maxSurge: 1
      # How many pods below desired count are allowed during an update.
      # With maxUnavailable: 0, all 3 existing pods keep running until
      # new ones are ready — zero downtime rollout.
      maxUnavailable: 0

  template:
    metadata:
      labels:
        app: myapi
        version: "1.0.0"
    spec:
      containers:
        - name: myapi
          # Replace YOUR_USERNAME with your Docker Hub username.
          # To use a local minikube image: set imagePullPolicy: Never
          # and run: minikube image load myapi:1.0.0
          image: YOUR_USERNAME/myapi:1.0.0
          imagePullPolicy: Always

          ports:
            - containerPort: 8000
              name: http

          # Inject all ConfigMap keys as environment variables.
          envFrom:
            - configMapRef:
                name: myapi-config
            - secretRef:
                name: myapi-secret

          # ----------------------------------------------------------------
          # Resource requests and limits
          # ----------------------------------------------------------------
          # requests: minimum guaranteed resources for scheduling.
          #   The scheduler only places a pod on a node that has at least
          #   this much free capacity.
          # limits: maximum allowed. The pod is OOMKilled if it exceeds
          #   memory. CPU is throttled (not killed) if it exceeds the limit.
          resources:
            requests:
              cpu: "100m"      # 100 millicores = 0.1 of a CPU core
              memory: "128Mi"  # 128 mebibytes
            limits:
              cpu: "500m"      # 0.5 CPU
              memory: "256Mi"

          # ----------------------------------------------------------------
          # Readiness probe — is this pod ready to receive traffic?
          # ----------------------------------------------------------------
          # K8s will NOT send traffic to a pod until readiness passes.
          # During rolling updates, the old pod keeps serving traffic until
          # the new pod's readiness probe succeeds.
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5   # Wait 5s before first check
            periodSeconds: 10        # Check every 10s
            failureThreshold: 3      # Mark unready after 3 failures

          # ----------------------------------------------------------------
          # Liveness probe — is this pod alive and functional?
          # ----------------------------------------------------------------
          # If liveness fails, K8s restarts the pod.
          # Use a longer initialDelaySeconds than readiness to prevent
          # restart loops during slow startup.
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 15
            periodSeconds: 20
            failureThreshold: 3

      # Terminate pods gracefully — give uvicorn time to finish requests.
      terminationGracePeriodSeconds: 30
```

---

## k8s/service.yaml

```yaml
# k8s/service.yaml
# A Service provides a stable network endpoint for a set of pods.
# Without a Service, pods are only reachable by their IP, which changes
# every time a pod is restarted or rescheduled.

apiVersion: v1
kind: Service
metadata:
  name: myapi-svc
  labels:
    app: myapi
spec:
  # selector: targets all pods with label app=myapi.
  # The Service load-balances requests across all matching pods.
  selector:
    app: myapi

  # NodePort exposes the service on a static port (30080) on every node.
  # Useful for local development with minikube.
  # In production, use LoadBalancer (cloud) or Ingress (see Project 04).
  type: NodePort

  ports:
    - name: http
      protocol: TCP
      port: 8000        # Port exposed on the ClusterIP (internal cluster access)
      targetPort: 8000  # Port on the pod to forward traffic to
      nodePort: 30080   # Port exposed on each node (must be 30000-32767)
                        # Omit nodePort to let K8s assign one automatically.
```

---

## Notes on kubectl Commands

```bash
# Apply all manifests in a directory
kubectl apply -f k8s/

# Watch pods as they start
kubectl get pods -l app=myapi --watch

# View logs from all pods matching a label
kubectl logs -l app=myapi --prefix

# Describe a resource to see events and config
kubectl describe deployment myapi
kubectl describe pod <pod-name>

# Get a shell inside a running pod
kubectl exec -it <pod-name> -- /bin/sh

# Delete all resources created by these manifests
kubectl delete -f k8s/

# See what's in a ConfigMap
kubectl get configmap myapi-config -o yaml

# Decode a secret value
kubectl get secret myapi-secret -o jsonpath='{.data.DB_PASSWORD}' | base64 -d
```

---

## 📂 Navigation

| | |
|---|---|
| Guide | [Project_Guide.md](./Project_Guide.md) |
| Steps | [Step_by_Step.md](./Step_by_Step.md) |
| All Projects | [04_Projects/](../) |
