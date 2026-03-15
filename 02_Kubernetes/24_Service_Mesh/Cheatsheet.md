# Module 24 — Service Mesh Cheatsheet

## Core Concepts

| Concept | Description |
|---|---|
| Sidecar proxy | Envoy container injected into every pod; intercepts all traffic |
| Control plane | Istiod — distributes config, manages certificates |
| Data plane | All the Envoy proxies running in pods |
| mTLS | Mutual TLS — both sides authenticate; traffic encrypted |
| VirtualService | Istio CRD — defines routing rules (weights, retries, timeouts) |
| DestinationRule | Istio CRD — traffic policy for a destination (circuit breaking, load balancing) |
| PeerAuthentication | Istio CRD — enforce mTLS mode per namespace or service |

---

## Istio Installation

```bash
# Download and install istioctl
curl -L https://istio.io/downloadIstio | sh -
cd istio-*
export PATH=$PWD/bin:$PATH

# Install Istio (demo profile includes extras like Kiali, Jaeger)
istioctl install --set profile=demo -y

# Minimal production install
istioctl install --set profile=minimal -y

# Verify installation
istioctl verify-install
istioctl analyze

# Enable sidecar injection for a namespace
kubectl label namespace production istio-injection=enabled

# Check if sidecars are injected (should show 2/2)
kubectl get pods -n production
```

---

## mTLS Configuration

```yaml
# Enforce strict mTLS across a namespace
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: production
spec:
  mtls:
    mode: STRICT    # STRICT | PERMISSIVE | DISABLE

---
# Per-service mTLS policy
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: payment-strict
  namespace: production
spec:
  selector:
    matchLabels:
      app: payment-service
  mtls:
    mode: STRICT
```

---

## Traffic Splitting (Canary)

```yaml
# DestinationRule: define subsets
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: payment-service
spec:
  host: payment-service
  subsets:
  - name: stable
    labels:
      version: v1
  - name: canary
    labels:
      version: v2

---
# VirtualService: route weights
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: payment-service
spec:
  hosts:
  - payment-service
  http:
  - route:
    - destination:
        host: payment-service
        subset: stable
      weight: 90
    - destination:
        host: payment-service
        subset: canary
      weight: 10
```

---

## Retries and Timeouts

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: myapp
spec:
  hosts:
  - myapp
  http:
  - timeout: 5s
    retries:
      attempts: 3
      perTryTimeout: 2s
      retryOn: 5xx,reset,connect-failure,retriable-4xx
    route:
    - destination:
        host: myapp
```

---

## Circuit Breaking

```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: payment-service
spec:
  host: payment-service
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 1000
        maxRequestsPerConnection: 1
    outlierDetection:
      consecutive5xxErrors: 5     # eject after 5 errors
      interval: 30s               # evaluation window
      baseEjectionTime: 30s       # ejection duration
      maxEjectionPercent: 100
```

---

## Authorization Policy (mTLS + RBAC)

```yaml
# Only allow frontend to call payment service
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: payment-authz
  namespace: production
spec:
  selector:
    matchLabels:
      app: payment-service
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/production/sa/frontend-sa"]
    to:
    - operation:
        methods: ["POST"]
        paths: ["/payment/*"]
```

---

## Linkerd Installation

```bash
# Install Linkerd CLI
curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install | sh

# Pre-installation check
linkerd check --pre

# Install Linkerd
linkerd install --crds | kubectl apply -f -
linkerd install | kubectl apply -f -

# Verify
linkerd check

# Inject namespace
kubectl annotate namespace production linkerd.io/inject=enabled

# Check status
linkerd viz install | kubectl apply -f -
linkerd viz dashboard
```

---

## Istio Useful Commands

```bash
# Check Istio configuration for a pod
istioctl proxy-config cluster <pod> -n <ns>
istioctl proxy-config listener <pod> -n <ns>
istioctl proxy-config route <pod> -n <ns>

# Analyze namespace for issues
istioctl analyze -n production

# Check mTLS status
istioctl authn tls-check <pod> -n <ns>

# Get Istio logs from a sidecar
kubectl logs <pod> -c istio-proxy -n <ns>

# Check Kiali dashboard (service topology)
kubectl port-forward svc/kiali 20001:20001 -n istio-system
```

---

## Mesh vs No Mesh Decision

| Need | Mesh needed? |
|---|---|
| Encrypt all service traffic (mTLS) | Yes |
| Canary/blue-green at network level | Yes |
| Zero-code distributed tracing | Yes |
| Circuit breaking without code | Yes |
| < 5 services, simple app | Likely no |
| Adding retries in 1 service | No (do it in code) |
| Strict resource constraints | Consider Linkerd |

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Service Mesh Theory](./Theory.md) |
| Interview Q&A | [Service Mesh Interview Q&A](./Interview_QA.md) |
| Next Module | [25 — GitOps and CI/CD](../25_GitOps_and_CICD/Theory.md) |
