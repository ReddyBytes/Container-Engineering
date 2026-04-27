# Module 05 — Code Examples: Deployments and ReplicaSets

## Example 1: Basic Deployment

```yaml
# deployment-basic.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  labels:
    app: my-app
spec:
  replicas: 3                            # Run 3 copies of the pod

  selector:
    matchLabels:
      app: my-app                        # Deployment manages pods with this label

  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1                  # At most 1 pod unavailable during update
      maxSurge: 1                        # At most 1 extra pod above desired count

  revisionHistoryLimit: 5                # Keep last 5 ReplicaSets for rollback

  template:
    metadata:
      labels:
        app: my-app                      # MUST match spec.selector.matchLabels
        version: "1.0"                   # Extra labels are fine
    spec:
      containers:
      - name: app                        # Container name (used in kubectl logs -c app)
        image: nginx:1.24                # Start with 1.24; we'll update to 1.25 below

        ports:
        - containerPort: 80

        resources:
          requests:
            memory: "64Mi"
            cpu: "100m"
          limits:
            memory: "128Mi"
            cpu: "200m"

        readinessProbe:                  # K8s won't send traffic until this passes
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 10
```

```bash
# Apply the deployment
kubectl apply -f deployment-basic.yaml

# Watch pods come up
kubectl get pods --watch

# Verify the deployment
kubectl get deployment my-app
# NAME     READY   UP-TO-DATE   AVAILABLE   AGE
# my-app   3/3     3            3           30s

# See the underlying ReplicaSet
kubectl get replicasets
# NAME                DESIRED   CURRENT   READY   AGE
# my-app-7d4b9c8f5   3         3         3       30s
```

---

## Example 2: Scale Up and Down

```bash
# Scale to 6 replicas (Black Friday is here!)
kubectl scale deployment my-app --replicas=6

# Watch pods scale up
kubectl get pods --watch

# Verify
kubectl get deployment my-app
# NAME     READY   UP-TO-DATE   AVAILABLE   AGE
# my-app   6/6     6            6           2m

# Scale back down (Black Friday is over)
kubectl scale deployment my-app --replicas=3

# Scale to zero (stop everything but keep the deployment config)
kubectl scale deployment my-app --replicas=0
# All pods terminated, deployment still exists

# Scale back up
kubectl scale deployment my-app --replicas=3
```

---

## Example 3: Trigger a Rolling Update

```bash
# Current state: running nginx:1.24
kubectl get deployment my-app -o wide
# IMAGES: nginx:1.24

# Update image to nginx:1.25 (this triggers a rolling update)
kubectl set image deployment/my-app app=nginx:1.25

# Watch the rollout happen in real time
kubectl rollout status deployment/my-app
# Waiting for deployment "my-app" rollout to finish: 1 out of 3 new replicas have been updated...
# Waiting for deployment "my-app" rollout to finish: 2 out of 3 new replicas have been updated...
# Waiting for deployment "my-app" rollout to finish: 1 old replicas are pending termination...
# deployment "my-app" successfully rolled out

# See that we now have TWO ReplicaSets: the new one (3 pods) and old one (0 pods)
kubectl get replicasets
# NAME                DESIRED   CURRENT   READY   AGE
# my-app-7d4b9c8f5   3         3         3       5m   <- NEW (nginx:1.25)
# my-app-6c5a8b9d4   0         0         0       8m   <- OLD (nginx:1.24, kept for rollback)

# View rollout history
kubectl rollout history deployment/my-app
# REVISION   CHANGE-CAUSE
# 1          <none>
# 2          <none>

# See what image is in revision 1 vs 2
kubectl rollout history deployment/my-app --revision=1
# Containers:
#   app:
#     Image: nginx:1.24

kubectl rollout history deployment/my-app --revision=2
# Containers:
#   app:
#     Image: nginx:1.25
```

---

## Example 4: Rollback

```bash
# Simulate a bad deployment — update to a bad image
kubectl set image deployment/my-app app=nginx:DOES-NOT-EXIST

# Watch pods fail (ImagePullBackOff)
kubectl get pods --watch
# NAME                    READY   STATUS             RESTARTS
# my-app-abc123-xyz       0/1     ImagePullBackOff   0

# Check rollout status (it will show it's stuck)
kubectl rollout status deployment/my-app
# Waiting for deployment "my-app" rollout to finish: 1 out of 3 new replicas have been updated...
# (this will not complete — Ctrl+C to cancel)

# Roll back to the previous working version
kubectl rollout undo deployment/my-app

# Verify the rollback
kubectl rollout status deployment/my-app
# deployment "my-app" successfully rolled out

# Check which image is running now
kubectl get deployment my-app -o wide
# Should show nginx:1.25 again

# Roll back to a specific revision
kubectl rollout undo deployment/my-app --to-revision=1
# Now running nginx:1.24
```

---

## Example 5: Pause and Resume a Rollout

```bash
# Pause the rollout (useful for batching multiple changes)
kubectl rollout pause deployment/my-app

# Make change 1: update the image
kubectl set image deployment/my-app app=nginx:1.26

# Make change 2: update resource limits
kubectl set resources deployment/my-app \
  -c=app \
  --limits=cpu=500m,memory=256Mi \
  --requests=cpu=200m,memory=128Mi

# Make change 3: add an environment variable
kubectl set env deployment/my-app LOG_LEVEL=debug

# Verify the deployment is still on the OLD version (not yet rolling out)
kubectl get pods
# All pods still running OLD version — changes haven't rolled out

# Now resume — single rollout applies ALL three changes together
kubectl rollout resume deployment/my-app

# Monitor
kubectl rollout status deployment/my-app
```

---

## Example 6: Deployment with Recreate Strategy

```yaml
# deployment-recreate.yaml
# Use this when only ONE version can run at a time (e.g., exclusive DB access)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: legacy-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: legacy-app
  strategy:
    type: Recreate                       # Delete ALL old pods first, then create new
    # No rollingUpdate block needed
  template:
    metadata:
      labels:
        app: legacy-app
    spec:
      containers:
      - name: legacy
        image: my-legacy-app:2.0
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

```bash
kubectl apply -f deployment-recreate.yaml

# When you update the image, watch what happens:
kubectl set image deployment/legacy-app legacy=my-legacy-app:2.1

# You'll see ALL old pods terminate before new pods start
# This causes brief downtime — expected with Recreate strategy
kubectl get pods --watch
```

---

## 📂 Navigation

| File | Description |
|------|-------------|
| [Theory.md](./Theory.md) | Deployments and ReplicaSets explained |
| [Cheatsheet.md](./Cheatsheet.md) | Quick reference commands |
| [Interview_QA.md](./Interview_QA.md) | Interview questions and answers |
| [Code_Example.md](./Code_Example.md) | You are here — working YAML examples |

**Previous:** [04_Pods](../04_Pods/Code_Example.md) |
**Next:** [06_Services](../06_Services/Theory.md)
