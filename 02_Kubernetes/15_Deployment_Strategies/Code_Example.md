# Deployment Strategies — Code Examples

All examples are production-quality with detailed comments explaining every decision.

---

## 1. Recreate Strategy — Full Stop, Full Start

```yaml
# recreate-deployment.yaml
# Use when the old and new versions absolutely cannot run simultaneously.
# Example: a monolith that holds an exclusive database lock on startup.
apiVersion: apps/v1
kind: Deployment
metadata:
  name: legacy-app
  annotations:
    deployment.kubernetes.io/reason: "exclusive-db-lock-requires-recreate"
spec:
  replicas: 3
  strategy:
    type: Recreate                     # All v1 pods terminated BEFORE any v2 pods start
    # No rollingUpdate block — Recreate has no sub-parameters
  selector:
    matchLabels:
      app: legacy-app
  template:
    metadata:
      labels:
        app: legacy-app
    spec:
      containers:
      - name: app
        image: myapp:v1                # Change to myapp:v2 to trigger the recreate rollout
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
          limits:
            cpu: "500m"
            memory: "256Mi"
        # No readiness probe needed for Recreate — there's always downtime anyway
```

```bash
kubectl apply -f recreate-deployment.yaml

# Trigger an update — watch the downtime window
kubectl set image deployment/legacy-app app=myapp:v2

# Watch all v1 pods terminate first, then v2 pods start
kubectl get pods -l app=legacy-app --watch
# v1 pods: Terminating → gone
# (gap: zero pods running — this IS the downtime)
# v2 pods: Pending → ContainerCreating → Running

kubectl rollout status deployment/legacy-app   # Waits for rollout to complete
kubectl rollout history deployment/legacy-app  # Shows revision history
```

---

## 2. RollingUpdate — The Production Default

```yaml
# rolling-update.yaml
# Zero-downtime update: always maintains capacity during rollout.
# maxUnavailable: 0 means no old pod is removed until its replacement is healthy.
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-api
spec:
  replicas: 4
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1                      # Allow 1 extra pod above desired count (5 pods max during rollout)
      maxUnavailable: 0                # Never go below 4 pods — maintains full capacity
      # With replicas=4, maxSurge=1, maxUnavailable=0:
      # Step 1: Create 1 new v2 pod (now 5 total)
      # Step 2: Wait for v2 pod to pass readiness probe
      # Step 3: Terminate 1 old v1 pod (back to 4 total)
      # Step 4: Repeat until all 4 are v2
  selector:
    matchLabels:
      app: web-api
  template:
    metadata:
      labels:
        app: web-api
    spec:
      containers:
      - name: api
        image: web-api:v1              # Pin to exact version — never use latest in production
        ports:
        - containerPort: 8080
        resources:
          requests:
            cpu: "200m"
            memory: "256Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"

        # Readiness probe is CRITICAL for RollingUpdate with maxUnavailable: 0
        # Without it, K8s removes old pods before the new pod is actually ready to serve traffic
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5       # Wait 5s after container starts before probing
          periodSeconds: 5             # Probe every 5 seconds
          failureThreshold: 3          # Mark unready after 3 consecutive failures
          successThreshold: 1          # Mark ready after 1 success

        # Lifecycle hook: give the app time to finish in-flight requests before shutdown
        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "sleep 5"]   # 5s grace for load balancer to drain
      terminationGracePeriodSeconds: 30   # K8s waits up to 30s for graceful shutdown
```

```bash
kubectl apply -f rolling-update.yaml

# Trigger a rolling update
kubectl set image deployment/web-api api=web-api:v2

# Watch the rolling update — observe the controlled replacement
kubectl rollout status deployment/web-api --timeout=5m

# See revision history
kubectl rollout history deployment/web-api
# REVISION  CHANGE-CAUSE
# 1         initial deploy
# 2         <none>  ← add --record flag or use annotations for change cause

# Rollback to previous version if v2 has issues
kubectl rollout undo deployment/web-api
# Or rollback to a specific revision:
kubectl rollout undo deployment/web-api --to-revision=1

# Pause a rolling update mid-way (e.g., to check metrics on partial rollout)
kubectl rollout pause deployment/web-api
kubectl rollout resume deployment/web-api
```

---

## 3. Blue/Green Strategy — Instant Cutover

```yaml
# blue-green.yaml
# Two full Deployments run simultaneously. Traffic switches by changing Service selector.
---
# Blue Deployment (current production)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-api-blue
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-api
      slot: blue                       # Unique label for this deployment slot
  template:
    metadata:
      labels:
        app: web-api
        slot: blue
        version: "1.0.0"               # Version label for visibility
    spec:
      containers:
      - name: api
        image: web-api:v1
        resources:
          requests:
            cpu: "200m"
            memory: "256Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
---
# Green Deployment (new version — deployed but NOT receiving traffic yet)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-api-green
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-api
      slot: green
  template:
    metadata:
      labels:
        app: web-api
        slot: green
        version: "2.0.0"
    spec:
      containers:
      - name: api
        image: web-api:v2              # New version deployed but isolated
        resources:
          requests:
            cpu: "200m"
            memory: "256Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
---
# The Service — this is the single control point for traffic switching
apiVersion: v1
kind: Service
metadata:
  name: web-api-svc
spec:
  selector:
    app: web-api
    slot: blue                         # Currently routes to BLUE. Change to "green" to cut over.
  ports:
  - port: 80
    targetPort: 8080
```

```bash
kubectl apply -f blue-green.yaml

# Confirm blue is serving traffic
kubectl get service web-api-svc -o jsonpath='{.spec.selector}'
# {"app":"web-api","slot":"blue"}

# Smoke test green before cutting over (port-forward directly to green pods)
kubectl port-forward deployment/web-api-green 8080:8080 &
curl http://localhost:8080/health      # Test green independently

# CUT OVER: change Service selector from blue to green — instant, atomic switch
kubectl patch service web-api-svc -p '{"spec":{"selector":{"app":"web-api","slot":"green"}}}'

# Verify cutover
kubectl get service web-api-svc -o jsonpath='{.spec.selector}'
# {"app":"web-api","slot":"green"}

# Instant ROLLBACK: switch selector back to blue if green has issues
kubectl patch service web-api-svc -p '{"spec":{"selector":{"app":"web-api","slot":"blue"}}}'

# Once green is confirmed stable, scale blue to 0 (keep it around for quick rollback)
kubectl scale deployment web-api-blue --replicas=0
# After full confidence: delete blue
kubectl delete deployment web-api-blue
```

---

## 4. Canary Strategy — Small Percentage First

```yaml
# canary.yaml
# Route ~10% of traffic to v2 by running 1 canary pod alongside 9 stable pods.
# Traffic is distributed proportionally to pod count by the Service.
---
# Stable (v1) — 9 pods = 90% of traffic
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-api-stable
spec:
  replicas: 9                          # 9 out of 10 total pods = 90% of traffic
  selector:
    matchLabels:
      app: web-api                     # SAME selector label as canary — same Service routes to both
  template:
    metadata:
      labels:
        app: web-api
        track: stable
    spec:
      containers:
      - name: api
        image: web-api:v1
        resources:
          requests:
            cpu: "200m"
            memory: "256Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
---
# Canary (v2) — 1 pod = ~10% of traffic
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-api-canary
spec:
  replicas: 1                          # 1 out of 10 total pods = 10% of traffic
  selector:
    matchLabels:
      app: web-api                     # Same label — the Service selects both stable and canary
  template:
    metadata:
      labels:
        app: web-api
        track: canary
    spec:
      containers:
      - name: api
        image: web-api:v2              # New version — receives ~10% of production traffic
        resources:
          requests:
            cpu: "200m"
            memory: "256Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
---
# One Service selects pods from BOTH Deployments (same app: web-api label)
apiVersion: v1
kind: Service
metadata:
  name: web-api-svc
spec:
  selector:
    app: web-api                       # Matches all pods from both stable and canary
  ports:
  - port: 80
    targetPort: 8080
```

```bash
kubectl apply -f canary.yaml

# Confirm traffic distribution: 9 stable + 1 canary = 10 total endpoints
kubectl get pods -l app=web-api        # Should show 10 pods total
kubectl get endpoints web-api-svc      # Shows all 10 pod IPs as endpoints

# Monitor canary error rate (requires Prometheus or similar)
# kubectl top pod -l track=canary      # CPU/memory usage on canary pod

# If canary looks healthy after observation period — gradually promote
kubectl scale deployment web-api-canary --replicas=3   # 3/12 = 25%
kubectl scale deployment web-api-stable --replicas=7

kubectl scale deployment web-api-canary --replicas=9   # 9/18 = 50%
kubectl scale deployment web-api-stable --replicas=3

# Full promotion: stable becomes v2
kubectl set image deployment/web-api-stable api=web-api:v2
kubectl scale deployment web-api-stable --replicas=9
kubectl scale deployment web-api-canary --replicas=0
kubectl delete deployment web-api-canary               # Clean up canary

# ROLLBACK: if canary shows errors — delete canary, all traffic returns to stable
kubectl delete deployment web-api-canary
```

---

## 5. Automated Canary with Argo Rollouts

```yaml
# argo-rollout.yaml
# Argo Rollouts replaces a Deployment and adds automated canary promotion with metric gates.
# Requires: kubectl apply -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout                          # Argo Rollouts CRD — replaces apps/v1 Deployment
metadata:
  name: web-api
spec:
  replicas: 10
  selector:
    matchLabels:
      app: web-api
  template:
    metadata:
      labels:
        app: web-api
    spec:
      containers:
      - name: api
        image: web-api:v1
        resources:
          requests:
            cpu: "200m"
            memory: "256Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
  strategy:
    canary:
      steps:
      - setWeight: 10                  # Step 1: Route 10% to canary
      - pause: {duration: 5m}          # Wait 5 minutes — check metrics manually or automatically
      - setWeight: 25                  # Step 2: Route 25% if previous step passed
      - pause: {duration: 10m}         # Wait 10 minutes
      - setWeight: 50                  # Step 3: 50%
      - pause: {}                      # Pause indefinitely — requires manual promotion
      - setWeight: 100                 # Step 4: Full rollout
      canaryService: web-api-canary-svc   # Separate service for canary pods (for metric targeting)
      stableService: web-api-stable-svc
```

```bash
# Install Argo Rollouts CLI plugin
kubectl argo rollouts version

# Deploy the rollout
kubectl apply -f argo-rollout.yaml

# Trigger a new rollout by updating the image
kubectl argo rollouts set image web-api api=web-api:v2

# Watch the automated canary progression
kubectl argo rollouts get rollout web-api --watch
# Shows: step progress, weight, pod counts, health status

# Manually promote past an indefinite pause
kubectl argo rollouts promote web-api

# Manually abort (rolls back to stable)
kubectl argo rollouts abort web-api

# Check rollout history
kubectl argo rollouts history rollout web-api
```

---

## 📂 Navigation

**In this folder:**
| File | |
|---|---|
| [📖 Theory.md](./Theory.md) | Full explanation |
| [⚡ Cheatsheet.md](./Cheatsheet.md) | Quick reference |
| [🎯 Interview_QA.md](./Interview_QA.md) | Interview prep |
| 💻 **Code_Example.md** | ← you are here |

⬅️ **Prev:** [Health Probes](../14_Health_Probes/Code_Example.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Sidecar Containers](../16_Sidecar_Containers/Code_Example.md)
🏠 **[Home](../../README.md)**
