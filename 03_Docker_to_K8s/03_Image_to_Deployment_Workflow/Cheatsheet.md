# Module 03 — Image to Deployment Workflow Cheatsheet

## The Complete Build-Push-Deploy Pipeline

```bash
# 1. Build the image
docker build -t myapp:v1 .

# 2. Tag for your registry
docker tag myapp:v1 ghcr.io/myorg/myapp:v1

# 3. Authenticate to registry
echo $GITHUB_TOKEN | docker login ghcr.io -u myusername --password-stdin

# 4. Push to registry
docker push ghcr.io/myorg/myapp:v1

# 5. Apply Deployment to cluster
kubectl apply -f deployment.yaml

# 6. Apply Service
kubectl apply -f service.yaml

# 7. Apply Ingress (for HTTP traffic)
kubectl apply -f ingress.yaml

# 8. Verify everything is running
kubectl get pods -n production
kubectl get service -n production
kubectl get ingress -n production
```

---

## Build Commands

```bash
# Standard build
docker build -t myapp:v1 .

# Multi-platform (for ARM nodes like AWS Graviton)
docker buildx build --platform linux/amd64,linux/arm64 -t myapp:v1 .

# Build with git SHA as tag (recommended in CI)
GIT_SHA=$(git rev-parse --short HEAD)
docker build -t myapp:$GIT_SHA .

# Build with build args (bake version info into binary)
docker build \
  --build-arg VERSION=1.0.0 \
  --build-arg GIT_SHA=$(git rev-parse --short HEAD) \
  -t myapp:v1 .

# Verify image exists locally
docker images myapp
docker inspect myapp:v1
```

---

## Registry Authentication

```bash
# Docker Hub
docker login
docker logout

# GitHub Container Registry (GHCR)
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# AWS ECR (credentials expire every 12 hours)
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  123456789.dkr.ecr.us-east-1.amazonaws.com

# Google Container Registry
gcloud auth configure-docker gcr.io

# Azure Container Registry
az acr login --name myregistry
```

---

## Creating imagePullSecrets (for Private Registries)

```bash
# Create pull secret from credentials
kubectl create secret docker-registry regcred \
  --docker-server=ghcr.io \
  --docker-username=myusername \
  --docker-password=$GITHUB_TOKEN \
  --namespace=production

# Create pull secret from existing Docker config
kubectl create secret generic regcred \
  --from-file=.dockerconfigjson=$HOME/.docker/config.json \
  --type=kubernetes.io/dockerconfigjson \
  --namespace=production

# View the secret (base64 encoded)
kubectl get secret regcred -o yaml -n production

# Attach imagePullSecret to a ServiceAccount (so all Pods use it)
kubectl patch serviceaccount default -n production \
  -p '{"imagePullSecrets": [{"name": "regcred"}]}'
```

---

## Deployment Commands

```bash
# Apply a Deployment
kubectl apply -f deployment.yaml

# Apply everything in a directory
kubectl apply -f k8s/

# Watch rollout progress
kubectl rollout status deployment/myapp -n production

# View all Pods for a Deployment
kubectl get pods -n production -l app=myapp

# Get deployment details
kubectl describe deployment myapp -n production

# Check which image is running
kubectl get deployment myapp -n production -o jsonpath='{.spec.template.spec.containers[0].image}'
```

---

## Update and Rollback Commands

```bash
# Update image (imperative — fast for debugging)
kubectl set image deployment/myapp \
  myapp=ghcr.io/myorg/myapp:v2 \
  -n production

# Update image (declarative — preferred for production)
# Edit deployment.yaml, then:
kubectl apply -f deployment.yaml

# Watch the rolling update
kubectl rollout status deployment/myapp -n production

# Pause a rollout (to stop mid-way)
kubectl rollout pause deployment/myapp -n production

# Resume a paused rollout
kubectl rollout resume deployment/myapp -n production

# View rollout history
kubectl rollout history deployment/myapp -n production

# Rollback to previous version
kubectl rollout undo deployment/myapp -n production

# Rollback to a specific revision
kubectl rollout undo deployment/myapp --to-revision=2 -n production

# Restart all Pods (forces fresh pull if imagePullPolicy: Always)
kubectl rollout restart deployment/myapp -n production
```

---

## Service and Ingress Commands

```bash
# Apply Service
kubectl apply -f service.yaml

# View services
kubectl get service -n production

# Describe a service (see endpoints / which Pods it routes to)
kubectl describe service myapp -n production

# Port-forward for local testing (no Ingress needed)
kubectl port-forward service/myapp 8080:80 -n production
kubectl port-forward pod/<pod-name> 8080:8080 -n production

# Apply Ingress
kubectl apply -f ingress.yaml

# View ingresses
kubectl get ingress -n production

# Describe ingress (see routing rules)
kubectl describe ingress myapp-ingress -n production
```

---

## Debugging a Deployment

```bash
# Check Pod status
kubectl get pods -n production

# Describe a Pod (look at Events section at bottom)
kubectl describe pod <pod-name> -n production

# View Pod logs
kubectl logs <pod-name> -n production

# Follow live logs
kubectl logs -f <pod-name> -n production

# Logs from previous container instance (after a crash)
kubectl logs <pod-name> -n production --previous

# Exec into a running container
kubectl exec -it <pod-name> -n production -- /bin/sh

# Check if image pull is failing
kubectl describe pod <pod-name> -n production | grep -A 10 Events

# Check resource usage
kubectl top pods -n production
```

---

## imagePullPolicy Quick Reference

| Policy | When to Use | Behavior |
|---|---|---|
| `Always` | Mutable tags, `latest` | Always contacts registry — guarantees fresh image |
| `IfNotPresent` | Versioned tags (v1, sha256) | Uses node cache if available — faster startup |
| `Never` | Pre-loaded / air-gapped | Fails if image not on node — never contacts registry |

**Default rule**: `latest` tag → `Always`. Any other tag → `IfNotPresent`.

**Best practice**: Use versioned tags + `IfNotPresent` for production.

---

## Key YAML Snippets

### Deployment with imagePullSecret

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: myapp
    spec:
      imagePullSecrets:
        - name: regcred
      containers:
        - name: myapp
          image: ghcr.io/myorg/myapp:v1
          imagePullPolicy: IfNotPresent
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
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
```

### ClusterIP Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: myapp
  namespace: production
spec:
  selector:
    app: myapp
  ports:
    - port: 80
      targetPort: 8080
  type: ClusterIP
```

### Ingress with TLS

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp-ingress
  namespace: production
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
  tls:
    - hosts:
        - myapp.example.com
      secretName: myapp-tls
```

---

## 📂 Navigation

⬅️ **Prev:** [Compose to K8s Migration](../02_Compose_to_K8s_Migration/Interview_QA.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Projects](../../04_Projects/01_Dockerize_a_Python_App/Theory.md)

| File | Description |
|---|---|
| [Theory.md](./Theory.md) | Image to Deployment — full explanation |
| [Cheatsheet.md](./Cheatsheet.md) | You are here — quick reference |
| [Interview_QA.md](./Interview_QA.md) | Interview questions and answers |
