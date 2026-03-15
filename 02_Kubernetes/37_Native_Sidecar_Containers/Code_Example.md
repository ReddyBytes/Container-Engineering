# Module 37 — Native Sidecar Containers Code Examples

## Example 1: Native Sidecar for Log Shipping (Fluent Bit)

```yaml
# native-sidecar-logging.yaml
# A web application with a Fluent Bit native sidecar for log shipping.
# The app writes logs to a shared volume. Fluent Bit reads and ships them.
# Fluent Bit starts BEFORE the app and stops AFTER the app.

---
# ConfigMap for Fluent Bit configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
  namespace: production
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush         1
        Log_Level     info
        Daemon        off

    [INPUT]
        Name          tail
        Path          /var/log/app/*.log
        Tag           app.*
        Refresh_Interval  5
        Mem_Buf_Limit 5MB
        Skip_Long_Lines On

    [FILTER]
        Name          kubernetes
        Match         app.*
        Merge_Log     On
        Keep_Log      Off

    [OUTPUT]
        Name          es
        Match         app.*
        Host          elasticsearch.logging.svc.cluster.local
        Port          9200
        Index         production-logs
        Type          _doc
---
# The application deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      # ---------------------------------------------------------------
      # NATIVE SIDECAR: runs before app, alongside app, stops after app
      # ---------------------------------------------------------------
      initContainers:
      - name: fluent-bit
        image: fluent/fluent-bit:3.0
        restartPolicy: Always          # <-- makes this a native sidecar
        resources:
          requests:
            memory: "64Mi"
            cpu: "50m"
          limits:
            memory: "128Mi"
            cpu: "100m"
        volumeMounts:
        - name: app-logs
          mountPath: /var/log/app      # reads logs the app writes here
        - name: fluent-bit-config
          mountPath: /fluent-bit/etc
        # Readiness probe: app won't start until Fluent Bit is ready
        readinessProbe:
          exec:
            command:
            - /bin/sh
            - -c
            - "fluent-bit --dry-run -c /fluent-bit/etc/fluent-bit.conf && exit 0"
          initialDelaySeconds: 5
          periodSeconds: 10
          failureThreshold: 3

      # ---------------------------------------------------------------
      # MAIN APPLICATION
      # ---------------------------------------------------------------
      containers:
      - name: web-app
        image: mycompany/web-app:v2.1.0
        ports:
        - containerPort: 8080
        resources:
          requests:
            memory: "256Mi"
            cpu: "200m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        env:
        - name: LOG_DIR
          value: "/var/log/app"
        - name: LOG_FILE
          value: "/var/log/app/app.log"
        volumeMounts:
        - name: app-logs
          mountPath: /var/log/app      # writes logs here

      volumes:
      - name: app-logs
        emptyDir: {}                   # shared between app and fluent-bit
      - name: fluent-bit-config
        configMap:
          name: fluent-bit-config
```

```bash
# Deploy
kubectl apply -f native-sidecar-logging.yaml

# Verify both containers are running
kubectl get pods -n production
# NAME                       READY   STATUS    RESTARTS
# web-app-xxx-yyy            2/2     Running   0
# Both the app container and the fluent-bit sidecar are counted

# Check the init containers (native sidecars show here)
kubectl describe pod web-app-xxx-yyy -n production | grep -A 20 "Init Containers"

# Verify startup order: fluent-bit started before web-app
kubectl get events -n production --sort-by='.lastTimestamp' | grep web-app
```

---

## Example 2: Native Sidecar in a Job (Correct Job Completion)

```yaml
# native-sidecar-job.yaml
# A batch data processing Job with a log-shipping sidecar.
# Old problem: Job would never complete because sidecar kept running.
# With native sidecar: Job completes when main container exits.
# Sidecar is then gracefully terminated (ships last logs, then exits).

apiVersion: batch/v1
kind: Job
metadata:
  name: data-export-job
  labels:
    app: data-export
spec:
  completions: 1
  backoffLimit: 2
  template:
    metadata:
      labels:
        app: data-export
    spec:
      restartPolicy: Never          # Job: don't restart main containers on failure

      initContainers:
      # ---------------------------------------------------------------
      # NATIVE SIDECAR: log shipper
      # Note: Job completion is determined ONLY by main containers.
      # When main container exits 0, Job = Complete.
      # K8s then sends SIGTERM to this sidecar for graceful shutdown.
      # ---------------------------------------------------------------
      - name: log-shipper
        image: fluent/fluent-bit:3.0
        restartPolicy: Always         # native sidecar — does NOT block Job completion
        resources:
          requests:
            memory: "32Mi"
            cpu: "25m"
          limits:
            memory: "64Mi"
            cpu: "50m"
        volumeMounts:
        - name: job-logs
          mountPath: /var/log/job
        - name: fluent-bit-config
          mountPath: /fluent-bit/etc
        env:
        - name: FLUSH_INTERVAL
          value: "1"                  # flush frequently to not miss logs

      containers:
      # ---------------------------------------------------------------
      # MAIN JOB CONTAINER: does the actual work
      # ---------------------------------------------------------------
      - name: data-exporter
        image: mycompany/data-exporter:v1.5
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        - name: OUTPUT_BUCKET
          value: "s3://my-exports-bucket/data/"
        - name: LOG_FILE
          value: "/var/log/job/export.log"
        volumeMounts:
        - name: job-logs
          mountPath: /var/log/job

      volumes:
      - name: job-logs
        emptyDir: {}
      - name: fluent-bit-config
        configMap:
          name: fluent-bit-job-config
```

```bash
# Run the job
kubectl apply -f native-sidecar-job.yaml

# Watch job completion (should complete correctly now)
kubectl get job data-export-job -w
# NAME               COMPLETIONS   DURATION   AGE
# data-export-job    0/1           5s         5s
# data-export-job    1/1           45s        45s   <-- Job completes!

# Without native sidecar (old problem — job would NEVER show 1/1):
# data-export-job    0/1           45s        45s   <-- hangs here forever

# Check job logs
kubectl logs job/data-export-job -c data-exporter
kubectl logs job/data-export-job -c log-shipper
```

---

## Example 3: Native Sidecar with Startup Ordering (Envoy Proxy)

```yaml
# native-sidecar-envoy.yaml
# An application with Envoy proxy as a native sidecar.
# The app only starts after Envoy's readiness probe passes.
# This guarantees ALL traffic goes through the proxy from the first connection.

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: envoy-config
data:
  envoy.yaml: |
    static_resources:
      listeners:
      - name: app_listener
        address:
          socket_address:
            address: 0.0.0.0
            port_value: 10000
        filter_chains:
        - filters:
          - name: envoy.filters.network.http_connection_manager
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
              stat_prefix: ingress_http
              route_config:
                name: local_route
                virtual_hosts:
                - name: local_service
                  domains: ["*"]
                  routes:
                  - match:
                      prefix: "/"
                    route:
                      cluster: app_cluster
              http_filters:
              - name: envoy.filters.http.router
                typed_config:
                  "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
      clusters:
      - name: app_cluster
        connect_timeout: 0.25s
        type: STATIC
        load_assignment:
          cluster_name: app_cluster
          endpoints:
          - lb_endpoints:
            - endpoint:
                address:
                  socket_address:
                    address: 127.0.0.1
                    port_value: 8080    # the app's actual port
    admin:
      address:
        socket_address:
          address: 0.0.0.0
          port_value: 9901              # admin/readiness port
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: service-with-proxy
spec:
  replicas: 2
  selector:
    matchLabels:
      app: service-with-proxy
  template:
    metadata:
      labels:
        app: service-with-proxy
    spec:
      initContainers:
      # ---------------------------------------------------------------
      # NATIVE SIDECAR: Envoy proxy
      # App container will NOT start until this readiness probe passes.
      # ---------------------------------------------------------------
      - name: envoy-proxy
        image: envoyproxy/envoy:v1.28-latest
        restartPolicy: Always         # native sidecar
        args:
        - "--config-path"
        - "/etc/envoy/envoy.yaml"
        ports:
        - containerPort: 10000        # proxy ingress port
        - containerPort: 9901         # admin port
        volumeMounts:
        - name: envoy-config
          mountPath: /etc/envoy
        resources:
          requests:
            memory: "64Mi"
            cpu: "50m"
          limits:
            memory: "256Mi"
            cpu: "200m"
        # App will NOT start until Envoy's admin endpoint responds 200
        readinessProbe:
          httpGet:
            path: /ready
            port: 9901
          initialDelaySeconds: 3
          periodSeconds: 5
          failureThreshold: 10
        livenessProbe:
          httpGet:
            path: /ready
            port: 9901
          periodSeconds: 30

      containers:
      # ---------------------------------------------------------------
      # MAIN APP: only starts after envoy-proxy is Ready
      # ---------------------------------------------------------------
      - name: app
        image: mycompany/app:v1
        ports:
        - containerPort: 8080         # only accessible locally through Envoy
        env:
        - name: LISTEN_ADDR
          value: "127.0.0.1:8080"     # bind to loopback only — Envoy handles external
        resources:
          requests:
            memory: "256Mi"
            cpu: "200m"
          limits:
            memory: "512Mi"
            cpu: "500m"

      volumes:
      - name: envoy-config
        configMap:
          name: envoy-config
```

---

## Example 4: Before/After — Old Workaround Pattern vs Native Sidecar

```yaml
# ================================================================
# BEFORE: The old workaround (fragile)
# ================================================================
# bad-sidecar-pattern.yaml — DO NOT USE, shown for comparison only

apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-old-style      # anti-pattern: sidecar as regular container
spec:
  template:
    spec:
      containers:
      # Problem 1: no ordering — app might start before fluentd is ready
      - name: app
        image: myapp:v1

      # Problem 2: if this exits early, logs are lost
      # Problem 3: in a Job, this blocks Job completion forever
      - name: fluentd
        image: fluent/fluentd:v1.17
        # No restartPolicy: Always here — if it crashes, no restart by default
        # (pod restartPolicy applies, but it's for the whole pod)
---
# ================================================================
# AFTER: Native sidecar (correct, K8s 1.29+)
# ================================================================
# good-sidecar-pattern.yaml

apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-native-sidecar    # correct: native sidecar with guaranteed lifecycle
spec:
  replicas: 2
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      initContainers:
      # -------------------------------------------------------
      # CHANGE 1: moved from 'containers' to 'initContainers'
      # CHANGE 2: added 'restartPolicy: Always'
      # RESULT: starts before app, runs alongside, stops after
      # -------------------------------------------------------
      - name: fluentd
        image: fluent/fluentd:v1.17
        restartPolicy: Always        # <-- THE KEY CHANGE
        resources:
          requests:
            memory: "64Mi"
            cpu: "50m"
          limits:
            memory: "200Mi"
            cpu: "100m"
        volumeMounts:
        - name: logs
          mountPath: /var/log/app
        # Readiness probe: app waits for fluentd to be ready
        readinessProbe:
          exec:
            command: ["ruby", "-e", "require 'fluent/version'; puts Fluent::VERSION"]
          initialDelaySeconds: 10
          periodSeconds: 15

      containers:
      # App starts AFTER fluentd is Ready (readiness probe passed)
      - name: app
        image: myapp:v1
        resources:
          requests:
            memory: "256Mi"
            cpu: "200m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        volumeMounts:
        - name: logs
          mountPath: /var/log/app

      volumes:
      - name: logs
        emptyDir: {}
```

```bash
# Compare the startup events between old and new patterns

# Old pattern: notice app and fluentd start at the same time
kubectl get events --sort-by='.lastTimestamp' | grep app-old-style
# 0s   Normal   Created   pod/app-old-style-xxx   Created container app
# 0s   Normal   Created   pod/app-old-style-xxx   Created container fluentd
# Race condition! Which started first?

# New pattern: notice fluentd starts first, then app
kubectl get events --sort-by='.lastTimestamp' | grep app-native-sidecar
# 0s   Normal   Created   pod/app-native-sidecar-xxx   Created container fluentd
# 8s   Normal   Created   pod/app-native-sidecar-xxx   Created container app
# Ordered! fluentd was ready before app started.

# Verify both containers are listed as Running
kubectl get pod -l app=myapp
# NAME                           READY   STATUS    RESTARTS
# app-native-sidecar-xxx-yyy     2/2     Running   0
#                                ^ 2 containers: app + fluentd sidecar
```

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Native Sidecar Containers Theory](./Theory.md) |
| Cheatsheet | [Native Sidecar Containers Cheatsheet](./Cheatsheet.md) |
| Interview Q&A | [Native Sidecar Containers Interview Q&A](./Interview_QA.md) |
| Previous Module | [36 — ValidatingAdmissionPolicy](../36_ValidatingAdmissionPolicy/Theory.md) |
