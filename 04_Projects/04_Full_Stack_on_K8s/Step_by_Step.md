# Step-by-Step: Full-Stack App on Kubernetes

---

## Step 1 — Build and Push Images

Make sure minikube is running and the ingress addon is enabled:

```bash
minikube start --cpus=2 --memory=4g
minikube addons enable ingress
```

Build and push the backend:

```bash
cd backend
docker build -t YOUR_USERNAME/fullstack-backend:1.0.0 .
docker push YOUR_USERNAME/fullstack-backend:1.0.0
cd ..
```

Build and push the frontend:

```bash
cd frontend
docker build -t YOUR_USERNAME/fullstack-frontend:1.0.0 .
docker push YOUR_USERNAME/fullstack-frontend:1.0.0
cd ..
```

**Alternative — load directly into minikube (skip the push):**

```bash
minikube image load YOUR_USERNAME/fullstack-backend:1.0.0
minikube image load YOUR_USERNAME/fullstack-frontend:1.0.0
```

Then set `imagePullPolicy: Never` in both deployments.

---

## Step 2 — Create the Namespace

All resources for this project live in the `fullstack` namespace. This isolates them from other workloads on the cluster.

```bash
kubectl apply -f k8s/namespace.yaml
```

**Expected:**
```
namespace/fullstack created
```

Set it as your default namespace for this session (saves typing `-n fullstack` on every command):

```bash
kubectl config set-context --current --namespace=fullstack
```

---

## Step 3 — Deploy PostgreSQL

Deploy in this order: PVC is referenced by StatefulSet, Service must exist for the backend to reach Postgres.

```bash
kubectl apply -f k8s/postgres-service.yaml
kubectl apply -f k8s/postgres-statefulset.yaml
```

Watch the Postgres pod initialize:

```bash
kubectl get pods -l app=postgres --watch
```

**Expected (takes ~30 seconds):**
```
NAME         READY   STATUS              RESTARTS   AGE
postgres-0   0/1     ContainerCreating   0          5s
postgres-0   0/1     Running             0          12s
postgres-0   1/1     Running             0          30s
```

`1/1 Running` means Postgres is up and the readiness probe is passing.

Verify the PVC was created and bound:

```bash
kubectl get pvc
```

**Expected:**
```
NAME                   STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS
postgres-storage-postgres-0   Bound    pvc-abc123...   5Gi        RWO            standard
```

`Bound` means the PVC has been allocated storage. On minikube, the `standard` StorageClass automatically provisions local storage.

---

## Step 4 — Deploy the Backend

Apply config and secrets first, then the deployment:

```bash
kubectl apply -f k8s/backend-configmap.yaml
kubectl apply -f k8s/backend-secret.yaml
kubectl apply -f k8s/backend-service.yaml
kubectl apply -f k8s/backend-deployment.yaml
```

Watch backend pods start:

```bash
kubectl get pods -l app=backend --watch
```

**Expected:**
```
NAME                       READY   STATUS    RESTARTS   AGE
backend-6d8b9f7c5-2kxp4   1/1     Running   0          45s
backend-6d8b9f7c5-9nvmt   1/1     Running   0          45s
```

Test the backend directly with port-forward:

```bash
kubectl port-forward service/backend-svc 8000:8000 &
curl http://localhost:8000/health
```

**Expected:**
```json
{"status": "ok", "postgres": "connected"}
```

Kill the port-forward: `kill %1`

---

## Step 5 — Deploy the Frontend

```bash
kubectl apply -f k8s/frontend-service.yaml
kubectl apply -f k8s/frontend-deployment.yaml
```

```bash
kubectl get pods -l app=frontend --watch
```

**Expected:**
```
NAME                        READY   STATUS    RESTARTS   AGE
frontend-7f8c9d6b4-1abc2   1/1     Running   0          20s
frontend-7f8c9d6b4-8xyz3   1/1     Running   0          20s
```

---

## Step 6 — Configure Ingress

Apply the Ingress resource:

```bash
kubectl apply -f k8s/ingress.yaml
```

Get the Ingress address:

```bash
kubectl get ingress
```

**Expected:**
```
NAME             CLASS   HOSTS       ADDRESS        PORTS   AGE
fullstack-ingress   nginx   app.local   192.168.49.2   80      30s
```

The ADDRESS is your minikube IP. Add it to `/etc/hosts` so `app.local` resolves:

```bash
echo "$(minikube ip) app.local" | sudo tee -a /etc/hosts
```

**Expected:**
```
192.168.49.2 app.local
```

---

## Step 7 — Test End-to-End

Test the API through the Ingress:

```bash
curl http://app.local/api/health
```

**Expected:**
```json
{"status": "ok", "postgres": "connected"}
```

Create an item through the Ingress:

```bash
curl -X POST http://app.local/api/items \
  -H "Content-Type: application/json" \
  -d '{"name": "desk lamp", "price": 49.99}'
```

**Expected:**
```json
{"id": 1, "name": "desk lamp", "price": 49.99}
```

Fetch items:

```bash
curl http://app.local/api/items
```

**Expected:**
```json
{"items": [{"id": 1, "name": "desk lamp", "price": 49.99}]}
```

Open the frontend in your browser:

```
http://app.local
```

You should see the React app, which calls `/api/items` and displays the list.

---

## Step 8 — Update One Service Independently

Build a new backend version (change a response message in `main.py`):

```bash
docker build -t YOUR_USERNAME/fullstack-backend:1.1.0 ./backend
docker push YOUR_USERNAME/fullstack-backend:1.1.0
```

Update only the backend deployment:

```bash
kubectl set image deployment/backend backend=YOUR_USERNAME/fullstack-backend:1.1.0
kubectl rollout status deployment/backend
```

**Expected:**
```
deployment "backend" successfully rolled out
```

The frontend and database are completely unaffected. Verify:

```bash
kubectl get pods
```

All frontend and postgres pods should still show the same age/restart count.

---

## Verify All Resources

Get an overview of everything in the namespace:

```bash
kubectl get all -n fullstack
```

**Expected:**
```
NAME                            READY   STATUS    RESTARTS   AGE
pod/backend-xxx-yyy             1/1     Running   0          10m
pod/frontend-xxx-yyy            1/1     Running   0          8m
pod/postgres-0                  1/1     Running   0          12m

NAME                  TYPE        CLUSTER-IP       PORT(S)    AGE
service/backend-svc   ClusterIP   10.96.xxx.xxx    8000/TCP   10m
service/frontend-svc  ClusterIP   10.96.xxx.yyy    80/TCP     8m
service/postgres      ClusterIP   None             5432/TCP   12m

NAME                       READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/backend    2/2     2            2           10m
deployment.apps/frontend   2/2     2            2           8m

NAME                                READY   AGE
statefulset.apps/postgres           1/1     12m
```

---

## Cleanup

```bash
kubectl delete namespace fullstack
# This deletes everything inside the namespace, including PVCs.
```

Remove the `/etc/hosts` entry:

```bash
sudo sed -i '' '/app.local/d' /etc/hosts
```

---

## 📂 Navigation

| | |
|---|---|
| Guide | [Project_Guide.md](./Project_Guide.md) |
| Code | [Code_Example.md](./Code_Example.md) |
| All Projects | [04_Projects/](../) |
