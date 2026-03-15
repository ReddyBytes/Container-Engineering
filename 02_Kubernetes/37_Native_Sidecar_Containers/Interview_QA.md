# Module 37 — Native Sidecar Containers Interview Q&A

---

## Q1: What is the fundamental difference between a native sidecar container and a regular sidecar pattern in Kubernetes?

**Answer:**

Before native sidecars (K8s 1.29+), there was no first-class sidecar concept. Developers would put helper containers (log agents, proxies) in the regular `containers` list alongside the main app. These had no guaranteed lifecycle relationship with the main container.

A **native sidecar** is an `initContainer` with `restartPolicy: Always`. This single field unlocks three lifecycle guarantees that regular containers don't have:

1. **Ordered startup**: native sidecars start before main containers (because they're in `initContainers`). If a native sidecar has a readiness probe, the next container in the init sequence won't start until that probe passes.

2. **Co-running**: unlike regular init containers (which must exit before main containers start), native sidecars run alongside the main containers for the entire pod lifetime.

3. **Ordered shutdown**: native sidecars receive SIGTERM after main containers have already exited. This ensures log agents ship the last lines, proxies handle the last connections.

---

## Q2: Why did native sidecars solve a critical problem for Kubernetes Jobs?

**Answer:**

With regular containers in a Job, the sidecar (e.g., a log-shipping Fluentd container) has no concept of "the main work is done." When the main container exits successfully, Kubernetes checks whether the pod is complete by looking at all containers. The sidecar is still running, so the Job never completes. It hangs indefinitely.

Workarounds were ugly: the main app had to write a sentinel file that the sidecar watched and then exited, or the sidecar polled for the main container's exit. These were fragile and hard to maintain.

With native sidecars, Kubernetes knows that `initContainers` with `restartPolicy: Always` are sidecars, not main workloads. When determining Job completion, it only examines the main containers (`spec.containers`). When the main container exits with success, the Job is marked complete, and Kubernetes sends SIGTERM to the native sidecar to let it shut down gracefully.

---

## Q3: What K8s version made native sidecar containers stable (GA)?

**Answer:**

Native sidecar containers reached **GA (stable) in Kubernetes 1.33** (2025). Timeline:

- K8s 1.28: Alpha (required `SidecarContainers=true` feature gate)
- K8s 1.29: Beta (feature gate enabled by default)
- K8s 1.33: GA (no feature gate required)

---

## Q4: How do you define a native sidecar container in YAML?

**Answer:**

Place the container in `spec.initContainers` and add `restartPolicy: Always`:

```yaml
spec:
  initContainers:
  - name: log-agent
    image: fluent/fluent-bit:3.0
    restartPolicy: Always        # this makes it a native sidecar
    volumeMounts:
    - name: logs
      mountPath: /var/log/app
  containers:
  - name: app
    image: myapp:latest
    volumeMounts:
    - name: logs
      mountPath: /var/log/app
  volumes:
  - name: logs
    emptyDir: {}
```

Everything else in the container spec works the same as any other container: resources, environment variables, volume mounts, probes.

---

## Q5: What happens to a native sidecar's readiness probe? How does it affect pod startup?

**Answer:**

When a native sidecar (initContainer with `restartPolicy: Always`) has a `readinessProbe`, Kubernetes uses it as a **startup gate**: the next item in the `initContainers` sequence will not start until this sidecar's readiness probe passes. If the sidecar is the last item in `initContainers`, the main containers will not start until its readiness probe passes.

This is the mechanism that solves the "proxy not ready when app starts" problem for service meshes. With Istio or Envoy as a native sidecar with a readiness probe, you guarantee that:

1. Envoy starts
2. Envoy's readiness probe passes (proxy is listening and healthy)
3. The application container starts
4. From the very first connection, all traffic goes through the mesh

Before native sidecars, the app and proxy would start in parallel — a race condition that could cause requests to bypass the proxy at startup.

---

## Q6: What is the startup order when you mix regular init containers and native sidecar init containers?

**Answer:**

The order is strictly sequential based on position in the `initContainers` array:

1. Regular init containers (no `restartPolicy: Always`) run first, in order, each must exit before the next starts.
2. Native sidecar init containers (`restartPolicy: Always`) run next, in order. Each starts and (if it has a readiness probe) must become Ready before the next starts.
3. Once all init containers have run and all native sidecars are Running+Ready, the main `containers` start in parallel.

```yaml
initContainers:
- name: db-migration         # Step 1: runs, exits (regular init)
  image: migrate:v1
- name: log-agent            # Step 2: starts, stays running (native sidecar)
  image: fluent-bit:3.0
  restartPolicy: Always
- name: envoy-proxy          # Step 3: starts, stays running (native sidecar)
  image: envoy:v1.28
  restartPolicy: Always
  readinessProbe: ...        # Step 4: app only starts after this passes
containers:
- name: app                  # Step 5: starts
  image: myapp:v1
```

---

## Q7: Before native sidecars, what were the common workaround patterns and why were they problematic?

**Answer:**

Teams used three main workarounds, each with significant drawbacks:

**1. Regular containers (parallel start)**
```yaml
containers:
- name: app
  image: myapp:v1
- name: log-agent
  image: fluentd:v1
```
Problems: no startup ordering (race condition), sidecar might exit before app finishes, Jobs hang forever.

**2. Init containers for "one-time setup only"**
Regular init containers (without `restartPolicy: Always`) must exit before main containers start. You couldn't use them as running sidecars — they'd need to run indefinitely, which would block all main containers from starting.

**3. Hack: shared file + polling in Jobs**
The main app would write a "done" file when finished:
```sh
# Main container: touch /tmp/done when work is complete
# Sidecar: watch for /tmp/done then kill itself
while ! [ -f /tmp/done ]; do sleep 1; done; exit 0
```
Problems: tight coupling between app and sidecar logic, brittle, the sidecar needs to know implementation details of the main app.

**4. postStart hook trick**
Start the sidecar process via a postStart lifecycle hook — runs in the background, unsupervised, with no restart capability.

All of these workarounds solved one problem while introducing others. Native sidecars replace them all cleanly.

---

## Q8: Can native sidecars have resource limits? What about security contexts?

**Answer:**

Yes. Native sidecars support the full container spec, including:

```yaml
initContainers:
- name: log-agent
  image: fluent/fluent-bit:3.0
  restartPolicy: Always
  resources:
    requests:
      memory: "64Mi"
      cpu: "50m"
    limits:
      memory: "128Mi"
      cpu: "100m"
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    readOnlyRootFilesystem: true
    allowPrivilegeEscalation: false
```

This is actually important for cluster resource accounting. When Kubernetes schedules a pod, it accounts for the resource requests of ALL containers — both main containers and native sidecar init containers. A 64Mi log agent sidecar adds 64Mi to the pod's memory request, which affects scheduling and resource quota consumption.

---

## Q9: How do native sidecar containers work with pod termination and graceful shutdown?

**Answer:**

Pod termination with native sidecars follows this order:

1. Kubernetes sends SIGTERM to all **main containers** simultaneously
2. Main containers have `terminationGracePeriodSeconds` to finish in-flight work and exit
3. After main containers exit (or grace period expires), Kubernetes sends SIGTERM to all **native sidecar containers**
4. Sidecars have their own portion of the `terminationGracePeriodSeconds` to complete shutdown
5. After all containers exit, the pod is deleted

The key guarantee: **sidecars always stop AFTER main containers**. This means:
- A log shipper will receive and ship the last log lines the app wrote before it exited
- An Envoy proxy will keep the mesh alive until the app has finished handling its last request
- A secret refresher won't stop mid-write while the app is still reading

This is why the ordering matters — without native sidecars, the log agent might be killed first, losing the last minutes of logs.

---

## Q10: What is the impact of native sidecars on pod scheduling and resource quotas?

**Answer:**

When the Kubernetes scheduler decides where to place a pod, it sums up the resource requests of:
- All main containers (`spec.containers`)
- All native sidecar init containers (`spec.initContainers` with `restartPolicy: Always`)
- The highest-resource regular init container (only one regular init container runs at a time, so only the max counts)

This means native sidecar resources ARE counted toward:
- **Node capacity**: a node with 8GB RAM might not fit a pod if main app (6GB) + sidecar (1.5GB) = 7.5GB
- **ResourceQuota**: a namespace quota limits total memory — sidecars count against it
- **LimitRange**: if the namespace has a LimitRange, sidecars must comply too

Teams sometimes forget this and are surprised when pod scheduling fails or quotas are exhausted. The sidecar's resource footprint is not free.

---

## Q11: How do native sidecars compare to the Istio sidecar injection model? Will Istio switch to native sidecars?

**Answer:**

Traditional Istio sidecar injection works via a mutating admission webhook that adds an Envoy proxy as a **regular container** to every pod in labeled namespaces. This has the classic problems: startup race conditions (the app might start before Envoy is ready), and Jobs can't complete if Istio is enabled.

Istio has added support for native sidecars starting with Istio 1.18+ (2023), and it became the recommended approach with the maturation of the K8s native sidecar feature. With native sidecar injection:

- The Envoy proxy is injected as an `initContainer` with `restartPolicy: Always`
- A readiness probe ensures the proxy is ready before the app starts
- Jobs complete correctly — Istio no longer blocks batch workloads
- Shutdown ordering is correct — Envoy stops after the app

To use native sidecar injection with Istio (on K8s 1.29+):
```yaml
# Label the namespace for native sidecar injection
kubectl label namespace my-namespace istio.io/dataplane-mode=ambient
# or configure via IstioOperator to use native sidecars
```

This is considered a significant quality-of-life improvement for Istio users, especially for teams running Jobs and batch workloads alongside a service mesh.

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Native Sidecar Containers Theory](./Theory.md) |
| Cheatsheet | [Native Sidecar Containers Cheatsheet](./Cheatsheet.md) |
| Code Examples | [Native Sidecar Containers Code Examples](./Code_Example.md) |
| Previous Module | [36 — ValidatingAdmissionPolicy](../36_ValidatingAdmissionPolicy/Theory.md) |
