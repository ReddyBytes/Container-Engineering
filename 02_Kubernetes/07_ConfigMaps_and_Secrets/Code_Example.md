# Module 07 — Code Examples: ConfigMaps and Secrets

## Example 1: ConfigMap as Environment Variables

```yaml
# app-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: default
data:
  # Simple string values
  DATABASE_HOST: "postgres.default.svc.cluster.local"
  DATABASE_PORT: "5432"
  DATABASE_NAME: "myapp"
  LOG_LEVEL: "info"
  CACHE_TTL_SECONDS: "300"
  FEATURE_DARK_MODE: "true"
  SERVICE_URL: "https://api.example.com"
---
# pod-env-from-configmap.yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-env-demo
spec:
  containers:
  - name: app
    image: busybox:1.36
    command: ["/bin/sh", "-c", "env | sort && sleep 3600"]
    env:
    # Individual key from ConfigMap, with custom env var name
    - name: DB_HOST                        # Env var name in the container
      valueFrom:
        configMapKeyRef:
          name: app-config                 # ConfigMap name
          key: DATABASE_HOST               # Key in the ConfigMap

    - name: DB_PORT
      valueFrom:
        configMapKeyRef:
          name: app-config
          key: DATABASE_PORT

    # Load ALL keys from ConfigMap as env vars (key names become var names)
    envFrom:
    - configMapRef:
        name: app-config                   # All 7 keys become env vars
```

```bash
kubectl apply -f app-configmap.yaml
kubectl apply -f pod-env-from-configmap.yaml

# View env vars inside the pod
kubectl logs app-env-demo | grep -E "DATABASE|LOG|CACHE|FEATURE"

# Or exec in
kubectl exec app-env-demo -- env | grep -E "DATABASE|LOG"
```

---

## Example 2: ConfigMap as Mounted Files

```yaml
# nginx-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: nginx-config
data:
  # Each key becomes a file in the mounted directory
  nginx.conf: |
    events {
      worker_connections 1024;
    }
    http {
      server {
        listen 80;
        server_name _;

        location / {
          root /usr/share/nginx/html;
          index index.html;
        }

        location /health {
          return 200 "healthy\n";
          add_header Content-Type text/plain;
        }
      }
    }

  # Second file in the same ConfigMap
  index.html: |
    <!DOCTYPE html>
    <html>
    <body><h1>Hello from ConfigMap!</h1></body>
    </html>
---
# nginx-pod-with-config.yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx-configured
spec:
  containers:
  - name: nginx
    image: nginx:1.25
    ports:
    - containerPort: 80
    volumeMounts:
    - name: nginx-config-vol
      mountPath: /etc/nginx/nginx.conf     # Mount a specific key as a single file
      subPath: nginx.conf                  # subPath = use only this key, not the whole directory
    - name: html-vol
      mountPath: /usr/share/nginx/html     # Mount the whole directory
  volumes:
  - name: nginx-config-vol
    configMap:
      name: nginx-config
      items:
      - key: nginx.conf
        path: nginx.conf                   # Map key to filename in mount
  - name: html-vol
    configMap:
      name: nginx-config
      items:
      - key: index.html
        path: index.html
```

```bash
kubectl apply -f nginx-configmap.yaml
kubectl apply -f nginx-pod-with-config.yaml

# Verify the files are mounted
kubectl exec nginx-configured -- cat /etc/nginx/nginx.conf
kubectl exec nginx-configured -- cat /usr/share/nginx/html/index.html

# Test the server
kubectl port-forward pod/nginx-configured 8080:80
curl http://localhost:8080        # Should return our custom HTML
curl http://localhost:8080/health # Should return "healthy"

# Update the ConfigMap (hot reload demo)
kubectl edit configmap nginx-config
# Change the HTML content and save

# Wait ~1-2 minutes, then check — file updates automatically
kubectl exec nginx-configured -- cat /usr/share/nginx/html/index.html
# The file content has updated!
# NOTE: nginx itself won't reload unless it watches for file changes
```

---

## Example 3: Secret from Literal Values

```yaml
# db-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
  namespace: default
type: Opaque
data:
  # Values must be base64-encoded
  # echo -n "postgres" | base64     → cG9zdGdyZXM=
  # echo -n "supersecret123" | base64 → c3VwZXJzZWNyZXQxMjM=
  DB_USER: cG9zdGdyZXM=
  DB_PASSWORD: c3VwZXJzZWNyZXQxMjM=

stringData:
  # stringData lets you write plain text; K8s encodes it on save
  # Great for readability in development; NEVER commit real passwords
  DB_NAME: "myapp_production"
  JWT_SECRET: "my-jwt-signing-key"
```

```bash
# Or create imperatively (more secure — no YAML with passwords to manage)
kubectl create secret generic db-credentials \
  --from-literal=DB_USER=postgres \
  --from-literal=DB_PASSWORD=supersecret123 \
  --from-literal=DB_NAME=myapp_production

# Verify the secret exists (values are hidden)
kubectl describe secret db-credentials
# Name:         db-credentials
# Type:         Opaque
# Data
# ====
# DB_NAME:      16 bytes
# DB_PASSWORD:  13 bytes
# DB_USER:      8 bytes

# Decode to verify (careful — this shows the actual value)
kubectl get secret db-credentials -o jsonpath='{.data.DB_PASSWORD}' | base64 -d
# supersecret123
```

---

## Example 4: Secret from File (TLS Certificates)

```bash
# Generate a self-signed certificate for testing
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ./tls.key -out ./tls.crt \
  -subj "/CN=my-app.example.com"

# Create TLS secret from files
kubectl create secret tls my-app-tls \
  --cert=./tls.crt \
  --key=./tls.key
```

```yaml
# pod-with-tls-secret.yaml
# Mount TLS cert and key into a container as files
apiVersion: v1
kind: Pod
metadata:
  name: tls-server
spec:
  containers:
  - name: server
    image: nginx:1.25
    volumeMounts:
    - name: tls-vol
      mountPath: /etc/tls                  # Files appear at /etc/tls/tls.crt and /etc/tls/tls.key
      readOnly: true                       # Best practice: mount secrets as read-only
  volumes:
  - name: tls-vol
    secret:
      secretName: my-app-tls               # Reference the TLS Secret
      defaultMode: 0400                    # File permissions: owner read-only (secure)
```

---

## Example 5: envFrom — All Keys at Once

```yaml
# combined-config.yaml
# Load all keys from a ConfigMap AND a Secret into the same pod
apiVersion: v1
kind: Pod
metadata:
  name: full-config-app
spec:
  containers:
  - name: app
    image: busybox:1.36
    command: ["/bin/sh", "-c", "env | sort && sleep 3600"]

    envFrom:
    # Load all ConfigMap keys
    - configMapRef:
        name: app-config
    # Load all Secret keys (mixed into same env)
    - secretRef:
        name: db-credentials
    # Optional: prefix all keys from this source (avoid name collisions)
    - configMapRef:
        name: feature-flags
        # NOTE: prefix option is available in some K8s versions
        # prefix: FEATURE_

    # You can still add individual vars on top of envFrom
    env:
    - name: POD_NAME
      valueFrom:
        fieldRef:
          fieldPath: metadata.name
    - name: NODE_NAME
      valueFrom:
        fieldRef:
          fieldPath: spec.nodeName
```

---

## Example 6: imagePullSecret for Private Registry

```bash
# Create Docker registry credentials
kubectl create secret docker-registry my-registry \
  --docker-server=registry.example.com \
  --docker-username=myuser \
  --docker-password=mypassword \
  --docker-email=ops@example.com
```

```yaml
# pod-private-image.yaml
# Pull an image from a private registry
apiVersion: v1
kind: Pod
metadata:
  name: private-app
spec:
  imagePullSecrets:
  - name: my-registry                    # Reference the Docker registry secret
  containers:
  - name: app
    image: registry.example.com/my-org/my-private-app:1.2.3
    resources:
      requests:
        memory: "128Mi"
        cpu: "100m"
      limits:
        memory: "256Mi"
        cpu: "200m"
```

```bash
kubectl apply -f pod-private-image.yaml

# If the imagePullSecret is wrong, you'll see:
# Failed to pull image: unauthorized: authentication required

# Attach imagePullSecret to a ServiceAccount so all pods in the namespace get it
kubectl patch serviceaccount default -p \
  '{"imagePullSecrets": [{"name": "my-registry"}]}'
```

---

## Navigation

| File | Description |
|------|-------------|
| [Theory.md](./Theory.md) | ConfigMaps and Secrets explained |
| [Cheatsheet.md](./Cheatsheet.md) | Quick reference commands |
| [Interview_QA.md](./Interview_QA.md) | Interview questions and answers |
| [Code_Example.md](./Code_Example.md) | You are here — working YAML examples |

**Previous:** [06_Services](../06_Services/Code_Example.md) |
**Next:** [08_Namespaces](../08_Namespaces/Theory.md)
