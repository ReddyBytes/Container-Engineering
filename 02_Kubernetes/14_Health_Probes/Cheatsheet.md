# Health Probes Cheatsheet

## Three Probe Types at a Glance

| Probe | Question | On Failure | On Success |
|-------|----------|------------|------------|
| Liveness | Is it alive? | Restart container | Nothing |
| Readiness | Ready for traffic? | Remove from Service endpoints | Add to Service endpoints |
| Startup | Done starting up? | Restart container | Enables liveness probe |

---

## kubectl Commands

```bash
# --- Viewing Probe Configuration ---

# View a pod's probe config (look under containers[].livenessProbe etc.)
kubectl describe pod <pod-name> -n <namespace>

# Get probe config in YAML
kubectl get pod <pod-name> -n <namespace> -o yaml | grep -A 20 Probe

# --- Debugging Probe Failures ---

# Check pod events for probe failures
kubectl describe pod <pod-name> -n <namespace>
# Look for: "Liveness probe failed:", "Readiness probe failed:"
# Look for: "Back-off restarting failed container"

# Check restart count (high count = liveness probe killing container)
kubectl get pods -n <namespace>
# RESTARTS column shows how many times the container has been restarted

# Watch pods in real time (observe readiness changes during deployment)
kubectl get pods -n <namespace> -w

# Get pod details including probe results
kubectl get pod <pod-name> -n <namespace> -o jsonpath='{.status.conditions}'

# See if a pod is ready (READY column shows containers/total)
kubectl get pods -n <namespace>
# 1/1 = ready, 0/1 = not ready (readiness probe failing)

# Check endpoints — only ready pods appear here
kubectl get endpoints <service-name> -n <namespace>
kubectl describe endpoints <service-name> -n <namespace>
# "NotReadyAddresses" shows pods currently failing readiness

# --- Testing Health Endpoints Manually ---

# Port-forward to test the health endpoint directly
kubectl port-forward pod/<pod-name> 8080:8080 -n <namespace>
# Then: curl http://localhost:8080/healthz

# Exec into the pod and test internally
kubectl exec -it <pod-name> -n <namespace> -- \
  wget -qO- http://localhost:8080/healthz

# Test a TCP socket check manually
kubectl exec -it <pod-name> -n <namespace> -- \
  nc -zv localhost 5432

# Test a gRPC health check (requires grpc_health_probe)
kubectl exec -it <pod-name> -n <namespace> -- \
  grpc_health_probe -addr=:50051

# --- Watching Probe Effects ---

# Watch pod restarts in real time (liveness probe failures)
kubectl get pods -n <namespace> -w --field-selector=metadata.name=<pod-name>

# Watch endpoint changes (readiness probe effects)
kubectl get endpoints <service-name> -n <namespace> -w

# Get events for all pods in a namespace
kubectl events -n <namespace>           # kubectl 1.26+
kubectl get events -n <namespace> --sort-by='.lastTimestamp'

# Filter events for probe failures
kubectl get events -n <namespace> | grep -i "probe\|liveness\|readiness"

# --- Deployment Rollout and Probes ---

# Readiness probes gate deployment rollouts
# Watch a rollout and see it pause for readiness
kubectl rollout status deployment/<name> -n <namespace>

# If readiness probe is wrong, rollout will stall:
kubectl rollout undo deployment/<name> -n <namespace>

# Temporarily override probe for debugging (not recommended for prod)
kubectl set env deployment/<name> DISABLE_HEALTH_CHECK=true -n <namespace>
```

---

## Probe Configuration Quick Reference

```yaml
# HTTP GET probe
livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 15    # wait 15s after start
  periodSeconds: 10          # check every 10s
  timeoutSeconds: 3          # timeout after 3s
  failureThreshold: 3        # fail 3 times before restarting
  successThreshold: 1        # 1 success to be considered healthy

# TCP Socket probe
readinessProbe:
  tcpSocket:
    port: 5432
  periodSeconds: 5
  failureThreshold: 3

# Exec probe
livenessProbe:
  exec:
    command: ["pg_isready", "-U", "postgres"]
  periodSeconds: 10

# gRPC probe
readinessProbe:
  grpc:
    port: 50051
  periodSeconds: 5

# Startup probe (for slow-starting apps)
startupProbe:
  httpGet:
    path: /healthz
    port: 8080
  failureThreshold: 30       # 30 * 10s = 5 minutes of startup runway
  periodSeconds: 10
```

---

## Tuning Guide

| Probe | initialDelaySeconds | periodSeconds | failureThreshold | timeoutSeconds |
|-------|--------------------:|-------------:|----------------:|---------------:|
| Startup | 0 | 5-10 | (maxStartup / period) | 3-5 |
| Liveness | 30-60 | 10-20 | 3-5 | 3-5 |
| Readiness | 5-10 | 5-10 | 3 | 2-3 |

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Theory.md](./Theory.md) |
| Interview Q&A | [Interview_QA.md](./Interview_QA.md) |
| Code Example | [Code_Example.md](./Code_Example.md) |
| Module Home | [14_Health_Probes](../) |
