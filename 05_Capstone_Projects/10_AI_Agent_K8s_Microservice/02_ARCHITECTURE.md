# Project 10: Architecture

---

## The Stateless Agent

A REST-wrapped AI agent is **stateless** in the same way a calculator is stateless: give it an input, get an output, it remembers nothing about previous calls. Each HTTP request to `/chat` is a completely independent conversation turn.

This is a deliberate design choice. Stateless services are trivially scalable — you can add replicas without worrying about which pod holds which conversation. If you need multi-turn memory, you add a Redis sidecar and store conversation history there, keyed by session ID. The agent itself stays stateless.

---

## Architecture Diagram

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │  Namespace: ai-agent                                                 │
  │                                                                      │
  │  ┌────────────────────────────────────────────────────────────────┐  │
  │  │  Deployment: ai-agent (replicas: 3, strategy: RollingUpdate)  │  │
  │  │                                                                │  │
  │  │  ┌──────────────────────────────────────────────────────────┐ │  │
  │  │  │  Pod spec                                                │ │  │
  │  │  │                                                          │ │  │
  │  │  │  container: ai-agent                                     │ │  │
  │  │  │    image: ai-agent:latest                                │ │  │
  │  │  │    port: 8000                                            │ │  │
  │  │  │    env:                                                  │ │  │
  │  │  │      ANTHROPIC_API_KEY: secretKeyRef → anthropic-secret  │ │  │
  │  │  │    livenessProbe:  GET /health  (every 10s)              │ │  │
  │  │  │    readinessProbe: GET /ready   (every 5s)               │ │  │
  │  │  │    resources:                                            │ │  │
  │  │  │      requests: cpu=100m, memory=256Mi                    │ │  │
  │  │  │      limits:   cpu=500m, memory=512Mi                    │ │  │
  │  │  └──────────────────────────────────────────────────────────┘ │  │
  │  └────────────────────────────────────────────────────────────────┘  │
  │                                                                      │
  │  Service: ai-agent-svc (ClusterIP, port 80 → targetPort 8000)       │
  │                                                                      │
  │  HPA: ai-agent-hpa                                                   │
  │    minReplicas: 2   maxReplicas: 10                                  │
  │    target: cpu utilization 60%                                       │
  │    stabilizationWindowSeconds (scale down): 300s                    │
  │                                                                      │
  │  Ingress: ai-agent-ingress                                           │
  │    host: agent.local → ai-agent-svc:80                              │
  └─────────────────────────────────────────────────────────────────────┘

  External:
    Secret: anthropic-secret
      key: ANTHROPIC_API_KEY → <base64-encoded key>
```

---

## K8s Secrets Flow

The Anthropic API key must never appear in:
- Source code
- Docker image layers
- K8s ConfigMaps (those are not encrypted at rest by default)
- Helm `values.yaml` committed to git

The correct pattern is a K8s **Secret**, injected as an environment variable at pod startup:

```
  kubectl create secret generic anthropic-secret \
    --from-literal=ANTHROPIC_API_KEY=sk-ant-...
         │
         ▼
  Secret object stored in etcd (encrypted at rest if etcd encryption is configured)
         │
         ▼
  Pod spec references the secret:
    env:
      - name: ANTHROPIC_API_KEY
        valueFrom:
          secretKeyRef:
            name: anthropic-secret
            key: ANTHROPIC_API_KEY
         │
         ▼
  Container sees: os.environ["ANTHROPIC_API_KEY"]
  Container never sees the raw YAML value — K8s injects it at runtime
```

---

## Probe Strategy

**Liveness probe** — answers: "is this pod alive and worth keeping?"

If liveness fails, kubelet kills the container and restarts it. Use it to detect hard failures: process deadlock, uncaught exception that left the process running but broken.

```
  GET /health → 200 if:
    - Process is running
    - Can instantiate Anthropic client
    - Claude API responds to a lightweight ping (e.g. list models)

  GET /health → 503 if:
    - Anthropic client raises AuthenticationError
    - Claude API is unreachable after timeout
```

**Readiness probe** — answers: "is this pod ready to receive traffic?"

If readiness fails, the pod is removed from the Service's endpoint list. It stays running but gets no requests. Use it to detect temporary unavailability: tools not loaded yet, model download in progress.

```
  GET /ready → 200 if:
    - /health passes
    - All tool functions are registered and callable
    - (Optional) A tool warm-up call succeeds

  GET /ready → 503 if:
    - Tools aren't registered yet
    - Any required tool raises an exception on test call
```

The key distinction: a liveness failure means "restart me," a readiness failure means "don't send me traffic yet."

---

## HPA Configuration

HPA watches the pod's CPU utilization (reported by Metrics Server) and adjusts the replica count.

```
  Current load:  60 rps, 3 pods, CPU at 80%
                 target CPU: 60%
                 desired replicas = ceil(3 * 80/60) = ceil(4.0) = 4
                 HPA scales up to 4 pods

  Load drops:    30 rps, 4 pods, CPU at 20%
                 stabilizationWindowSeconds: 300 (5 minutes)
                 HPA waits 5 minutes before scaling down
                 (prevents thrashing if load is bursty)
```

The `stabilizationWindowSeconds` for scale-down is critical for AI agents — LLM calls are bursty by nature. Without it, the HPA would scale down during a quiet period and then be unable to handle the next burst fast enough.

---

## Tech Stack

| Component | Technology | Notes |
|---|---|---|
| Agent framework | Anthropic SDK (`anthropic` Python package) | Native tool_use support |
| API wrapper | FastAPI + uvicorn | Async, lightweight |
| Metrics | `prometheus-client` | Counter, Histogram, Gauge |
| Tools | In-process Python functions | calculator, time, web search |
| Web search | `duckduckgo-search` | No API key needed |
| Base image | `python:3.12-slim` | Minimal attack surface |
| K8s version | 1.28+ | Required for stable HPA v2 |
| Metrics Server | Required for HPA | `minikube addons enable metrics-server` |

---

## Prometheus Metrics Design

Three metrics cover the most important signals for an AI agent service:

```
  agent_requests_total{endpoint, status_code}   Counter
    - increments every request
    - labels let you split by /chat vs /health vs /metrics
    - alert if error rate (status_code=5xx) exceeds threshold

  agent_request_duration_seconds{endpoint}      Histogram
    - records latency of every request
    - LLM calls have high variance: p50 might be 1s, p99 might be 30s
    - buckets: [0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]

  agent_active_requests                         Gauge
    - increments at request start, decrements at end
    - shows current concurrency
    - alert if this hits your pod's expected concurrency limit
```

These three metrics, scraped by Prometheus and visualized in Grafana, give you everything you need to operate the service.

---

## 📂 Navigation

⬅️ **Prev:** [01_MISSION.md](./01_MISSION.md) &nbsp;&nbsp; ➡️ **Next:** [03_GUIDE.md](./03_GUIDE.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
