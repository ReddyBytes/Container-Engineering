# 03 — Guide: Deploy an App to Kubernetes

This project is minimally guided. Steps describe what to do and why. Hints are available but try each step yourself first — consulting `kubectl explain` and the architecture diagrams is part of the exercise.

---

## ## Step 1 — Start minikube and Push Your Image

Start your local cluster:

```bash
minikube start --cpus=2 --memory=4g
```

Verify kubectl can reach it:
```bash
kubectl cluster-info
```

**Push to Docker Hub (recommended):**
```bash
docker build -t YOUR_USERNAME/myapi:1.0.0 .
docker push YOUR_USERNAME/myapi:1.0.0
```

Update the `image:` field in `k8s/deployment.yaml` to use `YOUR_USERNAME/myapi:1.0.0`.

**Or load directly into minikube (no registry needed):**
```bash
minikube image load myapi:1.0.0
```

Then set `imagePullPolicy: Never` in the Deployment.

---

## ## Step 2 — Write the ConfigMap

Create `k8s/configmap.yaml`. Store these non-secret values as ConfigMap data keys:

- `APP_ENV: "development"`
- `LOG_LEVEL: "info"`
- `WORKERS: "1"`

These will be injected as environment variables into every pod via `envFrom.configMapRef`.

<details>
<summary>💡 Hint</summary>

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: myapi-config
  labels:
    app: myapi
data:
  APP_ENV: "development"
  LOG_LEVEL: "info"
  WORKERS: "1"
```

</details>

---

## ## Step 3 — Write the Secret

Create `k8s/secret.yaml`. Encode your values with base64 before writing them:

```bash
echo -n "appuser"     | base64   # → YXBwdXNlcg==
echo -n "supersecret" | base64   # → c3VwZXJzZWNyZXQ=
echo -n "appdb"       | base64   # → YXBwZGI=
```

Store: `DB_USER`, `DB_PASSWORD`, `DB_NAME`.

<details>
<summary>💡 Hint</summary>

Secret kind is `v1/Secret` with `type: Opaque`. Values in `data:` must be base64-encoded strings. Use `stringData:` if you want to write plain text and let Kubernetes do the encoding — but never commit real secrets to version control either way.

</details>

---

## ## Step 4 — Write the Deployment

Create `k8s/deployment.yaml`. This is the most complex manifest — work through it field by field.

Requirements to hit:
- `replicas: 3`
- `selector.matchLabels.app: myapi`
- `strategy.type: RollingUpdate` with `maxSurge: 1` and `maxUnavailable: 0`
- Container image: `YOUR_USERNAME/myapi:1.0.0`
- `envFrom`: inject both the ConfigMap and the Secret
- `resources.requests`: `cpu: "100m"`, `memory: "128Mi"`
- `resources.limits`: `cpu: "500m"`, `memory: "256Mi"`
- `readinessProbe`: `httpGet /health` on port 8000, `initialDelaySeconds: 5`, `periodSeconds: 10`
- `livenessProbe`: `httpGet /health` on port 8000, `initialDelaySeconds: 15`, `periodSeconds: 20`
- `terminationGracePeriodSeconds: 30`

<details>
<summary>💡 Hint — envFrom syntax</summary>

```yaml
envFrom:
  - configMapRef:
      name: myapi-config
  - secretRef:
      name: myapi-secret
```

This injects every key from the ConfigMap and Secret as individual environment variables in the container.

</details>

<details>
<summary>✅ Answer</summary>

See `src/solution.py` (contains the deployment YAML as a docstring) or refer to `05_Capstone_Projects/03_Deploy_App_to_Kubernetes/Code_Example.md` for the fully annotated deployment manifest.

</details>

---

## ## Step 5 — Write the Service

Create `k8s/service.yaml`. Expose the Deployment on NodePort `30080`.

Requirements:
- `type: NodePort`
- `selector.app: myapi`
- `port: 8000`, `targetPort: 8000`, `nodePort: 30080`

---

## ## Step 6 — Apply Everything

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

---

## ## Step 7 — Verify Deployment

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

If any pod shows `0/1` or `CrashLoopBackOff`:
```bash
kubectl describe pod <POD_NAME>
kubectl logs <POD_NAME>
```

Check the Deployment summary:
```bash
kubectl describe deployment myapi
```

Look for: `3 desired | 3 updated | 3 total | 3 available | 0 unavailable`.

---

## ## Step 8 — Access the App

**With minikube:**
```bash
minikube service myapi-svc --url
```

Test:
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

Then: `curl http://localhost:8080/health`

---

## ## Step 9 — Scale

Scale to 5 replicas:
```bash
kubectl scale deployment myapi --replicas=5
```

Watch pods appear:
```bash
kubectl get pods -l app=myapi --watch
```

Hit `Ctrl+C` to stop. Scale back down:
```bash
kubectl scale deployment myapi --replicas=3
```

---

## ## Step 10 — Rolling Update

Build and push a new image tag:
```bash
docker build -t YOUR_USERNAME/myapi:1.1.0 .
docker push YOUR_USERNAME/myapi:1.1.0
```

Trigger the rollout:
```bash
kubectl set image deployment/myapi myapi=YOUR_USERNAME/myapi:1.1.0
```

Watch it progress:
```bash
kubectl rollout status deployment/myapi
```

**Expected:**
```
Waiting for deployment "myapi" rollout to finish: 1 out of 3 new replicas have been updated...
...
deployment "myapi" successfully rolled out
```

---

## ## Step 11 — Rollback

Roll back to the previous version:
```bash
kubectl rollout undo deployment/myapi
```

Verify the image reverted:
```bash
kubectl describe deployment myapi | grep Image
```

To roll back to a specific revision:
```bash
kubectl rollout history deployment/myapi
kubectl rollout undo deployment/myapi --to-revision=1
```

---

## ## Cleanup

```bash
kubectl delete -f k8s/
minikube stop
```

To delete the cluster entirely: `minikube delete`

---

⬅️ **Prev:** [02 — Multi-Container App with Compose](../02_Multi_Container_App_Compose/01_MISSION.md) &nbsp;&nbsp; ➡️ **Next:** [04 — Full Stack on K8s](../04_Full_Stack_on_K8s/01_MISSION.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
