# Module 22 — Monitoring and Logging Interview Q&A

---

## Q1: What are the four golden signals and why are they important?

**Answer:**

The four golden signals (from Google SRE) are the most critical metrics for any production service:

1. **Latency** — how long requests take (measure p50, p95, p99 separately — averages hide outliers)
2. **Traffic** — volume of demand (requests/second, events/second)
3. **Errors** — rate of failed requests (HTTP 5xx, timeouts, exceptions)
4. **Saturation** — how full the resource is (CPU%, memory%, disk%, queue depth)

They matter because if all four look healthy, users are generally having a good experience. They give you a comprehensive picture without drowning in hundreds of metrics. Start alert design here before adding custom metrics.

---

## Q2: How does Prometheus collect metrics from applications?

**Answer:**

Prometheus uses a **pull model** — it actively scrapes HTTP endpoints on a configurable interval (typically every 15 seconds). Your application (or an exporter) exposes a `/metrics` endpoint that returns data in Prometheus text format.

Key components:
- **Targets**: the list of endpoints Prometheus scrapes (configured via static config or service discovery)
- **Service Discovery**: in Kubernetes, Prometheus auto-discovers pods and services via the K8s API
- **Prometheus Operator**: adds ServiceMonitor and PodMonitor CRDs to configure scraping declaratively

Unlike push-based systems, the pull model means Prometheus controls the scrape rate, and targets don't need to know about Prometheus.

---

## Q3: What is the Prometheus Operator and what problems does it solve?

**Answer:**

Without the Prometheus Operator, you must manually edit Prometheus configuration files when services are added or removed — impossible to manage at scale in Kubernetes where pods constantly start and stop.

The Prometheus Operator introduces CRDs:
- **ServiceMonitor**: tells Prometheus which Services to scrape and how
- **PodMonitor**: direct pod scraping without a Service
- **PrometheusRule**: alert rules as Kubernetes objects
- **Alertmanager**: configuration as Kubernetes objects

Now your scrape configuration lives in the cluster as YAML manifests — it's version-controlled, reviewed, and auto-applied without restarting Prometheus.

---

## Q4: What is the difference between the EFK stack and Loki for logging?

**Answer:**

| Aspect | EFK (Elasticsearch + Fluentd/Fluent Bit + Kibana) | Loki + Promtail + Grafana |
|---|---|---|
| Storage | Full-text indexed (every word indexed) | Label-indexed only (labels, not content) |
| Search power | Very powerful, any field query | Good for known patterns, slower for arbitrary content search |
| Resource cost | High (Elasticsearch is heavy) | Low (Loki is designed for cost efficiency) |
| Query language | KQL (Kibana Query Language) | LogQL (similar to PromQL) |
| Integration | Separate stack | Same Grafana as metrics — unified dashboards |
| Best for | Large teams, complex log analysis | Teams already using Prometheus/Grafana |

For most Kubernetes teams, Loki is the practical choice due to lower operational cost and Grafana integration.

---

## Q5: Why should applications write logs to stdout/stderr instead of log files?

**Answer:**

Kubernetes is designed around the stdout/stderr convention:

1. **Kubelet captures it automatically** — logs go to `/var/log/pods/` on the node
2. **`kubectl logs` works** — you can see logs without exec-ing into the container
3. **Log collectors work automatically** — Fluentd/Fluent Bit/Promtail run as DaemonSets and read all node log files
4. **Ephemeral containers** — if a container crashes, a file inside it is gone; stdout is already captured
5. **No log rotation complexity** — Kubernetes handles rotation of stdout logs; file-based logs inside containers can fill up the container filesystem

Writing to files requires either mounting a volume for logs (complex) or handling rotation yourself. Stdout is simpler and the industry standard for containers.

---

## Q6: How do you view logs from a pod that keeps crashing (CrashLoopBackOff)?

**Answer:**

```bash
kubectl logs --previous <pod-name> -n <namespace>
```

The `--previous` flag shows logs from the previous (terminated) container instance, not the currently running (or waiting) one. This is essential for CrashLoopBackOff debugging where the container exits almost immediately.

Also useful:
- `kubectl describe pod <pod>` — shows events including exit codes and OOMKilled status
- `kubectl get events -n <namespace>` — cluster events for context
- Check if the exit code is `137` (OOMKilled) or `1` (application error)

---

## Q7: What is the difference between Prometheus and Grafana?

**Answer:**

- **Prometheus**: collects and stores metrics (it is a database + scraping engine + alerting rules engine). It has a basic UI but is not designed for dashboards.
- **Grafana**: visualizes data from many sources (Prometheus, Loki, CloudWatch, etc.). It doesn't store any data itself — it queries Prometheus via PromQL and renders the results as graphs and dashboards.

Think of Prometheus as the database and Grafana as the dashboard application. They work together: Prometheus stores the data, Grafana makes it beautiful and interactive.

---

## Q8: What is kube-state-metrics and why do you need it?

**Answer:**

cAdvisor (built into kubelet) gives you container-level resource metrics: CPU used, memory used. But it doesn't know about Kubernetes concepts: "how many replicas does this Deployment have?", "is this Pod in a failed phase?", "did this Job succeed?".

kube-state-metrics fills this gap by:
- Watching the Kubernetes API
- Exposing metrics about the state of K8s objects

Examples of what it exposes:
- `kube_deployment_status_replicas_available` — available replicas
- `kube_pod_status_phase` — pod phase (Running, Pending, Failed)
- `kube_job_status_succeeded` — job completion status
- `kube_node_status_condition` — node conditions (Ready, DiskPressure, etc.)

You need both cAdvisor (resource usage) and kube-state-metrics (object state) for complete cluster visibility.

---

## Q9: What is distributed tracing and how does it differ from logging?

**Answer:**

**Logging** captures individual events at each service: "received request", "queried database", "returned 500 error". Each log entry is isolated to one service.

**Distributed tracing** tracks a single request as it flows through multiple services, showing the timing at each step and how they relate. A trace is a tree of **spans** — each span represents one operation.

Example: a user request takes 2 seconds. Tracing reveals: frontend 20ms → user-service 50ms → product-service 1900ms → database 1800ms. Logs would show "slow request" in each service but wouldn't connect them or reveal the 1800ms database query.

Tracing requires instrumentation: your code must create spans and propagate trace IDs in headers. Tools: OpenTelemetry (standard SDK), Jaeger or Grafana Tempo (backends).

---

## Q10: How do you set up Alertmanager to send Slack notifications?

**Answer:**

Alertmanager is configured via a Secret or ConfigMap. The key sections are `route` (matching rules) and `receivers` (destinations):

```yaml
global:
  slack_api_url: 'https://hooks.slack.com/services/T.../B.../...'

route:
  receiver: 'slack-notifications'
  group_by: ['alertname', 'namespace']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

receivers:
- name: 'slack-notifications'
  slack_configs:
  - channel: '#alerts'
    text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
```

When a Prometheus alert fires, it sends to Alertmanager, which matches the alert against routes and sends the notification to the configured receiver.

---

## Q11: What is the difference between `kubectl logs` and a centralized logging system?

**Answer:**

| | kubectl logs | Centralized logging |
|---|---|---|
| Data retention | Only while pod exists on node | Configurable (days/weeks/months) |
| Historical queries | No (deleted pod = no logs) | Yes, full history |
| Multi-pod search | Limited (`-l` selector) | Full text/label search across all pods |
| Correlation | Manual | Automatic with metadata enrichment |
| Alerting on log content | No | Yes (Loki alert rules, Kibana watchers) |

`kubectl logs` is for quick, real-time debugging. Centralized logging (EFK/Loki) is for production where you need historical data, correlation across services, and log-based alerting.

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Monitoring and Logging Theory](./Theory.md) |
| Cheatsheet | [Monitoring and Logging Cheatsheet](./Cheatsheet.md) |
| Next Module | [23 — Security](../23_Security/Theory.md) |
