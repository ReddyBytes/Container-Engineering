# eBPF and Cilium — Code Examples

All examples are production-quality with detailed comments explaining every decision.

---

## 1. Installing Cilium and Replacing kube-proxy

```bash
# --- Install the Cilium CLI ---
CILIUM_CLI_VERSION=$(curl -s https://raw.githubusercontent.com/cilium/cilium-cli/main/stable.txt)
curl -L --fail --remote-name-all \
  https://github.com/cilium/cilium-cli/releases/download/${CILIUM_CLI_VERSION}/cilium-linux-amd64.tar.gz
tar xzvf cilium-linux-amd64.tar.gz -C /usr/local/bin
rm cilium-linux-amd64.tar.gz

# --- Install Cilium on a new cluster (replacing kube-proxy entirely) ---
# --kubeProxyReplacement=true: Cilium takes over ALL kube-proxy functions via eBPF
# This removes the iptables-based O(n) packet walking and replaces it with O(1) hash maps
cilium install --version 1.16.0 \
  --set kubeProxyReplacement=true \       # disable kube-proxy, use eBPF for Service load balancing
  --set hubble.enabled=true \             # enable Hubble for network observability
  --set hubble.relay.enabled=true \       # Hubble relay aggregates flows from all nodes
  --set hubble.ui.enabled=true            # Hubble UI: visual service dependency map

# --- Wait for Cilium to become healthy ---
cilium status --wait
# All agents should show: OK

# --- Run the built-in connectivity test (verifies pod-to-pod, pod-to-service, etc.) ---
cilium connectivity test
# This takes 5-10 minutes and tests ~50 different network scenarios.
# All should pass before the cluster accepts production traffic.

# --- Verify kube-proxy is NOT running (since Cilium replaced it) ---
kubectl get pods -n kube-system | grep kube-proxy
# Expected: no output — kube-proxy is gone
```

```bash
# --- Install Cilium on EKS via Helm (production setup) ---
# EKS uses AWS VPC CNI by default; this installs Cilium for NetworkPolicy enforcement
# while keeping the VPC CNI for IPAM (pod IPs from VPC subnet ranges)
helm repo add cilium https://helm.cilium.io/
helm repo update

helm install cilium cilium/cilium \
  --version 1.16.0 \
  --namespace kube-system \
  --set eni.enabled=true \               # use AWS ENI for pod IPs (keeps VPC routing)
  --set ipam.mode=eni \                  # IPAM via ENI, not Cilium's own IPAM
  --set egressMasqueradeInterfaces=eth0 \
  --set kubeProxyReplacement=true \
  --set k8sServiceHost=<API_SERVER_ENDPOINT> \  # EKS API server endpoint
  --set k8sServicePort=443 \
  --set hubble.enabled=true \
  --set hubble.relay.enabled=true \
  --set hubble.metrics.enabled="{dns,drop,tcp,flow,port-distribution,icmp,http}"
  # hubble.metrics: exposes Prometheus metrics on port 9091 for each metric type
```

---

## 2. CiliumNetworkPolicy: L7 HTTP-Aware Traffic Control

```yaml
# l7-network-policy.yaml
# Standard Kubernetes NetworkPolicy only allows/denies at L3/L4 (IP + port).
# CiliumNetworkPolicy can inspect the actual HTTP request (method, path, headers).
# This policy allows frontend pods to GET /api/* from backend,
# but rejects POST /admin (even though the port is the same).
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: backend-api-policy
  namespace: production
spec:
  # Apply this policy to pods matching this selector
  endpointSelector:
    matchLabels:
      app: backend
      tier: api

  # Define what ingress traffic is allowed
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend                    # only allow traffic from frontend pods
    toPorts:
    - ports:
      - port: "8080"
        protocol: TCP
      rules:
        http:
        # Rule 1: allow GET requests to the public API
        - method: GET
          path: /api/.*                  # regex — matches /api/v1/orders, /api/v2/items, etc.
        # Rule 2: allow POST to a specific safe endpoint only
        - method: POST
          path: /api/v1/events
          headers:                       # also require a specific header (optional)
          - "X-Request-Source: frontend"
        # Note: POST /admin is NOT listed here — it will be rejected at the kernel level

  # Allow Prometheus to scrape metrics (from the monitoring namespace)
  - fromEndpoints:
    - matchLabels:
        app: prometheus
        namespace: monitoring
    toPorts:
    - ports:
      - port: "9091"
        protocol: TCP

  # Define what egress traffic backend pods are allowed to make
  egress:
  - toEndpoints:
    - matchLabels:
        app: postgres                    # can only talk to postgres
    toPorts:
    - ports:
      - port: "5432"
        protocol: TCP
  - toEndpoints:
    - matchLabels:
        app: redis-cache
    toPorts:
    - ports:
      - port: "6379"
        protocol: TCP
  # Allow DNS resolution (required for any service discovery to work)
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
    toPorts:
    - ports:
      - port: "53"
        protocol: UDP
      rules:
        dns:
        - matchPattern: "*"             # allow DNS queries for any hostname
```

```bash
# Apply the policy
kubectl apply -f l7-network-policy.yaml

# Verify what policies are applied to a pod
kubectl exec -n production deploy/frontend -- curl -s http://backend:8080/api/v1/orders
# Expected: 200 OK (GET to /api/* is allowed)

kubectl exec -n production deploy/frontend -- curl -s -X POST http://backend:8080/admin/users
# Expected: Access Denied (POST to /admin is not in the policy)

# View all CiliumNetworkPolicies in the cluster
kubectl get ciliumnetworkpolicies -A
```

---

## 3. Hubble: Real-Time Network Flow Observability

```bash
# --- Install Hubble CLI ---
HUBBLE_VERSION=v0.13.0
curl -L --fail --remote-name-all \
  https://github.com/cilium/hubble/releases/download/${HUBBLE_VERSION}/hubble-linux-amd64.tar.gz
tar xzvf hubble-linux-amd64.tar.gz -C /usr/local/bin
rm hubble-linux-amd64.tar.gz

# --- Enable port-forward to the Hubble relay (aggregates flows from all nodes) ---
cilium hubble port-forward &

# Verify Hubble can observe the cluster
hubble status
# Expected: Receiving flows: Yes | Max flows/node: ...

# --- Live traffic inspection ---

# Watch all network flows in real time (every connection in the cluster)
hubble observe --follow

# Watch flows for a specific pod (debugging network issues)
hubble observe --pod production/payments-api-abc123 --follow

# Watch only HTTP traffic with details
hubble observe --protocol http --follow
# Output shows: source pod → destination pod, HTTP method, path, status code, latency

# Watch dropped flows (policy violations, connection errors)
hubble observe --verdict DROPPED --follow
# Use this to debug why traffic is being blocked — shows which policy dropped it

# Watch DNS queries (useful for debugging service discovery failures)
hubble observe --protocol dns --follow

# --- Historical flow query ---

# Show the last 100 flows to a specific service
hubble observe \
  --to-pod production/postgres-0 \
  --last 100

# Show flows that were dropped in the last 5 minutes
hubble observe \
  --since 5m \
  --verdict DROPPED \
  --namespace production

# Show HTTP flows with status codes >= 500 (errors)
hubble observe \
  --namespace production \
  --protocol http \
  --follow | grep "status=5"             # filter at shell level

# --- Open the Hubble UI (service dependency map) ---
cilium hubble ui
# Opens a browser with a real-time graph showing:
# - Which services communicate with each other
# - Traffic rates and error rates per edge
# - Dropped flows highlighted in red
# - Click any service to see all its inbound/outbound connections
```

---

## 4. Transparent Encryption with WireGuard

```bash
# --- Enable WireGuard encryption for all pod-to-pod traffic ---
# All traffic between nodes is encrypted at the kernel level.
# No TLS certificates, no service mesh, no application changes required.

# Install Cilium with WireGuard enabled
helm upgrade cilium cilium/cilium \
  --version 1.16.0 \
  --namespace kube-system \
  --reuse-values \
  --set encryption.enabled=true \
  --set encryption.type=wireguard        # uses Linux kernel WireGuard (since kernel 5.6)

# --- Verify encryption is active ---
# Check that Cilium agents report WireGuard as active
kubectl -n kube-system exec ds/cilium -- cilium encrypt status
# Output shows:
# Encryption: WireGuard
# Keys in use: 1
# Number of peers: <number of other nodes>

# Verify a specific node's WireGuard interface
kubectl -n kube-system exec ds/cilium -- wg show
# Shows: interface name, public key, peers, and traffic counters

# Check that inter-node traffic is encrypted
# Pick two pods on DIFFERENT nodes
POD_A=$(kubectl get pods -n production -l app=frontend -o jsonpath='{.items[0].metadata.name}')
NODE_A=$(kubectl get pod "$POD_A" -n production -o jsonpath='{.spec.nodeName}')
echo "Frontend pod on node: $NODE_A"

POD_B=$(kubectl get pods -n production -l app=backend -o jsonpath='{.items[0].metadata.name}')
NODE_B=$(kubectl get pod "$POD_B" -n production -o jsonpath='{.spec.nodeName}')
echo "Backend pod on node: $NODE_B"

# If NODE_A != NODE_B, traffic between them is encrypted over WireGuard
# Verify by watching WireGuard counters increase during a test call:
kubectl -n kube-system exec ds/cilium --node-selector=kubernetes.io/hostname="$NODE_A" \
  -- wg show | grep "transfer"
kubectl exec -n production "$POD_A" -- curl http://backend:8080/health
kubectl -n kube-system exec ds/cilium --node-selector=kubernetes.io/hostname="$NODE_A" \
  -- wg show | grep "transfer"          # transfer bytes should increase
```

---

## 5. Tetragon: Runtime Security Enforcement

```bash
# --- Install Tetragon ---
helm repo add cilium https://helm.cilium.io/
helm install tetragon cilium/tetragon \
  --namespace kube-system

# Verify Tetragon is running on all nodes
kubectl get pods -n kube-system -l app.kubernetes.io/name=tetragon
```

```yaml
# tetragon-policy-passwd.yaml
# Alert (and optionally kill) any process inside a container that reads /etc/passwd or /etc/shadow.
# Legitimate applications never need to read these files — it signals a recon attempt.
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: detect-sensitive-file-read
spec:
  kprobes:
  - call: "security_file_open"           # hook into the kernel's file open security check
    syscall: false
    args:
    - index: 0
      type: "file"
    selectors:
    - matchArgs:
      - index: 0
        operator: "Prefix"
        values:
        - "/etc/passwd"
        - "/etc/shadow"
        - "/etc/sudoers"
        - "/root/.ssh"                   # also alert on SSH key reads
      matchActions:
      - action: Sigkill                  # immediately kill the offending process
      # Use action: Post to just log it without killing (for initial rollout)
---
# tetragon-policy-network-bind.yaml
# Detect any process that binds a raw socket (common in cryptomining and network scanning tools)
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: detect-raw-socket
spec:
  kprobes:
  - call: "sys_socket"
    syscall: true
    args:
    - index: 0
      type: int
    - index: 1
      type: int
    selectors:
    - matchArgs:
      - index: 1
        operator: "Equal"
        values: ["3"]                    # SOCK_RAW = 3 — raw sockets bypass normal filtering
      matchActions:
      - action: Post                     # log the event (investigate before killing)
```

```bash
# Apply the TracingPolicies
kubectl apply -f tetragon-policy-passwd.yaml
kubectl apply -f tetragon-policy-network-bind.yaml

# --- Watch for security events in real time ---
kubectl exec -n kube-system ds/tetragon -c tetragon \
  -- tetra getevents -o compact --pods production/payments-api-xxx

# Output format (when a policy triggers):
# TYPE     PROCESS                   PARENT    FILENAME
# KPROBE   payments-api (pid 1234)   bash      /etc/passwd     ← ALERT

# Export events to JSON for SIEM ingestion
kubectl exec -n kube-system ds/tetragon -c tetragon \
  -- tetra getevents \
  --output json \
  --pods production/ > /tmp/security-events.json

# View all TracingPolicies and their status
kubectl get tracingpolicies
```

---

## 📂 Navigation

**In this folder:**
| File | |
|---|---|
| [Theory.md](./Theory.md) | Full explanation |
| [Cheatsheet.md](./Cheatsheet.md) | Quick reference |
| [Interview_QA.md](./Interview_QA.md) | Interview prep |
| **Code_Example.md** | you are here |

⬅️ **Prev:** [Karpenter](../33_Karpenter_Node_Autoprovisioning/Code_Example.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Ephemeral Containers and Debug](../35_Ephemeral_Containers_and_Debug/Code_Example.md)
🏠 **[Home](../../README.md)**
