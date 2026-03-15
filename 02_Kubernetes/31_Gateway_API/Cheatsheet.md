# Gateway API — Cheatsheet

## Install CRDs

```bash
# Standard channel (HTTPRoute, GatewayClass, Gateway, GRPCRoute)
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.0/standard-install.yaml

# Experimental channel (TCPRoute, TLSRoute, UDPRoute)
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.0/experimental-install.yaml
```

---

## Resource Hierarchy

```
GatewayClass  (cluster-scoped) → names the controller
    └── Gateway  (namespace-scoped) → defines port/protocol/TLS
            ├── HTTPRoute  → HTTP/HTTPS routing rules
            ├── GRPCRoute  → gRPC routing rules
            ├── TCPRoute   → raw TCP routing
            └── TLSRoute   → TLS passthrough routing
```

---

## GatewayClass (platform team)

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: nginx
spec:
  controllerName: gateway.nginx.org/nginx-gateway-controller
```

---

## Gateway (platform team)

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: prod-gw
  namespace: infra
spec:
  gatewayClassName: nginx
  listeners:
  - name: http
    port: 80
    protocol: HTTP
  - name: https
    port: 443
    protocol: HTTPS
    tls:
      mode: Terminate
      certificateRefs:
      - name: my-cert
```

---

## HTTPRoute — Path Routing (app team)

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: app-routes
  namespace: dev
spec:
  parentRefs:
  - name: prod-gw
    namespace: infra
  hostnames: ["app.example.com"]
  rules:
  - matches:
    - path: {type: PathPrefix, value: /api}
    backendRefs:
    - name: backend-svc
      port: 8080
  - matches:
    - path: {type: PathPrefix, value: /}
    backendRefs:
    - name: frontend-svc
      port: 3000
```

---

## Traffic Splitting

```yaml
rules:
- backendRefs:
  - name: app-stable
    port: 8080
    weight: 90          # 90% of traffic
  - name: app-canary
    port: 8080
    weight: 10          # 10% of traffic
```

---

## Header-Based Routing

```yaml
rules:
- matches:
  - headers:
    - name: X-Beta-User
      value: "true"
  backendRefs:
  - name: app-v2
    port: 8080
- backendRefs:          # default: everyone else
  - name: app-v1
    port: 8080
```

---

## URL Rewrite

```yaml
rules:
- matches:
  - path: {type: PathPrefix, value: /api}
  filters:
  - type: URLRewrite
    urlRewrite:
      path:
        type: ReplacePrefixMatch
        replacePrefixMatch: /      # strip /api prefix
  backendRefs:
  - name: backend-svc
    port: 8080
```

---

## Request Mirror (shadow traffic)

```yaml
rules:
- backendRefs:
  - name: production-svc
    port: 8080
  filters:
  - type: RequestMirror
    requestMirror:
      backendRef:
        name: shadow-svc
        port: 8080
```

---

## ReferenceGrant (cross-namespace)

Allow Gateway in `infra` namespace to reference a Service in `dev` namespace:

```yaml
apiVersion: gateway.networking.k8s.io/v1beta1
kind: ReferenceGrant
metadata:
  name: allow-infra-gw
  namespace: dev          # namespace of the target Service
spec:
  from:
  - group: gateway.networking.k8s.io
    kind: Gateway
    namespace: infra      # namespace of the Gateway
  to:
  - group: ""
    kind: Service
```

---

## Common kubectl Commands

```bash
# List all GatewayClasses
kubectl get gatewayclasses

# List Gateways in all namespaces
kubectl get gateways -A

# List HTTPRoutes in a namespace
kubectl get httproutes -n dev

# Describe an HTTPRoute (see status / conditions)
kubectl describe httproute app-routes -n dev

# Check Gateway status (is it programmed?)
kubectl get gateway prod-gw -n infra -o jsonpath='{.status.conditions}'
```

---

## Status Conditions to Know

| Condition | Meaning |
|---|---|
| `Accepted: True` | Route was accepted by the Gateway |
| `ResolvedRefs: True` | All backend Services were found |
| `Programmed: True` | Gateway is ready to route traffic |
| `Accepted: False` | parentRef doesn't exist or no ReferenceGrant |

---

## Ingress → HTTPRoute Quick Translation

| Ingress annotation | HTTPRoute equivalent |
|---|---|
| `nginx.ingress.kubernetes.io/canary-weight: "10"` | `weight: 10` on backendRef |
| `nginx.ingress.kubernetes.io/rewrite-target: /` | `URLRewrite` filter |
| `nginx.ingress.kubernetes.io/ssl-redirect: "true"` | `HTTPRoute` redirect filter |
| `nginx.ingress.kubernetes.io/proxy-body-size: 50m` | Set on Gateway/controller config |

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
