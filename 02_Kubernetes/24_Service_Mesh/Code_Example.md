# Service Mesh — Code Examples

All examples are production-quality with detailed comments explaining every decision.

---

## 1. Install Istio and Enable Sidecar Injection

```bash
# Step 1: Download the Istio CLI (istioctl)
curl -L https://istio.io/downloadIstio | sh -
cd istio-1.*                             # ← enter the downloaded directory
export PATH=$PWD/bin:$PATH               # ← add istioctl to PATH

# Step 2: Install Istio on the cluster (demo profile includes all features; use minimal for production)
istioctl install \
  --set profile=demo \                   # ← demo: good for learning; production: use "default" or "minimal"
  -y                                     # ← skip the confirmation prompt

# Step 3: Verify the installation
istioctl verify-install

# Confirm the Istio control plane pods are running in istio-system
kubectl get pods -n istio-system

# Step 4: Enable automatic sidecar injection for your namespace
# Once labeled, every new pod in this namespace gets an Envoy sidecar injected automatically
kubectl label namespace production istio-injection=enabled

# Verify the label was applied
kubectl get namespace production --show-labels

# Step 5: Roll existing deployments to trigger sidecar injection
# (existing pods don't get sidecars until they restart)
kubectl rollout restart deployment -n production

# After restart, pods should show 2/2 (app container + Envoy sidecar)
kubectl get pods -n production
# NAME                       READY   STATUS    RESTARTS
# my-api-7d4f9b-xxx          2/2     Running   0         ← 2/2 = app + Envoy
```

```bash
# Istio dashboard — Kiali shows the service mesh graph
kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.20/samples/addons/kiali.yaml
kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.20/samples/addons/prometheus.yaml
kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.20/samples/addons/grafana.yaml
kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.20/samples/addons/jaeger.yaml

# Access Kiali mesh visualizer
istioctl dashboard kiali
# Access Jaeger trace UI
istioctl dashboard jaeger
```

---

## 2. Enforce mTLS — Encrypt All Service-to-Service Communication

```yaml
# mtls-strict.yaml
# Enable STRICT mTLS for the production namespace
# STRICT means: only accept connections that use mTLS — plain HTTP is rejected
# This ensures every service call is encrypted AND both sides authenticate each other

---
# PeerAuthentication: defines the mTLS mode for a namespace (or the whole mesh)
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: production                  # ← applies to all workloads in this namespace
spec:
  mtls:
    mode: STRICT                         # ← STRICT: reject plain HTTP
    # PERMISSIVE: accept both mTLS and plain HTTP (use during migration)
    # DISABLE: no mTLS

---
# DestinationRule: tells Istio to USE mTLS when sending traffic to services in this namespace
# Without this, even with STRICT PeerAuthentication, the CLIENT side might not present certs
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: production-mtls
  namespace: production
spec:
  host: "*.production.svc.cluster.local" # ← applies to all services in the production namespace
  trafficPolicy:
    tls:
      mode: ISTIO_MUTUAL                 # ← use Istio-managed certificates for mTLS
```

```bash
kubectl apply -f mtls-strict.yaml

# Verify mTLS is working between services
# Run a test pod WITHOUT a sidecar and try to call a service in production
kubectl run plain-http-test \
  --image=curlimages/curl:8.5.0 \
  -n default \                           # ← default namespace has no sidecar injection
  --restart=Never \
  -- curl http://my-api.production.svc.cluster.local/health
# This should be REJECTED because production requires mTLS and this pod has no cert

# Verify from within the mesh (pod with sidecar)
kubectl exec -n production my-api-7d4f9b-xxx -c api \
  -- curl http://payment-service.production.svc.cluster.local/health
# This works — both pods have Envoy sidecars that negotiate mTLS automatically

# Check the mTLS policy status
istioctl authn tls-check my-api-7d4f9b-xxx.production
```

---

## 3. Traffic Splitting — Canary Deployment With VirtualService

```yaml
# canary-traffic-split.yaml
# Route 90% of traffic to the stable version and 10% to the canary
# This is done entirely at the mesh level — no application code changes needed

---
# Two deployments: stable (v1) and canary (v2)
# Each has a distinct version label so Istio can target them separately
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-service-v1              # ← stable version
  namespace: production
spec:
  replicas: 5
  selector:
    matchLabels:
      app: payment-service
      version: v1                        # ← version label used by DestinationRule subsets
  template:
    metadata:
      labels:
        app: payment-service
        version: v1
    spec:
      containers:
      - name: payment
        image: payment-service:1.0.0    # ← stable release

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-service-v2              # ← canary version
  namespace: production
spec:
  replicas: 1                           # ← fewer replicas; Istio handles the traffic percentage
  selector:
    matchLabels:
      app: payment-service
      version: v2
  template:
    metadata:
      labels:
        app: payment-service
        version: v2
    spec:
      containers:
      - name: payment
        image: payment-service:2.0.0    # ← canary release

---
# DestinationRule: define subsets (groups of pods) for traffic routing
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: payment-service-dr
  namespace: production
spec:
  host: payment-service
  subsets:
  - name: v1                            # ← subset name referenced in VirtualService
    labels:
      version: v1                       # ← selects pods with this label
  - name: v2
    labels:
      version: v2

---
# VirtualService: define the traffic split percentages
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: payment-service-vs
  namespace: production
spec:
  hosts:
  - payment-service                     # ← intercepts traffic to this K8s Service
  http:
  - route:
    - destination:
        host: payment-service
        subset: v1                      # ← 90% to stable
      weight: 90
    - destination:
        host: payment-service
        subset: v2                      # ← 10% to canary
      weight: 10
```

```bash
kubectl apply -f canary-traffic-split.yaml

# Verify the VirtualService is configured correctly
kubectl describe virtualservice payment-service-vs -n production

# Watch traffic distribution — Kiali shows a real-time service graph
# istioctl dashboard kiali

# Generate traffic and observe the split
kubectl run load-test \
  --image=curlimages/curl:8.5.0 \
  -n production \
  --restart=Never \
  -- /bin/sh -c "for i in \$(seq 1 100); do curl -s http://payment-service/health; done"

# Gradually increase canary weight once it looks healthy
# Edit weight: v1=80, v2=20 → then 50/50 → then 0/100 when confident
kubectl edit virtualservice payment-service-vs -n production
```

---

## 4. Circuit Breaking and Retries — Resilience Without Code Changes

```yaml
# resilience-policies.yaml
# Circuit breaking ejects unhealthy hosts to prevent cascade failures
# Retries handle transient errors automatically at the mesh level

---
# Circuit breaker: if a pod returns 5xx errors 5 times in 30s, stop sending it traffic
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: payment-service-circuit-breaker
  namespace: production
spec:
  host: payment-service
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100             # ← max concurrent TCP connections to any single pod
      http:
        h2UpgradePolicy: UPGRADE
        http1MaxPendingRequests: 100    # ← max queued requests waiting for a connection
        http2MaxRequests: 1000          # ← max active requests to the service
    outlierDetection:
      consecutive5xxErrors: 5           # ← eject a pod after 5 consecutive 5xx responses
      interval: 30s                     # ← check for failures every 30 seconds
      baseEjectionTime: 30s             # ← eject the pod for 30 seconds minimum
      maxEjectionPercent: 50            # ← never eject more than 50% of pods at once
      # ← this prevents the circuit breaker from taking out the entire service

---
# Retry policy: automatically retry failed requests before returning an error to the client
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: payment-service-retries
  namespace: production
spec:
  hosts:
  - payment-service
  http:
  - timeout: 10s                        # ← total timeout for the request (including retries)
    retries:
      attempts: 3                       # ← retry up to 3 times
      perTryTimeout: 2s                 # ← each attempt must complete within 2s
      retryOn: 5xx,reset,connect-failure,retriable-4xx
      # ← retry on: 5xx errors, connection resets, connection failures, 499 status
    route:
    - destination:
        host: payment-service
```

```bash
kubectl apply -f resilience-policies.yaml

# Simulate a failing pod and watch the circuit breaker in action
# Scale down one pod and inject a fault into another
kubectl apply -f - <<EOF
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: payment-fault-injection
  namespace: production
spec:
  hosts:
  - payment-service
  http:
  - fault:
      abort:
        percentage:
          value: 30                     # ← inject 30% HTTP 500 errors for testing
        httpStatus: 500
    route:
    - destination:
        host: payment-service
EOF

# Watch Istio metrics to see retries and circuit breaker trips
# istio_requests_total{response_code="500"} — should be low due to retries
# istio_requests_total{response_flags="UO"} — UO = upstream overflow (circuit breaker open)

# Remove the fault injection after testing
kubectl delete virtualservice payment-fault-injection -n production
```

---

## 5. Istio Observability — Golden Signals From the Mesh

```bash
# Istio generates these metrics automatically for every service — no app code needed:
# istio_requests_total         — request count (with labels: source, destination, status code)
# istio_request_duration_milliseconds — latency histogram
# istio_request_bytes          — request size
# istio_response_bytes         — response size

# --- PromQL queries for Istio metrics ---

# Request rate per second for the payment-service (last 5 minutes)
# rate(istio_requests_total{destination_service_name="payment-service", reporter="destination"}[5m])

# Error rate percentage
# rate(istio_requests_total{destination_service_name="payment-service", response_code=~"5.."}[5m])
# /
# rate(istio_requests_total{destination_service_name="payment-service"}[5m]) * 100

# p99 latency in milliseconds
# histogram_quantile(0.99,
#   rate(istio_request_duration_milliseconds_bucket{
#     destination_service_name="payment-service"
#   }[5m])
# )

# --- View distributed traces in Jaeger ---
istioctl dashboard jaeger
# In the Jaeger UI: select "payment-service" from the Service dropdown
# Each trace shows every hop the request took through the mesh
# Click a slow trace to see which service added the latency

# --- Use istioctl for mesh-level diagnostics ---

# Check proxy status for all sidecars
istioctl proxy-status

# Inspect the Envoy configuration for a specific pod
istioctl proxy-config cluster my-api-7d4f9b-xxx.production

# Analyze the mesh configuration for misconfigurations
istioctl analyze -n production

# Check which version of Envoy is running in each sidecar
kubectl get pods -n production \
  -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[?(@.name=="istio-proxy")].image}{"\n"}{end}'
```

---

## 📂 Navigation

**In this folder:**
| File | |
|---|---|
| [📖 Theory.md](./Theory.md) | Full explanation |
| [⚡ Cheatsheet.md](./Cheatsheet.md) | Quick reference |
| [🎯 Interview_QA.md](./Interview_QA.md) | Interview prep |
| 💻 **Code_Example.md** | ← you are here |

⬅️ **Prev:** [Security](../23_Security/Code_Example.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [GitOps and CI/CD](../25_GitOps_and_CICD/Code_Example.md)
🏠 **[Home](../../README.md)**
