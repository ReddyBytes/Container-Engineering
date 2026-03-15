# Deployment Strategies Cheatsheet

## Strategy Quick Reference

| Strategy | Downtime | How it works | Best for |
|----------|----------|--------------|---------|
| Recreate | Yes | Kill all → start new | Dev environments, incompatible versions |
| RollingUpdate | No | Replace pods gradually | Most production workloads |
| Blue/Green | No | Switch service selector | Instant rollback, clean cutover |
| Canary | No | Small % to new version | High-risk changes, real traffic testing |
| A/B Testing | No | Route by user attribute | Feature experiments, beta users |

---

## kubectl Commands

```bash
# --- Checking Deployment Strategy ---

# View current deployment strategy
kubectl get deployment <name> -n <namespace> -o jsonpath='{.spec.strategy}'

# Describe deployment (shows strategy, rollout status)
kubectl describe deployment <name> -n <namespace>

# --- Rolling Update Controls ---

# Watch a rolling update in progress
kubectl rollout status deployment/<name> -n <namespace>

# Watch pods being replaced during rollout
kubectl get pods -n <namespace> -w -l app=<label>

# Pause a rolling update mid-flight
kubectl rollout pause deployment/<name> -n <namespace>

# Resume a paused rolling update
kubectl rollout resume deployment/<name> -n <namespace>

# Rollback to the previous version
kubectl rollout undo deployment/<name> -n <namespace>

# Rollback to a specific revision
kubectl rollout undo deployment/<name> --to-revision=3 -n <namespace>

# View rollout history
kubectl rollout history deployment/<name> -n <namespace>

# View details of a specific revision
kubectl rollout history deployment/<name> --revision=2 -n <namespace>

# Trigger a rollout (after changing image)
kubectl set image deployment/<name> <container>=<image>:<tag> -n <namespace>

# Trigger a rolling restart (same image, forces pod replacement)
kubectl rollout restart deployment/<name> -n <namespace>

# --- Blue/Green Strategy ---

# Check which version is currently active (look at selector)
kubectl get service <svc-name> -n <namespace> -o jsonpath='{.spec.selector}'

# Switch service from blue to green (instant cutover)
kubectl patch service <svc-name> -n <namespace> \
  -p '{"spec":{"selector":{"version":"green"}}}'

# Switch back to blue (instant rollback)
kubectl patch service <svc-name> -n <namespace> \
  -p '{"spec":{"selector":{"version":"blue"}}}'

# Verify which pods are behind the service after switch
kubectl get endpoints <svc-name> -n <namespace>

# --- Canary Deployment ---

# Scale up canary deployment
kubectl scale deployment <name>-canary --replicas=2 -n <namespace>

# Scale down canary (rollback)
kubectl scale deployment <name>-canary --replicas=0 -n <namespace>

# Promote canary to full production (scale up new, scale down old)
kubectl scale deployment <name>-v2 --replicas=10 -n <namespace>
kubectl scale deployment <name>-v1 --replicas=0 -n <namespace>

# Check traffic distribution (count pods per version)
kubectl get pods -n <namespace> -l app=<name> \
  -o custom-columns=NAME:.metadata.name,VERSION:.metadata.labels.version

# --- Argo Rollouts (if installed) ---

# Install Argo Rollouts
kubectl apply -n argo-rollouts \
  -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml

# Get rollout status
kubectl argo rollouts get rollout <name> -n <namespace>

# Watch rollout progress
kubectl argo rollouts get rollout <name> -n <namespace> --watch

# Promote a canary (move to next step)
kubectl argo rollouts promote <name> -n <namespace>

# Abort a canary rollout
kubectl argo rollouts abort <name> -n <namespace>

# Retry a failed rollout
kubectl argo rollouts retry rollout <name> -n <namespace>
```

---

## RollingUpdate Strategy YAML Quick Reference

```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1          # or "25%" — extra pods above desired
      maxUnavailable: 0    # or "25%" — set to 0 for zero-downtime

# Recreate strategy
spec:
  strategy:
    type: Recreate         # no rollingUpdate block needed
```

---

## Blue/Green: Key Commands

```bash
# Deploy green (new version) alongside blue
kubectl apply -f deployment-green.yaml

# Wait for green to be ready
kubectl rollout status deployment/my-app-green -n production

# Switch traffic to green
kubectl patch service my-app -n production \
  -p '{"spec":{"selector":{"version":"green"}}}'

# Monitor — if issues arise:
kubectl patch service my-app -n production \
  -p '{"spec":{"selector":{"version":"blue"}}}'

# Cleanup blue once confident
kubectl delete deployment my-app-blue -n production
```

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Theory.md](./Theory.md) |
| Interview Q&A | [Interview_QA.md](./Interview_QA.md) |
| Module Home | [15_Deployment_Strategies](../) |
