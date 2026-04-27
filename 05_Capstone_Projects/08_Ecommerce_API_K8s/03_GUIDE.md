# 08 — Guide: Deploy E-Commerce API to Kubernetes

Eight steps take you from a local Docker image to a fully autoscaling Kubernetes deployment. Each step has a hint to nudge you, then a full answer with annotated YAML.

Work through each step yourself before expanding the answer — the struggle is where the learning happens.

---

## Step 1 — Prerequisite Check: Image Ready

### The goal

Before writing a single manifest you need to confirm your Docker image is accessible to the cluster. minikube runs its own Docker daemon separate from your host machine, so `docker build` on your laptop does not automatically make the image available inside minikube.

### 💡 Hint

Point your shell at minikube's Docker daemon so images you build are visible inside the cluster without a registry push.

```bash
eval $(minikube docker-env)
```

### ✅ Answer

```bash
# Point shell at minikube's Docker daemon
eval $(minikube docker-env)

# Build the image inside minikube's daemon
docker build -t ecommerce-api:1.0.0 .

# Verify it appears in minikube
docker images | grep ecommerce-api

# Confirm cluster is reachable
kubectl cluster-info

# Confirm metrics-server is running (needed for HPA)
kubectl get deployment metrics-server -n kube-system

# Confirm ingress addon is enabled
minikube addons list | grep ingress
```

In the Deployment manifest you will set `imagePullPolicy: Never` to tell Kubernetes not to try pulling from a remote registry — use the locally built image instead.

---

## Step 2 — Namespace, ConfigMap, and Secret

### The goal

Isolate all project resources in a dedicated **namespace**. Externalise configuration that changes between environments (database hostname, port, app settings) into a **ConfigMap**. Store credentials (database password, JWT secret key) in a **Secret** so they are never hardcoded in a manifest.

### 💡 Hint

- Namespace: a single YAML with `kind: Namespace`
- ConfigMap: key-value pairs under `data:`
- Secret: values must be base64-encoded — use `echo -n 'value' | base64`

### ✅ Answer

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ecommerce   # ← all other manifests reference this namespace
```

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ecommerce-config
  namespace: ecommerce
data:
  POSTGRES_DB: ecommerce        # ← database name the app connects to
  POSTGRES_USER: appuser        # ← non-root postgres user
  POSTGRES_HOST: postgres-service  # ← K8s DNS name of the postgres Service
  POSTGRES_PORT: "5432"
  APP_ENV: production
  LOG_LEVEL: INFO
```

```yaml
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: ecommerce-secret
  namespace: ecommerce
type: Opaque
data:
  # echo -n 'mysecretpassword' | base64
  POSTGRES_PASSWORD: bXlzZWNyZXRwYXNzd29yZA==
  # echo -n 'supersecretjwtkey' | base64
  SECRET_KEY: c3VwZXJzZWNyZXRqd3RrZXk=
```

Kubernetes stores Secrets as base64, not encrypted, by default. In production clusters use sealed-secrets or AWS Secrets Manager integration — but base64 is fine for local development.

---

## Step 3 — PostgreSQL: PVC, Deployment, and Service

### The goal

Deploy PostgreSQL with a **PersistentVolumeClaim** so database files survive pod restarts. Wire it together with a **ClusterIP Service** so the app can reach it by a stable DNS name (`postgres-service`).

### 💡 Hint

- PVC declares the storage request; the cluster provisions a matching PersistentVolume automatically on minikube
- The Deployment mounts the PVC at `/var/lib/postgresql/data`
- The Service selector must match the Deployment's pod labels exactly

### ✅ Answer

```yaml
# k8s/postgres-pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
  namespace: ecommerce
spec:
  accessModes:
    - ReadWriteOnce          # ← one node can mount read-write at a time (standard for databases)
  resources:
    requests:
      storage: 5Gi           # ← 5 gigabytes of durable storage
```

```yaml
# k8s/postgres-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: ecommerce
spec:
  replicas: 1                # ← databases are not horizontally scaled with plain Deployments
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: db
          image: postgres:15-alpine
          ports:
            - containerPort: 5432
          env:
            - name: POSTGRES_DB
              valueFrom:
                configMapKeyRef:
                  name: ecommerce-config
                  key: POSTGRES_DB
            - name: POSTGRES_USER
              valueFrom:
                configMapKeyRef:
                  name: ecommerce-config
                  key: POSTGRES_USER
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:          # ← pull password from Secret, not ConfigMap
                  name: ecommerce-secret
                  key: POSTGRES_PASSWORD
          resources:
            requests:
              cpu: 250m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
          volumeMounts:
            - name: postgres-data
              mountPath: /var/lib/postgresql/data  # ← standard postgres data directory
      volumes:
        - name: postgres-data
          persistentVolumeClaim:
            claimName: postgres-pvc    # ← binds to the PVC created above
```

```yaml
# k8s/postgres-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres-service       # ← this name becomes the DNS hostname inside the cluster
  namespace: ecommerce
spec:
  selector:
    app: postgres              # ← must match labels on the Deployment pods
  ports:
    - port: 5432               # ← port other pods use to reach this service
      targetPort: 5432         # ← port the postgres container is listening on
  type: ClusterIP              # ← internal only, not reachable from outside the cluster
```

---

## Step 4 — App Deployment with Probes and Resource Limits

### The goal

Deploy the E-Commerce API with three replicas. Add a **readiness probe** (Kubernetes only sends traffic to pods that are ready) and a **liveness probe** (Kubernetes restarts pods that are unhealthy). Set resource requests and limits to protect the cluster from runaway containers.

### 💡 Hint

- FastAPI exposes a health endpoint at `/health` by default — use that for both probes
- `initialDelaySeconds` gives the app time to start before the first probe fires
- `imagePullPolicy: Never` tells minikube to use the locally built image

### ✅ Answer

```yaml
# k8s/app-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ecommerce-api
  namespace: ecommerce
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ecommerce-api
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1        # ← allow 1 extra pod during rollout
      maxUnavailable: 0  # ← never take a pod down before its replacement is ready
  template:
    metadata:
      labels:
        app: ecommerce-api
    spec:
      containers:
        - name: app
          image: ecommerce-api:1.0.0
          imagePullPolicy: Never      # ← use locally built image in minikube
          ports:
            - containerPort: 8000
          env:
            - name: POSTGRES_HOST
              valueFrom:
                configMapKeyRef:
                  name: ecommerce-config
                  key: POSTGRES_HOST
            - name: POSTGRES_PORT
              valueFrom:
                configMapKeyRef:
                  name: ecommerce-config
                  key: POSTGRES_PORT
            - name: POSTGRES_DB
              valueFrom:
                configMapKeyRef:
                  name: ecommerce-config
                  key: POSTGRES_DB
            - name: POSTGRES_USER
              valueFrom:
                configMapKeyRef:
                  name: ecommerce-config
                  key: POSTGRES_USER
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: ecommerce-secret
                  key: POSTGRES_PASSWORD
            - name: SECRET_KEY
              valueFrom:
                secretKeyRef:
                  name: ecommerce-secret
                  key: SECRET_KEY
            - name: APP_ENV
              valueFrom:
                configMapKeyRef:
                  name: ecommerce-config
                  key: APP_ENV
          resources:
            requests:
              cpu: 100m      # ← scheduler uses this to find a node with spare capacity
              memory: 128Mi
            limits:
              cpu: 500m      # ← container is throttled if it exceeds this
              memory: 512Mi  # ← container is OOM-killed if it exceeds this
          readinessProbe:
            httpGet:
              path: /health  # ← Kubernetes sends traffic only when this returns 200
              port: 8000
            initialDelaySeconds: 10  # ← give app time to start before first probe
            periodSeconds: 5
            failureThreshold: 3
          livenessProbe:
            httpGet:
              path: /health  # ← Kubernetes restarts pod if this fails repeatedly
              port: 8000
            initialDelaySeconds: 30  # ← longer delay: app must fully initialise before liveness fires
            periodSeconds: 10
            failureThreshold: 3
```

If your FastAPI app does not expose `/health`, add this to your `main.py`:

```python
@app.get("/health")
def health():
    return {"status": "ok"}
```

---

## Step 5 — App Service (ClusterIP)

### The goal

Expose the App Deployment inside the cluster via a **Service**. The Ingress controller will forward external traffic to this Service.

### 💡 Hint

Service `selector` must match the `labels` on the Deployment's pod template — not the Deployment name.

### ✅ Answer

```yaml
# k8s/app-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: app-service
  namespace: ecommerce
spec:
  selector:
    app: ecommerce-api      # ← matches labels.app on the Deployment pod template
  ports:
    - port: 80              # ← the port the Ingress will hit
      targetPort: 8000      # ← the port the FastAPI container listens on
  type: ClusterIP           # ← internal only; Ingress handles external access
```

---

## Step 6 — Ingress Manifest

### The goal

Create an **Ingress** resource that routes external HTTP requests arriving at `shop.local/api` to the `app-service`. The nginx Ingress controller (enabled as a minikube addon) reads this resource and reconfigures itself.

### 💡 Hint

- Add `nginx.ingress.kubernetes.io/rewrite-target: /` annotation so `/api/products` becomes `/products` when forwarded to the app
- Add `shop.local` pointing to `$(minikube ip)` in your `/etc/hosts`

### ✅ Answer

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ecommerce-ingress
  namespace: ecommerce
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /$2  # ← strip /api prefix before forwarding
spec:
  ingressClassName: nginx
  rules:
    - host: shop.local                         # ← add to /etc/hosts → $(minikube ip)
      http:
        paths:
          - path: /api(/|$)(.*)               # ← capture group $2 used in rewrite-target
            pathType: Prefix
            backend:
              service:
                name: app-service
                port:
                  number: 80
```

After applying, add the entry to your local hosts file:

```bash
echo "$(minikube ip)  shop.local" | sudo tee -a /etc/hosts

# Test it
curl http://shop.local/api/health
```

---

## Step 7 — Apply All Manifests and Verify

### The goal

Apply all manifests in dependency order and confirm every pod reaches the `Running` state with all containers ready.

### 💡 Hint

Apply the namespace first, then everything else. Use `kubectl get all -n ecommerce` for a quick overview and `kubectl describe pod` for details if something is stuck.

### ✅ Answer

```bash
# Apply in dependency order
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/postgres-pvc.yaml
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/postgres-service.yaml
kubectl apply -f k8s/app-deployment.yaml
kubectl apply -f k8s/app-service.yaml
kubectl apply -f k8s/ingress.yaml

# Or apply the whole directory at once (Kubernetes handles ordering by kind)
kubectl apply -f k8s/

# Check everything is running
kubectl get all -n ecommerce

# Expected output (abbreviated):
# NAME                                  READY   STATUS    RESTARTS
# pod/ecommerce-api-xxx-yyy             1/1     Running   0
# pod/ecommerce-api-xxx-zzz             1/1     Running   0
# pod/ecommerce-api-xxx-www             1/1     Running   0
# pod/postgres-xxx-yyy                  1/1     Running   0
#
# NAME                TYPE        CLUSTER-IP   PORT(S)
# service/app-service ClusterIP   10.x.x.x     80/TCP
# service/postgres-service ClusterIP 10.x.x.x  5432/TCP

# Check PVC is bound
kubectl get pvc -n ecommerce
# NAME           STATUS   CAPACITY   ACCESS MODES
# postgres-pvc   Bound    5Gi        RWO

# Check Ingress
kubectl get ingress -n ecommerce

# If a pod is not starting, inspect it
kubectl describe pod <pod-name> -n ecommerce
kubectl logs <pod-name> -n ecommerce
```

Common issues:

| Symptom | Cause | Fix |
|---|---|---|
| `CrashLoopBackOff` on app pod | App cannot reach postgres | Check postgres pod is running first; verify ConfigMap hostname matches Service name |
| `Pending` PVC | No storage class available | On minikube run `minikube addons enable default-storageclass` |
| `ImagePullBackOff` | Image not in minikube's daemon | Re-run `eval $(minikube docker-env)` then rebuild |
| Probes failing | `/health` endpoint missing | Add the health endpoint to `main.py` and rebuild image |

---

## Step 8 — Configure HPA and Trigger Scale-Out

### The goal

Write a **HorizontalPodAutoscaler** that scales the `ecommerce-api` Deployment between 2 and 10 replicas, targeting 50% average CPU utilisation. Then generate load to watch it scale out in real time.

### 💡 Hint

- HPA requires the metrics-server to be running: `kubectl get deployment metrics-server -n kube-system`
- Use `kubectl run` to launch a temporary pod running a load generator (`busybox` with a `wget` loop)
- `kubectl get hpa -n ecommerce -w` shows the scaling events as they happen

### ✅ Answer

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ecommerce-api-hpa
  namespace: ecommerce
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ecommerce-api     # ← the Deployment to scale
  minReplicas: 2            # ← never scale below 2 (availability floor)
  maxReplicas: 10           # ← never scale above 10 (cost ceiling)
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 50  # ← scale out when average CPU across pods exceeds 50%
```

```bash
# Apply the HPA
kubectl apply -f k8s/hpa.yaml

# Confirm HPA is watching the deployment
kubectl get hpa -n ecommerce
# NAME                  REFERENCE                  TARGETS   MINPODS   MAXPODS   REPLICAS
# ecommerce-api-hpa     Deployment/ecommerce-api   2%/50%    2         10        3

# Generate load in a separate terminal
kubectl run load-generator \
  --image=busybox:1.28 \
  --restart=Never \
  -n ecommerce \
  -- /bin/sh -c "while true; do wget -q -O- http://app-service/health; done"

# Watch the HPA scale out in real time (in another terminal)
kubectl get hpa -n ecommerce -w
# After a minute or two, REPLICAS should climb above 3

# Watch pods being created
kubectl get pods -n ecommerce -w

# Stop the load generator
kubectl delete pod load-generator -n ecommerce

# After ~5 minutes (stabilisation window) the HPA will scale back down to minReplicas: 2
```

The stabilisation window prevents thrashing: the HPA waits 5 minutes of sustained low CPU before scaling down, but responds within 15 seconds to sustained high CPU.

---

⬅️ **Prev:** [07 — JWT Auth API Docker](../07_JWT_Auth_API_Docker/01_MISSION.md) &nbsp;&nbsp; ➡️ **Next:** [09 — Containerize RAG System](../09_RAG_System_Containerized/01_MISSION.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
