# eBPF and Cilium — Cheatsheet

## Install Cilium CLI

```bash
CILIUM_CLI_VERSION=v0.16.0
curl -L --fail --remote-name-all \
  https://github.com/cilium/cilium-cli/releases/download/${CILIUM_CLI_VERSION}/cilium-linux-amd64.tar.gz
sudo tar xzvf cilium-linux-amd64.tar.gz -C /usr/local/bin
```

---

## Install Cilium (Helm — Production)

```bash
helm repo add cilium https://helm.cilium.io/
helm repo update

# EKS with ENI mode (replaces kube-proxy, enables Hubble)
helm install cilium cilium/cilium \
  --version 1.16.0 \
  --namespace kube-system \
  --set eni.enabled=true \
  --set ipam.mode=eni \
  --set kubeProxyReplacement=true \
  --set hubble.enabled=true \
  --set hubble.relay.enabled=true \
  --set hubble.ui.enabled=true

# Verify installation
cilium status --wait
cilium connectivity test
```

---

## Key Helm Values Reference

```yaml
# kube-proxy replacement (no more iptables for Services)
kubeProxyReplacement: true

# Hubble network observability
hubble:
  enabled: true
  relay:
    enabled: true
  ui:
    enabled: true

# WireGuard encryption for pod-to-pod traffic
encryption:
  enabled: true
  type: wireguard

# Cilium hostNetwork policy (also protect host processes)
hostFirewall:
  enabled: true

# BPF masquerading (faster than iptables-based masquerading)
bpf:
  masquerade: true

# Tetragon runtime security
tetragon:
  enabled: true
```

---

## Cilium CLI Commands

```bash
# Check overall Cilium health
cilium status

# Run built-in connectivity test (end-to-end network validation)
cilium connectivity test

# Check which pods are managed by Cilium (Endpoints)
kubectl get ciliumnodes
kubectl get ciliumendpoints -A

# Check NetworkPolicy enforcement status
kubectl get ciliumnetworkpolicies -A

# Restart Cilium DaemonSet (e.g., after config change)
kubectl rollout restart daemonset cilium -n kube-system

# Check Cilium config
kubectl get configmap cilium-config -n kube-system -o yaml
```

---

## Standard Kubernetes NetworkPolicy (works with Cilium)

```yaml
# Allow only frontend to access backend on port 8080
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
```

---

## CiliumNetworkPolicy: L7 HTTP (Cilium-specific)

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: l7-http-policy
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    toPorts:
    - ports:
      - port: "8080"
        protocol: TCP
      rules:
        http:
        # Allow GET /api/* only
        - method: GET
          path: /api/.*
        # Allow POST /api/orders only
        - method: POST
          path: /api/orders
```

---

## CiliumNetworkPolicy: DNS Filtering

```yaml
# Allow backend to reach only specific external domains
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: dns-allow-specific
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      app: backend
  egress:
  # Allow DNS resolution
  - toEndpoints:
    - matchLabels:
        io.kubernetes.pod.namespace: kube-system
        k8s-app: kube-dns
    toPorts:
    - ports:
      - port: "53"
        protocol: UDP
      rules:
        dns:
        - matchPattern: "*.mycompany.com"
        - matchPattern: "api.stripe.com"
  # Allow HTTPS to matched domains
  - toFQDNs:
    - matchPattern: "*.mycompany.com"
    - matchName: "api.stripe.com"
    toPorts:
    - ports:
      - port: "443"
        protocol: TCP
```

---

## Hubble CLI

```bash
# Install Hubble CLI
HUBBLE_VERSION=v0.13.0
curl -L --fail --remote-name-all \
  https://github.com/cilium/hubble/releases/download/${HUBBLE_VERSION}/hubble-linux-amd64.tar.gz
sudo tar xzvf hubble-linux-amd64.tar.gz -C /usr/local/bin

# Open port-forward to Hubble relay
cilium hubble port-forward &

# View live flows (all traffic in cluster)
hubble observe --follow

# Filter by namespace
hubble observe --namespace production --follow

# Filter by pod
hubble observe --pod production/api-xxx --follow

# Filter dropped traffic (NetworkPolicy denials)
hubble observe --verdict DROPPED --follow

# Filter HTTP traffic only
hubble observe --protocol http --follow

# Show flows with L7 details
hubble observe --output json | jq '.flow.l7'

# Open Hubble UI in browser
cilium hubble ui
```

---

## Tetragon

```bash
# Install Tetragon
helm repo add cilium https://helm.cilium.io/
helm install tetragon cilium/tetragon \
  --namespace kube-system

# View security events
kubectl exec -n kube-system -l app.kubernetes.io/name=tetragon \
  -c tetragon -- tetra getevents -o compact --pods my-pod

# Watch process execution events
kubectl exec -n kube-system -l app.kubernetes.io/name=tetragon \
  -c tetragon -- tetra getevents --event-types PROCESS_EXEC
```

---

## eBPF Quick Facts

| Fact | Detail |
|---|---|
| Kernel requirement | Linux 4.8+ (basic); 5.3+ (recommended for Cilium) |
| Verification | Kernel verifier ensures safety before execution |
| Performance | O(1) hash map lookups vs O(n) iptables chains |
| Hook points | XDP, tc, kprobes, tracepoints, syscall hooks |
| Languages | C (compiled to BPF bytecode), Rust, Go (libbpf-go) |

---

## CNI Comparison at a Glance

| | Flannel | Calico | Cilium |
|---|---|---|---|
| L7 policy | No | No | Yes |
| kube-proxy replacement | No | Partial | Full |
| Observability | None | Limited | Full (Hubble) |
| Encryption | No | Yes | Yes (WireGuard) |
| Runtime security | No | No | Tetragon |
| Performance | Moderate | Good | Excellent |

---

## 📂 Navigation

| | Link |
|---|---|
| ⬅️ Prev | [Karpenter](../33_Karpenter_Node_Autoprovisioning/Interview_QA.md) |
| Theory | [eBPF and Cilium Theory](./Theory.md) |
| Interview Q&A | [eBPF and Cilium Interview Q&A](./Interview_QA.md) |
| ➡️ Next | [Ephemeral Containers](../35_Ephemeral_Containers_and_Debug/Theory.md) |
- [Cheatsheet.md](./Cheatsheet.md) — Quick reference
- [Interview_QA.md](./Interview_QA.md) — Common interview questions
