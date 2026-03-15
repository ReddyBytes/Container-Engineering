# Compose to Kubernetes Migration — Code Examples

This file shows a real docker-compose.yml (web + postgres + redis) and the equivalent Kubernetes manifests side by side.

---

## The Application: docker-compose.yml

```yaml
# docker-compose.yml
# A web app with PostgreSQL and Redis
version: "3.9"

services:
  # Frontend + API web service
  web:
    build: .                          # → In K8s: build externally, push to registry
    image: my-org/web:v1.0.0
    ports:
      - "80:3000"                     # → K8s Service + Ingress
    environment:
      NODE_ENV: production
      PORT: "3000"
      LOG_LEVEL: info                 # → K8s ConfigMap
      DATABASE_URL: postgres://appuser:${DB_PASSWORD}@postgres:5432/myapp
      REDIS_URL: redis://redis:6379   # → K8s Secret (has password)
      JWT_SECRET: ${JWT_SECRET}       # → K8s Secret
    depends_on:                       # → K8s readinessProbe
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
    restart: unless-stopped           # → K8s restartPolicy: Always (default)
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: "0.5"
          memory: 512M
        reservations:
          cpus: "0.25"
          memory: 256M

  # PostgreSQL database
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: appuser
      POSTGRES_PASSWORD: ${DB_PASSWORD}  # → K8s Secret
    volumes:
      - pgdata:/var/lib/postgresql/data  # → PersistentVolumeClaim
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U appuser -d myapp"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # Redis cache
  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
    restart: unless-stopped

volumes:
  pgdata:    # Named volume → PersistentVolumeClaim
```

---

## Equivalent Kubernetes Manifests

### 00-namespace.yaml

```yaml
# All resources live in this namespace for clean isolation
apiVersion: v1
kind: Namespace
metadata:
  name: my-app
  labels:
    app.kubernetes.io/name: my-app
```

---

### 01-configmap.yaml

```yaml
# Non-sensitive configuration values
# These replace docker-compose `environment:` for non-secret values
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: my-app
data:
  NODE_ENV: "production"
  PORT: "3000"
  LOG_LEVEL: "info"
  # Note: these reference the K8s Service names for internal DNS
  # "postgres" resolves to postgres.my-app.svc.cluster.local
  DATABASE_URL: "postgres://appuser:$(DB_PASSWORD)@postgres:5432/myapp"
  REDIS_URL: "redis://redis:6379"
  POSTGRES_DB: "myapp"
  POSTGRES_USER: "appuser"
```

---

### 02-secret.yaml

```yaml
# Sensitive values: passwords, tokens, keys
# In production, manage these with Vault, AWS Secrets Manager, or Sealed Secrets
# Never commit real secrets to git — use placeholder values and override in CI/CD
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
  namespace: my-app
type: Opaque
# Values must be base64 encoded: echo -n "value" | base64
# In production, use kubectl create secret or a secrets manager
stringData:            # stringData is automatically base64-encoded
  DB_PASSWORD: "changeme-use-real-secret-in-production"
  JWT_SECRET: "changeme-use-real-secret-in-production"
  POSTGRES_PASSWORD: "changeme-use-real-secret-in-production"
```

---

### 03-postgres-pvc.yaml

```yaml
# Persistent storage for PostgreSQL data
# Replaces the named volume "pgdata" from docker-compose.yml
# StorageClass "standard" provisions storage dynamically (cloud provider)
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-data
  namespace: my-app
spec:
  accessModes:
    - ReadWriteOnce          # One node can read/write at a time (appropriate for DB)
  resources:
    requests:
      storage: 10Gi
  # storageClassName: gp3   # Uncomment and set for your cloud provider
  #                         # AWS: gp3, gp2
  #                         # GCP: standard-rwo
  #                         # Azure: managed-premium
```

---

### 04-postgres-deployment.yaml

```yaml
# PostgreSQL database
# Note: For production databases, use a StatefulSet or a managed DB service (RDS, Cloud SQL)
# This Deployment approach is acceptable for development/staging
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: my-app
  labels:
    app.kubernetes.io/name: postgres
    app.kubernetes.io/part-of: my-app
spec:
  replicas: 1   # Databases should not be replicated this way — use StatefulSet or managed DB
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
          image: postgres:16-alpine
          ports:
            - containerPort: 5432
          env:
            # Pull non-sensitive values from ConfigMap
            - name: POSTGRES_DB
              valueFrom:
                configMapKeyRef:
                  name: app-config
                  key: POSTGRES_DB
            - name: POSTGRES_USER
              valueFrom:
                configMapKeyRef:
                  name: app-config
                  key: POSTGRES_USER
            # Pull sensitive values from Secret
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: app-secrets
                  key: POSTGRES_PASSWORD
          # Readiness probe: traffic is only sent when postgres is accepting connections
          # Replaces healthcheck + depends_on from docker-compose.yml
          readinessProbe:
            exec:
              command:
                - sh
                - -c
                - pg_isready -U appuser -d myapp
            initialDelaySeconds: 10
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 5
          # Liveness probe: restart container if it becomes unhealthy
          livenessProbe:
            exec:
              command:
                - sh
                - -c
                - pg_isready -U appuser -d myapp
            initialDelaySeconds: 30
            periodSeconds: 20
            timeoutSeconds: 5
          resources:
            requests:
              cpu: "250m"      # 0.25 CPU cores
              memory: "256Mi"
            limits:
              cpu: "500m"      # 0.5 CPU cores
              memory: "512Mi"
          # Mount the persistent volume
          volumeMounts:
            - name: postgres-data
              mountPath: /var/lib/postgresql/data
      volumes:
        - name: postgres-data
          persistentVolumeClaim:
            claimName: postgres-data   # References the PVC we created above

---
# Service: enables other Pods to reach postgres at hostname "postgres"
# Replaces docker-compose networks — all Pods in the same namespace can reach this
apiVersion: v1
kind: Service
metadata:
  name: postgres            # ← Other Pods use this DNS name to connect
  namespace: my-app
spec:
  selector:
    app: postgres           # Routes to Pods with this label
  ports:
    - port: 5432
      targetPort: 5432
  type: ClusterIP           # Internal only — not exposed outside the cluster
```

---

### 05-redis-deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: my-app
  labels:
    app.kubernetes.io/name: redis
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
        - name: redis
          image: redis:7-alpine
          # Pass command args — same as docker-compose `command:`
          args:
            - redis-server
            - --maxmemory
            - 256mb
            - --maxmemory-policy
            - allkeys-lru
          ports:
            - containerPort: 6379
          readinessProbe:
            exec:
              command: [redis-cli, ping]
            initialDelaySeconds: 5
            periodSeconds: 10
          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "200m"
              memory: "300Mi"

---
apiVersion: v1
kind: Service
metadata:
  name: redis         # ← Other Pods connect to this hostname
  namespace: my-app
spec:
  selector:
    app: redis
  ports:
    - port: 6379
      targetPort: 6379
  type: ClusterIP
```

---

### 06-web-deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: my-app
  labels:
    app.kubernetes.io/name: web
    app.kubernetes.io/version: v1.0.0
spec:
  replicas: 2   # Same as docker-compose deploy.replicas: 2
  selector:
    matchLabels:
      app: web
  # Rolling update strategy: replace one Pod at a time
  # Equivalent to Swarm's update_config
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1         # Allow one extra Pod during update
      maxUnavailable: 0   # Never go below desired replica count (zero-downtime)
  template:
    metadata:
      labels:
        app: web
        version: v1.0.0
    spec:
      # Init container: wait for postgres to be ready before starting
      # This is the K8s equivalent of depends_on: postgres: condition: service_healthy
      initContainers:
        - name: wait-for-postgres
          image: busybox:1.36
          command:
            - sh
            - -c
            - |
              echo "Waiting for postgres..."
              until nc -z postgres 5432; do
                echo "postgres not ready, waiting..."
                sleep 2
              done
              echo "postgres is ready!"

      containers:
        - name: web
          image: my-org/web:v1.0.0
          ports:
            - containerPort: 3000
          # Load all non-sensitive config from ConfigMap as env vars
          envFrom:
            - configMapRef:
                name: app-config
          # Inject specific secrets
          env:
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: app-secrets
                  key: DB_PASSWORD
            - name: JWT_SECRET
              valueFrom:
                secretKeyRef:
                  name: app-secrets
                  key: JWT_SECRET
          # Readiness probe: traffic only sent when /health returns 200
          # This replaces healthcheck + depends_on in docker-compose.yml
          readinessProbe:
            httpGet:
              path: /health
              port: 3000
            initialDelaySeconds: 15
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
          # Liveness probe: restart container if it stops responding
          livenessProbe:
            httpGet:
              path: /health
              port: 3000
            initialDelaySeconds: 30
            periodSeconds: 20
            timeoutSeconds: 5
          # Resource requests/limits — same as docker-compose deploy.resources
          resources:
            requests:
              cpu: "250m"      # 0.25 CPU (same as compose reservations: 0.25)
              memory: "256Mi"  # 256MB
            limits:
              cpu: "500m"      # 0.5 CPU (same as compose limits: 0.5)
              memory: "512Mi"  # 512MB

---
# Service: internal load balancer across web Pods
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
  type: ClusterIP
```

---

### 07-ingress.yaml

```yaml
# Ingress: HTTP routing from the internet to the web service
# Replaces the docker-compose ports: "80:3000" external exposure
# Requires an Ingress controller (nginx-ingress, traefik, etc.) in your cluster
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-ingress
  namespace: my-app
  annotations:
    kubernetes.io/ingress.class: nginx
    # Uncomment for automatic TLS with cert-manager
    # cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  rules:
    - host: myapp.example.com     # Replace with your domain
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: web
                port:
                  number: 80
  # Uncomment for TLS
  # tls:
  #   - hosts:
  #       - myapp.example.com
  #     secretName: web-tls
```

---

## Apply All Manifests

```bash
# Apply in order (dependencies first)
kubectl apply -f 00-namespace.yaml
kubectl apply -f 01-configmap.yaml
kubectl apply -f 02-secret.yaml
kubectl apply -f 03-postgres-pvc.yaml
kubectl apply -f 04-postgres-deployment.yaml
kubectl apply -f 05-redis-deployment.yaml
kubectl apply -f 06-web-deployment.yaml
kubectl apply -f 07-ingress.yaml

# Or apply all at once (kubectl handles ordering)
kubectl apply -f . --namespace my-app

# Watch pods come up
kubectl get pods -n my-app -w

# Verify everything is running
kubectl get all -n my-app
```

---

## Using kompose to Generate Initial Manifests

```bash
# Install kompose
brew install kompose

# Run in directory containing docker-compose.yml
kompose convert -o k8s/

# Review and ALWAYS edit the output:
# - Add resource requests/limits
# - Add readiness/liveness probes
# - Move secrets from ConfigMap to Secret
# - Replace hostPath volumes with proper PVCs
# - Add Ingress (kompose creates NodePort, not Ingress)
# - Add namespace

ls k8s/
# postgres-deployment.yaml
# postgres-service.yaml
# redis-deployment.yaml
# redis-service.yaml
# web-deployment.yaml
# web-service.yaml
# pgdata-persistentvolumeclaim.yaml
```

---

## 📂 Navigation

| | Link |
|---|---|
| Previous | [01 · Docker vs Kubernetes](../01_Docker_vs_K8s/Theory.md) |
| Theory | [Compose Migration Theory](./Theory.md) |
| Interview Q&A | [Compose Migration Q&A](./Interview_QA.md) |
| Next | [03 · Image to Deployment Workflow](../03_Image_to_Deployment_Workflow/Theory.md) |
| Section Home | [Section 03 — Docker to K8s](../README.md) |
