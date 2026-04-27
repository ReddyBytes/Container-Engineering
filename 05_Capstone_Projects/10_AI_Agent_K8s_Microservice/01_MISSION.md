# Project 10: Deploy a Multi-Tool AI Agent as a K8s Microservice

## 🔴 Build Yourself · 8 hours

---

## The Problem

You've built an AI agent that runs as a script: you call it, it uses tools, it answers, it exits. It lives in a Python file on your laptop. If you want someone else to use it, you send them the file and hope their environment matches yours.

Production is a different contract. A production service is always on. It scales when demand rises. It exposes health endpoints so the cluster can restart it if it crashes. Its API keys live in the cluster's secret store, not in a `.env` file on a developer's machine. And you can tell, at a glance from a dashboard, whether it's healthy.

This project takes that agent script and promotes it to a **production K8s microservice**: containerized, deployed with a K8s Deployment, scaled by HPA, secured with K8s Secrets, and instrumented with Prometheus metrics.

---

## Your Mission

Deploy a **multi-tool Claude AI agent** as a production Kubernetes microservice with:

- **FastAPI wrapper** around the Claude SDK — the agent accepts HTTP requests instead of CLI input
- **K8s Secrets** for the Anthropic API key — never in code, never in a ConfigMap
- **Liveness probe** that verifies the Claude API is actually reachable, not just that the process is running
- **Readiness probe** that verifies all tools are responding before the pod accepts traffic
- **HPA** that scales the deployment between 2 and 10 pods based on CPU usage
- **Prometheus metrics** using `prometheus-client`: request count, request latency, active conversations

---

## Skills You'll Practice

- **K8s Secrets** — creating secrets with `kubectl create secret` and injecting as env vars
- **Deployment strategy** for stateless AI services — why `RollingUpdate` works and what to set for `maxUnavailable`
- **Liveness vs readiness probes** for LLM-backed services — the liveness probe tests the process; the readiness probe tests the external dependency
- **HPA configuration** — target CPU, min/max replicas, stabilization windows to prevent thrashing
- **Prometheus instrumentation** — `Counter`, `Histogram`, `Gauge` with `prometheus-client`
- **Multi-tool agent pattern** — Claude with `tool_use` content blocks, tool dispatch loop

---

## What You're Building

```
  External traffic
       │
       ▼
  ┌─────────────────────────────────────────────────────────────┐
  │  K8s Cluster                                                 │
  │                                                              │
  │  ┌────────┐     ┌─────────────────────────────────────────┐ │
  │  │ Ingress│────►│  Service (ClusterIP)                    │ │
  │  └────────┘     └────────────────┬────────────────────────┘ │
  │                                   │                          │
  │                  ┌────────────────▼────────────────────────┐ │
  │                  │  AI Agent Deployment (3 replicas)        │ │
  │                  │                                          │ │
  │                  │  Pod 1   Pod 2   Pod 3                   │ │
  │                  │   │       │       │                      │ │
  │                  │   └───────┴───────┘                      │ │
  │                  │           │                              │ │
  │                  └───────────┼──────────────────────────────┘ │
  │                              │                                 │
  │              ┌───────────────┼───────────────────┐            │
  │              │               ▼                   │            │
  │              │   ANTHROPIC_API_KEY               │            │
  │              │   (K8s Secret → env var injection) │           │
  │              └───────────────────────────────────┘            │
  │                              │                                 │
  └──────────────────────────────┼─────────────────────────────┘  │
                                  │ external HTTPS
                                  ▼
                          Claude API (api.anthropic.com)

  Tool services (in-process, no separate containers):
    - calculator    (Python eval on safe AST)
    - current_time  (datetime.now())
    - web_search    (DuckDuckGo via duckduckgo-search)
```

---

## Acceptance Criteria

Your solution passes when all five of these are true:

1. `kubectl get pods -n ai-agent` shows 3 pods in `Running` state with `2/2` containers ready
2. `kubectl exec <pod> -- curl -s localhost:8000/health` returns `{"status":"ok","claude":"reachable"}`
3. `curl -X POST <ingress-url>/chat -d '{"message":"what time is it?"}' ` returns a response that uses the `current_time` tool
4. `kubectl get hpa -n ai-agent` shows `TARGETS` reporting a CPU percentage (not `<unknown>`)
5. `curl <ingress-url>/metrics` returns Prometheus-format text with `agent_requests_total` and `agent_request_duration_seconds`

---

## Difficulty: 🔴 Build Yourself

No step-by-step guide. No hints. You have the architecture above, the acceptance criteria, and the starter code in `src/starter.py`. The full reference solution is in `src/solution.py`.

This is the final project. If you've completed projects 01–09, you have every skill needed to build this.

Time estimate: **8 hours** for someone who has completed the prior projects.

---

## 📂 Navigation

⬅️ **Prev:** [09 — Containerize RAG System](../09_RAG_System_Containerized/01_MISSION.md) &nbsp;&nbsp; ➡️ **This is the final project**

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
