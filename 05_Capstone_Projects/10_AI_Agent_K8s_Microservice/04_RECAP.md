# Project 10: Recap

## What You Built

You took an AI agent — something that previously only ran as a script on a developer's laptop — and made it a **production Kubernetes microservice**. It runs in multiple replicas, scales automatically under load, protects its API key with K8s Secrets, and tells the cluster exactly when it's healthy and when it's not.

This is the shape of almost every AI service deployed in production today: a stateless FastAPI wrapper around an LLM call, deployed to K8s, scaled horizontally, instrumented with Prometheus.

---

## Key Concepts

**Stateless AI services**

An AI agent that holds no in-memory state between requests can scale to any number of replicas without coordination. Pod 1 and Pod 2 handle different requests without knowing about each other. This is the property that makes horizontal scaling work.

If you need conversation memory across turns, you keep the agent stateless and add an external store — Redis, DynamoDB, Postgres — keyed by session ID. The agent reads and writes state explicitly; it doesn't hold it.

**K8s Secrets for API keys**

The pipeline: developer creates secret with `kubectl create secret generic` → secret stored in etcd → pod spec references secret with `secretKeyRef` → kubelet injects the value as an environment variable at pod startup → container reads `os.environ["ANTHROPIC_API_KEY"]`.

The API key never appears in:
- Source code
- Dockerfile
- docker-compose.yml committed to git
- K8s Deployment YAML

It lives only in etcd (where it can be encrypted at rest) and in the pod's environment at runtime.

**Observable agents**

```
  Three signals that matter for an AI agent:

  agent_requests_total{endpoint,status_code}
    ↓ alert if error_rate > 1% over 5 minutes

  agent_request_duration_seconds (p99)
    ↓ alert if p99 latency > 30 seconds

  agent_active_requests
    ↓ alert if sustained above pod concurrency limit
```

Without these, you're flying blind. With them, you can set alerts, build dashboards, and know exactly when the service is degraded — before users start complaining.

**Liveness vs readiness probes for LLM services**

A subtle distinction that matters in practice:

```
  Liveness probe fails → kubelet restarts the container
    Use for: process is running but broken (deadlock, invalid API key)

  Readiness probe fails → pod removed from Service endpoints (no traffic)
    Use for: temporarily not ready (tools loading, model warming up)
```

For LLM services, the readiness probe doing a real API call has a cost — you pay per API request. The pattern used in this project (calling `client.models.list()` instead of `client.messages.create()`) verifies connectivity without generating tokens.

---

## Architecture Recap

```
  kubectl apply -f k8s/

  ┌─────────────────────────────────────────────────────────┐
  │  Namespace: ai-agent                                    │
  │                                                         │
  │  Secret: anthropic-secret                               │
  │    ANTHROPIC_API_KEY → env var injection                │
  │                                                         │
  │  Deployment: ai-agent (3 → 10 replicas via HPA)        │
  │    liveness:  GET /health (every 10s)                   │
  │    readiness: GET /ready  (every 5s)                    │
  │    resources: requests.cpu = 100m (required for HPA)    │
  │                                                         │
  │  Service: ai-agent-svc (ClusterIP, :80 → :8000)        │
  │                                                         │
  │  HPA: target 60% CPU, scale 2-10, 5min cooldown        │
  │                                                         │
  │  Ingress: agent.local → ai-agent-svc                   │
  └─────────────────────────────────────────────────────────┘
```

---

## Extend It

**Add Redis for conversation memory**

Deploy a Redis StatefulSet to the same namespace. Add a `session_id` field to `ChatRequest`. On each `/chat` call, load conversation history from Redis, append the new turn, call Claude, store the updated history, return the response. The agent stays stateless; Redis holds the state.

**Deploy to EKS with ECR**

Push the image to AWS ECR instead of a local registry. Configure an EKS cluster with an OIDC provider. Use IAM Roles for Service Accounts (IRSA) instead of K8s Secrets for credential injection — AWS injects temporary credentials automatically, no long-lived API keys needed.

**Add distributed tracing with OpenTelemetry**

Instrument the FastAPI app with `opentelemetry-instrumentation-fastapi`. Export traces to Jaeger or Tempo. Each `/chat` request becomes a trace with spans for: receiving the request, calling Claude, calling each tool, assembling the response. You can see exactly where time is spent.

```
  Trace: POST /chat (total: 4.2s)
    ├── Claude API call round 1  (2.1s)
    ├── web_search tool          (0.8s)
    ├── Claude API call round 2  (1.2s)
    └── response serialization   (0.1s)
```

---

## Lessons Learned

| Problem | Root cause | Fix |
|---|---|---|
| HPA shows `<unknown>` for TARGETS | No CPU request set on pod spec | Add `resources.requests.cpu` |
| Pod CrashLoopBackOff on startup | `ANTHROPIC_API_KEY` not set or invalid | Create the K8s Secret before applying the Deployment |
| Liveness probe keeps killing pods | Probe calls `/chat` which bills and is slow | Use `/health` with `client.models.list()` instead |
| Agent loops forever on tool calls | No MAX_TOOL_ROUNDS guard | Add a round counter and break out of the loop |
| Tool results not passed back correctly | `tool_use_id` in result doesn't match block ID | Always use `block.id` from the response, not a generated ID |

---

## 📂 Navigation

⬅️ **Prev:** [09 — Containerize RAG System](../09_RAG_System_Containerized/01_MISSION.md) &nbsp;&nbsp; ➡️ **This is the final project**

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
