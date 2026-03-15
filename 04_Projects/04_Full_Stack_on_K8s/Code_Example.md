# Code Examples: Full-Stack App on Kubernetes

---

## k8s/namespace.yaml

```yaml
# k8s/namespace.yaml
# Namespaces provide logical isolation within a cluster.
# All project resources go in the 'fullstack' namespace.

apiVersion: v1
kind: Namespace
metadata:
  name: fullstack
  labels:
    project: fullstack-demo
```

---

## k8s/postgres-service.yaml

```yaml
# k8s/postgres-service.yaml
# Headless service (clusterIP: None) for the StatefulSet.
# Headless services give each pod a stable DNS name:
#   postgres-0.postgres.fullstack.svc.cluster.local
# This is important for stateful apps where pods aren't interchangeable.

apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: fullstack
  labels:
    app: postgres
spec:
  # clusterIP: None makes this a headless service.
  # No virtual IP is allocated; DNS returns the pod IPs directly.
  clusterIP: None
  selector:
    app: postgres
  ports:
    - port: 5432
      targetPort: 5432
      name: postgres
```

---

## k8s/postgres-statefulset.yaml

```yaml
# k8s/postgres-statefulset.yaml
# StatefulSet is the right workload type for databases.
# Unlike Deployments, StatefulSets:
#   - Give pods stable, ordered names (postgres-0, postgres-1, ...)
#   - Give each pod its own PVC (not shared)
#   - Terminate pods in reverse order on scale-down
#   - Guarantee ordered startup (postgres-0 before postgres-1)

apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: fullstack
spec:
  serviceName: postgres    # Must match the headless Service name above
  replicas: 1              # For a learning project, 1 replica is fine.
                           # Production uses a HA setup (postgres-operator, etc.)
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
          env:
            - name: POSTGRES_USER
              valueFrom:
                secretKeyRef:
                  name: backend-secret
                  key: DB_USER
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: backend-secret
                  key: DB_PASSWORD
            - name: POSTGRES_DB
              valueFrom:
                secretKeyRef:
                  name: backend-secret
                  key: DB_NAME
            # Store data in a known directory for the PVC mount
            - name: PGDATA
              value: /var/lib/postgresql/data/pgdata
          ports:
            - containerPort: 5432
          resources:
            requests:
              cpu: "100m"
              memory: "256Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
          readinessProbe:
            exec:
              command:
                - pg_isready
                - -U
                - $(POSTGRES_USER)
                - -d
                - $(POSTGRES_DB)
            initialDelaySeconds: 10
            periodSeconds: 10
          # Mount the PVC at the Postgres data directory
          volumeMounts:
            - name: postgres-storage
              mountPath: /var/lib/postgresql/data

  # volumeClaimTemplates creates a PVC for each pod.
  # postgres-0 gets 'postgres-storage-postgres-0'.
  volumeClaimTemplates:
    - metadata:
        name: postgres-storage
      spec:
        accessModes:
          - ReadWriteOnce   # Only one node can mount this volume at a time
        resources:
          requests:
            storage: 5Gi
        # storageClassName: standard  # Uncomment if you need to specify a class
```

---

## k8s/backend-configmap.yaml

```yaml
# k8s/backend-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: backend-config
  namespace: fullstack
  labels:
    app: backend
data:
  DB_HOST: "postgres.fullstack.svc.cluster.local"
  DB_PORT: "5432"
  LOG_LEVEL: "info"
  APP_ENV: "production"
```

---

## k8s/backend-secret.yaml

```yaml
# k8s/backend-secret.yaml
# Values are base64-encoded.
# echo -n "appuser" | base64     => YXBwdXNlcg==
# echo -n "dbpassword123" | base64 => ZGJwYXNzd29yZDEyMw==
# echo -n "appdb" | base64       => YXBwZGI=

apiVersion: v1
kind: Secret
metadata:
  name: backend-secret
  namespace: fullstack
  labels:
    app: backend
type: Opaque
data:
  DB_USER: YXBwdXNlcg==
  DB_PASSWORD: ZGJwYXNzd29yZDEyMw==
  DB_NAME: YXBwZGI=
```

---

## k8s/backend-deployment.yaml

```yaml
# k8s/backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: fullstack
  labels:
    app: backend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: backend
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
        - name: backend
          image: YOUR_USERNAME/fullstack-backend:1.0.0
          imagePullPolicy: Always
          ports:
            - containerPort: 8000
          envFrom:
            - configMapRef:
                name: backend-config
            - secretRef:
                name: backend-secret
          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "500m"
              memory: "256Mi"
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 20
            periodSeconds: 20
```

---

## k8s/backend-service.yaml

```yaml
# k8s/backend-service.yaml
# ClusterIP — only reachable from within the cluster.
# The Ingress routes /api/* to this service.
apiVersion: v1
kind: Service
metadata:
  name: backend-svc
  namespace: fullstack
  labels:
    app: backend
spec:
  type: ClusterIP
  selector:
    app: backend
  ports:
    - port: 8000
      targetPort: 8000
      name: http
```

---

## k8s/frontend-deployment.yaml

```yaml
# k8s/frontend-deployment.yaml
# The frontend is a static React build served by nginx.
# nginx is configured to proxy /api requests to the backend service.

apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: fullstack
  labels:
    app: frontend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
        - name: frontend
          image: YOUR_USERNAME/fullstack-frontend:1.0.0
          imagePullPolicy: Always
          ports:
            - containerPort: 80
          resources:
            requests:
              cpu: "50m"
              memory: "64Mi"
            limits:
              cpu: "200m"
              memory: "128Mi"
          readinessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 5
            periodSeconds: 10
```

---

## k8s/frontend-service.yaml

```yaml
# k8s/frontend-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: frontend-svc
  namespace: fullstack
  labels:
    app: frontend
spec:
  type: ClusterIP
  selector:
    app: frontend
  ports:
    - port: 80
      targetPort: 80
      name: http
```

---

## k8s/ingress.yaml

```yaml
# k8s/ingress.yaml
# Ingress routes external HTTP(S) traffic to Services inside the cluster.
# Requires an Ingress controller to be installed (nginx-ingress here).
# On minikube: minikube addons enable ingress

apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: fullstack-ingress
  namespace: fullstack
  annotations:
    # Use the nginx ingress controller
    kubernetes.io/ingress.class: "nginx"
    # Strip the /api prefix before forwarding to the backend.
    # The backend sees /items instead of /api/items.
    nginx.ingress.kubernetes.io/rewrite-target: /$2
spec:
  rules:
    - host: app.local
      http:
        paths:
          # Route /api/* to the backend service.
          # The regex capture group ($2) is used by rewrite-target above.
          - path: /api(/|$)(.*)
            pathType: ImplementationSpecific
            backend:
              service:
                name: backend-svc
                port:
                  number: 8000

          # Route everything else to the frontend.
          # This must come AFTER the /api rule.
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend-svc
                port:
                  number: 80
```

---

## frontend/Dockerfile

```dockerfile
# frontend/Dockerfile
# Two-stage build for the React app.
# Stage 1: build the static files with Node.
# Stage 2: serve them with nginx.

FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --silent
COPY . .
RUN npm run build

FROM nginx:1.25-alpine AS runtime
# Remove the default nginx HTML content
RUN rm -rf /usr/share/nginx/html/*
# Copy the React build output
COPY --from=builder /app/build /usr/share/nginx/html
# Copy our nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

---

## frontend/nginx.conf

```nginx
# frontend/nginx.conf
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # Serve the React app. All unknown paths return index.html
    # so that React Router handles client-side routing.
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Gzip static assets
    gzip on;
    gzip_types text/plain text/css application/javascript application/json;
}
```

---

## 📂 Navigation

| | |
|---|---|
| Guide | [Project_Guide.md](./Project_Guide.md) |
| Steps | [Step_by_Step.md](./Step_by_Step.md) |
| All Projects | [04_Projects/](../) |
