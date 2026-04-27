# Monitoring and Logging — Code Examples

All examples are production-quality with detailed comments explaining every decision.

---

## 1. Deploy kube-prometheus-stack — Full Metrics Stack in One Command

```bash
# Install the kube-prometheus-stack Helm chart
# This deploys: Prometheus, Grafana, Alertmanager, Node Exporter, kube-state-metrics
# It is the recommended starting point for Kubernetes monitoring

# Add the Prometheus community Helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install in a dedicated monitoring namespace
# --create-namespace creates the namespace if it doesn't exist
helm install kube-prometheus-stack \
  prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set prometheus.prometheusSpec.retention=15d \         # ← keep 15 days of metrics (default is 10d)
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=50Gi \
  --set grafana.adminPassword=changeme-in-production      # ← set a real password in production

# Verify all pods come up healthy
kubectl get pods -n monitoring --watch

# Access Grafana at http://localhost:3000 (default login: admin / changeme-in-production)
kubectl port-forward -n monitoring \
  svc/kube-prometheus-stack-grafana \
  3000:80

# Access Prometheus at http://localhost:9090
kubectl port-forward -n monitoring \
  svc/kube-prometheus-stack-prometheus \
  9090:9090

# Access Alertmanager at http://localhost:9093
kubectl port-forward -n monitoring \
  svc/kube-prometheus-stack-alertmanager \
  9093:9093
```

```bash
# Verify metrics are flowing — run PromQL queries in the Prometheus UI

# Total number of running pods cluster-wide
# kube_pod_status_phase{phase="Running"}

# CPU usage by pod (as a fraction of the CPU limit)
# rate(container_cpu_usage_seconds_total[5m])

# Memory usage by namespace
# sum by(namespace) (container_memory_working_set_bytes{container!=""})

# Check that Node Exporter is scraping all nodes
kubectl get pods -n monitoring -l app.kubernetes.io/name=node-exporter
```

---

## 2. ServiceMonitor — Tell Prometheus to Scrape Your Application

```yaml
# app-with-metrics.yaml
# A deployment that exposes a /metrics endpoint for Prometheus to scrape
# The app uses the prometheus/client_python or similar library to expose metrics

---
# Deployment: expose metrics on port 8080 at /metrics
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-api
  namespace: production
  labels:
    app: my-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-api
  template:
    metadata:
      labels:
        app: my-api
        version: "1.0"
    spec:
      serviceAccountName: my-api-sa
      automountServiceAccountToken: false
      containers:
      - name: api
        image: my-api:1.0
        ports:
        - name: http
          containerPort: 8080
        - name: metrics                  # ← name the metrics port so ServiceMonitor can reference it
          containerPort: 9090
        resources:
          requests:
            cpu: "200m"
            memory: "256Mi"
          limits:
            cpu: "1"
            memory: "512Mi"

---
# Service: routes traffic to pods; ServiceMonitor will select this Service
apiVersion: v1
kind: Service
metadata:
  name: my-api
  namespace: production
  labels:
    app: my-api                          # ← ServiceMonitor selector must match this label
spec:
  selector:
    app: my-api
  ports:
  - name: http
    port: 80
    targetPort: 8080
  - name: metrics                        # ← named port; ServiceMonitor references by name
    port: 9090
    targetPort: 9090

---
# ServiceMonitor: instructs Prometheus Operator to scrape the my-api Service
# Must be in the same namespace as the app, or use namespace selectors in Prometheus config
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: my-api-monitor
  namespace: production
  labels:
    release: kube-prometheus-stack       # ← this label must match the Prometheus Operator's selector
spec:
  selector:
    matchLabels:
      app: my-api                        # ← selects the Service with this label
  endpoints:
  - port: metrics                        # ← must match the named port in the Service
    interval: 15s                        # ← scrape every 15 seconds
    path: /metrics                       # ← the HTTP path to scrape
    scheme: http
```

```bash
kubectl apply -f app-with-metrics.yaml

# Confirm the ServiceMonitor was picked up by Prometheus
# In Prometheus UI: Status → Targets → look for "production/my-api-monitor"
kubectl port-forward svc/kube-prometheus-stack-prometheus 9090:9090 -n monitoring &
# Open http://localhost:9090/targets

# Query a metric from your app in PromQL
# rate(http_requests_total{job="my-api"}[5m])
```

---

## 3. Prometheus Alert Rules — Fire When Error Rate Is High

```yaml
# alert-rules.yaml
# PrometheusRule CRD — defines alerting rules that the Prometheus Operator picks up
# Alerts fire to Alertmanager, which routes them to Slack/PagerDuty

apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: my-api-alerts
  namespace: production
  labels:
    release: kube-prometheus-stack       # ← must match Prometheus Operator's ruleSelector labels
spec:
  groups:
  - name: my-api.rules
    rules:

    # Alert when the HTTP error rate exceeds 5% over a 5-minute window
    - alert: HighErrorRate
      expr: |
        rate(http_requests_total{job="my-api", status=~"5.."}[5m])
        /
        rate(http_requests_total{job="my-api"}[5m])
        > 0.05                           # ← 5% error rate threshold
      for: 2m                            # ← must be true for 2 consecutive minutes before firing
      labels:
        severity: warning
        team: backend
      annotations:
        summary: "High error rate on {{ $labels.pod }}"
        description: "Error rate is {{ $value | humanizePercentage }} on pod {{ $labels.pod }}"

    # Alert when a pod has restarted more than 5 times in the last hour
    - alert: PodRestartingTooOften
      expr: |
        increase(kube_pod_container_status_restarts_total{
          namespace="production"
        }[1h]) > 5                       # ← more than 5 restarts in 60 minutes
      for: 0m                            # ← fire immediately (no stabilization window)
      labels:
        severity: critical
      annotations:
        summary: "Pod {{ $labels.pod }} is crash-looping"
        description: "Container {{ $labels.container }} has restarted {{ $value }} times in the last hour"

    # Alert when p99 latency exceeds 500ms
    - alert: HighLatency
      expr: |
        histogram_quantile(0.99,
          rate(http_request_duration_seconds_bucket{job="my-api"}[5m])
        ) > 0.5                          # ← p99 latency > 500ms
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High p99 latency on my-api"
        description: "p99 latency is {{ $value | humanizeDuration }}"
```

```bash
kubectl apply -f alert-rules.yaml

# Verify the rule was loaded by Prometheus
# In Prometheus UI: Alerts tab should show "HighErrorRate", "PodRestartingTooOften", "HighLatency"

# Check the rule via kubectl
kubectl get prometheusrule my-api-alerts -n production

# Manually trigger an alert by generating errors (for testing)
kubectl run error-generator \
  --image=busybox:1.36 -n production \
  --restart=Never \
  -- /bin/sh -c "while true; do wget -q http://my-api/nonexistent-path 2>&1; done"
```

---

## 4. Loki + Promtail — Centralized Log Aggregation

```bash
# Install the Loki stack: Loki (log storage) + Promtail (log collector DaemonSet)
# Grafana is already installed via kube-prometheus-stack — we just add Loki as a datasource

helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Install Loki (single-binary mode for development; use distributed mode for production)
helm install loki \
  grafana/loki-stack \
  --namespace monitoring \
  --set promtail.enabled=true \          # ← install Promtail DaemonSet on every node
  --set grafana.enabled=false \          # ← use the Grafana from kube-prometheus-stack
  --set loki.persistence.enabled=true \
  --set loki.persistence.size=20Gi

# Verify Promtail is running on every node (one pod per node)
kubectl get pods -n monitoring -l app=promtail -o wide

# Add Loki as a datasource in Grafana:
# Grafana UI → Configuration → Data Sources → Add data source → Loki
# URL: http://loki:3100
```

```yaml
# promtail-extra-config.yaml
# Extend Promtail to add custom labels and drop noisy logs
# Apply as a ConfigMap and reference it in the Promtail Helm values

apiVersion: v1
kind: ConfigMap
metadata:
  name: promtail-extra-scrape
  namespace: monitoring
data:
  extra-scrape.yaml: |
    scrape_configs:
    - job_name: kubernetes-pods-custom
      kubernetes_sd_configs:
      - role: pod
      relabel_configs:
      # Add the pod's namespace as a label on every log entry
      - source_labels: [__meta_kubernetes_namespace]
        target_label: namespace
      # Add the app label from pod labels
      - source_labels: [__meta_kubernetes_pod_label_app]
        target_label: app
      # Drop health-check noise from the ingress controller
      pipeline_stages:
      - drop:
          expression: ".*GET /healthz.*"   # ← discard health check log lines
```

```bash
# Query logs in Grafana Explore tab using LogQL

# Show all error logs from the my-api app in production
# {namespace="production", app="my-api"} |= "ERROR"

# Show logs from the last 15 minutes with structured JSON parsing
# {namespace="production", app="my-api"} | json | level="error"

# Count error log lines per minute
# rate({namespace="production", app="my-api"} |= "ERROR" [1m])

# Show logs from a specific pod
# {namespace="production", pod="my-api-7d4f9b-xxx"}
```

---

## 5. kubectl Log Commands — Day-to-Day Debugging

```bash
# --- Basic log access ---

# Stream logs from a running pod
kubectl logs -f my-api-7d4f9b-xxx -n production

# Show the last 200 lines (useful for large log volumes)
kubectl logs --tail=200 my-api-7d4f9b-xxx -n production

# Logs from the previous container (after a crash/restart)
kubectl logs --previous my-api-7d4f9b-xxx -n production
# ← invaluable for diagnosing OOMKills and CrashLoopBackOffs

# Logs from a specific container in a multi-container pod
kubectl logs my-api-7d4f9b-xxx -c api -n production

# Logs from all containers in the pod simultaneously
kubectl logs --all-containers=true my-api-7d4f9b-xxx -n production

# --- Aggregate logs across multiple pods ---

# Stream logs from ALL pods matching a label selector
kubectl logs -f -l app=my-api -n production --all-containers=true

# Stream logs from the most recent pod (useful after a rollout)
kubectl logs -f \
  -l app=my-api \
  -n production \
  --max-log-requests=10                  # ← limit concurrent log streams for large deployments

# --- Time-filtered logs ---

# Logs from the last hour
kubectl logs my-api-7d4f9b-xxx -n production --since=1h

# Logs since a specific timestamp
kubectl logs my-api-7d4f9b-xxx -n production \
  --since-time="2024-01-15T10:00:00Z"

# --- Inspect pod events (not logs, but essential for debugging) ---

# Show all events for a pod (scheduling failures, OOMKills, probe failures)
kubectl describe pod my-api-7d4f9b-xxx -n production | tail -30

# Show all events in a namespace sorted by time
kubectl get events -n production --sort-by='.lastTimestamp'

# Watch events in real time
kubectl get events -n production --watch

# Filter for warning events only
kubectl get events -n production --field-selector type=Warning
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

⬅️ **Prev:** [Service Accounts](../21_Service_Accounts/Code_Example.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Security](../23_Security/Code_Example.md)
🏠 **[Home](../../README.md)**
