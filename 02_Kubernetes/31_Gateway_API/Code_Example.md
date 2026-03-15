# Gateway API — Code Examples

All examples use NGINX Gateway Fabric as the controller. Install prerequisites first:

```bash
# Install Gateway API standard CRDs
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.0/standard-install.yaml

# Install NGINX Gateway Fabric via Helm
helm install ngf oci://ghcr.io/nginx/charts/nginx-gateway-fabric \
  --namespace nginx-gateway \
  --create-namespace \
  --wait
```

---

## Example 1: GatewayClass + Gateway (NGINX Gateway Fabric)

This is the infrastructure layer — created by the platform team once per cluster/environment.

```yaml
---
# GatewayClass: tells Kubernetes which controller handles this type of Gateway
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: nginx
spec:
  controllerName: gateway.nginx.org/nginx-gateway-controller
  description: "NGINX Gateway Fabric - production"

---
# Gateway: the actual listener — defines ports and TLS
# Lives in the 'infra' namespace, managed by the platform team
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: prod-gateway
  namespace: infra
spec:
  gatewayClassName: nginx
  listeners:
  # HTTP listener — will redirect to HTTPS via HTTPRoute
  - name: http
    port: 80
    protocol: HTTP
    allowedRoutes:
      namespaces:
        from: All          # accept HTTPRoutes from any namespace
  # HTTPS listener with TLS termination
  - name: https
    port: 443
    protocol: HTTPS
    tls:
      mode: Terminate      # terminate TLS here; backend gets plain HTTP
      certificateRefs:
      - name: prod-tls-cert
        namespace: infra
    allowedRoutes:
      namespaces:
        from: All

---
# The TLS certificate (created from a cert-manager Certificate or manually)
apiVersion: v1
kind: Secret
metadata:
  name: prod-tls-cert
  namespace: infra
type: kubernetes.io/tls
data:
  # Replace with actual base64-encoded cert and key
  tls.crt: <base64-encoded-cert>
  tls.key: <base64-encoded-key>
```

Apply and verify:

```bash
kubectl apply -f gateway.yaml
kubectl get gateway prod-gateway -n infra
# NAME           CLASS   ADDRESS        PROGRAMMED   AGE
# prod-gateway   nginx   203.0.113.10   True         2m

kubectl describe gateway prod-gateway -n infra | grep -A 20 "Conditions:"
```

---

## Example 2: HTTPRoute for Path-Based Routing

This is the application layer — created by the dev team in their namespace.
Routes `app.example.com/` to a frontend service and `app.example.com/api` to a backend service.

```yaml
---
# Frontend service and deployment (abbreviated)
apiVersion: v1
kind: Service
metadata:
  name: frontend-svc
  namespace: dev
spec:
  selector:
    app: frontend
  ports:
  - port: 3000
    targetPort: 3000

---
# Backend service
apiVersion: v1
kind: Service
metadata:
  name: backend-svc
  namespace: dev
spec:
  selector:
    app: backend
  ports:
  - port: 8080
    targetPort: 8080

---
# HTTPRoute: path-based routing
# /        → frontend-svc:3000
# /api/*   → backend-svc:8080 (with /api prefix stripped)
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: app-routes
  namespace: dev
spec:
  parentRefs:
  - name: prod-gateway
    namespace: infra        # references the Gateway in the infra namespace
  hostnames:
  - "app.example.com"
  rules:
  # Rule 1: /api/* → backend, strip the /api prefix
  - matches:
    - path:
        type: PathPrefix
        value: /api
    filters:
    - type: URLRewrite
      urlRewrite:
        path:
          type: ReplacePrefixMatch
          replacePrefixMatch: /   # /api/users → /users
    backendRefs:
    - name: backend-svc
      port: 8080
  # Rule 2: /* → frontend (catch-all, must be last)
  - matches:
    - path:
        type: PathPrefix
        value: /
    backendRefs:
    - name: frontend-svc
      port: 3000

---
# Redirect HTTP to HTTPS
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: http-redirect
  namespace: dev
spec:
  parentRefs:
  - name: prod-gateway
    namespace: infra
    sectionName: http       # attach only to the HTTP listener
  hostnames:
  - "app.example.com"
  rules:
  - filters:
    - type: RequestRedirect
      requestRedirect:
        scheme: https
        statusCode: 301
```

---

## Example 3: HTTPRoute with 90/10 Traffic Split (Canary Deployment)

Deploy v2 of your application and send 10% of users to it. Increase gradually until confident.

```yaml
---
# Stable version service
apiVersion: v1
kind: Service
metadata:
  name: app-stable
  namespace: dev
spec:
  selector:
    app: myapp
    version: stable
  ports:
  - port: 8080
    targetPort: 8080

---
# Canary version service
apiVersion: v1
kind: Service
metadata:
  name: app-canary
  namespace: dev
spec:
  selector:
    app: myapp
    version: canary
  ports:
  - port: 8080
    targetPort: 8080

---
# HTTPRoute with weighted traffic split
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: canary-split
  namespace: dev
spec:
  parentRefs:
  - name: prod-gateway
    namespace: infra
  hostnames:
  - "app.example.com"
  rules:
  - backendRefs:
    - name: app-stable
      port: 8080
      weight: 90            # 90% of requests go here
    - name: app-canary
      port: 8080
      weight: 10            # 10% of requests go here
```

To promote the canary to 50/50, simply update the weights and reapply:

```bash
# Update weights to 50/50
kubectl patch httproute canary-split -n dev --type='json' \
  -p='[
    {"op": "replace", "path": "/spec/rules/0/backendRefs/0/weight", "value": 50},
    {"op": "replace", "path": "/spec/rules/0/backendRefs/1/weight", "value": 50}
  ]'

# Full promotion: set stable to 100, delete canary backend ref
kubectl patch httproute canary-split -n dev --type='json' \
  -p='[{"op": "replace", "path": "/spec/rules/0/backendRefs/0/weight", "value": 100}]'
```

---

## Example 4: HTTPRoute with Header-Based Routing (A/B Testing)

Route users who have the beta opt-in header to the new version. Everyone else gets the stable version.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: ab-test-route
  namespace: dev
spec:
  parentRefs:
  - name: prod-gateway
    namespace: infra
  hostnames:
  - "app.example.com"
  rules:
  # Rule 1: beta users → v2
  # Matched when X-Beta-User: true header is present
  - matches:
    - headers:
      - name: X-Beta-User
        value: "true"
        type: Exact
    backendRefs:
    - name: app-v2-svc
      port: 8080
    # Inject a response header so the client knows which version served them
    filters:
    - type: ResponseHeaderModifier
      responseHeaderModifier:
        add:
        - name: X-Served-By
          value: "v2"

  # Rule 2: internal QA team → v2 (match by header prefix using Regex)
  - matches:
    - headers:
      - name: X-User-Email
        value: ".*@qa.example.com"
        type: RegularExpression
    backendRefs:
    - name: app-v2-svc
      port: 8080

  # Rule 3: specific cookie → v2 (match query param)
  - matches:
    - queryParams:
      - name: version
        value: "2"
    backendRefs:
    - name: app-v2-svc
      port: 8080

  # Rule 4: default → v1 (everyone else)
  - backendRefs:
    - name: app-v1-svc
      port: 8080
    filters:
    - type: ResponseHeaderModifier
      responseHeaderModifier:
        add:
        - name: X-Served-By
          value: "v1"
```

---

## Example 5: Migrating an Existing Ingress to HTTPRoute

### Before: Ingress with nginx annotations

```yaml
# Old Ingress — nginx-specific, not portable
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  namespace: dev
  annotations:
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/rewrite-target: /$2
    nginx.ingress.kubernetes.io/canary: "true"
    nginx.ingress.kubernetes.io/canary-weight: "10"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-connect-timeout: "30"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
spec:
  tls:
  - hosts:
    - app.example.com
    secretName: prod-tls-cert
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /api(/|$)(.*)
        pathType: Prefix
        backend:
          service:
            name: backend-svc
            port:
              number: 8080
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-svc
            port:
              number: 3000
```

### After: Gateway API (portable, no annotations)

```yaml
# New HTTPRoute — works on any conformant controller
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: app-routes
  namespace: dev
  # No annotations needed — everything is in the spec
spec:
  parentRefs:
  - name: prod-gateway
    namespace: infra         # TLS is configured on the Gateway, not here
  hostnames:
  - "app.example.com"
  rules:
  # Path: /api/* → backend, strip /api prefix
  # (replaces rewrite-target annotation)
  - matches:
    - path:
        type: PathPrefix
        value: /api
    filters:
    - type: URLRewrite
      urlRewrite:
        path:
          type: ReplacePrefixMatch
          replacePrefixMatch: /
    # Canary split (replaces canary-weight annotation)
    backendRefs:
    - name: backend-svc
      port: 8080
      weight: 90
    - name: backend-svc-canary
      port: 8080
      weight: 10

  # Path: / → frontend
  - matches:
    - path:
        type: PathPrefix
        value: /
    backendRefs:
    - name: frontend-svc
      port: 3000

---
# HTTP → HTTPS redirect (replaces ssl-redirect annotation)
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: https-redirect
  namespace: dev
spec:
  parentRefs:
  - name: prod-gateway
    namespace: infra
    sectionName: http
  hostnames:
  - "app.example.com"
  rules:
  - filters:
    - type: RequestRedirect
      requestRedirect:
        scheme: https
        statusCode: 301
```

### Migration notes

```
nginx annotation                          HTTPRoute equivalent
─────────────────────────────────────────────────────────────
rewrite-target: /$2                  →   URLRewrite filter
canary-weight: "10"                  →   weight: 10 on backendRef
ssl-redirect: "true"                 →   RequestRedirect filter (HTTP listener)
proxy-connect-timeout: "30"          →   BackendLBPolicy (experimental) or controller config
proxy-body-size: "50m"               →   Gateway-level config or BackendTLSPolicy
```

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
