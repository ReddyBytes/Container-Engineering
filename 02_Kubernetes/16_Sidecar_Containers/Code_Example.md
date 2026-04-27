# Sidecar Containers — Code Examples

All examples are production-quality with detailed comments explaining every decision.

---

## 1. Log Shipper Sidecar

The main app writes to a file. The sidecar tails that file and ships it to a centralized system.
Both containers share a volume — the only coupling between them.

```yaml
# log-shipper-sidecar.yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-log-shipper
  labels:
    app: web-api
spec:
  containers:

  # ── Main Application Container ─────────────────────────────────────────────
  - name: web-api
    image: nginx:1.25
    ports:
    - containerPort: 8080
    resources:
      requests:
        cpu: "200m"
        memory: "256Mi"
      limits:
        cpu: "500m"
        memory: "512Mi"
    volumeMounts:
    - name: log-volume
      mountPath: /var/log/nginx        # nginx writes access.log and error.log here

  # ── Log Shipper Sidecar ───────────────────────────────────────────────────
  # This container has ONE job: read logs and forward them to Elasticsearch.
  # The main app is completely unaware this sidecar exists.
  - name: log-shipper
    image: fluent/fluent-bit:2.2.0    # Fluent Bit: lightweight log forwarder
    resources:
      requests:
        cpu: "50m"                     # Sidecars should be lean — don't steal from the main app
        memory: "32Mi"
      limits:
        cpu: "100m"
        memory: "64Mi"
    volumeMounts:
    - name: log-volume
      mountPath: /var/log/nginx        # Same mount path — reads what nginx writes
    - name: fluent-bit-config
      mountPath: /fluent-bit/etc       # Fluent Bit config telling it where to ship logs
    env:
    - name: ELASTICSEARCH_HOST
      value: "elasticsearch.logging.svc.cluster.local"   # DNS name in logging namespace

  volumes:
  # emptyDir lives for the lifetime of the pod — perfect for inter-container log sharing
  - name: log-volume
    emptyDir: {}

  - name: fluent-bit-config
    configMap:
      name: fluent-bit-config          # Pre-created ConfigMap with Fluent Bit configuration
```

```bash
kubectl apply -f log-shipper-sidecar.yaml

# Watch both containers start in the same pod
kubectl get pod app-with-log-shipper   # READY column shows "2/2" when both containers are ready

# Tail logs from the main app
kubectl logs app-with-log-shipper -c web-api

# Tail logs from the sidecar (shows what it's forwarding)
kubectl logs app-with-log-shipper -c log-shipper -f

# Exec into either container — they share the same network and volume
kubectl exec -it app-with-log-shipper -c web-api -- ls /var/log/nginx/
kubectl exec -it app-with-log-shipper -c log-shipper -- ls /var/log/nginx/
# Both see the same files — shared volume

# Clean up
kubectl delete pod app-with-log-shipper
```

---

## 2. Init Container + Sidecar Pattern

Init containers run and complete BEFORE sidecar or app containers start.
Combine them: init for setup, sidecar for ongoing support.

```yaml
# init-plus-sidecar.yaml
# Pattern: init clones config, app serves it, sidecar reloads config on changes
apiVersion: v1
kind: Pod
metadata:
  name: config-managed-app
spec:
  # ── Init Container: runs ONCE before any other container ────────────────────
  # Job: clone configuration from a Git repo into a shared volume
  initContainers:
  - name: git-clone-config
    image: alpine/git:2.40.1
    command: ["git", "clone", "https://github.com/example/app-config.git", "/config"]
    volumeMounts:
    - name: config-volume
      mountPath: /config               # Writes config files here for the main app to read
    resources:
      requests:
        cpu: "50m"
        memory: "32Mi"
      limits:
        cpu: "100m"
        memory: "64Mi"
    # Init container exits with 0 on success → then main + sidecar start
    # Init container exits non-0 → pod fails to start (retried per restartPolicy)

  containers:
  # ── Main Application ────────────────────────────────────────────────────────
  - name: app
    image: nginx:1.25
    volumeMounts:
    - name: config-volume
      mountPath: /etc/nginx/conf.d     # Reads config written by init container
    resources:
      requests:
        cpu: "200m"
        memory: "256Mi"
      limits:
        cpu: "500m"
        memory: "512Mi"

  # ── Config Reloader Sidecar ─────────────────────────────────────────────────
  # Watches for ConfigMap changes and signals nginx to reload without restart
  - name: config-reloader
    image: jimmidyson/configmap-reload:v0.9.0  # Watches mounted ConfigMap volumes for changes
    args:
    - --volume-dir=/etc/nginx/conf.d   # Directory to watch for changes
    - --webhook-url=http://localhost:8080/-/reload   # URL to call when changes detected
    # localhost works because all containers in a pod share the same network namespace
    resources:
      requests:
        cpu: "10m"                     # Config reloader is very lightweight
        memory: "16Mi"
      limits:
        cpu: "50m"
        memory: "32Mi"
    volumeMounts:
    - name: config-volume
      mountPath: /etc/nginx/conf.d     # Watches the same volume the app reads from

  volumes:
  - name: config-volume
    emptyDir: {}                       # Shared between init container (writes) and both main containers (reads)
```

```bash
kubectl apply -f init-plus-sidecar.yaml

# Watch the init container run first
kubectl get pod config-managed-app --watch
# Init:0/1 → Init:1/1 → PodInitializing → Running

# Confirm init container ran and exited successfully
kubectl describe pod config-managed-app | grep -A 5 "Init Containers:"

# See that app and sidecar are both running (2/2 Ready)
kubectl get pod config-managed-app
# READY: 2/2  STATUS: Running

# Check init container logs (always available even after it exits)
kubectl logs config-managed-app -c git-clone-config
```

---

## 3. Native Sidecar (Kubernetes 1.29+) — Solving the Job Problem

Before 1.29, a sidecar log shipper prevented Job pods from completing because it kept running.
The native sidecar pattern fixes this.

```yaml
# native-sidecar-job.yaml
# The sidecar runs alongside the Job's main container,
# but is automatically terminated when the Job completes.
apiVersion: batch/v1
kind: Job
metadata:
  name: data-processor
spec:
  template:
    spec:
      restartPolicy: Never             # Jobs use Never or OnFailure, not Always

      # ── Native Sidecar (Kubernetes 1.29+) ────────────────────────────────────
      # Defined in initContainers with restartPolicy: Always
      # K8s treats this as a sidecar: starts before app, runs alongside it,
      # restarts if it crashes, and is terminated cleanly when the Job completes
      initContainers:
      - name: log-shipper
        image: fluent/fluent-bit:2.2.0
        restartPolicy: Always          # ← this is what makes it a native sidecar in K8s 1.29+
        resources:
          requests:
            cpu: "50m"
            memory: "32Mi"
          limits:
            cpu: "100m"
            memory: "64Mi"
        volumeMounts:
        - name: log-volume
          mountPath: /var/log/app

      # ── Main Job Container ───────────────────────────────────────────────────
      containers:
      - name: data-processor
        image: python:3.11-slim
        command: ["python", "/app/process.py"]
        # When this container finishes (exit 0), the Job is complete
        # The native sidecar is then gracefully terminated — unlike old-style sidecars
        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
          limits:
            cpu: "2"
            memory: "2Gi"
        volumeMounts:
        - name: log-volume
          mountPath: /var/log/app

      volumes:
      - name: log-volume
        emptyDir: {}
```

```bash
kubectl apply -f native-sidecar-job.yaml

# Watch the job
kubectl get job data-processor --watch
# COMPLETIONS: 0/1 → 1/1 (Job completed successfully)

# With native sidecar: Job reaches Completed status even though sidecar was running
kubectl describe job data-processor | grep -E "Succeeded|Conditions"

# Pre-1.29 behavior (without restartPolicy: Always on initContainer):
# The sidecar would keep running → Job would NEVER reach Completed → stuck forever
kubectl delete job data-processor
```

---

## 4. Ambassador Sidecar — Abstracting External Services

The main app talks to localhost. The ambassador sidecar handles the complexity of reaching external services.

```yaml
# ambassador-sidecar.yaml
# App talks to redis on localhost:6380.
# Ambassador proxies to the actual Redis cluster, handling auth and TLS.
apiVersion: v1
kind: Pod
metadata:
  name: app-with-ambassador
spec:
  containers:

  # ── Main Application ─────────────────────────────────────────────────────
  # The app just connects to localhost:6380 — it has NO knowledge of where Redis lives
  - name: app
    image: myapp:v1
    env:
    - name: REDIS_URL
      value: "redis://localhost:6380"  # Talks to the ambassador sidecar, not Redis directly
    resources:
      requests:
        cpu: "200m"
        memory: "256Mi"
      limits:
        cpu: "500m"
        memory: "512Mi"

  # ── Ambassador Sidecar ────────────────────────────────────────────────────
  # Listens on localhost:6380. Proxies to the real Redis cluster in another namespace.
  # Handles: auth, TLS, connection pooling, retry logic — invisible to the main app.
  - name: redis-ambassador
    image: haproxytech/haproxy-alpine:2.8   # HAProxy as the ambassador proxy
    ports:
    - containerPort: 6380                   # Listens here — same as what the app connects to
    # localhost:6380 → actual Redis at redis-cluster.data.svc.cluster.local:6379
    resources:
      requests:
        cpu: "50m"
        memory: "32Mi"
      limits:
        cpu: "100m"
        memory: "64Mi"
    volumeMounts:
    - name: haproxy-config
      mountPath: /usr/local/etc/haproxy

  volumes:
  - name: haproxy-config
    configMap:
      name: redis-ambassador-config    # HAProxy config: frontend localhost:6380, backend redis-cluster:6379
```

```bash
kubectl apply -f ambassador-sidecar.yaml

# Both containers share the same localhost — the app can reach the ambassador on 127.0.0.1:6380
kubectl exec -it app-with-ambassador -c app -- netstat -tlnp
# Should show ports from BOTH containers: app's port AND ambassador's 6380

# Test connectivity through the ambassador
kubectl exec -it app-with-ambassador -c app -- redis-cli -h localhost -p 6380 ping
# PONG — ambassador proxied the request to the real Redis cluster

# The ambassador logs show it's proxying
kubectl logs app-with-ambassador -c redis-ambassador

kubectl delete pod app-with-ambassador
```

---

## 5. Adapter Sidecar — Normalizing Legacy Output

```yaml
# adapter-sidecar.yaml
# Legacy app writes logs in a proprietary format.
# Adapter sidecar transforms them to JSON for the logging infrastructure.
apiVersion: v1
kind: Pod
metadata:
  name: legacy-app-with-adapter
spec:
  containers:

  # ── Legacy Application ───────────────────────────────────────────────────
  # Writes logs in old-school key=value format: time=12:00 level=ERROR msg="disk full"
  - name: legacy-app
    image: legacy-app:v3               # Old app that can't be modified to output JSON
    command: ["/bin/sh", "-c"]
    args:
    - |
      while true; do
        echo "time=$(date +%H:%M:%S) level=INFO msg=\"processing request\" req_id=abc123"
        echo "time=$(date +%H:%M:%S) level=ERROR msg=\"db timeout\" req_id=def456 latency=5001"
        sleep 2
      done >> /var/log/app/app.log     # Writes to file, NOT stdout
    volumeMounts:
    - name: log-volume
      mountPath: /var/log/app
    resources:
      requests:
        cpu: "100m"
        memory: "128Mi"
      limits:
        cpu: "200m"
        memory: "256Mi"

  # ── Adapter Sidecar ───────────────────────────────────────────────────────
  # Reads the legacy log format, transforms to JSON, writes to stdout.
  # The logging infrastructure (Fluentd, Loki) reads stdout — standard format.
  - name: log-adapter
    image: python:3.11-alpine
    command: ["/bin/sh", "-c"]
    args:
    - |
      import sys, re, json
      # Read legacy log lines and transform to JSON
      for line in open("/var/log/app/app.log"):
          parts = dict(re.findall(r'(\w+)=(\S+)', line.strip()))
          print(json.dumps({"timestamp": parts.get("time"), "level": parts.get("level"),
                            "message": parts.get("msg","").strip('"')}), flush=True)
    volumeMounts:
    - name: log-volume
      mountPath: /var/log/app          # Reads the same file the legacy app writes
    resources:
      requests:
        cpu: "25m"                     # Very lightweight transformation
        memory: "32Mi"
      limits:
        cpu: "50m"
        memory: "64Mi"

  volumes:
  - name: log-volume
    emptyDir: {}
```

```bash
kubectl apply -f adapter-sidecar.yaml

# Legacy app writes key=value format to a file
kubectl logs legacy-app-with-adapter -c legacy-app
# (no output — it writes to a file, not stdout)

# Adapter reads the file and outputs JSON to stdout
kubectl logs legacy-app-with-adapter -c log-adapter -f
# {"timestamp": "12:00:01", "level": "INFO", "message": "processing request"}
# {"timestamp": "12:00:01", "level": "ERROR", "message": "db timeout"}

# The logging infrastructure sees clean JSON from the adapter's stdout
# The legacy app required ZERO code changes
kubectl delete pod legacy-app-with-adapter
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

⬅️ **Prev:** [Deployment Strategies](../15_Deployment_Strategies/Code_Example.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Jobs and CronJobs](../17_Jobs_and_CronJobs/Code_Example.md)
🏠 **[Home](../../README.md)**
