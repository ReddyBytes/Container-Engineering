# Health Probes — Interview Q&A

---

**Q1: What are the three types of health probes in Kubernetes and what does each do?**

1. **Liveness probe**: Checks if the container is alive. If it fails, Kubernetes restarts the container. Detects deadlocks, infinite loops, or corrupted state.

2. **Readiness probe**: Checks if the container is ready to receive traffic. If it fails, the pod is removed from the Service's endpoint list (no traffic is sent to it). The container is NOT restarted. The pod rejoins the load balancer when the probe succeeds again.

3. **Startup probe**: Checks if the application has finished starting up. While running, the liveness probe is disabled. If startup probe fails beyond its threshold, the container is restarted. This prevents premature liveness probe failures during slow application initialization.

---

**Q2: What is the difference between liveness and readiness probes? When would a readiness failure NOT cause a restart?**

The key difference is the consequence of failure: liveness failure restarts the container, readiness failure removes it from the load balancer without restarting. A readiness failure without restart is appropriate when:
- The app is temporarily overloaded and needs backpressure (stop sending new traffic, let it catch up)
- The app is warming up caches or loading data
- A downstream dependency is slow but the app is still healthy
- During graceful shutdown: the pod marks itself not-ready before stopping

If the app is fundamentally broken (deadlock, panic), liveness should catch it and restart. If it's temporarily busy or warming up, readiness handles it gracefully.

---

**Q3: Why would you use a startup probe instead of just setting a high initialDelaySeconds on the liveness probe?**

`initialDelaySeconds` is a fixed delay — you always wait that long, even if the app starts in 5 seconds. A startup probe actively polls the app, so once it passes, the liveness probe activates immediately — no unnecessary waiting.

Also, with `initialDelaySeconds`, all pods in a deployment wait the full delay, which slows rollouts. Startup probes provide tight detection: slow apps get their full startup window, fast apps get detected immediately.

If you set `initialDelaySeconds: 300` (5 minutes) on a liveness probe for a slow-starting app, every pod restart incurs a 5-minute blind spot. A startup probe with `failureThreshold: 36, periodSeconds: 5` gives up to 3 minutes of runway but activates liveness immediately once ready.

---

**Q4: What are the four probe mechanisms available in Kubernetes?**

1. **HTTP GET**: Sends an HTTP request to a path/port. Status 200-399 = success. Best for web services.
2. **TCP Socket**: Opens a TCP connection. Accepted connection = success. Best for non-HTTP services like databases.
3. **Exec**: Runs a command in the container. Exit code 0 = success. Best for CLI health check tools (e.g., `pg_isready`, `redis-cli ping`).
4. **gRPC**: Calls the standard gRPC health protocol. Requires the app to implement the protocol. Available since Kubernetes 1.24.

---

**Q5: Why is it a mistake to check downstream dependencies (like a database) in a readiness probe?**

If your readiness probe calls your database and the database is experiencing slow queries, your pod fails its readiness probe and gets removed from the load balancer. Now instead of slow responses, users get connection errors — likely worse. It also creates a cascading failure: all pods fail readiness simultaneously, taking the entire service offline.

Readiness probes should check local state only — can the application accept connections? Is its local cache loaded? Is the HTTP server listening? Let the application's own error handling and circuit breakers deal with downstream dependency issues.

---

**Q6: What happens during a Kubernetes deployment rollout if a readiness probe fails?**

Kubernetes pauses the rollout. The deployment controller will not create new pods beyond `maxSurge` or remove more old pods beyond `maxUnavailable` if the new pods are not passing readiness. If the new pods never become ready (readiness probe keeps failing), the rollout stalls indefinitely — no more pods are replaced. The old pods continue serving traffic. You must manually diagnose and either fix the probe/application or roll back with `kubectl rollout undo`.

---

**Q7: What does `successThreshold` do and when would you set it higher than 1?**

`successThreshold` specifies how many consecutive successes are required before a probe is considered healthy again. For liveness probes it must be 1. For readiness probes, setting it higher (e.g., 3) prevents flapping: the pod is not re-added to the load balancer after a single successful probe if it has been oscillating. This is useful for applications that have intermittent spikes — requiring 3 consecutive successes ensures the app is genuinely stable before traffic is restored.

---

**Q8: How do you debug a pod that keeps restarting?**

1. Check restart count: `kubectl get pods -n <ns>` — high RESTARTS = liveness probe killing it
2. Describe the pod: `kubectl describe pod <name> -n <ns>` — look for "Liveness probe failed" in Events
3. View previous container logs: `kubectl logs <pod> -n <ns> --previous`
4. Check probe configuration: is `timeoutSeconds` too short? Is `initialDelaySeconds` too low?
5. Port-forward and test the health endpoint manually: `curl http://localhost:8080/healthz`
6. Exec into the running container and test internally
7. Consider adding a startup probe if the issue is slow initialization

---

**Q9: What happens to in-flight requests when a pod's readiness probe fails?**

Existing TCP connections to the pod are not immediately dropped — the pod is only removed from the Service's endpoint list, preventing new connections from being routed to it. In-flight requests on existing connections continue until they complete or the connection is closed. This is why readiness failures during graceful shutdown work well: mark not-ready first, wait for existing requests to complete, then shut down.

---

**Q10: Can a pod be liveness-healthy but readiness-failing?**

Yes, and this is a normal, desired state. A pod can be alive (no restart needed) but temporarily not ready to serve traffic. Examples:
- Loading initial data into an in-memory cache
- Performing database migrations at startup
- Circuit breaker tripped due to downstream issues
- Intentionally removed from load balancer for maintenance

The pod stays running, the liveness probe passes, but readiness fails, so no traffic flows to it. This is exactly the intended behavior.

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Theory.md](./Theory.md) |
| Cheatsheet | [Cheatsheet.md](./Cheatsheet.md) |
| Code Example | [Code_Example.md](./Code_Example.md) |
| Module Home | [14_Health_Probes](../) |
