# HPA, VPA, and Autoscaling — Code Examples

All examples are production-quality with detailed comments explaining every decision.

---

## 1. HPA on CPU — Web API That Scales With Traffic

```yaml
# deployment.yaml
# The deployment that HPA will manage — resource requests are REQUIRED for HPA to work
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-api
  namespace: production
spec:
  replicas: 2                           # HPA will override this after it takes control
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
        image: nginx:1.25
        resources:
          requests:
            cpu: "200m"                 # ← HPA calculates utilization as (actual / request)
            memory: "128Mi"             #   without a CPU request, HPA cannot function
          limits:
            cpu: "500m"
            memory: "256Mi"
```

```yaml
# hpa-cpu.yaml
# HPA targeting 60% average CPU utilization across all replicas
apiVersion: autoscaling/v2               # ← use v2, not the older autoscaling/v1
kind: HorizontalPodAutoscaler
metadata:
  name: web-api-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-api                        # ← must match the Deployment name exactly
  minReplicas: 2                         # ← never scale below 2 (single replica = downtime during rollout)
  maxReplicas: 20                        # ← hard cap to avoid runaway scaling costs
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60           # ← scale up if avg CPU across all pods > 60%
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60    # ← wait 60s before scaling up again (prevents flapping)
      policies:
      - type: Percent
        value: 100                       # ← at most double the replica count per step
        periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300   # ← wait 5 minutes before scaling down (traffic may return)
      policies:
      - type: Pods
        value: 2                         # ← remove at most 2 pods per 60s during scale-down
        periodSeconds: 60
```

```bash
# Apply both resources
kubectl apply -f deployment.yaml -f hpa-cpu.yaml

# Watch HPA in action — see current/desired replicas and utilization
kubectl get hpa web-api-hpa -n production --watch

# Full HPA status including recent events
kubectl describe hpa web-api-hpa -n production

# Check actual CPU usage (requires metrics-server installed)
kubectl top pods -n production -l app=web-api

# Simulate load to trigger scale-up
kubectl run load-generator \
  --image=busybox:1.36 \
  --restart=Never \
  -n production \
  -- /bin/sh -c "while true; do wget -q -O- http://web-api; done"

# Clean up the load test
kubectl delete pod load-generator -n production
```

---

## 2. HPA With Memory and Custom Metrics

```yaml
# hpa-multi-metric.yaml
# Production HPA using both CPU and memory metrics
# HPA scales when EITHER metric exceeds the target — it picks the higher replica count
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: data-processor-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: data-processor
  minReplicas: 3
  maxReplicas: 50
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70           # ← scale if CPU > 70%
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80           # ← also scale if memory > 80%
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second   # ← custom metric from your app's /metrics endpoint
      target:
        type: AverageValue
        averageValue: "100"              # ← scale if avg requests/s per pod exceeds 100
```

```bash
# Verify HPA is reading all three metrics
kubectl describe hpa data-processor-hpa -n production

# Check which metric is currently driving the scale decision
# Look for "current replicas" vs each metric's "current value"
kubectl get hpa data-processor-hpa -n production -o yaml | grep -A 20 "currentMetrics"

# See the formula: desiredReplicas = ceil(current * (current_metric / target_metric))
# Example: 5 pods * (120 rps / 100 rps) = ceil(6) = 6 pods
```

---

## 3. VPA — Rightsize Container Resources Automatically

```yaml
# vpa.yaml
# VPA in "Off" mode first — collect recommendations WITHOUT making changes
# Best practice: always observe before enabling Auto mode in production
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: backend-vpa
  namespace: production
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  updatePolicy:
    updateMode: "Off"                    # ← Off = recommendations only, no restarts
    # Options: Off | Initial | Auto | Recreate
    # Initial = set resources on new pods only (no eviction of running pods)
    # Auto    = evict and recreate pods with updated resources (brief downtime risk)
  resourcePolicy:
    containerPolicies:
    - containerName: "*"                 # ← apply to all containers in the pod
      minAllowed:
        cpu: "50m"                       # ← VPA will never recommend below this
        memory: "64Mi"
      maxAllowed:
        cpu: "4"                         # ← VPA will never recommend above this (safety cap)
        memory: "8Gi"
      controlledResources:
        - cpu
        - memory
```

```bash
# Install VPA (not installed by default — requires separate install)
# Using the official VPA installation script:
git clone https://github.com/kubernetes/autoscaler.git
cd autoscaler/vertical-pod-autoscaler
./hack/vpa-up.sh

# Apply the VPA object
kubectl apply -f vpa.yaml

# Wait a few hours for VPA to observe actual usage, then check recommendations
kubectl describe vpa backend-vpa -n production

# The output will show something like:
# Recommendation:
#   Container Recommendations:
#     Container Name: backend
#     Lower Bound:    cpu: 50m, memory: 100Mi
#     Target:         cpu: 200m, memory: 300Mi   ← apply these to your Deployment
#     Upper Bound:    cpu: 1, memory: 1Gi
#     Uncapped Target: cpu: 180m, memory: 270Mi

# Use these recommendations to update your Deployment's resource requests
# Then switch to "Initial" mode so new pods get right-sized automatically
```

---

## 4. Safe HPA + VPA Combination

```yaml
# hpa-on-rps-vpa-on-memory.yaml
# HPA and VPA can coexist safely IF they target different axes:
# - HPA scales pod COUNT based on requests-per-second (not CPU)
# - VPA resizes pod MEMORY based on actual usage
# They will NOT interfere because they are controlling different resources

---
# HPA scaling on a custom RPS metric (not CPU — avoids conflict with VPA)
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-server
  minReplicas: 2
  maxReplicas: 30
  metrics:
  - type: Pods
    pods:
      metric:
        name: requests_per_second        # ← custom metric, NOT cpu.utilization
      target:
        type: AverageValue
        averageValue: "200"

---
# VPA managing memory only — controlled to avoid CPU axis conflict with HPA
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: api-vpa
  namespace: production
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-server
  updatePolicy:
    updateMode: "Initial"               # ← only applies to newly created pods, no evictions
  resourcePolicy:
    containerPolicies:
    - containerName: "api"
      controlledResources:
        - memory                        # ← VPA only touches memory, leaves CPU alone
      minAllowed:
        memory: "128Mi"
      maxAllowed:
        memory: "4Gi"
```

```bash
# Verify neither is fighting the other
# HPA should show stable desired replicas tracking RPS
kubectl get hpa api-hpa -n production

# VPA recommendations should show memory target without CPU interference
kubectl describe vpa api-vpa -n production

# Check that pods are getting the VPA-recommended memory on creation
kubectl get pods -n production -l app=api-server -o yaml | \
  grep -A 4 "resources:"
```

---

## 5. KEDA — Event-Driven Autoscaling From an SQS Queue

```yaml
# keda-sqs-scaler.yaml
# KEDA scales a worker Deployment based on the number of messages in an AWS SQS queue
# Workers only run when there is work — scale to zero when queue is empty
# Requires KEDA installed and an IAM role/IRSA for SQS read access

apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: sqs-worker-scaler
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sqs-worker                   # ← the Deployment that processes queue messages
  pollingInterval: 30                  # ← check SQS queue depth every 30 seconds
  cooldownPeriod: 300                  # ← wait 5 minutes before scaling to zero after queue empties
  minReplicaCount: 0                   # ← scale to ZERO when queue is empty (not possible with native HPA)
  maxReplicaCount: 20                  # ← hard cap on workers
  triggers:
  - type: aws-sqs-queue
    authenticationRef:
      name: keda-sqs-auth              # ← reference to TriggerAuthentication with AWS credentials
    metadata:
      queueURL: https://sqs.us-east-1.amazonaws.com/123456789012/job-queue
      queueLength: "5"                 # ← target: 1 worker per 5 messages in queue
      awsRegion: us-east-1
      identityOwner: pod               # ← use pod's IRSA role, not keda's role

---
# TriggerAuthentication using IRSA (no static credentials)
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: keda-sqs-auth
  namespace: production
spec:
  podIdentity:
    provider: aws                      # ← use the pod's IAM role via IRSA
```

```bash
# Install KEDA via Helm
helm repo add kedacore https://kedacore.github.io/charts
helm repo update
helm install keda kedacore/keda --namespace keda --create-namespace

# Apply the ScaledObject and TriggerAuthentication
kubectl apply -f keda-sqs-scaler.yaml

# Watch KEDA scale the worker deployment as messages arrive
kubectl get scaledobject sqs-worker-scaler -n production --watch

# See current replica count and queue depth
kubectl describe scaledobject sqs-worker-scaler -n production

# When the queue is empty, workers should scale to 0
kubectl get pods -n production -l app=sqs-worker
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

⬅️ **Prev:** [Jobs and CronJobs](../17_Jobs_and_CronJobs/Code_Example.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Resource Quotas and Limits](../19_Resource_Quotas_and_Limits/Code_Example.md)
🏠 **[Home](../../README.md)**
