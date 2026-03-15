# eBPF and Cilium — Interview Q&A

---

**Q1: What is eBPF and why is it significant for Kubernetes networking?**

eBPF (extended Berkeley Packet Filter) is a Linux kernel technology that allows sandboxed programs to run inside the kernel without changing kernel source code or loading kernel modules. The kernel's built-in verifier checks every eBPF program before execution — it cannot loop infinitely, crash the kernel, or access arbitrary memory.

For Kubernetes networking, eBPF is significant because it allows network processing to happen at the earliest possible point in the packet path (XDP, the eXpress Data Path, hooks before even allocating a socket buffer), using hash map lookups that are O(1) regardless of cluster size. This is the fundamental alternative to iptables, which processes packets through a linear chain of rules at O(n). At 1,000 Services with 5 pods each, that is potentially 50,000+ iptables comparisons per packet. With eBPF, it is one hash map lookup.

---

**Q2: What are the problems with kube-proxy and iptables at scale?**

Three main problems. First, **O(n) packet processing**: every packet must traverse the entire iptables chain. Each Kubernetes Service adds ~15 iptables rules. A cluster with 2,000 Services has ~30,000 rules per node, and every packet walks all of them. This adds measurable CPU overhead and latency at scale.

Second, **global locking**: updating iptables requires acquiring a global kernel lock. During the update, all packet processing on that node pauses. In a cluster with frequent scaling events (Services being added/removed), these pauses add up.

Third, **no observability**: iptables has no built-in way to tell you which rule matched, how frequently rules fire, or why a connection was dropped. Debugging networking issues means `tcpdump` and guesswork. eBPF-based implementations can emit detailed flow data to userspace with essentially zero overhead.

---

**Q3: What is Cilium and what does "kube-proxy replacement" mean?**

Cilium is a CNCF-graduated CNI (Container Network Interface) plugin for Kubernetes that implements networking, network policy enforcement, and load balancing using eBPF. It is the default CNI on GKE (as Dataplane V2) and is available on EKS.

"kube-proxy replacement" means Cilium completely removes the kube-proxy DaemonSet from the cluster. Instead of kube-proxy programming iptables rules for Service load balancing, Cilium handles it with eBPF hash maps programmed directly into the kernel. When a pod connects to a ClusterIP, Cilium's eBPF programs intercept the packet at the kernel level and redirect it to a healthy backend pod — no iptables chains, no NAT tables, no global locks. The result is O(1) load balancing that scales to thousands of services without degradation.

---

**Q4: What is L7 NetworkPolicy and why is it more powerful than standard Kubernetes NetworkPolicy?**

Standard Kubernetes NetworkPolicy operates at Layer 3/4: it allows or denies traffic based on pod label selectors, namespace selectors, and TCP/UDP port numbers. "Allow frontend to connect to backend on port 8080" is as specific as it gets.

L7 NetworkPolicy (supported by Cilium via `CiliumNetworkPolicy`) inspects the actual application protocol content. For HTTP, you can write policies like "allow only GET requests to paths matching `/api/.*`" or "deny all POST requests to `/admin`". For gRPC, you can allow specific service methods. For DNS, you can restrict which domain names a pod can resolve.

This matters for security because a standard NetworkPolicy that allows port 8080 cannot distinguish between a legitimate API call and an SSRF attack or internal API abuse. With L7 policy, you can express your actual intended communication patterns and reject everything else — without changing your application code.

---

**Q5: How does Cilium's WireGuard encryption work and how does it compare to a service mesh?**

Cilium can enable transparent pod-to-pod encryption using WireGuard, which has been part of the Linux kernel since version 5.6. When enabled, Cilium configures WireGuard tunnels between nodes. All pod-to-pod traffic across nodes is automatically encrypted at the kernel level — no certificate management, no per-connection TLS handshake, no sidecar containers.

Compared to a service mesh (Istio, Linkerd): service meshes implement mTLS at the application layer using sidecar proxies. Each connection involves a full TLS handshake with certificate exchange. This adds latency per connection and resource consumption per pod (the sidecar proxy). WireGuard encryption in Cilium happens at the kernel level — the overhead is minimal (modern CPUs encrypt/decrypt at line rate using AES-NI), and there is nothing to inject into your pods. The trade-off: service meshes provide connection-level observability, retry logic, and circuit breaking, which Cilium alone does not. For pure encryption-in-transit requirements, Cilium/WireGuard is simpler and more efficient.

---

**Q6: What is Hubble and what network visibility does it provide?**

Hubble is Cilium's built-in network observability system. Because Cilium processes every packet at the kernel level, it can observe all network flows in the cluster without any instrumentation changes to applications, no sidecar proxies, and no traffic overhead.

Hubble provides: real-time flow visibility (source pod, destination pod, protocol, verdict — allowed or dropped), HTTP request/response observability (method, path, status code, latency), DNS query and response logging, service dependency maps (a graph of which services communicate with which), and NetworkPolicy drop analysis (which policy blocked which flow and why).

Practically, Hubble replaces several categories of tools: network flow loggers, service mesh observability planes (for basic cases), and much of what you might use `tcpdump` or Wireshark for. The `hubble observe --verdict DROPPED` command is the fastest way to debug a NetworkPolicy misconfiguration — it shows you exactly which flows were denied and by which endpoint selector.

---

**Q7: How does Cilium differ from Calico? When would you choose one over the other?**

Both are production-ready CNCF-graduated CNIs with NetworkPolicy support. The key differences:

**Calico** has been production-standard longer, is more familiar to most operators, and supports BGP routing (useful when you need pods to be directly routable from outside the cluster). Calico v3.x introduced eBPF mode, which provides kube-proxy replacement, but it was added later and is less deeply integrated than Cilium's native eBPF implementation. Calico does not support L7 NetworkPolicy.

**Cilium** was built on eBPF from day one. It supports L7 NetworkPolicy (HTTP, DNS, gRPC), has Hubble for observability, WireGuard encryption as a first-class feature, and Tetragon for runtime security. It is now the default on GKE and a recommended option on EKS.

Choose Calico when: you need BGP routing, your team has existing Calico expertise, or you are running an older kernel (< 5.3) where Cilium's eBPF features are limited. Choose Cilium when: you are starting a new cluster, you want L7 policy or Hubble observability, you are on a managed K8s service that defaults to it, or you want kube-proxy replacement with full eBPF performance.

---

**Q8: What is Tetragon and how does it use eBPF for security?**

Tetragon is a Cilium sub-project that uses eBPF to implement Kubernetes-native runtime security. While Cilium handles network-level policy, Tetragon attaches to kernel syscall hooks to monitor and enforce security policies at the process level — inside containers.

Tetragon can: detect which binaries execute inside containers (catch unexpected process execution, indicating a breakout or RCE), monitor file access (alert when a container reads `/etc/shadow` or `/proc/1/environ`), observe network system calls (detect when a container opens a raw socket, indicating cryptomining or port scanning), detect privilege escalation attempts (ptrace, namespace transitions, capability additions), and optionally terminate (SIGKILL) the offending process immediately.

The key advantage over userspace security tools (Falco in non-eBPF mode): Tetragon's eBPF programs run in the kernel and execute before userspace code. An attacker who has compromised a container cannot bypass Tetragon by manipulating userspace — the enforcement point is at the kernel system call boundary.

---

**Q9: What Linux kernel version is required for Cilium and why does it matter?**

Cilium requires Linux kernel 4.9.17 at minimum, but modern features require 5.3+. The practical recommendation for production Cilium in 2024 is kernel 5.10 or newer (which is available on EKS, GKE, and recent Ubuntu/Debian versions).

Why it matters: eBPF programs are compiled to BPF bytecode and must use kernel features that exist in the target kernel. Newer kernels expose more eBPF hook points and map types. For example:
- kube-proxy replacement requires kernel 5.1+ (for BPF socket load balancing)
- WireGuard encryption requires kernel 5.6+
- BPF socket redirect (full kube-proxy replacement with host networking) requires 5.10+

On AWS EKS, the default Amazon Linux 2023 AMI uses kernel 6.1, which supports all Cilium features. On older AMIs (Amazon Linux 2 with 5.10 kernel), most features work. The Cilium compatibility matrix at docs.cilium.io lists exact requirements per feature.

---

**Q10: Explain the difference between XDP, tc, and other eBPF hook points.**

eBPF programs can attach at different points in the kernel's packet processing pipeline, each with different capabilities and performance characteristics:

**XDP (eXpress Data Path)**: The earliest hook — runs on the NIC driver or as a software hook before the kernel allocates a socket buffer (skb). This is the fastest path — packets that should be dropped or redirected never even enter the network stack. Used for DDoS mitigation and fast packet filtering. Limitation: cannot access socket/connection state.

**tc (Traffic Control) ingress/egress**: Runs after skb allocation, on the tc subsystem. Can read and modify packet headers, access connection state (via BPF maps), and redirect packets. This is where Cilium implements most of its load balancing and policy enforcement — enough access to the packet context, but still kernel-level performance.

**kprobe/tracepoint**: Attach to arbitrary kernel functions or tracepoints. Used for observability (Hubble flow data) and Tetragon security monitoring. Cannot modify packets but can observe and enforce via signals.

**socket**: Attach to socket operations (connect, bind, accept). Used for socket-level load balancing — Cilium can redirect a connect() call to a backend pod before even sending a packet, avoiding network overhead entirely.

Cilium uses tc and socket-level hooks primarily, with XDP for specific high-performance scenarios.

---

**Q11: How does Cilium handle DNS-based network policies (FQDN policies)?**

Traditional NetworkPolicy can only target IPs and CIDR ranges. But external services like `api.stripe.com` have changing IPs — you cannot write a static IP-based policy for them.

Cilium's `CiliumNetworkPolicy` supports FQDN (Fully Qualified Domain Name) selectors. It works by intercepting DNS responses using an eBPF-based DNS proxy: when a pod's DNS query resolves `api.stripe.com` to a set of IPs, Cilium dynamically programs those IPs into the pod's policy. If the IPs change (new DNS response), Cilium updates the policy automatically.

```yaml
egress:
- toFQDNs:
  - matchName: "api.stripe.com"
  toPorts:
  - ports:
    - port: "443"
      protocol: TCP
```

This FQDN policy automatically follows IP changes. Combined with DNS filtering rules (restricting which domains a pod can even resolve), Cilium FQDN policies provide a complete solution for egress control to external services — something impossible with standard Kubernetes NetworkPolicy.

---

**Q12: What is XDP acceleration and how does Cilium use it?**

XDP (eXpress Data Path) is an eBPF hook that fires at the earliest possible point in the Linux networking stack — inside the NIC driver, before the kernel allocates a socket buffer (skb). Because the packet is processed before the kernel's normal network stack, XDP is dramatically faster than even tc-level eBPF processing. For packets that should be dropped or immediately redirected, XDP avoids all the overhead of traversing the full kernel networking path.

Cilium uses XDP in specific high-performance scenarios:

**Load balancer acceleration**: When Cilium is deployed as an external load balancer (e.g., in front of a Kubernetes cluster using `externalTrafficPolicy: Cluster`), XDP can process incoming packets at wire speed — potentially millions of packets per second per core — and redirect them to the correct backend pod before any socket processing occurs.

**DDoS mitigation**: Packets matching known-bad IP ranges or rate-limit patterns can be dropped at the XDP layer in microseconds, before any kernel resource is consumed. This is far more effective than iptables-based blocking under high packet rates.

**Limitations of XDP**: XDP programs cannot access socket state (connection tracking, established TCP sessions) because that state has not been created yet when XDP runs. XDP is for stateless, fast-path decisions only. Most of Cilium's NetworkPolicy enforcement happens at the tc layer (which has access to full socket context), not at XDP.

To check if Cilium is using XDP on your cluster:

```bash
# Check Cilium XDP acceleration status
cilium status | grep XDP

# View XDP programs attached to interfaces
ip link show  # look for xdpgeneric or xdpdrv flags
```

Native XDP (`xdpdrv`) is faster than generic XDP (`xdpgeneric`) — native requires a NIC driver that supports XDP natively, which most cloud hypervisor NICs do.

---

## 📂 Navigation

| | Link |
|---|---|
| ⬅️ Prev | [Karpenter](../33_Karpenter_Node_Autoprovisioning/Interview_QA.md) |
| Theory | [eBPF and Cilium Theory](./Theory.md) |
| Cheatsheet | [eBPF and Cilium Cheatsheet](./Cheatsheet.md) |
| ➡️ Next | [Ephemeral Containers](../35_Ephemeral_Containers_and_Debug/Theory.md) |
