# Module 02 — Compose to Kubernetes Migration

## The Map Is Not the Territory

When you first look at a Kubernetes manifest after working with Docker Compose, it feels overwhelming. What was five lines in Compose is fifty lines in Kubernetes YAML. What was implied (networking, service discovery) is now explicit.

But the underlying concepts are the same. You're still saying "run this image, expose this port, connect to this database." Kubernetes just gives you more knobs because it handles more complexity.

This module is your translation guide — from the Compose mental model to the Kubernetes mental model. By the end, every key in a docker-compose.yml will have a clear K8s equivalent.

---

## The Core Concept Mapping

Docker Compose thinks in terms of **services** — self-contained units with an image, config, and dependencies. Kubernetes splits this into two separate objects:

- A **Deployment** describes what to run (image, replicas, resource limits, probes)
- A **Service** describes how to reach it (which Pods to route to, what port to expose)

This separation gives you flexibility: you can change routing independently of what's running, and you can have multiple Services pointing to the same Pods.

### Full Mapping Table

| docker-compose.yml key | Kubernetes equivalent | Notes |
|---|---|---|
| `services:` | `Deployment` | One Deployment per service |
| `image:` | `spec.containers[].image` | Same image reference |
| `ports:` | `Service` spec | ClusterIP, NodePort, or LoadBalancer |
| `environment:` | `ConfigMap` (non-sensitive) | Mounted as env vars |
| `environment:` (secrets) | `Secret` | For passwords, tokens, keys |
| `env_file:` | `ConfigMap` + `envFrom` | |
| `volumes:` (named) | `PersistentVolumeClaim` | Requires StorageClass |
| `volumes:` (bind mount) | `hostPath` (avoid in prod) | Or emptyDir for temp |
| `networks:` | K8s Service + NetworkPolicy | Default flat pod network |
| `depends_on: condition: service_healthy` | `readinessProbe` | Traffic withheld until ready |
| `depends_on:` (order) | `initContainers` | Must complete before main container |
| `restart: unless-stopped` | `restartPolicy: Always` | Default in Deployments |
| `healthcheck:` | `livenessProbe` / `readinessProbe` | K8s has two separate probes |
| `deploy.replicas:` | `spec.replicas` | In Deployment spec |
| `deploy.resources.limits:` | `resources.limits` | CPU and memory |
| `deploy.resources.reservations:` | `resources.requests` | CPU and memory |
| `deploy.update_config:` | `strategy.rollingUpdate` | `maxSurge`, `maxUnavailable` |
| `secrets:` | `Secret` (mounted as volume) | |
| `configs:` | `ConfigMap` (mounted as volume) | |
| `build:` | Not in K8s — use CI/CD | Build externally, push to registry |

---

## The depends_on Problem

`depends_on` in Compose is simple: start service B after service A starts. But "starts" doesn't mean "ready to accept connections."

Kubernetes solves this more robustly:

**readinessProbe**: Kubernetes withholds traffic from a Pod until its readiness probe succeeds. If your API depends on the database, configure the API's readiness probe to check the database connection. Traffic won't be sent to the API Pod until it's truly ready.

**initContainers**: If you need to wait for a condition before the main container starts (not just traffic routing), use an init container. It runs to completion before the main container starts:

```yaml
initContainers:
  - name: wait-for-db
    image: busybox
    command: ['sh', '-c', 'until nc -z postgres 5432; do sleep 2; done']
```

---

## The kompose Tool

`kompose` is an official tool that converts Docker Compose files to Kubernetes manifests automatically:

```bash
# Install kompose
brew install kompose   # macOS
# or
curl -L https://github.com/kubernetes/kompose/releases/download/v1.32.0/kompose-linux-amd64 -o kompose

# Convert docker-compose.yml in current directory
kompose convert

# Convert specific file
kompose convert -f docker-compose.yml

# Output to a specific directory
kompose convert -o k8s/

# Convert and immediately apply (for testing)
kompose up
```

Kompose generates a set of YAML files: one Deployment + one Service per Compose service, plus PersistentVolumeClaims for named volumes.

---

## Limitations of kompose Output (Always Review!)

Kompose is a great starting point, but its output is never production-ready without review:

1. **No resource requests/limits**: Generated Deployments have no CPU/memory constraints. Add them.

2. **No liveness/readiness probes**: Kompose can convert `healthcheck:` but doesn't add probes from `depends_on`. Add probes manually.

3. **Naive storage**: Volume mounts become `hostPath` or empty `PersistentVolumeClaim` specs. You need to match the StorageClass to your cluster.

4. **No Ingress**: Port mappings become `NodePort` Services, not `Ingress` objects. For production HTTP routing, convert to Ingress.

5. **No Secrets management**: `environment:` keys with passwords become plain ConfigMaps. Move sensitive values to K8s Secrets.

6. **No Namespace**: Resources land in `default`. In production, create proper namespaces.

7. **Labels may be minimal**: Add standard labels (`app.kubernetes.io/name`, `app.kubernetes.io/version`) for tooling compatibility.

---

## Manual Migration Walkthrough

### Step 1: Identify services and their roles

Look at your Compose file. Classify each service:
- **Stateless web/API**: → Deployment + ClusterIP Service
- **Database/cache**: → StatefulSet or Deployment + PVC + ClusterIP Service
- **Background worker**: → Deployment (no Service needed if it doesn't accept connections)
- **Scheduled job**: → CronJob

### Step 2: Create Namespace

```bash
kubectl create namespace my-app
```

### Step 3: Create ConfigMaps and Secrets

```bash
# Non-sensitive config
kubectl create configmap app-config \
  --from-literal=LOG_LEVEL=info \
  --from-literal=PORT=3000 \
  -n my-app

# Sensitive values
kubectl create secret generic app-secrets \
  --from-literal=DB_PASSWORD=supersecret \
  --from-literal=JWT_SECRET=abc123 \
  -n my-app
```

### Step 4: Create PersistentVolumeClaims for volumes

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

### Step 5: Write Deployments and Services

Convert each Compose service to a Deployment + Service pair.

### Step 6: Add Ingress for HTTP traffic

Replace Compose port mappings with an Ingress object for hostname/path-based routing.

### Step 7: Test in staging before production

Apply to a staging namespace, run smoke tests, then apply to production.

---

## 📂 Navigation

| | Link |
|---|---|
| Previous | [01 · Docker vs Kubernetes](../01_Docker_vs_K8s/Theory.md) |
| Code Examples | [Compose to K8s Code Examples](./Code_Example.md) |
| Interview Q&A | [Compose Migration Q&A](./Interview_QA.md) |
| Next | [03 · Image to Deployment Workflow](../03_Image_to_Deployment_Workflow/Theory.md) |
| Section Home | [Section 03 — Docker to K8s](../README.md) |
