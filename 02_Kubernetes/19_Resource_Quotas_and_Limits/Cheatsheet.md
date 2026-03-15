# Resource Quotas and Limits Cheatsheet

## QoS Classes Quick Reference

| QoS Class | Requirements | Eviction Priority |
|---|---|---|
| Guaranteed | requests == limits for ALL containers (CPU + memory) | Evicted last |
| Burstable | Some requests/limits set, but requests != limits | Evicted second |
| BestEffort | No requests or limits on ANY container | Evicted first |

---

## kubectl Commands

```bash
# --- Viewing Resource Usage ---

# Node resource usage
kubectl top nodes

# Pod resource usage in a namespace
kubectl top pods -n <namespace>

# Pod resource usage sorted by CPU
kubectl top pods -n <namespace> --sort-by=cpu

# Pod resource usage sorted by memory
kubectl top pods -n <namespace> --sort-by=memory

# Container-level resource usage
kubectl top pods -n <namespace> --containers

# See requests and limits for all pods in a namespace
kubectl get pods -n <namespace> -o json | \
  jq '.items[] | {name: .metadata.name, containers: [.spec.containers[] | {name: .name, resources: .resources}]}'

# --- Checking QoS Class ---

# Get QoS class for a pod
kubectl get pod <name> -n <namespace> \
  -o jsonpath='{.status.qosClass}'

# Get QoS class for all pods in a namespace
kubectl get pods -n <namespace> \
  -o custom-columns=NAME:.metadata.name,QOS:.status.qosClass

# --- LimitRange ---

# View LimitRanges in a namespace
kubectl get limitrange -n <namespace>
kubectl get limits -n <namespace>     # short form

# Describe a LimitRange (see defaults and min/max)
kubectl describe limitrange <name> -n <namespace>

# Check what defaults will be applied to a new pod
kubectl describe limitrange default-limits -n <namespace>

# --- ResourceQuota ---

# View ResourceQuotas in a namespace
kubectl get resourcequota -n <namespace>
kubectl get quota -n <namespace>      # short form

# Describe a ResourceQuota (see used vs hard limits)
kubectl describe resourcequota <name> -n <namespace>

# Get all quota usage across all namespaces
kubectl get resourcequota -A

# Describe quota to see current usage
kubectl describe quota team-quota -n my-team
# Used: requests.cpu: 3/10 means 3 of 10 CPU cores are claimed

# --- OOMKilled Diagnosis ---

# Check if a container was OOMKilled
kubectl describe pod <name> -n <namespace>
# Look for: Reason: OOMKilled, Exit Code: 137

# View previous container logs (before OOM kill)
kubectl logs <pod-name> -c <container-name> --previous -n <namespace>

# Get OOM events for a namespace
kubectl get events -n <namespace> | grep -i oom

# Check current memory usage vs limits
kubectl top pod <name> -n <namespace> --containers

# --- Node Pressure Conditions ---

# Check if a node has memory pressure
kubectl describe node <node-name> | grep -A 5 Conditions
# Look for: MemoryPressure: True

# Check node capacity vs allocatable
kubectl describe node <node-name> | grep -A 10 "Capacity:\|Allocatable:"

# See all resources requested on a node
kubectl describe node <node-name> | grep -A 20 "Allocated resources:"

# --- Resource Quota Errors ---

# If pod creation fails due to quota:
# Error: exceeded quota: team-quota, requested: requests.cpu=500m, used: requests.cpu=9.5, limited: requests.cpu=10
kubectl describe quota team-quota -n my-team  # check current usage
kubectl top pods -n my-team                   # find which pods are heavy users

# --- PodDisruptionBudget ---

# List PDBs
kubectl get pdb -n <namespace>

# Describe a PDB (see min available, allowed disruptions)
kubectl describe pdb <name> -n <namespace>

# Check disruption status (ALLOWED DISRUPTIONS column)
kubectl get pdb -n <namespace>
```

---

## LimitRange YAML Quick Reference

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: default-limits
  namespace: my-namespace
spec:
  limits:
    - type: Container           # applies to each container
      defaultRequest:
        cpu: 100m
        memory: 128Mi
      default:
        cpu: 500m
        memory: 512Mi
      min:
        cpu: 50m
        memory: 64Mi
      max:
        cpu: "4"
        memory: 8Gi

    - type: Pod                 # applies to the total pod (all containers combined)
      max:
        cpu: "8"
        memory: 16Gi

    - type: PersistentVolumeClaim
      max:
        storage: 100Gi
      min:
        storage: 1Gi
```

---

## ResourceQuota YAML Quick Reference

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-quota
  namespace: my-namespace
spec:
  hard:
    requests.cpu: "10"
    limits.cpu: "20"
    requests.memory: 20Gi
    limits.memory: 40Gi
    pods: "100"
    services: "20"
    secrets: "50"
    configmaps: "50"
    persistentvolumeclaims: "10"
    requests.storage: 500Gi
    count/deployments.apps: "20"
    count/cronjobs.batch: "10"
    services.loadbalancers: "5"
```

---

## Container Resource Behavior Quick Reference

| Situation | What happens | Exit code |
|---|---|---|
| Memory usage hits limit | OOMKilled (kernel kills process) | 137 |
| CPU usage hits limit | CPU throttled (slows down) | No exit |
| Node memory pressure | BestEffort pods evicted first | Pod deleted |
| Quota exceeded | Pod creation rejected by API server | N/A (admission error) |
| No resources + quota set | Pod creation rejected | N/A (admission error) |

---

## Common Resource Sizing Starting Points

| Workload type | CPU request | CPU limit | Memory request | Memory limit |
|---|---|---|---|---|
| Small API / microservice | 100m | 500m | 128Mi | 256Mi |
| Medium web service | 250m | 1000m | 256Mi | 512Mi |
| Database (PostgreSQL) | 500m | 2000m | 512Mi | 2Gi |
| ML / batch job | 1000m | 4000m | 1Gi | 8Gi |

These are starting points only — always measure actual usage and adjust.

---

## 📂 Navigation

⬅️ **Prev:** [HPA/VPA Autoscaling](../18_HPA_VPA_Autoscaling/Interview_QA.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Network Policies](../20_Network_Policies/Theory.md)

| | Link |
|---|---|
| Theory | [Theory.md](./Theory.md) |
| Interview Q&A | [Interview_QA.md](./Interview_QA.md) |
| Module Home | [19_Resource_Quotas_and_Limits](../) |
