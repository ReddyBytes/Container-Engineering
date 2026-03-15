# Module 37 — Native Sidecar Containers Cheatsheet

## The One-Line Summary

Add `restartPolicy: Always` to an `initContainer` to make it a native sidecar: starts before main containers, runs alongside them, stops after them.

---

## Minimal Native Sidecar Template

```yaml
spec:
  initContainers:
  - name: my-sidecar
    image: my-sidecar:latest
    restartPolicy: Always        # <-- this is the ONLY required addition
    # Add any other container spec fields here
  containers:
  - name: app
    image: myapp:latest
```

---

## Full Native Sidecar with All Features

```yaml
spec:
  initContainers:
  - name: log-agent
    image: fluent/fluent-bit:3.0
    restartPolicy: Always        # makes this a native sidecar
    # Resources (good practice)
    resources:
      requests:
        memory: "64Mi"
        cpu: "50m"
      limits:
        memory: "128Mi"
        cpu: "100m"
    # Readiness probe: main containers wait for this to pass
    readinessProbe:
      exec:
        command: ["/fluent-bit/bin/fluent-bit", "-v"]
      initialDelaySeconds: 5
      periodSeconds: 10
    # Volume mount: read logs from shared volume
    volumeMounts:
    - name: varlog
      mountPath: /var/log/app
    - name: fluent-bit-config
      mountPath: /fluent-bit/etc
    env:
    - name: FLUSH_INTERVAL
      value: "1"
  containers:
  - name: app
    image: myapp:latest
    volumeMounts:
    - name: varlog
      mountPath: /var/log/app
  volumes:
  - name: varlog
    emptyDir: {}
  - name: fluent-bit-config
    configMap:
      name: fluent-bit-config
```

---

## Lifecycle Behavior

| Behavior | Regular container | Native sidecar (initContainer + restartPolicy: Always) |
|----------|-------------------|------------------------------------------------------|
| Starts before main containers | No (parallel) | Yes (guaranteed) |
| Runs alongside main containers | Yes | Yes |
| Has ordered startup | No | Yes (initContainer order) |
| Readiness gates next container | No | Yes (if readinessProbe defined) |
| Survives if it crashes | Yes (restartPolicy) | Yes (always restarted) |
| Stops after main containers | No | Yes (guaranteed) |
| Blocks Job completion | Yes (old problem) | No (Job-aware) |
| Works in Jobs | Badly | Yes |

---

## Startup Ordering Rules

```
initContainer 1 (regular) → exits
initContainer 2 (regular) → exits
initContainer 3 (restartPolicy: Always) → starts + becomes Ready
initContainer 4 (restartPolicy: Always) → starts + becomes Ready
THEN: main containers start
```

- Regular init containers always run before native sidecars
- Within native sidecars, they start in order (top to bottom)
- Each native sidecar must be Ready (probe passes) before the next one starts
- All native sidecars must be Ready before main containers start

---

## Jobs with Native Sidecars

```yaml
# Job completion is determined by main containers only.
# Sidecars are automatically terminated after main containers exit.
apiVersion: batch/v1
kind: Job
metadata:
  name: data-pipeline
spec:
  template:
    spec:
      restartPolicy: Never       # Job's restart policy (for main containers)
      initContainers:
      - name: log-shipper
        image: fluent/fluent-bit:3.0
        restartPolicy: Always    # native sidecar in a Job
        volumeMounts:
        - name: logs
          mountPath: /var/log
      containers:
      - name: pipeline
        image: my-pipeline:v1
        volumeMounts:
        - name: logs
          mountPath: /var/log
        command: ["python", "pipeline.py"]
        # When this exits 0, the Job is COMPLETE.
        # The log-shipper sidecar is then gracefully terminated.
      volumes:
      - name: logs
        emptyDir: {}
```

---

## Before/After Migration

```yaml
# BEFORE: sidecar as regular container (fragile)
spec:
  containers:
  - name: app
    image: myapp:v1
  - name: envoy-proxy          # starts in parallel — race condition!
    image: envoy:v1.28
    # App might connect before envoy is ready
    # In Jobs: envoy keeps running after app exits

# AFTER: native sidecar (correct lifecycle)
spec:
  initContainers:
  - name: envoy-proxy
    image: envoy:v1.28
    restartPolicy: Always      # now a native sidecar
    readinessProbe:            # app waits for this probe
      httpGet:
        path: /ready
        port: 9901
  containers:
  - name: app
    image: myapp:v1
    # app only starts after envoy-proxy probe passes
```

---

## Common Sidecar Patterns

| Use Case | Sidecar Image | Key Config |
|----------|--------------|------------|
| Log shipping | `fluent/fluent-bit:3.0` | volumeMount shared log dir |
| Log shipping | `fluentd:v1.17` | volumeMount shared log dir |
| Service mesh | `envoy:v1.28` | readinessProbe on admin port |
| Secret refresh | `vault-agent` / `secrets-store-csi` | volumeMount for secrets |
| Config watcher | custom | volumeMount emptyDir |
| Metrics exporter | `prom/node-exporter` | expose port 9100 |

---

## Version Support

| K8s Version | Status |
|-------------|--------|
| 1.28 | Alpha (feature gate needed) |
| 1.29 | Beta (enabled by default) |
| 1.33 | **GA / Stable** (2025) |

---

## Probes on Native Sidecars

```yaml
initContainers:
- name: my-sidecar
  image: my-sidecar:latest
  restartPolicy: Always
  # All three probe types are supported
  startupProbe:
    httpGet:
      path: /healthz
      port: 8080
    failureThreshold: 30
    periodSeconds: 5
  readinessProbe:              # gates startup of next init/main containers
    httpGet:
      path: /ready
      port: 8080
    initialDelaySeconds: 5
    periodSeconds: 10
  livenessProbe:               # triggers restart if sidecar becomes unhealthy
    httpGet:
      path: /healthz
      port: 8080
    periodSeconds: 30
```

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Native Sidecar Containers Theory](./Theory.md) |
| Interview Q&A | [Native Sidecar Containers Interview Q&A](./Interview_QA.md) |
| Code Examples | [Native Sidecar Containers Code Examples](./Code_Example.md) |
| Previous Module | [36 — ValidatingAdmissionPolicy](../36_ValidatingAdmissionPolicy/Theory.md) |
