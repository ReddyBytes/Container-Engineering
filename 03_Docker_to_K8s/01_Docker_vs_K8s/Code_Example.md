# Docker vs Kubernetes — Code Examples

All examples are production-quality with detailed comments explaining every decision.

---

## 1. Side-by-Side: Running a Web App with Docker vs Kubernetes

```bash
# =======================================================
# DOCKER: run a single nginx container on one machine
# =======================================================

# Start nginx, publish port 80 on the host
docker run -d \
  --name web-server \
  -p 80:80 \                            # host_port:container_port
  --restart unless-stopped \            # restart if the container crashes or host reboots
  nginx:1.25

# Check it's running
docker ps

# Send a request
curl http://localhost:80

# Stop and remove
docker stop web-server && docker rm web-server

# Problems with this approach:
# - If this machine crashes, the service is down until you manually restart it
# - To run 5 copies, you have to docker run 5 times and manage each one
# - No built-in health-based traffic routing
```

```yaml
# =======================================================
# KUBERNETES: declare desired state — K8s maintains it
# =======================================================
# nginx-deployment.yaml
# A Deployment tells K8s: "keep 3 nginx replicas running at all times."
# If one crashes, K8s restarts it. If a node fails, K8s reschedules to another.
# You don't manage individual containers — you declare intent.
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-server
  namespace: default
spec:
  replicas: 3                            # desired count — K8s enforces this continuously
  selector:
    matchLabels:
      app: web-server                    # ties this Deployment to the pods it manages
  template:
    metadata:
      labels:
        app: web-server
    spec:
      containers:
      - name: nginx
        image: nginx:1.25
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: 100m                    # K8s uses this to schedule onto a node with capacity
            memory: 64Mi
          limits:
            cpu: 200m
            memory: 128Mi
        # Health checks tell K8s when a pod is ready to serve traffic (readiness)
        # and when to restart a pod (liveness). Docker has no equivalent by default.
        livenessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 3
          periodSeconds: 5
---
# nginx-service.yaml
# A Service is a stable virtual IP that load balances across all healthy pod replicas.
# Docker has no equivalent — you'd manually track which containers are up.
apiVersion: v1
kind: Service
metadata:
  name: web-server
  namespace: default
spec:
  selector:
    app: web-server                      # routes traffic to pods with this label
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP                        # accessible within the cluster only
```

```bash
kubectl apply -f nginx-deployment.yaml
kubectl apply -f nginx-service.yaml

# K8s distributes 3 replicas across nodes automatically
kubectl get pods -o wide                # shows which node each pod runs on

# Kill a pod — K8s replaces it immediately
kubectl delete pod $(kubectl get pods -l app=web-server -o name | head -1)
kubectl get pods                        # a new pod appears within seconds

# Scale to 10 replicas with one command
kubectl scale deployment web-server --replicas=10
kubectl get pods
```

---

## 2. Docker Compose vs Kubernetes Manifests

```yaml
# docker-compose.yml
# A multi-service app defined with Docker Compose.
# Runs on ONE machine. No auto-healing, no auto-scaling, no cross-node load balancing.
version: "3.9"
services:
  web:
    image: myregistry/web-app:2.0
    ports:
    - "80:8080"
    environment:
    - DATABASE_URL=postgres://db:5432/appdb
    - REDIS_URL=redis://cache:6379
    depends_on:               # Compose waits for the container to START, not to be READY
    - db
    - cache
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
    - POSTGRES_DB=appdb
    - POSTGRES_USER=appuser
    - POSTGRES_PASSWORD=secret
    volumes:
    - postgres-data:/var/lib/postgresql/data

  cache:
    image: redis:7-alpine

volumes:
  postgres-data:
```

```yaml
# kubernetes/web-deployment.yaml
# The Kubernetes equivalent: handles multiple nodes, health-based traffic routing,
# rolling updates, and secret management that Compose does not support.
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1                  # keep at least 2 replicas up during updates
      maxSurge: 1                        # allow 1 extra pod during rollout
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
      - name: web
        image: myregistry/web-app:2.0
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets          # K8s Secret — not plaintext in the manifest
              key: database-url
        - name: REDIS_URL
          value: "redis://cache-service:6379"   # service DNS name resolves automatically
        readinessProbe:                  # K8s only routes traffic AFTER this probe passes
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
          failureThreshold: 3           # remove from load balancer after 3 failures
---
# kubernetes/postgres-statefulset.yaml
# Databases need StatefulSet (stable network identity + ordered deployment),
# not Deployment (random pod names, no ordering guarantees)
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: production
spec:
  serviceName: postgres                 # creates a headless service for stable DNS
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15
        env:
        - name: POSTGRES_DB
          value: appdb
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: db-username
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: db-password
        volumeMounts:
        - name: postgres-data
          mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:                 # PVC per pod — persists across pod restarts
  - metadata:
      name: postgres-data
    spec:
      accessModes: [ReadWriteOnce]
      storageClassName: gp3
      resources:
        requests:
          storage: 20Gi
```

```bash
# Apply all manifests at once (K8s handles dependency ordering via readinessProbe)
kubectl apply -f kubernetes/

# In Compose, "depends_on" is startup order only.
# In K8s, readinessProbe ensures the web pod only receives traffic AFTER postgres is ready.
kubectl get pods -w   # watch pods come up in order
```

---

## 3. Rolling Update and Rollback

```bash
# =======================================================
# DOCKER: update requires manual intervention
# =======================================================
# Pull the new image on the server
docker pull myregistry/web-app:2.1

# Stop old container (downtime starts here)
docker stop web-server

# Start new container (downtime ends here — manual coordination required for zero-downtime)
docker run -d \
  --name web-server \
  -p 80:8080 \
  myregistry/web-app:2.1

# To rollback: stop and start with the old image tag (manual, error-prone)
docker stop web-server && docker rm web-server
docker run -d --name web-server -p 80:8080 myregistry/web-app:2.0
```

```bash
# =======================================================
# KUBERNETES: zero-downtime rolling update + one-command rollback
# =======================================================

# Update the image — K8s replaces pods one at a time, checking readinessProbe
# before proceeding. Zero downtime as long as replicas >= 2.
kubectl set image deployment/web-app web=myregistry/web-app:2.1 -n production

# Watch the rolling update in progress
kubectl rollout status deployment/web-app -n production
# Output: Waiting for deployment "web-app" rollout to finish: 1 out of 3 new replicas have been updated...

# View rollout history (K8s keeps the last 10 ReplicaSets by default)
kubectl rollout history deployment/web-app -n production
# REVISION  CHANGE-CAUSE
# 1         <none>
# 2         <none>

# Rollback to the previous version (the old ReplicaSet scales back up)
kubectl rollout undo deployment/web-app -n production

# Rollback to a specific revision
kubectl rollout undo deployment/web-app -n production --to-revision=1

# Pause a rollout (investigate before proceeding)
kubectl rollout pause deployment/web-app -n production
kubectl rollout resume deployment/web-app -n production
```

---

## 4. Environment Variables: Docker -e vs ConfigMap and Secret

```bash
# =======================================================
# DOCKER: environment variables as flags or .env files
# =======================================================

# Inline environment variables (visible in ps, history, logs)
docker run -d \
  -e DATABASE_PASSWORD=mysecret \       # plaintext in shell history — not safe
  -e LOG_LEVEL=info \
  myregistry/app:1.0

# Docker .env file (slightly better, but still a plaintext file on disk)
# .env file:
# DATABASE_PASSWORD=mysecret
# LOG_LEVEL=info
docker run --env-file .env myregistry/app:1.0
```

```yaml
# kubernetes/configmap.yaml
# Non-sensitive configuration — safe to store in Git and version-controlled manifests.
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: production
data:
  LOG_LEVEL: "info"
  FEATURE_FLAG_DARK_MODE: "true"
  APP_ENV: "production"
  MAX_CONNECTIONS: "100"
---
# kubernetes/secret.yaml
# Sensitive values — base64-encoded (not encrypted at rest by default,
# but stored in etcd and never appear in Git).
# In production: use External Secrets Operator or Sealed Secrets instead.
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
  namespace: production
type: Opaque
data:
  # echo -n "s3cr3t!Pass" | base64
  database-url: cG9zdGdyZXM6Ly9hcHB1c2VyOnMzY3IzdCFQYXNzQGRiOjU0MzIvYXBwZGI=
  db-username: YXBwdXNlcg==
  db-password: czNjcjN0IVBhc3M=
---
# kubernetes/deployment-with-config.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: production
spec:
  replicas: 2
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
      - name: web
        image: myregistry/web-app:2.0
        # Load all ConfigMap keys as environment variables at once
        envFrom:
        - configMapRef:
            name: app-config             # injects LOG_LEVEL, FEATURE_FLAG_DARK_MODE, etc.

        # Load individual secret values as environment variables
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: db-password
```

```bash
# Apply ConfigMap and Secret
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/secret.yaml
kubectl apply -f kubernetes/deployment-with-config.yaml

# Verify env vars are injected into the pod (without revealing the values in logs)
kubectl exec -n production deploy/web-app -- env | grep -E "LOG_LEVEL|APP_ENV"

# Update config without redeploying (ConfigMap change is picked up on next pod restart)
kubectl edit configmap app-config -n production
kubectl rollout restart deployment/web-app -n production  # force pods to restart and pick up new config
```

---

## 5. Auto-Scaling: Kubernetes HPA vs Docker Manual Scaling

```bash
# =======================================================
# DOCKER: scaling is manual
# =======================================================
# Traffic spike at midnight? You have to notice it, SSH in, and manually scale.
docker run -d --name web-2 -p 8081:8080 myregistry/web-app:2.0  # start another manually
docker run -d --name web-3 -p 8082:8080 myregistry/web-app:2.0
# Plus you need to update your load balancer to include these ports — no automation.
```

```yaml
# hpa.yaml
# HorizontalPodAutoscaler automatically adds or removes replicas based on CPU usage.
# When CPU exceeds 70%, K8s adds pods. When it drops, it scales back down.
# No human intervention required.
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-app-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app                        # the Deployment to scale
  minReplicas: 2                         # never go below 2 (keeps the service up if traffic drops)
  maxReplicas: 20                        # never exceed 20 (cost guardrail)
  metrics:
  # Scale based on CPU utilization
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70           # add a replica when average CPU across pods > 70%

  # Also scale based on memory (optional — prevent OOM kills under load)
  - type: Resource
    resource:
      name: memory
      target:
        type: AverageValue
        averageValue: 800Mi              # add a replica when average memory > 800Mi per pod

  behavior:
    scaleUp:
      stabilizationWindowSeconds: 30    # wait 30s before scaling up again (prevent thrashing)
      policies:
      - type: Pods
        value: 2                         # add at most 2 pods per scale-up event
        periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300   # wait 5 minutes before scaling down (traffic might return)
      policies:
      - type: Pods
        value: 1                         # remove at most 1 pod per scale-down event
        periodSeconds: 60
```

```bash
kubectl apply -f hpa.yaml

# Watch the HPA in action
kubectl get hpa web-app-hpa -n production -w
# TARGETS shows current CPU vs target: 45%/70% means no scaling needed

# Simulate load to trigger scale-up
kubectl run load-generator --image=busybox --restart=Never \
  -- /bin/sh -c "while true; do wget -q -O- http://web-app-service/; done"

# Watch pods scale out automatically
kubectl get pods -n production -l app=web-app -w

# Stop load generator and watch scale-in (after 5-minute stabilization window)
kubectl delete pod load-generator
```

---

## 📂 Navigation

**In this folder:**
| File | |
|---|---|
| [Theory.md](./Theory.md) | Full explanation |
| [Cheatsheet.md](./Cheatsheet.md) | Quick reference |
| [Interview_QA.md](./Interview_QA.md) | Interview prep |
| **Code_Example.md** | you are here |

⬅️ **Prev:** [Home](../../../README.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Compose to K8s Migration](../02_Compose_to_K8s_Migration/Code_Example.md)
🏠 **[Home](../../../README.md)**
