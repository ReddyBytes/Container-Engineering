# Module 24 — Service Mesh Interview Q&A

---

## Q1: What problem does a service mesh solve, and why can't you just handle it in application code?

**Answer:**

The core problem is **cross-cutting concerns** in microservices: mTLS, retries, circuit breaking, distributed tracing, and observability all need to be implemented in every service-to-service communication path.

If you handle it in application code:
- Every team must implement it correctly in every language (Go, Python, Java, Node.js)
- Implementations differ and have different bugs
- Updating the retry policy requires deploying new versions of every service
- You can't enforce consistency — one service forgets to add mTLS

A service mesh moves this to the **infrastructure layer** via sidecar proxies. Now:
- All services get these features transparently (no code changes)
- Policy changes are applied centrally without redeploying apps
- Consistent behavior across all services regardless of language
- Operations team can manage network policy independently from application teams

The tradeoff: added complexity, latency overhead, and new operational surface to manage.

---

## Q2: Explain the Istio control plane and data plane.

**Answer:**

**Data Plane** — all the Envoy sidecar proxies running alongside every application pod. They handle the actual traffic: intercepting, routing, encrypting, and collecting telemetry. Each proxy gets its configuration from the control plane.

**Control Plane** — Istiod, a single binary containing three logical components:
- **Pilot**: watches Kubernetes services and endpoints, translates them into Envoy configuration (xDS API), and pushes updates to all proxies
- **Citadel**: acts as a certificate authority — issues and rotates mTLS certificates for all service identities
- **Galley**: validates Istio configuration and distributes it

The separation means application proxies (data plane) are thin and fast — they don't need to communicate with the control plane on every request. Configuration is pushed down once, and the proxy handles all traffic locally.

---

## Q3: What is mTLS and how does a service mesh implement it without code changes?

**Answer:**

**mTLS (Mutual TLS)** is TLS where both the client and server authenticate each other with certificates. In standard TLS (HTTPS), only the server presents a certificate. In mTLS, the client also presents one — so both sides prove their identity before exchanging data.

How a mesh implements it without code changes:
1. Istiod's Citadel issues a certificate to every service's sidecar (identity = Kubernetes Service Account)
2. When Pod A calls Pod B, Pod A's Envoy sidecar intercepts the outbound connection
3. Envoy upgrades the connection to mTLS, presenting Pod A's certificate
4. Pod B's Envoy sidecar receives the connection, validates Pod A's certificate, and presents its own
5. Both sides are authenticated; traffic is encrypted
6. Pod B's application receives a plain HTTP connection from its own sidecar (localhost)

The application code on both sides just makes and receives plain HTTP calls. All TLS handling is transparent.

---

## Q4: What is the difference between Istio's VirtualService and DestinationRule?

**Answer:**

They work together but serve different purposes:

**VirtualService**: defines **routing rules** — what happens to traffic before it reaches the destination. Use it for:
- Traffic splitting (weight-based)
- Header-based routing ("route requests with header `x-user: beta` to v2")
- Retries and timeouts
- Fault injection (for chaos testing)
- URL rewrites and redirects

**DestinationRule**: defines **traffic policies** for a specific destination — how to handle the connection once you've decided where to send it. Use it for:
- Defining subsets (which pods belong to `v1`, which to `v2`)
- Circuit breaking (outlier detection)
- Connection pool settings (max connections)
- TLS settings (what certificates to use)
- Load balancing algorithm (round robin, least connections)

You typically use both together: VirtualService says "send 10% to canary subset", DestinationRule defines what pods are in the "canary" subset and sets circuit breaking on it.

---

## Q5: What is circuit breaking in the context of a service mesh?

**Answer:**

Circuit breaking is a pattern that prevents cascading failures. Named after electrical circuit breakers: when something is overloaded, it "opens the circuit" to stop damage, then tests if it's safe to "close" again.

In a service mesh (Istio's `outlierDetection`):
1. Envoy tracks error rates for each host in a service
2. If a host exceeds the threshold (e.g., 5 consecutive 5xx errors in 30 seconds), Envoy **ejects** it from the load balancer pool
3. Traffic stops going to that host for the ejection period (e.g., 30 seconds)
4. After the period, the host gets a test request; if it succeeds, it's re-added

This prevents a slow or failing instance from being hammered with traffic, giving it time to recover while other healthy instances handle the load. Without circuit breaking, a degraded service can bring down all its callers (they all wait for timeouts, exhausting thread pools).

---

## Q6: What is Envoy and why do most service meshes use it?

**Answer:**

Envoy is a high-performance, open-source proxy developed by Lyft and donated to CNCF. It has become the de facto data plane for service meshes because:

- **Rich feature set**: HTTP/1.1, HTTP/2, gRPC, TCP, WebSockets, mTLS, circuit breaking, retries, rate limiting, load balancing algorithms
- **Dynamic configuration via xDS API**: configuration can be pushed to Envoy without restart — essential for Kubernetes where endpoints change constantly
- **Excellent observability**: generates detailed metrics and traces automatically
- **Extensibility**: Wasm filter extension mechanism for custom logic

Istio, AWS App Mesh, Google Traffic Director, and Contour all use Envoy as their proxy. The main exception is Linkerd, which uses a custom Rust-based micro-proxy optimized for lower resource usage.

---

## Q7: How does Istio implement canary deployments differently from Kubernetes Deployments?

**Answer:**

**Kubernetes Deployment rolling update / replica-based**: canary using two Deployments (v1 with 9 replicas, v2 with 1 replica) — traffic is split by pod count ratio. Not precise — you can't do exactly 5% without lots of pods.

**Istio VirtualService weight-based**: precise percentage routing regardless of replica count. You can send exactly 5% to v2 even if v2 has just 1 replica and v1 has 1 replica. The traffic split is in the mesh configuration, not pod count.

Istio also supports **header-based routing** — send all requests from beta users (detected by a cookie or header) to v2, while everyone else gets v1. This is impossible with replica-based canary.

```yaml
# Route 5% to canary — exact, regardless of pod count
http:
- route:
  - destination:
      host: myapp
      subset: stable
    weight: 95
  - destination:
      host: myapp
      subset: canary
    weight: 5
```

---

## Q8: What is the overhead of running a service mesh, and when is it too much?

**Answer:**

**Latency overhead**: ~1–5ms per service hop for Envoy (context switching to the proxy and back). For high-frequency internal calls (thousands/second), this can accumulate. Linkerd's Rust proxy is lower at ~0.5ms.

**Resource overhead per pod**:
- Envoy sidecar: 50–200MB memory, 5–30m CPU in steady state
- With 100 pods, that's potentially 5–20GB of extra memory cluster-wide

**Operational complexity**:
- New CRDs (VirtualService, DestinationRule, etc.)
- New debugging dimension — "is it the app or the mesh?"
- Teams need to learn Istio concepts
- Certificate rotation, Istiod availability becomes critical path

When it's too much:
- Very small clusters (< 10 pods) — overhead is proportionally large
- Latency-critical systems where 2ms per hop is unacceptable
- Teams with limited operational bandwidth (managing Istio is a real job)
- Simple architectures that don't need traffic management

---

## Q9: How does Istio integrate with Prometheus for observability?

**Answer:**

Istio's Envoy sidecars automatically expose Prometheus metrics at `/stats/prometheus` — no application instrumentation needed. These metrics include:

- `istio_requests_total` — request count by source, destination, method, status code
- `istio_request_duration_milliseconds` — latency histogram
- `istio_request_bytes` — request size
- `istio_response_bytes` — response size

A ServiceMonitor (from Prometheus Operator) or Istio's own Prometheus configuration scrapes these from every sidecar.

Result: every service in the mesh automatically gets golden signal dashboards (latency, traffic, errors, saturation) in Grafana — without any application code changes. This is one of the biggest selling points of a service mesh: instant observability for all services.

---

## Q10: Compare Istio and Linkerd. When would you choose each?

**Answer:**

| | Istio | Linkerd |
|---|---|---|
| Proxy | Envoy (C++) | Rust micro-proxy |
| Resource usage | Higher | ~10x lower |
| Feature set | Very rich | Focused |
| Traffic management | Advanced (weights, header, fault) | Basic load balancing |
| Learning curve | Steep | Gentle |
| mTLS | Configurable per namespace/service | On by default, automatic |
| Tracing | Yes (with Jaeger/Zipkin) | Yes (with Jaeger) |
| Dashboard | Kiali | Linkerd viz |

**Choose Istio when**: you need advanced traffic management (canary with precise weights, header routing, fault injection), are on a major cloud provider with good Istio support, or have a dedicated platform team to manage it.

**Choose Linkerd when**: you primarily want mTLS and basic observability, are resource-constrained, want simpler operations, or are new to service meshes and want to start with something approachable.

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Service Mesh Theory](./Theory.md) |
| Cheatsheet | [Service Mesh Cheatsheet](./Cheatsheet.md) |
| Next Module | [25 — GitOps and CI/CD](../25_GitOps_and_CICD/Theory.md) |
