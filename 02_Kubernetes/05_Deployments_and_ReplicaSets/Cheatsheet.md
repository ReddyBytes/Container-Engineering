# Module 05 — Deployments and ReplicaSets Cheatsheet

## Creating and Managing Deployments

```bash
# Create a deployment imperatively (for quick testing)
kubectl create deployment my-app --image=nginx:1.25 --replicas=3

# Apply from YAML file (recommended for production)
kubectl apply -f deployment.yaml

# List deployments
kubectl get deployments
kubectl get deploy          # short form

# Detailed deployment info
kubectl describe deployment my-app

# See the deployment as YAML
kubectl get deployment my-app -o yaml

# See all resources related to a deployment (deployment + replicasets + pods)
kubectl get all -l app=my-app
```

## Scaling

```bash
# Scale a deployment to N replicas
kubectl scale deployment my-app --replicas=10

# Scale down to zero (stops all pods but keeps the deployment)
kubectl scale deployment my-app --replicas=0

# Autoscaling (see 18_HPA_VPA for full coverage)
kubectl autoscale deployment my-app --min=2 --max=10 --cpu-percent=50
```

## Rolling Updates

```bash
# Update the container image (triggers rolling update)
kubectl set image deployment/my-app <container-name>=nginx:1.26

# Set image with record (records command in rollout history annotation)
kubectl set image deployment/my-app app=nginx:1.26 --record

# Update resources
kubectl set resources deployment/my-app -c=app \
  --limits=cpu=500m,memory=256Mi \
  --requests=cpu=100m,memory=128Mi

# Apply changes from updated YAML
kubectl apply -f deployment.yaml

# Edit deployment interactively (opens your $EDITOR)
kubectl edit deployment my-app
```

## Monitoring Rollouts

```bash
# Watch rollout progress (blocks until complete or failed)
kubectl rollout status deployment/my-app

# Watch pods during rollout
kubectl get pods -w
kubectl get pods --watch

# List rollout history (shows revision numbers)
kubectl rollout history deployment/my-app

# Show what changed in revision 3
kubectl rollout history deployment/my-app --revision=3

# Show current status of rollout
kubectl get deployment my-app

# Show ReplicaSets to see old/new versions
kubectl get replicasets
kubectl get rs              # short form

# See which ReplicaSet owns a pod
kubectl get pod <pod-name> -o yaml | grep ownerReferences -A 5
```

## Rollback

```bash
# Undo the last rollout (go back one revision)
kubectl rollout undo deployment/my-app

# Rollback to a specific revision
kubectl rollout undo deployment/my-app --to-revision=2

# Check status after rollback
kubectl rollout status deployment/my-app

# Verify which image is now running
kubectl describe deployment my-app | grep Image
```

## Pause and Resume

```bash
# Pause rollout (lets you batch multiple changes)
kubectl rollout pause deployment/my-app

# Make changes while paused (these don't trigger a rollout yet)
kubectl set image deployment/my-app app=nginx:1.26
kubectl set env deployment/my-app ENV=production

# Resume — triggers a single rollout with all accumulated changes
kubectl rollout resume deployment/my-app

# Check status after resume
kubectl rollout status deployment/my-app
```

## ReplicaSet Commands

```bash
# List ReplicaSets
kubectl get replicasets
kubectl get rs

# Describe a ReplicaSet
kubectl describe rs <replicaset-name>

# Delete a ReplicaSet (and all its pods)
# WARNING: normally done automatically by Deployment
kubectl delete rs <replicaset-name>
```

## Deleting Deployments

```bash
# Delete a deployment (also deletes its ReplicaSets and Pods)
kubectl delete deployment my-app

# Delete via YAML file
kubectl delete -f deployment.yaml

# Delete without deleting its pods (orphan the pods)
kubectl delete deployment my-app --cascade=orphan
```

---

## Navigation

| File | Description |
|------|-------------|
| [Theory.md](./Theory.md) | Deployments and ReplicaSets explained |
| [Cheatsheet.md](./Cheatsheet.md) | You are here — quick reference |
| [Interview_QA.md](./Interview_QA.md) | Interview questions and answers |
| [Code_Example.md](./Code_Example.md) | Working YAML examples |

**Previous:** [04_Pods](../04_Pods/Cheatsheet.md) |
**Next:** [06_Services](../06_Services/Theory.md)
