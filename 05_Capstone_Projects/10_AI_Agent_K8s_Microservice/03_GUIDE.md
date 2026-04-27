# Project 10: Build Spec

## 🔴 Build Yourself

No step-by-step guide is provided. This is the final capstone project — you have all the skills. Use the acceptance criteria below as your specification, the architecture in `02_ARCHITECTURE.md` as your design, and `src/starter.py` as your starting point.

---

## Acceptance Criteria

Build a system where all five of these are true simultaneously:

**1. Pods are running and ready**

```
kubectl get pods -n ai-agent

NAME                        READY   STATUS    RESTARTS
ai-agent-7d9f6b4c8-abc12    1/1     Running   0
ai-agent-7d9f6b4c8-def34    1/1     Running   0
ai-agent-7d9f6b4c8-ghi56    1/1     Running   0
```

All pods show `1/1` READY. Zero restarts means liveness probe is not triggering false positives.

**2. Health endpoint confirms Claude is reachable**

```bash
kubectl exec <pod-name> -n ai-agent -- curl -s localhost:8000/health
# Expected:
{"status": "ok", "claude": "reachable", "tools": ["calculator", "current_time", "web_search"]}
```

**3. Agent uses tools correctly**

```bash
curl -X POST http://agent.local/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "what time is it right now?"}'
# Expected: response includes the actual current time, proving current_time tool was called
```

```bash
curl -X POST http://agent.local/chat \
  -d '{"message": "what is 847 multiplied by 23?"}'
# Expected: response includes 19481, proving calculator tool was called
```

**4. HPA is functioning**

```
kubectl get hpa -n ai-agent

NAME            REFERENCE            TARGETS   MINPODS   MAXPODS   REPLICAS
ai-agent-hpa    Deployment/ai-agent  12%/60%   2         10        3
```

`TARGETS` must show a real CPU percentage, not `<unknown>`. `<unknown>` means the Metrics Server isn't running or resource requests aren't set on the pod spec.

**5. Prometheus metrics are exposed**

```bash
curl http://agent.local/metrics | grep agent_requests_total
# Expected output (Prometheus text format):
# HELP agent_requests_total Total number of requests by endpoint and status
# TYPE agent_requests_total counter
agent_requests_total{endpoint="/chat",status_code="200"} 14.0
agent_requests_total{endpoint="/health",status_code="200"} 42.0
```

---

## Architectural Decision Hints

These are the three decisions where engineers get stuck. One hint each — the rest is implementation.

**Secrets management:**

The `secretKeyRef` field in a pod's `env` spec injects a secret value as an environment variable. The secret must exist in the same namespace as the pod before the pod can start. Create it with `kubectl create secret generic` before applying your Deployment manifest.

**Probe design for LLM services:**

The liveness probe should call a lightweight endpoint — not `/chat` (which bills you per call). The `/health` endpoint should make a minimal Claude API call, such as listing available models, to verify the API key is valid and the endpoint is reachable. If your API key is invalid, the pod should fail liveness and restart with a clear error in the logs.

**HPA prerequisites:**

HPA requires two things that are often missing: (1) the Metrics Server must be running in the cluster (`minikube addons enable metrics-server` or the equivalent), and (2) the pod spec must have `resources.requests.cpu` set — HPA calculates utilization as `actual_cpu / requested_cpu`. Without a CPU request, HPA has no denominator and reports `<unknown>`.

---

## Full Reference Solution

<details>
<summary>✅ Full Solution (click to reveal)</summary>

The complete working solution is at `src/solution.py`. It includes:

- FastAPI app with `/chat`, `/health`, `/ready`, and `/metrics` endpoints
- Multi-tool Claude agent: calculator, current_time, web_search
- Prometheus instrumentation with Counter, Histogram, and Gauge
- Complete K8s YAML manifests embedded as strings at the bottom of the file (Namespace, Secret placeholder, Deployment, Service, HPA, Ingress)
- Dockerfile and docker-compose.yml for local testing

Read the solution only after attempting your own implementation. The goal is for you to hit the problems yourself — "why does HPA show `<unknown>`?" is a lesson that sticks when you've debugged it once.

</details>

---

## 📂 Navigation

⬅️ **Prev:** [02_ARCHITECTURE.md](./02_ARCHITECTURE.md) &nbsp;&nbsp; ➡️ **Next:** [04_RECAP.md](./04_RECAP.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
