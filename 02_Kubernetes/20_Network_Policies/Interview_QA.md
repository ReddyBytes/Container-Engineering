# Network Policies — Interview Q&A

---

## Beginner Questions

---

**Q1: What is a NetworkPolicy in Kubernetes?**

**Answer:**

A NetworkPolicy is a Kubernetes resource that acts as a firewall for pods. It lets you define rules about which pods can send traffic to which other pods, and where pods are allowed to send traffic to. Without any NetworkPolicies, every pod in the cluster can freely communicate with every other pod — no restrictions at all.

You create a NetworkPolicy by specifying:
- **podSelector**: which pods this policy applies to
- **ingress rules**: who is allowed to send traffic TO those pods
- **egress rules**: where those pods are allowed to send traffic TO

NetworkPolicies are whitelist-based: once a pod is selected by any policy, only explicitly allowed traffic gets through. Everything else is denied.

---

**Q2: What is the default network behavior in Kubernetes — and why is it a security concern?**

**Answer:**

By default, Kubernetes uses a flat, fully open network: every pod can reach every other pod on any port, regardless of which namespace they are in. There is no network segmentation at all.

This is a security concern because:
- A compromised frontend pod can directly query the database
- Malicious or buggy code in one service can reach sensitive internal APIs in other namespaces
- There is no network-level boundary between teams or services on a shared cluster
- Lateral movement after a breach is trivially easy — an attacker who compromises one pod can probe the entire cluster

NetworkPolicies fix this by letting you restrict which pods can talk to which, following the principle of least privilege.

---

**Q3: What is the "default-deny" pattern and why is it recommended?**

**Answer:**

The default-deny pattern means applying a NetworkPolicy that selects all pods in a namespace but allows no traffic:

```yaml
spec:
  podSelector: {}        # selects ALL pods in the namespace
  policyTypes: [Ingress, Egress]
  # no ingress or egress rules = nothing is allowed
```

This is recommended because it inverts the security posture from "open by default, block what you know is bad" to "closed by default, allow only what is explicitly needed."

With default-deny:
- New pods and services are automatically isolated until deliberately opened
- Every traffic flow is intentional and auditable
- A misconfigured pod can't accidentally reach a sensitive service

The workflow is: apply default-deny first, then add specific allow policies for each traffic flow your application needs.

---

**Q4: What happens if you apply an egress default-deny policy and forget to allow DNS?**

**Answer:**

Everything breaks — and it looks nothing like a DNS problem.

DNS in Kubernetes runs as CoreDNS in the `kube-system` namespace on UDP/TCP port 53. When you apply an egress default-deny policy, pods can no longer send any outbound traffic — including DNS queries. The result: pods cannot resolve any service names or external hostnames.

The error messages you see look like connection failures ("Connection refused", "dial tcp: no such host") rather than DNS errors, which makes this one of the most confusing NetworkPolicy bugs.

The fix: always apply a DNS egress allowance immediately after applying your default-deny-egress policy:

```yaml
egress:
  - ports:
      - protocol: UDP
        port: 53
      - protocol: TCP
        port: 53
```

---

## Intermediate Questions

---

**Q5: How do you create a deny-all policy for a namespace?**

**Answer:**

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: production
spec:
  podSelector: {}         # empty = selects ALL pods in the namespace
  policyTypes:
    - Ingress
    - Egress
  # No ingress rules = deny all inbound
  # No egress rules = deny all outbound
```

This policy selects every pod in the `production` namespace and, because it specifies both `Ingress` and `Egress` in `policyTypes` but provides no rules, it denies all inbound and outbound traffic.

After applying this, you add specific allow policies for each flow you need.

---

**Q6: What CNI plugins support NetworkPolicy enforcement?**

**Answer:**

NetworkPolicy enforcement is done by the CNI (Container Network Interface) plugin — not by Kubernetes itself. Kubernetes only stores the policy objects; the CNI actually enforces them in the network.

CNI plugins that enforce NetworkPolicy:
- **Calico** — most common choice for self-managed clusters, full NetworkPolicy support
- **Cilium** — eBPF-based, most powerful; also extends NetworkPolicy with L7 HTTP/gRPC rules via `CiliumNetworkPolicy`
- **Weave Net** — full support, simpler setup
- **Antrea** — VMware-backed, full support

CNI plugins that do NOT enforce NetworkPolicy:
- **Flannel** — only handles L3 routing, no policy enforcement
- **kubenet** — too simple, no policy support

Critical gotcha: on a Flannel-based cluster, you can create NetworkPolicy objects — they are stored in etcd — but they have absolutely no effect on network traffic. This creates a dangerous false sense of security.

---

**Q7: What is the difference between podSelector and namespaceSelector?**

**Answer:**

**`podSelector`** matches pods by their labels, within the same namespace as the NetworkPolicy. For example:
```yaml
- from:
    - podSelector:
        matchLabels:
          app: frontend
```
This allows traffic from pods labeled `app: frontend` that are in the same namespace as the policy.

**`namespaceSelector`** matches all pods in namespaces that have specific labels. For example:
```yaml
- from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: monitoring
```
This allows traffic from ANY pod in the `monitoring` namespace.

**Combined (AND logic):** when both appear in the same `from` list item (no extra dash before the second one), they are ANDed — the source pod must be in a matching namespace AND have a matching label.

**Separate items (OR logic):** when they are separate `from` list items, they are ORed — either condition is sufficient.

---

**Q8: How do you allow DNS with a NetworkPolicy when you have egress restrictions?**

**Answer:**

Add an egress rule allowing UDP and TCP on port 53 to the `kube-system` namespace where CoreDNS runs:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns-egress
  namespace: production
spec:
  podSelector: {}
  policyTypes:
    - Egress
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
```

This uses AND logic — the DNS traffic must be destined for pods with the `k8s-app: kube-dns` label that are in the `kube-system` namespace. Including both TCP and UDP is important: DNS normally uses UDP, but falls back to TCP for large responses.

---

**Q9: How do you allow traffic between specific pods across namespaces?**

**Answer:**

You need a NetworkPolicy on the destination pods that uses `namespaceSelector` to identify the source namespace and `podSelector` to identify the source pods. The two selectors must be in the same `from` list item (AND logic):

```yaml
# On the payments namespace, allow checkout service from the orders namespace
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-orders-checkout
  namespace: payments
spec:
  podSelector:
    matchLabels:
      app: payment-service
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: orders
          podSelector:
            matchLabels:
              app: checkout-service
      ports:
        - protocol: TCP
          port: 8080
```

The `kubernetes.io/metadata.name` label is automatically applied to every namespace since Kubernetes 1.21, so you can reference namespaces by name without adding custom labels.

---

**Q10: How do you allow monitoring tools like Prometheus to scrape metrics from pods?**

**Answer:**

Apply a NetworkPolicy on the pods being scraped that allows ingress from the Prometheus pod in the monitoring namespace:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-prometheus-scraping
  namespace: production
spec:
  podSelector:
    matchLabels:
      monitoring: "true"      # add this label to pods you want scraped
  policyTypes:
    - Ingress
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
          port: 9090           # or 8080, whichever port exposes /metrics
```

A common pattern is to label any pod that exposes metrics with `monitoring: "true"`, then apply one policy that covers all of them.

---

## Advanced Questions

---

**Q11: What is the difference between NetworkPolicy and service mesh mTLS?**

**Answer:**

They operate at different layers and solve related but different problems:

**NetworkPolicy** works at L3/L4 (IP addresses and TCP/UDP ports). It answers: "Can pod A's IP connect to pod B on port 8080?" It provides network-level segmentation — enforced by the CNI plugin in the kernel.

**Service mesh mTLS** (Mutual TLS, used by Istio, Linkerd, Cilium) works at L7. It answers: "Is this specific service's identity (certificate) authorized to call this endpoint?" It provides:
- Cryptographic identity verification — the calling service proves who it is
- Encrypted traffic in-transit — even within the cluster
- L7 authorization (HTTP path, method, JWT claims)
- Observability (tracing, metrics on service-to-service calls)

| Feature | NetworkPolicy | Service Mesh mTLS |
|---------|--------------|-------------------|
| Layer | L3/L4 (IP/port) | L7 (identity/HTTP) |
| Encryption | No | Yes |
| Identity verification | No | Yes (certificates) |
| HTTP path filtering | No (Cilium only) | Yes |
| Complexity | Low | High |

For most teams, NetworkPolicies are sufficient. Service meshes add significant operational overhead — adopt them when you specifically need encryption-in-transit, strong identity, or L7 authorization.

---

**Q12: How do you debug NetworkPolicy issues when traffic is unexpectedly blocked?**

**Answer:**

Systematic approach:

**Step 1: Verify the CNI supports NetworkPolicy**
```bash
kubectl get pods -n kube-system | grep -Ei "calico|cilium|weave|antrea"
```
If you see Flannel — policies don't work at all.

**Step 2: Check pod labels match your selector**
```bash
kubectl get pod <pod-name> -n <namespace> --show-labels
```
A typo in a label is the most common cause of unexpected blocks.

**Step 3: List all policies that could affect the pod**
```bash
kubectl get netpol -n <namespace> -o yaml
```

**Step 4: Test connectivity directly**
```bash
kubectl exec -it <source-pod> -n <namespace> -- \
  curl -v --connect-timeout 5 http://<target>:8080
```

**Step 5: Test DNS separately**
```bash
kubectl exec -it <pod> -n <namespace> -- nslookup kubernetes.default
```
If DNS fails, you're missing a DNS egress allow rule.

**Step 6: For Cilium clusters, check enforcement state**
```bash
kubectl exec -n kube-system ds/cilium -- cilium endpoint list
kubectl exec -n kube-system ds/cilium -- cilium monitor --type drop
```
The `cilium monitor` command shows real-time packet drops with the reason.

**Common causes:**
- Missing DNS egress rule (breaks everything in non-obvious ways)
- AND vs OR confusion in podSelector + namespaceSelector
- Policy in wrong namespace
- Pod labels don't match selector

---

**Q13: What are Cilium's L7 NetworkPolicies and how do they differ from standard NetworkPolicies?**

**Answer:**

Standard Kubernetes NetworkPolicies operate at L3/L4 — they can allow or deny traffic based on IP addresses, ports, and protocols. They cannot inspect the contents of HTTP requests.

Cilium's `CiliumNetworkPolicy` (and `CiliumClusterwideNetworkPolicy`) extends this to L7 by leveraging eBPF to inspect application-layer traffic:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-specific-http-paths
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
              - method: GET
                path: /api/products    # only this path is allowed
              - method: POST
                path: /api/cart
```

This policy allows the frontend to make `GET /api/products` and `POST /api/cart` to the backend — but would block `DELETE /api/admin` even though it's the same port 8080.

Other Cilium L7 capabilities:
- **gRPC method filtering** — allow specific gRPC service methods
- **Kafka topic filtering** — allow only certain Kafka topics per pod
- **DNS filtering** — allow only specific DNS names in egress

Standard NetworkPolicies are sufficient for most security requirements. Cilium L7 policies are valuable when you need fine-grained API-level access control without deploying a full service mesh.

---

## 📂 Navigation

⬅️ **Prev:** [Resource Quotas and Limits](../19_Resource_Quotas_and_Limits/Interview_QA.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Service Accounts](../21_Service_Accounts/Theory.md)

| | Link |
|---|---|
| Theory | [Theory.md](./Theory.md) |
| Cheatsheet | [Cheatsheet.md](./Cheatsheet.md) |
