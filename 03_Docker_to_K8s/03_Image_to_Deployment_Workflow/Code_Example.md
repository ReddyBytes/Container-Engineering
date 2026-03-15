# Image to Deployment Workflow — Code Examples

This is the complete step-by-step workflow every engineer follows to get code running in Kubernetes.

---

## The Application

```go
// main.go — a simple Go HTTP server
package main

import (
    "encoding/json"
    "fmt"
    "log"
    "net/http"
    "os"
)

func main() {
    port := os.Getenv("PORT")
    if port == "" {
        port = "8080"
    }

    http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
        fmt.Fprintf(w, "Hello from myapp version %s\n", os.Getenv("APP_VERSION"))
    })

    // Health endpoint for K8s probes
    http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("Content-Type", "application/json")
        json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
    })

    log.Printf("Starting server on port %s", port)
    log.Fatal(http.ListenAndServe(":"+port, nil))
}
```

---

## Step 1: Write the Dockerfile

```dockerfile
# Dockerfile
# Multi-stage: build → minimal runtime image

# ============================================================
# Stage 1: Compile the Go binary
# ============================================================
FROM golang:1.22 AS builder
WORKDIR /app

# Copy dependency manifests first (better cache)
COPY go.mod go.sum ./
RUN go mod download

# Copy source and build
COPY . .
# CGO_ENABLED=0: static binary, no external C libraries
# GOOS=linux: compile for Linux (even if you're on macOS)
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o server .

# ============================================================
# Stage 2: Minimal production image
# ============================================================
FROM alpine:3.19

# CA certificates for HTTPS calls
RUN apk --no-cache add ca-certificates

WORKDIR /app

# Non-root user for security
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
COPY --from=builder /app/server .
RUN chown appuser:appgroup server
USER appuser

# Health check (used by Docker/Swarm; K8s uses probes instead)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q -O- http://localhost:8080/health || exit 1

EXPOSE 8080
CMD ["./server"]
```

---

## Step 2: Build the Image

```bash
# Build with semantic version tag
docker build -t myapp:1.0.0 .

# Build with multiple tags (semver + git SHA)
GIT_SHA=$(git rev-parse --short HEAD)
docker build \
  -t myapp:1.0.0 \
  -t myapp:${GIT_SHA} \
  .

# Verify the build
docker images myapp
# REPOSITORY   TAG       SIZE
# myapp        1.0.0     14.2MB
# myapp        a3f9b2c   14.2MB

# Test it locally
docker run --rm -p 8080:8080 -e APP_VERSION=1.0.0 myapp:1.0.0
curl http://localhost:8080/health
# {"status":"ok"}
```

---

## Step 3: Push to Registry (GHCR)

```bash
# Authenticate to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io \
  --username MY_GITHUB_USERNAME \
  --password-stdin

# Tag with the full registry path
REGISTRY="ghcr.io/my-org"
docker tag myapp:1.0.0 ${REGISTRY}/myapp:1.0.0
docker tag myapp:1.0.0 ${REGISTRY}/myapp:${GIT_SHA}

# Push both tags
docker push ${REGISTRY}/myapp:1.0.0
docker push ${REGISTRY}/myapp:${GIT_SHA}

# Verify
docker manifest inspect ${REGISTRY}/myapp:1.0.0
```

---

## Step 4: Kubernetes Deployment YAML with imagePullSecrets

```yaml
# deployment.yaml
# Complete production-ready Deployment

---
# Create the pull secret so K8s nodes can authenticate to GHCR
# (run this once manually or in CI before applying the Deployment)
# kubectl create secret docker-registry ghcr-pull-secret \
#   --docker-server=ghcr.io \
#   --docker-username=MY_GITHUB_USERNAME \
#   --docker-password=$GITHUB_TOKEN \
#   --namespace=production

apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: production
  labels:
    app.kubernetes.io/name: myapp
    app.kubernetes.io/version: "1.0.0"
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  # Rolling update: never go below 3 replicas during update
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1         # One extra Pod allowed during update
      maxUnavailable: 0   # Zero downtime: old Pod kept until new one is ready

  template:
    metadata:
      labels:
        app: myapp
        version: "1.0.0"
    spec:
      # --------------------------------------------------------
      # imagePullSecrets: grants nodes permission to pull from
      # private registry (ghcr.io in this case)
      # --------------------------------------------------------
      imagePullSecrets:
        - name: ghcr-pull-secret

      containers:
        - name: app
          # Use specific tag — never "latest" in production
          image: ghcr.io/my-org/myapp:1.0.0

          # imagePullPolicy: Always ensures we get the exact image
          # for the tag, not a stale cached version on the node
          imagePullPolicy: Always

          ports:
            - containerPort: 8080

          env:
            - name: PORT
              value: "8080"
            - name: APP_VERSION
              value: "1.0.0"

          # --------------------------------------------------------
          # Readiness probe: traffic is ONLY sent to this Pod after
          # this probe succeeds. Prevents "premature traffic."
          # --------------------------------------------------------
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 5    # Wait 5s after start before first check
            periodSeconds: 10          # Check every 10 seconds
            timeoutSeconds: 5          # Fail if no response in 5 seconds
            failureThreshold: 3        # 3 consecutive failures = not ready

          # --------------------------------------------------------
          # Liveness probe: K8s RESTARTS the container if this fails.
          # Catches deadlocks, OOM situations, and other stuck states.
          # --------------------------------------------------------
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 15   # Give app more time before first liveness check
            periodSeconds: 20
            timeoutSeconds: 5
            failureThreshold: 3

          # Resource management: always set both requests and limits
          resources:
            requests:
              cpu: "100m"     # 0.1 CPU cores (soft minimum)
              memory: "64Mi"  # 64 MB (used for scheduling)
            limits:
              cpu: "200m"     # 0.2 CPU cores (hard maximum)
              memory: "128Mi" # 128 MB (OOMKilled if exceeded)

---
# Service: exposes the Deployment internally within the cluster
apiVersion: v1
kind: Service
metadata:
  name: myapp
  namespace: production
spec:
  selector:
    app: myapp          # Routes to Pods with this label
  ports:
    - port: 80          # Port the Service listens on
      targetPort: 8080  # Port the container listens on
  type: ClusterIP       # Internal only

---
# Ingress: routes external HTTP traffic to the Service
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp
  namespace: production
  annotations:
    kubernetes.io/ingress.class: nginx
spec:
  rules:
    - host: myapp.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: myapp
                port:
                  number: 80
```

---

## Step 5: Apply and Verify

```bash
# Apply the manifests
kubectl apply -f deployment.yaml

# Watch pods come up in real-time
kubectl get pods -n production -w
# NAME                     READY   STATUS              RESTARTS   AGE
# myapp-6d8f9b7c4-xkp2s    0/1     ContainerCreating   0          2s
# myapp-6d8f9b7c4-xkp2s    0/1     Running             0          5s
# myapp-6d8f9b7c4-xkp2s    1/1     Running             0          15s  ← ready probe passed

# Verify all 3 replicas are running
kubectl get deployment myapp -n production
# NAME    READY   UP-TO-DATE   AVAILABLE
# myapp   3/3     3            3

# Check the Service
kubectl get service myapp -n production

# Check the Ingress
kubectl get ingress myapp -n production

# View logs from all replicas
kubectl logs -l app=myapp -n production --tail=20

# Exec into a Pod to debug
kubectl exec -it deployment/myapp -n production -- sh

# Test the health endpoint from inside the cluster
kubectl run test --rm -it --image=alpine -- wget -q -O- http://myapp.production.svc.cluster.local/health
```

---

## Step 6: Update the Image (Rolling Update)

```bash
# ============================================================
# Scenario: you've built and pushed a new version: 1.0.1
# ============================================================

# Build and push the new version
docker build -t myapp:1.0.1 .
docker tag myapp:1.0.1 ghcr.io/my-org/myapp:1.0.1
docker push ghcr.io/my-org/myapp:1.0.1

# ============================================================
# Option A: Imperative update (quick, but not in git history)
# ============================================================
kubectl set image deployment/myapp \
  app=ghcr.io/my-org/myapp:1.0.1 \
  --namespace=production

# ============================================================
# Option B: Declarative update (preferred — change is in git)
# Edit deployment.yaml: change image tag to 1.0.1
# Then:
# ============================================================
kubectl apply -f deployment.yaml

# ============================================================
# Watch the rolling update
# Old Pods: Terminating
# New Pods: ContainerCreating → Running
# ============================================================
kubectl rollout status deployment/myapp -n production
# Waiting for deployment "myapp" rollout to finish: 1 out of 3 new replicas have been updated...
# Waiting for deployment "myapp" rollout to finish: 2 out of 3 new replicas have been updated...
# Waiting for deployment "myapp" rollout to finish: 2 old replicas are pending termination...
# deployment "myapp" successfully rolled out

# Verify the new version is running
kubectl describe deployment myapp -n production | grep Image
# Image: ghcr.io/my-org/myapp:1.0.1

# ============================================================
# If the rollout is bad — instant rollback
# ============================================================
kubectl rollout undo deployment/myapp -n production

# View rollout history
kubectl rollout history deployment/myapp -n production
# REVISION  CHANGE-CAUSE
# 1         initial deployment
# 2         updated to v1.0.1
# 3         rolled back to v1.0.0
```

---

## Step 7: Create the imagePullSecret in CI (Full Script)

```bash
#!/bin/bash
# This script is typically run in CI after pushing the image
# It ensures the K8s cluster can pull from your private registry

NAMESPACE="production"
SECRET_NAME="ghcr-pull-secret"

# Check if secret exists, delete and recreate (to rotate credentials)
kubectl delete secret ${SECRET_NAME} -n ${NAMESPACE} --ignore-not-found

kubectl create secret docker-registry ${SECRET_NAME} \
  --docker-server=ghcr.io \
  --docker-username="${GITHUB_ACTOR}" \
  --docker-password="${GITHUB_TOKEN}" \
  --namespace="${NAMESPACE}"

echo "Pull secret created: ${SECRET_NAME} in namespace ${NAMESPACE}"

# Patch the default ServiceAccount to use this pull secret automatically
# (so you don't need imagePullSecrets in every Deployment)
kubectl patch serviceaccount default \
  -n ${NAMESPACE} \
  -p "{\"imagePullSecrets\": [{\"name\": \"${SECRET_NAME}\"}]}"
```

---

## Complete CI/CD → K8s Pipeline Reference

```bash
# The complete workflow from code to production (manual version)

# 1. Build
docker build -t myapp:${VERSION} .

# 2. Test
docker run --rm myapp:${VERSION} ./server --run-tests

# 3. Scan
trivy image --exit-code 1 --severity CRITICAL myapp:${VERSION}

# 4. Tag
docker tag myapp:${VERSION} ghcr.io/my-org/myapp:${VERSION}

# 5. Push
docker push ghcr.io/my-org/myapp:${VERSION}

# 6. Deploy
kubectl set image deployment/myapp \
  app=ghcr.io/my-org/myapp:${VERSION} \
  --namespace=production

# 7. Wait for rollout
kubectl rollout status deployment/myapp --namespace=production --timeout=5m

# 8. Verify
kubectl get pods -n production -l app=myapp
```

---

## 📂 Navigation

| | Link |
|---|---|
| Previous | [02 · Compose to K8s Migration](../02_Compose_to_K8s_Migration/Code_Example.md) |
| Theory | [Image to Deployment Theory](./Theory.md) |
| Next | [Section 02 — Kubernetes](../../02_Kubernetes/01_What_is_Kubernetes/Theory.md) |
| Section Home | [Section 03 — Docker to K8s](../README.md) |
