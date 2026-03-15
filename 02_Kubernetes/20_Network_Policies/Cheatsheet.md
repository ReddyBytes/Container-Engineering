# Network Policies Cheatsheet

## Core Concepts Quick Reference

| Concept | Meaning |
|---------|---------|
| Default behavior | All pods can reach all pods — no restrictions |
| NetworkPolicy | Whitelist-based firewall rules for pods |
| Ingress rule | Which sources can send traffic TO the selected pods |
| Egress rule | Where the selected pods can send traffic |
| podSelector `{}` | Selects ALL pods in the namespace |
| policyTypes | Which directions to control: Ingress, Egress, or both |
| Default-deny effect | Adding any policy that selects a pod switches it to deny-by-default |

---

## kubectl Commands

```bash
# --- Viewing Network Policies ---

# List all NetworkPolicies in a namespace
kubectl get networkpolicies -n <namespace>
kubectl get netpol -n <namespace>           # short form

# List NetworkPolicies across all namespaces
kubectl get netpol -A

# Describe a specific policy (see ingress/egress rules)
kubectl describe netpol <name> -n <namespace>

# View policy as YAML
kubectl get netpol <name> -n <namespace> -o yaml

# --- Checking Labels ---

# List pod labels (must match your podSelector)
kubectl get pods -n <namespace> --show-labels

# List namespace labels (must match your namespaceSelector)
kubectl get namespaces --show-labels

# Label a namespace for use in namespaceSelector
kubectl label namespace <name> team=payments
kubectl label namespace <name> environment=production

# --- Testing Connectivity ---

# Run a temporary test pod for connectivity testing
kubectl run nettest \
  --image=busybox:1.36 \
  --rm -it \
  --restart=Never \
  -n <namespace> \
  -- sh

# From inside the test pod:
# wget -qO- --timeout=5 http://backend-service:8080
# nc -zv database-service 5432
# nslookup kubernetes.default.svc.cluster.local

# Test connectivity from an existing pod
kubectl exec -it <pod-name> -n <namespace> -- \
  curl -s --connect-timeout 5 http://<target>:<port>

# Test DNS resolution
kubectl exec -it <pod-name> -n <namespace> -- \
  nslookup kubernetes.default.svc.cluster.local

# --- Checking CNI Support ---

# Which CNI is running (NetworkPolicy requires Calico/Cilium/Weave/Antrea)
kubectl get pods -n kube-system | grep -Ei "calico|cilium|weave|antrea"

# --- Cilium-specific debugging ---

# List endpoint policy enforcement state
kubectl exec -n kube-system ds/cilium -- cilium endpoint list

# Inspect policy for a specific endpoint
kubectl exec -n kube-system ds/cilium -- cilium policy get

# Check Cilium network policies
kubectl get ciliumnetworkpolicies -A

# --- Calico-specific debugging ---

# List Calico network policies
kubectl get networkpolicies.crd.projectcalico.org -A

# List global (cluster-scoped) Calico policies
kubectl get globalnetworkpolicies.crd.projectcalico.org

# Inspect using calicoctl
calicoctl get networkpolicy -n <namespace>
```

---

## NetworkPolicy YAML Quick Reference

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: example-policy
  namespace: my-namespace
spec:
  podSelector:            # which pods this policy applies TO
    matchLabels:
      app: backend        # use {} to select ALL pods in namespace

  policyTypes:
    - Ingress
    - Egress

  ingress:
    - from:
        - podSelector:           # from pods with this label (same namespace)
            matchLabels:
              app: frontend
        - namespaceSelector:     # OR from any pod in this namespace
            matchLabels:
              team: monitoring
      ports:
        - protocol: TCP
          port: 8080

  egress:
    - to:
        - podSelector:
            matchLabels:
              app: database
      ports:
        - protocol: TCP
          port: 5432
    - ports:               # allow DNS (always include this!)
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
```

---

## Key Patterns

### Pattern 1: Default Deny All (Start Here)

```yaml
# Apply this FIRST to every production namespace
kubectl apply -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: my-namespace
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
EOF
```

### Pattern 2: Allow DNS Egress (Apply Immediately After Deny-All)

```yaml
kubectl apply -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns-egress
  namespace: my-namespace
spec:
  podSelector: {}
  policyTypes: [Egress]
  egress:
    - ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
EOF
```

### Pattern 3: Allow Specific Pod-to-Pod Traffic

```yaml
kubectl apply -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: my-namespace
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080
EOF
```

### Pattern 4: Allow Cross-Namespace (Monitoring Scraping)

```yaml
kubectl apply -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-monitoring-scrape
  namespace: my-namespace
spec:
  podSelector:
    matchLabels:
      monitoring: "true"
  policyTypes: [Ingress]
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: monitoring
          podSelector:
            matchLabels:
              app: prometheus
      ports:
        - protocol: TCP
          port: 9090
EOF
```

### Pattern 5: Namespace Isolation (Same Namespace Only)

```yaml
kubectl apply -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-same-namespace
  namespace: my-namespace
spec:
  podSelector: {}
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector: {}   # empty = all pods in SAME namespace
EOF
```

---

## AND vs OR Logic in Selectors

```yaml
# AND: pod must be in the monitoring namespace AND have app=prometheus label
ingress:
  - from:
      - namespaceSelector:        # same list item, no extra dash
          matchLabels:
            kubernetes.io/metadata.name: monitoring
        podSelector:
          matchLabels:
            app: prometheus

# OR: allow from monitoring namespace, OR allow from pods with app=prometheus label
ingress:
  - from:
      - namespaceSelector:        # separate list items with their own dashes
          matchLabels:
            kubernetes.io/metadata.name: monitoring
      - podSelector:
          matchLabels:
            app: prometheus
```

---

## CNI Plugin Support

| CNI | NetworkPolicy Support | Notes |
|-----|-----------------------|-------|
| Calico | Full | Most common in self-managed clusters |
| Cilium | Full + L7 extensions | eBPF-based, most powerful |
| Weave Net | Full | Simpler setup |
| Antrea | Full | VMware-backed |
| Flannel | None | Policies silently ignored |
| kubenet | None | Too simple |

---

## When to Use What

| Situation | Solution |
|-----------|----------|
| Lock down a new namespace | Apply `default-deny-all` + `allow-dns-egress` |
| Allow frontend to reach backend | NetworkPolicy on backend allowing frontend podSelector |
| Allow Prometheus to scrape all pods | NetworkPolicy on target pods allowing monitoring namespace |
| Allow traffic from specific IP range | Use `ipBlock` with CIDR |
| Need L7 (HTTP path) filtering | Use Cilium `CiliumNetworkPolicy` or service mesh |
| Need mutual TLS between services | Use service mesh (Istio, Linkerd) |

---

## 📂 Navigation

⬅️ **Prev:** [Resource Quotas and Limits](../19_Resource_Quotas_and_Limits/Interview_QA.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Service Accounts](../21_Service_Accounts/Theory.md)

| | Link |
|---|---|
| Theory | [Theory.md](./Theory.md) |
| Interview Q&A | [Interview_QA.md](./Interview_QA.md) |
