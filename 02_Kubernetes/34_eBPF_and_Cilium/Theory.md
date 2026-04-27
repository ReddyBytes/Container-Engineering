# Module 34: eBPF and Cilium

## The Story: When the Network Becomes the Bottleneck

Traditional Kubernetes networking goes through a long chain: your app makes a network call → kernel network stack → iptables rules (potentially thousands of them) → kube-proxy → more iptables → destination pod. As clusters grow to thousands of pods, those iptables tables grow massive, every packet traverses hundreds of rules, and performance tanks. eBPF is like replacing all those paper checkpoints with a smart digital fast-lane: programs that run directly in the kernel, near the network card, with microsecond decisions.

Your cluster has grown. 200 services. 1,500 pods. Tens of thousands of iptables rules accumulating in every node's kernel. A new pod starts. Before it can receive any traffic, your node needs to update iptables rules across potentially 20,000 entries — linearly, one by one, with a global lock. A network engineer watches the CPU spike and thinks: "This cannot be right."

They are correct. The networking model that powered Kubernetes since its earliest days — kube-proxy plus iptables — was never designed for this scale. It worked when clusters had dozens of services. At hundreds or thousands, it becomes a liability. In 2024, the solution is already running in your cloud provider's managed Kubernetes service. It is called **Cilium**, and it is built on **eBPF**.

> **🐳 Coming from Docker?**
>
> Docker networking uses Linux bridge devices and iptables rules to route traffic between containers. On a small cluster this is fast enough. But Kubernetes clusters with thousands of pods generate tens of thousands of iptables rules — and iptables is evaluated linearly, so every packet traverses every rule. eBPF replaces this with programs that run directly in the Linux kernel, near the network card, making routing decisions in microseconds regardless of cluster size. Cilium uses eBPF to replace kube-proxy entirely, enforce L7 NetworkPolicies (filtering by HTTP path, not just port), and provide Hubble — deep visibility into network flows without touching your application code.

---

## 📌 Learning Priority

**Must Learn** — core concepts, needed to understand the rest of this file:
[eBPF Overview](#ebpf-a-programmable-kernel) · [Cilium CNI](#cilium-ebpf-based-cni-for-kubernetes) · [kube-proxy Replacement](#kube-proxy-replacement)

**Should Learn** — important for real projects and interviews:
[L7 NetworkPolicy](#l7-networkpolicy) · [Hubble Observability](#hubble-built-in-network-observability) · [CNI Comparison](#comparison-flannel-vs-calico-vs-cilium)

**Good to Know** — useful in specific situations, not needed daily:
[Transparent Encryption](#transparent-encryption-wireguard) · [Tetragon Security](#tetragon-runtime-security-with-ebpf)

**Reference** — skim once, look up when needed:
[iptables Problem](#traditional-kubernetes-networking-the-iptables-problem) · [Installation](#installation)

---

## Traditional Kubernetes Networking: The iptables Problem

Every Kubernetes cluster needs a way to load balance traffic to Services. The default implementation is **kube-proxy**, which runs as a DaemonSet and programs iptables rules on every node.

When a packet destined for `ClusterIP:port` hits a node, the kernel walks through iptables rules in a linear chain to find the matching Service, then randomly selects a backend pod IP via DNAT. For a cluster with 1,000 Services and 5 pods each, this means up to **5,000 iptables rules per node**, walked in O(n) time for every single packet.

Problems at scale:

| Problem | Details |
|---|---|
| **O(n) packet processing** | Every packet walks the full iptables chain. With 10,000 rules, that is 10,000 comparisons per packet. |
| **Global kernel lock** | Any iptables update requires locking the entire table — all traffic pauses during updates. |
| **Rule explosion** | Each Service adds ~15 iptables rules. 1,000 services = 15,000 rules. |
| **No observability** | iptables has no built-in way to tell you which rule matched, or how often. |
| **No L7 visibility** | iptables sees IP/port only. It cannot inspect HTTP methods, paths, or gRPC methods. |
| **Static NAT** | DNAT rewrites destination IPs, making packet-level debugging confusing. |

---

## eBPF: A Programmable Kernel

**eBPF** (extended Berkeley Packet Filter) is a revolutionary Linux kernel technology that allows you to run sandboxed programs inside the kernel without changing kernel source code or loading kernel modules.

Think of it as: **if iptables is a fixed set of rules you configure, eBPF is a programmable runtime you can inject into the kernel itself.**

```mermaid
graph TD
    subgraph "Traditional Path (kube-proxy + iptables)"
        P1[Incoming Packet] -->|enters kernel| IP[iptables chains<br/>PREROUTING → FORWARD<br/>5,000+ rules, O(n)]
        IP -->|DNAT rewrite| D1[Destination Pod]
    end

    subgraph "eBPF Path (Cilium, no iptables)"
        P2[Incoming Packet] -->|XDP / tc hook| EB[eBPF Program<br/>hash map lookup O(1)<br/>kernel-level LB]
        EB -->|direct redirect| D2[Destination Pod]
    end

    style IP fill:#e74c3c,color:#fff
    style EB fill:#50c878,color:#fff
```

Key eBPF properties:
- **Safe**: eBPF programs are verified by the kernel's verifier before execution — they cannot crash the kernel, cause infinite loops, or access arbitrary memory
- **Performant**: eBPF runs at kernel speed, at the earliest possible point in the packet path (XDP = before even allocating a socket buffer)
- **Dynamic**: eBPF programs can be loaded and unloaded at runtime without rebooting or changing kernel configuration
- **Observable**: eBPF can emit events to userspace (perf ring buffers, maps) — enabling deep observability with zero kernel changes

eBPF programs can attach to dozens of kernel hooks: network packet processing, system calls, tracepoints, kprobes, and more.

---

## Cilium: eBPF-Based CNI for Kubernetes

**Cilium** is a CNCF-graduated project that uses eBPF to implement Kubernetes Container Networking Interface (CNI), NetworkPolicy enforcement, and load balancing — replacing kube-proxy entirely.

As of 2024:
- **Default CNI on GKE** (Dataplane V2, powered by Cilium since 2021)
- **Default CNI on EKS with VPC CNI + Cilium** (network policies)
- **Default on EKS Anywhere**
- Used by Cloudflare, Adobe, Bell Canada, and hundreds of other production deployments
- CNCF Graduated (2023)

---

## Cilium Features

### kube-proxy Replacement

In `kube-proxy-replacement: true` mode, Cilium removes kube-proxy entirely and implements Service load balancing with eBPF hash maps instead of iptables chains.

The difference:
- **iptables**: O(n) lookup through a linear rule chain
- **eBPF map**: O(1) hash map lookup regardless of cluster size

At 10,000 services, iptables requires 150,000 rules per node. Cilium uses a hash table — lookup time is constant regardless of table size. This is not a minor improvement; at scale, it means measurably lower network latency and CPU usage on every node.

### L7 NetworkPolicy

Standard Kubernetes NetworkPolicy operates at L3/L4 — it allows or denies traffic based on pod selectors, namespace selectors, and port numbers. Cilium extends this to **Layer 7**:

```yaml
# Cilium NetworkPolicy: allow only HTTP GET to /api from frontend pods
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
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
          path: /api.*
```

This policy does not just allow connections from frontend to backend on port 8080 — it inspects the HTTP method and path of every request. A `POST /admin` from the frontend is rejected at the kernel level, without reaching the backend container.

### Transparent Encryption (WireGuard)

Cilium can encrypt all pod-to-pod traffic using WireGuard, built into the Linux kernel since 5.6. This provides encryption-in-transit without requiring a service mesh or mTLS at the application level.

```bash
# Enable during Cilium installation
helm install cilium cilium/cilium \
  --set encryption.enabled=true \
  --set encryption.type=wireguard
```

No certificate management, no mutual TLS handshakes per connection — just kernel-level WireGuard encryption. Traffic between nodes is encrypted automatically.

### Load Balancing

Cilium implements Kubernetes Service load balancing using eBPF, providing:
- **DSR (Direct Server Return)**: servers respond directly to clients without returning through the load balancer, reducing bandwidth usage
- **Maglev consistent hashing**: stable backend selection even as pods scale up and down (no thundering herd during rebalancing)
- **Session persistence**: consistent routing of packets from the same source to the same backend
- Faster than iptables at every scale

---

## Hubble: Built-In Network Observability

**Hubble** is Cilium's built-in network observability layer. It provides a real-time view of all network flows in the cluster — without any instrumentation changes to your applications.

Because Cilium processes every packet at the kernel level, Hubble can observe:
- Which services are talking to each other (service dependency map)
- HTTP request rates, latency, and status codes per endpoint
- DNS queries and resolutions
- TCP connection establishment and termination
- NetworkPolicy drops (which policies are blocking which traffic, and why)
- L7 protocol details (HTTP method, path, gRPC service/method)

```bash
# Install Hubble CLI
HUBBLE_VERSION=v0.13.0
curl -L --fail --remote-name-all \
  https://github.com/cilium/hubble/releases/download/${HUBBLE_VERSION}/hubble-linux-amd64.tar.gz
tar xzvf hubble-linux-amd64.tar.gz

# Enable port-forward to Hubble relay
cilium hubble port-forward &

# Watch live traffic flows
hubble observe --follow

# Watch flows for a specific pod
hubble observe --pod production/api-service-xxx --follow

# Watch only HTTP flows with errors
hubble observe --protocol http --verdict DROPPED --follow
```

Hubble UI provides a visual service dependency map — a real-time graph of which services are communicating, with traffic rates and error rates per edge. This alone replaces many commercial network monitoring tools.

---

## Tetragon: Runtime Security with eBPF

**Tetragon** is a Cilium sub-project that uses eBPF for Kubernetes-native runtime security. Where Cilium handles networking, Tetragon handles security observability and enforcement at the syscall level.

Capabilities:
- **Process execution tracing**: detect which binaries run inside containers
- **File access monitoring**: alert when a container reads `/etc/shadow` or writes to `/var/run/docker.sock`
- **Network policy at syscall level**: block a process from making network calls entirely
- **Container escape detection**: detect ptrace calls, namespace escapes, privilege escalation attempts
- **Cryptomining detection**: identify processes opening raw sockets or consuming unusual CPU patterns

```yaml
# Tetragon TracingPolicy: alert when any process runs in a container reads /etc/passwd
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: detect-passwd-read
spec:
  kprobes:
  - call: "security_file_open"
    syscall: false
    args:
    - index: 0
      type: "file"
    selectors:
    - matchArgs:
      - index: 0
        operator: "Prefix"
        values: ["/etc/passwd", "/etc/shadow"]
      matchActions:
      - action: Sigkill        # kill the offending process immediately
```

Tetragon's eBPF enforcement happens before any userspace code runs — it is impossible to bypass from within a container.

---

## Comparison: Flannel vs Calico vs Cilium

| Feature | Flannel | Calico | Cilium |
|---|---|---|---|
| Basis | VXLAN / host-gw | iptables / eBPF | eBPF (native) |
| L3/L4 NetworkPolicy | No | Yes | Yes |
| L7 NetworkPolicy | No | No | Yes (HTTP, DNS, gRPC) |
| kube-proxy replacement | No | Partial (eBPF mode) | Full |
| Encryption | No | WireGuard (optional) | WireGuard (native) |
| Observability | None | Limited | Hubble (full L7 flow visibility) |
| Runtime security | No | No | Tetragon |
| Performance at scale | Poor (VXLAN overhead) | Good | Excellent (eBPF maps) |
| CNCF status | Not CNCF | CNCF graduated | CNCF graduated |
| Managed K8s default | Some older clusters | Common | GKE default, EKS option |
| Complexity | Low | Medium | Medium-High |

---

## Installation

```bash
# Install via Cilium CLI (recommended for testing)
CILIUM_CLI_VERSION=v0.16.0
curl -L --fail --remote-name-all \
  https://github.com/cilium/cilium-cli/releases/download/${CILIUM_CLI_VERSION}/cilium-linux-amd64.tar.gz
tar xzvf cilium-linux-amd64.tar.gz -C /usr/local/bin

cilium install --version 1.16.0 \
  --set kubeProxyReplacement=true \
  --set hubble.enabled=true \
  --set hubble.relay.enabled=true \
  --set hubble.ui.enabled=true

# Verify
cilium status --wait
cilium connectivity test
```

For production EKS:

```bash
helm repo add cilium https://helm.cilium.io/
helm install cilium cilium/cilium \
  --version 1.16.0 \
  --namespace kube-system \
  --set eni.enabled=true \
  --set ipam.mode=eni \
  --set egressMasqueradeInterfaces=eth0 \
  --set kubeProxyReplacement=true \
  --set hubble.enabled=true \
  --set hubble.relay.enabled=true
```

---

## Summary

eBPF is the most significant change to Linux kernel networking in a decade. It gives Cilium the ability to implement Kubernetes networking at O(1) performance, enforce security policies at the L7 HTTP/gRPC level, provide encryption without service mesh complexity, and deliver full network observability through Hubble — all without modifying application code or adding sidecar containers. In 2024, Cilium is the default or recommended CNI on every major managed Kubernetes service. Understanding eBPF and Cilium is no longer optional knowledge for Kubernetes practitioners.


---

## 📝 Practice Questions

- 📝 [Q69 · ebpf-cilium](../kubernetes_practice_questions_100.md#q69--thinking--ebpf-cilium)


---

## 📂 Navigation

| | Link |
|---|---|
| ⬅️ Prev | [Karpenter](../33_Karpenter_Node_Autoprovisioning/Interview_QA.md) |
| Cheatsheet | [eBPF and Cilium Cheatsheet](./Cheatsheet.md) |
| Interview Q&A | [eBPF and Cilium Interview Q&A](./Interview_QA.md) |
| ➡️ Next | [Ephemeral Containers](../35_Ephemeral_Containers_and_Debug/Theory.md) |
