# Module 02 — Compose to Kubernetes Migration Cheatsheet

## Kompose — Automated Conversion

```bash
# Install kompose (macOS)
brew install kompose

# Install kompose (Linux)
curl -L https://github.com/kubernetes/kompose/releases/download/v1.32.0/kompose-linux-amd64 \
  -o /usr/local/bin/kompose && chmod +x /usr/local/bin/kompose

# Convert docker-compose.yml in current directory (outputs YAML files)
kompose convert

# Convert a specific file
kompose convert -f docker-compose.yml

# Output all manifests to a directory
kompose convert -f docker-compose.yml -o k8s/

# Convert and immediately apply to cluster (for testing only)
kompose up

# Convert and delete from cluster
kompose down

# Preview what kompose will create (dry run)
kompose convert --dry-run
```

---

## Manual Migration Commands

```bash
# Step 1: Create a namespace for your app
kubectl create namespace my-app

# Step 2: Create ConfigMap from key=value pairs
kubectl create configmap app-config \
  --from-literal=LOG_LEVEL=info \
  --from-literal=PORT=3000 \
  -n my-app

# Step 3: Create ConfigMap from a .env file
kubectl create configmap app-config \
  --from-env-file=.env \
  -n my-app

# Step 4: Create a Secret for sensitive values
kubectl create secret generic app-secrets \
  --from-literal=DB_PASSWORD=supersecret \
  --from-literal=JWT_SECRET=abc123 \
  -n my-app

# Step 5: Apply all manifests
kubectl apply -f k8s/ -n my-app

# Step 6: Watch rollout
kubectl rollout status deployment/web -n my-app

# Step 7: View running pods
kubectl get pods -n my-app

# Step 8: Check logs
kubectl logs -f deployment/web -n my-app
```

---

## Compose → K8s Concept Mapping

| docker-compose.yml key | Kubernetes Resource | When to Use |
|---|---|---|
| `services:` | `Deployment` | Every stateless service |
| `services:` (database) | `StatefulSet` | When pod identity and stable storage matter |
| `image:` | `spec.containers[].image` | Same image reference |
| `ports:` | `Service` (ClusterIP) | Internal service-to-service traffic |
| `ports:` (public) | `Service` (LoadBalancer) + `Ingress` | External HTTP/HTTPS traffic |
| `environment:` | `ConfigMap` (envFrom) | Non-sensitive config |
| `environment:` (secrets) | `Secret` (envFrom) | Passwords, tokens, keys |
| `env_file:` | `ConfigMap` + `envFrom` | Config from a file |
| `volumes:` (named) | `PersistentVolumeClaim` | Persistent data that survives Pod restarts |
| `volumes:` (bind mount) | `hostPath` (avoid in prod) or `emptyDir` | Temp storage or local dev only |
| `networks:` | Kubernetes Service + NetworkPolicy | Flat pod network with optional restrictions |
| `depends_on:` | `initContainers` | Wait for a condition before starting |
| `depends_on: condition: healthy` | `readinessProbe` | Withhold traffic until ready |
| `restart: unless-stopped` | `restartPolicy: Always` | Default in Deployments |
| `healthcheck:` | `livenessProbe` + `readinessProbe` | K8s has two separate probe types |
| `deploy.replicas:` | `spec.replicas` | Number of pod copies |
| `deploy.resources.limits:` | `resources.limits` | Max CPU and memory allowed |
| `deploy.resources.reservations:` | `resources.requests` | Minimum guaranteed CPU and memory |
| `deploy.update_config:` | `strategy.rollingUpdate` | `maxSurge`, `maxUnavailable` |
| `secrets:` | `Secret` (mounted as volume) | File-based secret injection |
| `configs:` | `ConfigMap` (mounted as volume) | File-based config injection |
| `build:` | Not in K8s — use CI/CD | Build externally, push to registry |

---

## Key YAML Templates

### Deployment (replaces a Compose service)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: my-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      initContainers:
        - name: wait-for-db
          image: busybox
          command: ['sh', '-c', 'until nc -z postgres 5432; do sleep 2; done']
      containers:
        - name: web
          image: myrepo/web:v1
          ports:
            - containerPort: 3000
          envFrom:
            - configMapRef:
                name: app-config
            - secretRef:
                name: app-secrets
          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
          readinessProbe:
            httpGet:
              path: /health
              port: 3000
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /health
              port: 3000
            initialDelaySeconds: 15
            periodSeconds: 20
```

### Service (replaces Compose ports + network)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: my-app
spec:
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 3000
  type: ClusterIP       # Use LoadBalancer for external, ClusterIP for internal
```

### PersistentVolumeClaim (replaces named volume)

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-data
  namespace: my-app
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 10Gi
```

### Ingress (replaces Compose port mapping for HTTP)

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-ingress
  namespace: my-app
spec:
  rules:
    - host: myapp.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: web
                port:
                  number: 80
```

---

## depends_on → Kubernetes Equivalents

```yaml
# Compose depends_on (order only):
depends_on:
  - db

# K8s equivalent: initContainer that waits for db to be reachable
initContainers:
  - name: wait-for-db
    image: busybox
    command: ['sh', '-c', 'until nc -z postgres 5432; do sleep 2; done']

# ---

# Compose depends_on (health condition):
depends_on:
  db:
    condition: service_healthy

# K8s equivalent: readinessProbe on the app — traffic withheld until probe passes
readinessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
```

---

## Common Migration Pitfalls and Fixes

| Issue | What Kompose Does | What You Should Do |
|---|---|---|
| No resource limits | Generates Deployments without limits | Add `resources.requests` and `resources.limits` |
| Plain secrets | Puts passwords in ConfigMaps | Move to `kind: Secret`, base64-encode values |
| Port mapping becomes NodePort | Works but exposes node IP | Replace with ClusterIP + Ingress |
| Named volumes → empty PVC | PVC spec is incomplete | Add `storageClassName` matching your cluster |
| No probes | No liveness/readiness probes | Add both probes to every container |
| `default` namespace | All resources in default | Create a dedicated namespace |
| No Ingress | HTTP traffic via NodePort | Add Ingress for hostname-based routing |

---

## 📂 Navigation

⬅️ **Prev:** [Docker vs Kubernetes](../01_Docker_vs_K8s/Interview_QA.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Image to Deployment Workflow](../03_Image_to_Deployment_Workflow/Theory.md)

| File | Description |
|---|---|
| [Theory.md](./Theory.md) | Compose to K8s Migration — full explanation |
| [Cheatsheet.md](./Cheatsheet.md) | You are here — quick reference |
| [Interview_QA.md](./Interview_QA.md) | Interview questions and answers |
