# Gateway API — Interview Q&A

---

**Q1: What are the main problems with Kubernetes Ingress that Gateway API was designed to solve?**

Ingress has three core problems. First, it only supports HTTP/HTTPS — there is no native way to route TCP or UDP traffic, which means teams resort to controller-specific CRDs that are not portable. Second, any advanced feature (canary routing, header matching, rewrites) requires vendor-specific annotations that do not work across controllers — an nginx annotation means nothing to Traefik or the AWS ALB controller. Third, there is no role separation — a developer with namespace access can inadvertently reconfigure infrastructure-level settings. Gateway API solves all three: it supports multiple protocols natively, moves all traffic management features into the spec (no annotations needed), and separates responsibilities across GatewayClass, Gateway, and HTTPRoute.

---

**Q2: What are the three core resource types in Gateway API and which team typically owns each?**

- **GatewayClass** (cluster-scoped): owned by the infrastructure or platform team. Defines which controller implementation to use (e.g., nginx, Envoy, Istio). Created once per cluster per controller type.
- **Gateway**: owned by the platform team. Lives in a shared namespace (e.g., `infra`). Defines listeners — which ports, protocols, and TLS settings are active.
- **HTTPRoute** (or other Route types): owned by the application team. Lives in the application's namespace. Defines the actual routing rules — which paths go to which services, traffic weights, header matches. The app team never needs to touch the Gateway.

This separation means a developer cannot accidentally reconfigure TLS or change the underlying load balancer configuration.

---

**Q3: How do you implement a 90/10 canary deployment with Gateway API?**

You use the `weight` field on `backendRefs` within an `HTTPRoute` rule:

```yaml
rules:
- backendRefs:
  - name: app-stable
    port: 8080
    weight: 90
  - name: app-canary
    port: 8080
    weight: 10
```

The weights are relative integers. 90 + 10 = 100 means 90% goes to stable and 10% to canary. This is portable — it works the same way on nginx, Envoy Gateway, Istio, and all conformant controllers. With Ingress, you would need controller-specific annotations that work on nginx but not on ALB.

---

**Q4: What is a ReferenceGrant and when do you need one?**

A `ReferenceGrant` is a resource that explicitly authorizes a cross-namespace reference. You need it when a Gateway in one namespace (e.g., `infra`) needs to accept HTTPRoutes that point to Services in a different namespace (e.g., `dev`). By default, cross-namespace references are denied.

You create the `ReferenceGrant` in the *target* namespace (where the Service lives). It says: "I grant permission to Gateways in namespace X to reference Services in my namespace." This prevents namespace owners from being surprised by external traffic being routed through their services.

---

**Q5: What is the difference between GatewayClass and Gateway? Why are there two separate resources?**

`GatewayClass` is analogous to `StorageClass` — it is a cluster-wide definition of a controller type. It is created once by someone with cluster-admin access and says "this name maps to this controller." You might have `GatewayClass: nginx` and `GatewayClass: istio` in the same cluster.

`Gateway` is an instance of a GatewayClass — it is a concrete listener with specific ports, protocols, and TLS config. A cluster might have one `nginx` GatewayClass but multiple Gateways: one for production, one for staging, one for internal services. The separation also allows different teams to own each: a central SRE team manages GatewayClasses, while platform teams manage individual Gateways.

---

**Q6: When did Gateway API reach GA and what does that mean for production use?**

Gateway API reached General Availability (GA) in Kubernetes 1.28, released in October 2023. The core resources — GatewayClass, Gateway, HTTPRoute, and GRPCRoute — are now part of the `v1` API group (`gateway.networking.k8s.io/v1`), meaning they are stable, supported, and will not have breaking changes. GRPCRoute reached GA in Kubernetes 1.31 (2024). TCPRoute and UDPRoute remain in the experimental channel. For production use, the standard channel resources are fully recommended. The Kubernetes project considers Ingress feature-frozen and Gateway API is the active development path.

---

**Q7: How do you implement header-based routing for A/B testing with Gateway API?**

You create two rules in the same HTTPRoute. The first rule matches a specific header and routes to the new version. The second rule has no match (it acts as the default) and routes to the stable version:

```yaml
rules:
- matches:
  - headers:
    - name: X-Beta-User
      value: "true"
  backendRefs:
  - name: app-v2
    port: 8080
- backendRefs:     # no matches → catch-all default
  - name: app-v1
    port: 8080
```

You can also match on header presence (headerType: RegularExpression), query parameters, HTTP methods, or combinations of all three.

---

**Q8: What is request mirroring and when would you use it in Gateway API?**

Request mirroring sends a copy of every request to a secondary backend in addition to the primary backend. The user only gets a response from the primary — the mirror is fire-and-forget. Use cases:

1. **Shadow testing**: Route production traffic to a new version without affecting users. Compare response differences in logs.
2. **Load testing**: Mirror a percentage of real traffic to a test environment to measure real-world performance.
3. **Debugging**: Copy traffic to a debug service that logs full request/response details.

In Gateway API, this is configured with the `RequestMirror` filter type on an HTTPRoute rule, which is a native feature — no annotations needed.

---

**Q9: List four conformant Gateway API implementations and how they differ.**

1. **NGINX Gateway Fabric**: The official NGINX project's implementation. Straightforward, production-ready, good for teams already using nginx as an ingress controller.
2. **Envoy Gateway**: CNCF project that puts a Gateway API control plane in front of Envoy proxy. Highly performant, good xDS integration, suitable for advanced traffic management.
3. **Istio**: Full service mesh that uses Gateway API as its primary external traffic model. Adds mTLS, observability, and service-to-service policies in addition to ingress routing.
4. **AWS Load Balancer Controller**: Implements Gateway API for AWS ALB (HTTP) and NLB (TCP/UDP). Routes map to actual AWS load balancer rules — no in-cluster proxy.

All four accept the same `HTTPRoute` YAML. The difference is in the underlying infrastructure, performance characteristics, and additional features they expose through their own CRDs.

---

**Q10: How would you migrate an existing Ingress to Gateway API without downtime?**

Use a phased approach:

1. Install the Gateway API CRDs and a conformant controller. This does not affect existing Ingress resources.
2. Create a `GatewayClass` and `Gateway` that mirrors your Ingress controller's external IP or hostname.
3. Translate your Ingress rules to `HTTPRoute` resources. Path rules map directly; annotation-based features become native filters.
4. Test by temporarily pointing a test hostname to the new Gateway. Validate routing, TLS, and headers.
5. Use DNS-level traffic shifting (weighted CNAME) to gradually move traffic from the old Ingress endpoint to the new Gateway endpoint.
6. Once 100% of traffic is on the Gateway, delete the old Ingress resources.

Both Ingress and HTTPRoute can run simultaneously — there is no forced cutover moment.

---

**Q11: What is the `Programmed` condition on a Gateway and why does it matter?**

The `Programmed: True` condition means the Gateway controller has successfully translated the Gateway spec into actual data-plane configuration — the load balancer or proxy is running and ready to accept traffic. It is distinct from `Accepted: True` (the Gateway spec is valid and the controller accepts it). You can have `Accepted: True` but `Programmed: False` if, for example, the TLS certificate referenced in the Gateway does not exist or is invalid. Always check both conditions when debugging routing issues. Similarly, an `HTTPRoute` has `Accepted` (the Gateway accepted the route) and `ResolvedRefs` (the backend Services were found and are reachable).

---

## 📂 Navigation

| | |
|---|---|
| Previous | [30_Cost_Optimization](../30_Cost_Optimization/) |
| Next | [32_KEDA_Event_Driven_Autoscaling](../32_KEDA_Event_Driven_Autoscaling/) |
| Up | [02_Kubernetes](../) |

**Files in this module:**
- [Theory.md](./Theory.md) — Concepts and architecture
- [Cheatsheet.md](./Cheatsheet.md) — Quick reference
- [Interview_QA.md](./Interview_QA.md) — Common interview questions
- [Code_Example.md](./Code_Example.md) — Working YAML examples
