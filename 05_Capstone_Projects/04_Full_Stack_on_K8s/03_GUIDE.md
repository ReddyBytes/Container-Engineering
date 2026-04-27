# 04 — Guide: Full-Stack App on Kubernetes

Work through each step in order. Try each step yourself before opening the hints.

---

## ## Step 1 — Start minikube and enable Ingress

minikube ships without an Ingress controller. You need to enable the addon before
any Ingress resources will work.

<details>
<summary>💡 Hint</summary>

Two commands: start minikube with enough resources for three services, then enable
the ingress addon.

```bash
minikube start --cpus=2 --memory=4g
minikube addons enable ingress
```

</details>

<details>
<summary>✅ Answer</summary>

```bash
minikube start --cpus=2 --memory=4g
minikube addons enable ingress
```

Verify the ingress controller pod is running:

```bash
kubectl get pods -n ingress-nginx
```

Expected: a pod named `ingress-nginx-controller-xxx` with status `Running`.

</details>

---

## ## Step 2 — Build and push (or load) images

Build Docker images for the frontend and backend. You can either push them to
Docker Hub or load them directly into minikube (no push required).

<details>
<summary>💡 Hint</summary>

Use `docker build -t` to tag each image, then either `docker push` to a registry
or `minikube image load` to load it directly. If you load locally, also set
`imagePullPolicy: Never` in the deployment YAML.

</details>

<details>
<summary>✅ Answer</summary>

Option A — push to Docker Hub:

```bash
cd backend
docker build -t YOUR_USERNAME/fullstack-backend:1.0.0 .
docker push YOUR_USERNAME/fullstack-backend:1.0.0
cd ..

cd frontend
docker build -t YOUR_USERNAME/fullstack-frontend:1.0.0 .
docker push YOUR_USERNAME/fullstack-frontend:1.0.0
cd ..
```

Option B — load directly into minikube (no registry needed):

```bash
minikube image load YOUR_USERNAME/fullstack-backend:1.0.0
minikube image load YOUR_USERNAME/fullstack-frontend:1.0.0
```

Then in both deployment YAMLs, set:
```yaml
imagePullPolicy: Never
```

</details>

---

## ## Step 3 — Create the namespace

All project resources live in the `fullstack` namespace. Create it first.

<details>
<summary>💡 Hint</summary>

Apply a YAML that declares a `Namespace` resource with `name: fullstack`.
Then set it as your default context namespace to avoid typing `-n fullstack` on
every command.

</details>

<details>
<summary>✅ Answer</summary>

`k8s/namespace.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: fullstack
  labels:
    project: fullstack-demo
```

Apply it:

```bash
kubectl apply -f k8s/namespace.yaml
kubectl config set-context --current --namespace=fullstack
```

Expected: `namespace/fullstack created`

</details>

---

## ## Step 4 — Deploy PostgreSQL

Deploy in this order: headless Service first (so the DNS name exists), then the
StatefulSet (which references the service name). The StatefulSet will create the
PVC automatically via `volumeClaimTemplates`.

<details>
<summary>💡 Hint</summary>

Apply `postgres-service.yaml` then `postgres-statefulset.yaml`. The service must
use `clusterIP: None` to make it headless. The StatefulSet needs `serviceName`
set to match the service name. Watch the pod with `kubectl get pods --watch`.

</details>

<details>
<summary>✅ Answer</summary>

```bash
kubectl apply -f k8s/postgres-service.yaml
kubectl apply -f k8s/postgres-statefulset.yaml
kubectl get pods -l app=postgres --watch
```

Expected (takes ~30 seconds):

```
NAME         READY   STATUS              RESTARTS   AGE
postgres-0   0/1     ContainerCreating   0          5s
postgres-0   0/1     Running             0          12s
postgres-0   1/1     Running             0          30s
```

Verify the PVC was created and bound:

```bash
kubectl get pvc
```

Expected: `postgres-storage-postgres-0` with status `Bound`.

</details>

---

## ## Step 5 — Deploy the backend

Apply in this order: ConfigMap and Secret must exist before the Deployment reads
them as environment variables.

<details>
<summary>💡 Hint</summary>

Apply `backend-configmap.yaml`, `backend-secret.yaml`, `backend-service.yaml`,
then `backend-deployment.yaml`. The Secret values must be base64-encoded.
Test with `kubectl port-forward` before moving on.

</details>

<details>
<summary>✅ Answer</summary>

```bash
kubectl apply -f k8s/backend-configmap.yaml
kubectl apply -f k8s/backend-secret.yaml
kubectl apply -f k8s/backend-service.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl get pods -l app=backend --watch
```

Test the backend directly:

```bash
kubectl port-forward service/backend-svc 8000:8000 &
curl http://localhost:8000/health
```

Expected:

```json
{"status": "ok", "postgres": "connected"}
```

Kill the port-forward: `kill %1`

The ConfigMap sets `DB_HOST: "postgres.fullstack.svc.cluster.local"` — this is
the stable DNS name of the headless Service you created in Step 4.

</details>

---

## ## Step 6 — Deploy the frontend

<details>
<summary>💡 Hint</summary>

Apply the frontend Service and Deployment. The frontend image is nginx serving
the React build. The `nginx.conf` must include `try_files $uri $uri/ /index.html`
so React Router handles client-side navigation.

</details>

<details>
<summary>✅ Answer</summary>

```bash
kubectl apply -f k8s/frontend-service.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl get pods -l app=frontend --watch
```

Expected: two frontend pods reach `1/1 Running`.

</details>

---

## ## Step 7 — Configure the Ingress

Apply the Ingress resource and add `app.local` to your `/etc/hosts` so your
browser knows where to send requests.

<details>
<summary>💡 Hint</summary>

Apply `ingress.yaml`. Then run `minikube ip` to get the cluster IP and add it
to `/etc/hosts` with the hostname `app.local`. The Ingress uses a regex path for
`/api/*` with a rewrite annotation to strip the prefix.

</details>

<details>
<summary>✅ Answer</summary>

```bash
kubectl apply -f k8s/ingress.yaml
kubectl get ingress
```

Expected: an ADDRESS column showing the minikube IP (e.g. `192.168.49.2`).

Add to `/etc/hosts`:

```bash
echo "$(minikube ip) app.local" | sudo tee -a /etc/hosts
```

</details>

---

## ## Step 8 — Test end-to-end

<details>
<summary>💡 Hint</summary>

Curl the `/api/health` endpoint through the Ingress. Then POST an item and GET
the list. Finally open `http://app.local` in a browser.

</details>

<details>
<summary>✅ Answer</summary>

```bash
curl http://app.local/api/health
```

Expected: `{"status": "ok", "postgres": "connected"}`

```bash
curl -X POST http://app.local/api/items \
  -H "Content-Type: application/json" \
  -d '{"name": "desk lamp", "price": 49.99}'
```

Expected: `{"id": 1, "name": "desk lamp", "price": 49.99}`

```bash
curl http://app.local/api/items
```

Expected: `{"items": [{"id": 1, "name": "desk lamp", "price": 49.99}]}`

Open `http://app.local` in a browser — the React app should display the items.

</details>

---

## ## Step 9 — Update one service independently

Modify the backend (e.g. change a response message), build a new image version,
and update only the backend deployment. The frontend and database must be
completely unaffected.

<details>
<summary>💡 Hint</summary>

Build a `1.1.0` image. Use `kubectl set image deployment/backend` to update only
the backend. Then `kubectl rollout status` to watch it roll out. Check that
frontend and postgres pods show unchanged ages.

</details>

<details>
<summary>✅ Answer</summary>

```bash
docker build -t YOUR_USERNAME/fullstack-backend:1.1.0 ./backend
docker push YOUR_USERNAME/fullstack-backend:1.1.0

kubectl set image deployment/backend backend=YOUR_USERNAME/fullstack-backend:1.1.0
kubectl rollout status deployment/backend
```

Expected: `deployment "backend" successfully rolled out`

Verify the other pods are untouched:

```bash
kubectl get pods
```

Frontend and postgres pods should show the same AGE and zero restarts.

</details>

---

## ## Cleanup

```bash
kubectl delete namespace fullstack
sudo sed -i '' '/app.local/d' /etc/hosts
```

Deleting the namespace removes everything inside it, including PVCs.

---

⬅️ **Prev:** [03 — Deploy App to Kubernetes](../03_Deploy_App_to_Kubernetes/03_GUIDE.md) &nbsp;&nbsp; ➡️ **Next:** [05 — CI/CD Build Push Deploy](../05_CICD_Build_Push_Deploy/01_MISSION.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
