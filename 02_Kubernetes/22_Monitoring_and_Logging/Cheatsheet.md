# Module 22 — Monitoring and Logging Cheatsheet

## The Four Golden Signals

| Signal | What to measure | Example |
|---|---|---|
| Latency | Request duration (p50, p95, p99) | API response time |
| Traffic | Request rate | Requests per second |
| Errors | Failure rate | HTTP 5xx / total |
| Saturation | Resource usage | CPU%, memory%, queue depth |

---

## Prometheus Commands

```bash
# Install kube-prometheus-stack (recommended)
helm repo add prometheus-community \
  https://prometheus-community.github.io/helm-charts
helm repo update
helm install kube-prometheus-stack \
  prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace

# Port-forward to access Prometheus UI
kubectl port-forward svc/kube-prometheus-stack-prometheus \
  9090:9090 -n monitoring

# Port-forward to access Grafana
kubectl port-forward svc/kube-prometheus-stack-grafana \
  3000:80 -n monitoring

# Check Prometheus targets (is it scraping your app?)
# Visit http://localhost:9090/targets

# List Prometheus rules
kubectl get prometheusrules -n monitoring

# List ServiceMonitors
kubectl get servicemonitors -A
```

---

## ServiceMonitor CRD

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: myapp-monitor
  namespace: monitoring
  labels:
    release: kube-prometheus-stack   # must match Prometheus selector
spec:
  namespaceSelector:
    matchNames:
    - production
  selector:
    matchLabels:
      app: myapp
  endpoints:
  - port: metrics          # port name in Service
    path: /metrics
    interval: 15s
```

---

## PodMonitor CRD

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: myapp-pod-monitor
  namespace: monitoring
spec:
  namespaceSelector:
    matchNames:
    - production
  selector:
    matchLabels:
      app: myapp
  podMetricsEndpoints:
  - port: metrics
    interval: 30s
```

---

## PrometheusRule — Alert Rules

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: myapp-alerts
  namespace: monitoring
  labels:
    release: kube-prometheus-stack
spec:
  groups:
  - name: myapp
    rules:
    - alert: HighErrorRate
      expr: |
        rate(http_requests_total{status=~"5.."}[5m])
        / rate(http_requests_total[5m]) > 0.05
      for: 2m
      labels:
        severity: warning
      annotations:
        summary: "Error rate > 5% on {{ $labels.service }}"
    - alert: PodCrashLooping
      expr: rate(kube_pod_container_status_restarts_total[15m]) > 0
      for: 5m
      labels:
        severity: critical
```

---

## Common PromQL Queries

```promql
# CPU usage per pod
rate(container_cpu_usage_seconds_total{namespace="production"}[5m])

# Memory usage per pod
container_memory_working_set_bytes{namespace="production"}

# HTTP request rate
rate(http_requests_total[5m])

# Error rate %
rate(http_requests_total{code=~"5.."}[5m])
/ rate(http_requests_total[5m]) * 100

# 99th percentile latency
histogram_quantile(0.99,
  rate(http_request_duration_seconds_bucket[5m]))

# Pod restart count
increase(kube_pod_container_status_restarts_total[1h])

# Node CPU utilization
1 - avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) by (node)
```

---

## kubectl Log Commands

```bash
# Follow logs
kubectl logs -f <pod> -n <ns>

# Previous container logs (after crash)
kubectl logs --previous <pod> -n <ns>

# All containers in pod
kubectl logs <pod> --all-containers=true -n <ns>

# Last N lines
kubectl logs --tail=100 <pod> -n <ns>

# Logs since time duration
kubectl logs --since=30m <pod> -n <ns>
kubectl logs --since-time="2024-03-01T00:00:00Z" <pod> -n <ns>

# Logs from all pods with label
kubectl logs -l app=myapp -n <ns> --all-containers=true

# Multi-container: specific container
kubectl logs <pod> -c <container-name> -n <ns>
```

---

## Loki + Grafana Stack (Helm)

```bash
# Install Loki stack
helm repo add grafana https://grafana.github.io/helm-charts
helm install loki-stack grafana/loki-stack \
  --namespace monitoring \
  --set grafana.enabled=true \
  --set promtail.enabled=true
```

---

## LogQL (Loki Query Language)

```logql
# Filter by namespace and app
{namespace="production", app="myapp"}

# Find error lines
{namespace="production"} |= "ERROR"

# Filter then parse
{namespace="production", app="myapp"}
  | json
  | level="error"

# Log rate (for graphs)
rate({namespace="production", app="myapp"}[5m])

# Count errors by pod
sum by (pod) (
  count_over_time({namespace="production"} |= "ERROR" [5m])
)
```

---

## Key Metrics Components

| Component | Role |
|---|---|
| Node Exporter | CPU, memory, disk, network per node |
| kube-state-metrics | Deployment replicas, pod phases, job status |
| cAdvisor | Container CPU/memory (built into kubelet) |
| Prometheus | Scrape + store time-series |
| Alertmanager | Route alerts to Slack, PagerDuty, email |
| Grafana | Dashboards and visualization |

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Monitoring and Logging Theory](./Theory.md) |
| Interview Q&A | [Monitoring and Logging Interview Q&A](./Interview_QA.md) |
| Next Module | [23 — Security](../23_Security/Theory.md) |
