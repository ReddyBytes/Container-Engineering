# Step-by-Step: Deploy an App to Kubernetes

---

## Step 1 — Start minikube and Push Your Image

Start your local cluster:

```bash
minikube start --cpus=2 --memory=4g
```

**Expected:**
```
😄  minikube v1.32.0 on Darwin 14.0
✨  Using the docker driver
...
🏄  Done! kubectl is now configured to use "minikube" cluster
```

Verify kubectl can reach it:

```bash
kubectl cluster-info
```

**Expected:**
```
Kubernetes control plane is running at https://127.0.0.1:PORT
```

**Option A — Push to Docker Hub (recommended):**

```bash
docker build -t YOUR_USERNAME/myapi:1.0.0 .
docker push YOUR_USERNAME/myapi:1.0.0
```

Update the image reference in `k8s/deployment.yaml` to use `YOUR_USERNAME/myapi:1.0.0`.

**Option B — Load directly into minikube (no registry needed):**

```bash
minikube image load myapi:1.0.0
```

Then set `imagePullPolicy: Never` in your Deployment (shown in Code_Example.md).

---

## Step 2 — Write the ConfigMap

Create `k8s/configmap.yaml` (see Code_Example.md for the full file).

ConfigMaps store non-sensitive configuration — log levels, feature flags, app settings. The API reads these as environment variables.

```bash
mkdir -p k8s
```

---

## Step 3 — Write the Secret

Create `k8s/secret.yaml` (see Code_Example.md for the full file).

Secrets store sensitive data. Values must be base64-encoded. To encode:

```bash
echo -n "supersecret" | base64
```

**Expected:**
```
c3VwZXJzZWNyZXQ=
```

Note: base64 is encoding, not encryption. For real secrets management, use Vault, External Secrets Operator, or Sealed Secrets. For learning, this is fine.

---

## Step 4 — Write the Deployment

Create `k8s/deployment.yaml` (see Code_Example.md for the full file).

Key configuration choices in this Deployment:

- `replicas: 3` — three pods means the app survives one pod dying
- `resources.requests` — tells the scheduler the minimum CPU/memory needed
- `resources.limits` — caps resource usage so one bad pod can't starve others
- `readinessProbe` — K8s won't send traffic to a pod until `/health` returns 200
- `livenessProbe` — K8s restarts a pod if `/health` stops returning 200
- `envFrom: configMapRef` and `envFrom: secretRef` — injects all keys as env vars

---

## Step 5 — Write the Service

Create `k8s/service.yaml` (see Code_Example.md for the full file).

The Service creates a stable DNS name and IP for your Deployment. Without a Service, pods are unreachable by name (their IPs change every restart).

- `ClusterIP` is the default — only reachable from inside the cluster
- `NodePort` exposes the service on a static port (30000–32767) on every node

---

## Step 6 — Apply Everything

Apply all manifests at once:

```bash
kubectl apply -f k8s/
```

**Expected:**
```
configmap/myapi-config created
secret/myapi-secret created
deployment.apps/myapi created
service/myapi-svc created
```

Kubernetes processes the files alphabetically. Order matters for dependencies, but these four resources have no ordering requirement.

---

## Step 7 — Verify Deployment

Check pods are running:

```bash
kubectl get pods -l app=myapi
```

**Expected (after ~30 seconds):**
```
NAME                     READY   STATUS    RESTARTS   AGE
myapi-7d9b8c6f5-4xk2p   1/1     Running   0          45s
myapi-7d9b8c6f5-9mnvr   1/1     Running   0          45s
myapi-7d9b8c6f5-x7qpt   1/1     Running   0          45s
```

All three pods should be `1/1 Running`. If any show `0/1` or `CrashLoopBackOff`, describe the pod:

```bash
kubectl describe pod <POD_NAME>
# Look at the Events section at the bottom
```

Check the Deployment:

```bash
kubectl describe deployment myapi
```

Look for:
```
Replicas: 3 desired | 3 updated | 3 total | 3 available | 0 unavailable
```

Check the Service:

```bash
kubectl get service myapi-svc
```

**Expected:**
```
NAME        TYPE       CLUSTER-IP      EXTERNAL-IP   PORT(S)          AGE
myapi-svc   NodePort   10.96.xxx.xxx   <none>        8000:30080/TCP   1m
```

---

## Step 8 — Access the App

**With minikube:**

```bash
minikube service myapi-svc --url
```

**Expected:**
```
http://192.168.49.2:30080
```

Open that URL or test with curl:

```bash
curl $(minikube service myapi-svc --url)/health
```

**Expected:**
```json
{"status": "ok"}
```

**With port-forward (works on any cluster):**

```bash
kubectl port-forward service/myapi-svc 8080:8000
```

Then in another terminal:

```bash
curl http://localhost:8080/health
```

---

## Step 9 — Scale Up

Scale from 3 to 5 replicas:

```bash
kubectl scale deployment myapi --replicas=5
```

Watch pods appear in real time:

```bash
kubectl get pods -l app=myapi --watch
```

**Expected (you'll see two new pods go from Pending → ContainerCreating → Running):**
```
NAME                     READY   STATUS              RESTARTS   AGE
myapi-7d9b8c6f5-4xk2p   1/1     Running             0          5m
myapi-7d9b8c6f5-9mnvr   1/1     Running             0          5m
myapi-7d9b8c6f5-x7qpt   1/1     Running             0          5m
myapi-7d9b8c6f5-abc12   0/1     ContainerCreating   0          2s
myapi-7d9b8c6f5-def34   0/1     ContainerCreating   0          2s
```

Hit `Ctrl+C` to stop watching.

Scale back down:

```bash
kubectl scale deployment myapi --replicas=3
```

---

## Step 10 — Rolling Update

Build and push a new version of the image:

```bash
docker build -t YOUR_USERNAME/myapi:1.1.0 .
docker push YOUR_USERNAME/myapi:1.1.0
```

Update the deployment to use the new image:

```bash
kubectl set image deployment/myapi myapi=YOUR_USERNAME/myapi:1.1.0
```

Watch the rollout happen — Kubernetes brings up new pods before terminating old ones:

```bash
kubectl rollout status deployment/myapi
```

**Expected:**
```
Waiting for deployment "myapi" rollout to finish: 1 out of 3 new replicas have been updated...
Waiting for deployment "myapi" rollout to finish: 2 out of 3 new replicas have been updated...
Waiting for deployment "myapi" rollout to finish: 1 old replicas are pending termination...
deployment "myapi" successfully rolled out
```

Check the rollout history:

```bash
kubectl rollout history deployment/myapi
```

**Expected:**
```
REVISION  CHANGE-CAUSE
1         <none>
2         <none>
```

---

## Step 11 — Rollback

Suppose the new version has a bug. Roll back to the previous revision:

```bash
kubectl rollout undo deployment/myapi
```

**Expected:**
```
deployment.apps/myapi rolled back
```

Verify pods are running the old image:

```bash
kubectl describe deployment myapi | grep Image
```

**Expected:**
```
Image: YOUR_USERNAME/myapi:1.0.0
```

To roll back to a specific revision:

```bash
kubectl rollout undo deployment/myapi --to-revision=1
```

---

## Cleanup

```bash
kubectl delete -f k8s/
minikube stop  # or: minikube delete to remove the cluster entirely
```

---

## 📂 Navigation

| | |
|---|---|
| Guide | [Project_Guide.md](./Project_Guide.md) |
| Code | [Code_Example.md](./Code_Example.md) |
| All Projects | [04_Projects/](../) |
