# Resource Quotas and Limits — Code Examples

All examples are production-quality with detailed comments explaining every decision.

---

## 1. Resource Requests and Limits — QoS Classes in Practice

```yaml
# qos-demo.yaml
# Three pods demonstrating all three QoS classes
# QoS class determines eviction order when the node runs out of memory

---
# BestEffort — evicted FIRST under memory pressure
# Avoid in production; only for throwaway debugging pods
apiVersion: v1
kind: Pod
metadata:
  name: besteffort-pod
  namespace: default
spec:
  containers:
  - name: app
    image: busybox:1.36
    command: ["sleep", "3600"]
    # ← no resources block at all = BestEffort QoS class
    # this pod gets whatever is left over and is first to die

---
# Burstable — evicted SECOND; can use more than it requested if spare capacity exists
apiVersion: v1
kind: Pod
metadata:
  name: burstable-pod
  namespace: default
spec:
  containers:
  - name: app
    image: busybox:1.36
    command: ["sleep", "3600"]
    resources:
      requests:
        cpu: "100m"                      # ← requests and limits are different = Burstable
        memory: "64Mi"
      limits:
        cpu: "500m"                      # ← can burst to 5x the requested CPU
        memory: "256Mi"                  # ← OOMKilled if it exceeds 256Mi

---
# Guaranteed — evicted LAST; gets exactly what it asks for, no more, no less
apiVersion: v1
kind: Pod
metadata:
  name: guaranteed-pod
  namespace: default
spec:
  containers:
  - name: app
    image: busybox:1.36
    command: ["sleep", "3600"]
    resources:
      requests:
        cpu: "200m"                      # ← requests == limits for ALL resources = Guaranteed
        memory: "128Mi"
      limits:
        cpu: "200m"                      # ← must equal the request value
        memory: "128Mi"                  # ← must equal the request value
```

```bash
kubectl apply -f qos-demo.yaml

# Verify each pod's QoS class
kubectl get pod besteffort-pod -o jsonpath='{.status.qosClass}'   # BestEffort
kubectl get pod burstable-pod  -o jsonpath='{.status.qosClass}'   # Burstable
kubectl get pod guaranteed-pod -o jsonpath='{.status.qosClass}'   # Guaranteed

# Check actual resource usage
kubectl top pod besteffort-pod burstable-pod guaranteed-pod

# Simulate OOMKill: run this to use more memory than the burstable limit
# kubectl exec burstable-pod -- sh -c "dd if=/dev/zero of=/tmp/mem bs=1M count=300"
# Then: kubectl describe pod burstable-pod | grep "OOMKilled"
```

---

## 2. LimitRange — Namespace-Level Defaults and Bounds

```yaml
# namespace-setup.yaml
# Create a namespace for the team and apply a LimitRange so every pod
# automatically gets sane resource bounds even if developers forget to set them

---
apiVersion: v1
kind: Namespace
metadata:
  name: team-backend

---
# LimitRange: applied by the admission controller at pod creation time
# Without this, a developer who forgets resources gets a BestEffort pod
apiVersion: v1
kind: LimitRange
metadata:
  name: backend-limits
  namespace: team-backend
spec:
  limits:
  - type: Container
    default:                             # ← these limits are injected if the container sets none
      cpu: "500m"
      memory: "256Mi"
    defaultRequest:                      # ← these requests are injected if the container sets none
      cpu: "100m"
      memory: "128Mi"
    max:                                 # ← containers cannot specify more than this (rejected at admission)
      cpu: "4"
      memory: "4Gi"
    min:                                 # ← containers cannot specify less than this
      cpu: "50m"
      memory: "64Mi"
  - type: Pod
    max:                                 # ← sum of all containers in a pod cannot exceed this
      cpu: "8"
      memory: "8Gi"
  - type: PersistentVolumeClaim
    max:
      storage: "50Gi"                    # ← PVCs cannot request more than 50Gi
    min:
      storage: "1Gi"
```

```bash
kubectl apply -f namespace-setup.yaml

# Verify the LimitRange was created
kubectl describe limitrange backend-limits -n team-backend

# Create a pod WITHOUT any resource spec — watch the defaults get injected
kubectl run no-limits-pod \
  --image=nginx:1.25 \
  -n team-backend \
  --restart=Never

# The pod should exist but now have the LimitRange defaults applied
kubectl get pod no-limits-pod -n team-backend -o yaml | grep -A 10 "resources:"
# Output should show: cpu: 500m (limit), memory: 256Mi (limit), cpu: 100m (request), memory: 128Mi (request)

# Try to create a pod exceeding the max — it should be REJECTED
kubectl run too-big-pod \
  --image=nginx:1.25 \
  -n team-backend \
  --restart=Never \
  --limits='cpu=8,memory=8Gi'
# Error: pods "too-big-pod" is forbidden: maximum cpu usage per Container is 4, but limit is 8
```

---

## 3. ResourceQuota — Namespace Budget Enforcement

```yaml
# resource-quota.yaml
# Quota for a multi-tenant cluster where the data team shares infrastructure
# Prevents one team from consuming the entire cluster during a training run

---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: data-team-quota
  namespace: team-data
spec:
  hard:
    # Compute budgets
    requests.cpu: "20"                   # ← all pods combined cannot request more than 20 cores
    requests.memory: "40Gi"             # ← all pods combined cannot request more than 40Gi RAM
    limits.cpu: "40"                     # ← all pods combined cannot use more than 40 cores
    limits.memory: "80Gi"               # ← all pods combined cannot use more than 80Gi RAM
    # Object count limits — prevent runaway job creation from filling etcd
    pods: "100"                          # ← hard cap on number of pods
    count/jobs.batch: "20"              # ← limit concurrent batch jobs
    count/cronjobs.batch: "10"          # ← limit scheduled jobs
    # Storage budgets
    requests.storage: "1Ti"             # ← total PVC storage across all claims
    persistentvolumeclaims: "20"        # ← maximum number of PVCs
    # Service types (expensive resources)
    services.loadbalancers: "2"         # ← LoadBalancers cost money in cloud environments
```

```bash
kubectl apply -f resource-quota.yaml

# View quota usage at a glance
kubectl get resourcequota data-team-quota -n team-data

# Detailed quota status showing used vs hard limits
kubectl describe resourcequota data-team-quota -n team-data

# Example output:
# Resource             Used   Hard
# --------             ----   ----
# limits.cpu           12     40
# limits.memory        24Gi   80Gi
# pods                 15     100
# requests.cpu         6      20
# requests.memory      12Gi   40Gi

# When quota is exhausted, new pod creation is rejected:
# Error: pods "new-job" is forbidden: exceeded quota: data-team-quota,
#        requested: requests.cpu=4, used: requests.cpu=20, limited: requests.cpu=20
```

---

## 4. LimitRange + ResourceQuota Together — Full Namespace Setup

```yaml
# production-namespace.yaml
# Complete production namespace setup: namespace, LimitRange, and ResourceQuota
# LimitRange ensures every pod has limits; ResourceQuota caps the total budget
# These two work together — LimitRange fills in missing specs, Quota tracks the totals

---
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    team: platform
    env: prod

---
# LimitRange: ensures no pod is BestEffort, sets sensible defaults
apiVersion: v1
kind: LimitRange
metadata:
  name: production-limits
  namespace: production
spec:
  limits:
  - type: Container
    default:
      cpu: "500m"
      memory: "256Mi"
    defaultRequest:
      cpu: "100m"
      memory: "128Mi"
    max:
      cpu: "4"
      memory: "8Gi"
    min:
      cpu: "50m"
      memory: "64Mi"

---
# ResourceQuota: caps total consumption across all pods in the namespace
apiVersion: v1
kind: ResourceQuota
metadata:
  name: production-quota
  namespace: production
spec:
  hard:
    requests.cpu: "50"
    requests.memory: "100Gi"
    limits.cpu: "100"
    limits.memory: "200Gi"
    pods: "200"
    services: "50"
    secrets: "100"                       # ← prevent secret sprawl
    configmaps: "100"
    services.loadbalancers: "5"          # ← cloud LBs are expensive
    persistentvolumeclaims: "50"
    requests.storage: "5Ti"
```

```bash
kubectl apply -f production-namespace.yaml

# Confirm both are applied
kubectl get limitrange,resourcequota -n production

# Test the interaction: create a pod with no resource spec
# The LimitRange will inject defaults, and the ResourceQuota will count them
kubectl run test-pod --image=nginx:1.25 -n production --restart=Never

# The pod now counts against the quota using the LimitRange defaults
kubectl describe resourcequota production-quota -n production
# requests.cpu: 100m (the LimitRange default request, not zero)

# Without LimitRange, this pod would have 0 CPU request, but the ResourceQuota
# would reject it because a quota is set on requests.cpu and the pod has none
```

---

## 5. Diagnosing OOMKilled and CPU Throttling

```yaml
# stress-pod.yaml
# Pod that demonstrates both OOMKill and CPU throttling scenarios
apiVersion: v1
kind: Pod
metadata:
  name: resource-stress-demo
  namespace: default
spec:
  containers:
  - name: stress
    image: polinux/stress                # ← stress testing tool — do not use in production
    command: ["stress"]
    args:
    - "--cpu"
    - "2"                                # ← request 2 CPU cores of work (exceeds our limit)
    - "--vm"
    - "1"
    - "--vm-bytes"
    - "64M"                              # ← allocate 64MB memory (within limit — won't OOMKill)
    - "--vm-hang"
    - "0"
    resources:
      requests:
        cpu: "100m"
        memory: "32Mi"
      limits:
        cpu: "200m"                      # ← CPU capped at 200m; stress asks for 2000m → throttled
        memory: "128Mi"                  # ← memory limit; change vm-bytes to 256M to trigger OOMKill
```

```bash
kubectl apply -f stress-pod.yaml

# Check pod is running (not OOMKilled yet — we're within memory limit)
kubectl get pod resource-stress-demo

# See CPU throttling happening — actual usage will be near the 200m limit
kubectl top pod resource-stress-demo

# Full resource detail
kubectl describe pod resource-stress-demo | grep -A 10 "Limits\|Requests"

# --- Trigger OOMKill ---
# Edit the pod's vm-bytes to 256M (exceeds the 128Mi limit) and reapply
# kubectl delete pod resource-stress-demo
# (edit args: "--vm-bytes" "256M")
# kubectl apply -f stress-pod.yaml

# After OOMKill, see the failure
kubectl describe pod resource-stress-demo | grep -A 5 "Last State"
# Output:
# Last State: Terminated
#   Reason:    OOMKilled
#   Exit Code: 137           ← 137 = killed by SIGKILL (128 + 9)

# See restart count incrementing (Kubernetes restarts OOMKilled pods)
kubectl get pod resource-stress-demo --watch

# Check CPU throttling metrics (if Prometheus is installed)
# container_cpu_cfs_throttled_seconds_total{container="stress"}
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

⬅️ **Prev:** [HPA, VPA, and Autoscaling](../18_HPA_VPA_Autoscaling/Code_Example.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Network Policies](../20_Network_Policies/Code_Example.md)
🏠 **[Home](../../README.md)**
