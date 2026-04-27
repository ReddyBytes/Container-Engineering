# Module 06 — Interview Q&A: Services

---

**Q1: Why do you need Services in Kubernetes instead of just using pod IPs?**

Pod IPs are ephemeral. When a pod is restarted, scaled, or rescheduled to a different node, it
gets a new IP address. If your application hardcodes pod IPs, it breaks every time this happens.
A Service provides a stable virtual IP (ClusterIP) and DNS name that never changes, regardless
of how many pods come and go behind it. The Service automatically discovers healthy pods via
label selectors and load-balances traffic across them.

---

**Q2: What are the four Service types and when do you use each?**

- **ClusterIP** (default): creates a virtual IP accessible only inside the cluster. Use for
  internal service-to-service communication — backend APIs, databases, caches.
- **NodePort**: opens a high-numbered port (30000–32767) on every node and routes external
  traffic to the service. Use for local development or on-premises access where a cloud LB
  isn't available. Not recommended for production public traffic.
- **LoadBalancer**: provisions a cloud load balancer (AWS ELB, GCP LB, Azure LB) and routes
  external traffic to the service. Use for production internet-facing services.
- **ExternalName**: creates a DNS CNAME alias to an external service. No proxying occurs.
  Use for accessing external services by a Kubernetes DNS name to keep pod config portable.

---

**Q3: How do Services find which pods to route traffic to?**

Through label selectors. The Service's `spec.selector` field specifies a set of key-value labels.
Kubernetes continuously maintains an Endpoints object for the Service, listing the IP:port pairs
of all running pods whose labels match the selector. The Endpoints controller watches pod events
and updates this list in real time. kube-proxy reads the Endpoints list and programs routing
rules accordingly. If you scale a Deployment, new pod IPs are automatically added; if pods crash,
they are removed.

---

**Q4: What is the difference between `port` and `targetPort` in a Service?**

- `port`: the port that the Service listens on — what clients use to connect to the Service.
- `targetPort`: the port on the backing pods to forward traffic to — what the application
  inside the container is actually listening on.

Example: `port: 80, targetPort: 8080` means clients connect to `my-service:80`, and the Service
forwards to pods' port 8080. The two can be the same, but separating them lets you expose a
standard port (80) while the app uses a non-privileged port (8080) inside the container.

---

**Q5: What is a headless Service?**

A headless Service is created with `spec.clusterIP: None`. Instead of creating a virtual IP,
DNS queries for the Service return the individual pod IP addresses directly. This gives clients
direct access to specific pods, which is essential for StatefulSets where each pod has a unique
identity (pod-0, pod-1, pod-2) and clients need to connect to a specific one (e.g., the primary
database node). Headless Services are also used when you want to implement your own client-side
load balancing.

---

**Q6: How does kube-proxy implement Service routing?**

kube-proxy runs on every node and watches the API server for Service and Endpoints changes.
In the default iptables mode, it programs DNAT (Destination Network Address Translation) rules.
When a packet from any pod or node is destined for a ClusterIP, the kernel's netfilter intercepts
it in the PREROUTING chain and randomly rewrites the destination to one of the healthy pod IPs
from the Endpoints list. The original ClusterIP never actually exists as a network interface —
it's purely a routing target for iptables rules.

---

**Q7: What is the DNS name for a Service?**

Every Service gets a DNS name following this pattern:
`<service-name>.<namespace>.svc.cluster.local`

From a pod in the same namespace, you can use the short form: just the service name.
From a pod in a different namespace, you need the fully qualified form or at minimum
`<service-name>.<namespace>`.

CoreDNS (running in kube-system) provides this DNS resolution for all pods in the cluster.

---

**Q8: What happens if a Service has no matching pods (empty endpoints)?**

Traffic sent to the Service's ClusterIP will fail with a connection refused or timeout error.
The Service itself still exists and has a stable IP, but there are no backend pods to route to.
You can see this with `kubectl get endpoints my-service` — it will show `<none>`.

This commonly happens when the Service's label selector doesn't match the pod labels (a typo
is a frequent cause), when the deployment is scaled to zero, or when all pods are unhealthy
and failing readiness probes.

---

**Q9: What is the difference between NodePort and LoadBalancer service types?**

Both expose a service externally, but they differ in implementation and use case:

**NodePort** opens the same high-numbered port on every node. External clients connect directly
to a node's IP on that port. The client must know a node IP, and if a node goes down, that
route is broken. There's no automatic health checking of nodes. Simple but limited.

**LoadBalancer** provisions a cloud load balancer in front of the nodes. The load balancer has
a stable public IP/DNS, health-checks nodes, and distributes traffic. Clients connect to the
load balancer, not directly to nodes. More robust and production-ready, but costs money per
service and requires a cloud provider integration.

---

**Q10: Can a Service route to pods in a different namespace?**

Not directly via label selectors — a Service's selector only matches pods in the same namespace.
However, you can create a headless Service without a selector and manually create an Endpoints
object pointing to pod IPs in another namespace. Alternatively, use ExternalName to point to
a service in another namespace:
```yaml
spec:
  type: ExternalName
  externalName: my-service.other-namespace.svc.cluster.local
```

---

**Q11: What is session affinity in Services?**

By default, each request to a Service is load-balanced independently — consecutive requests from
the same client may go to different pods. Session affinity (also called sticky sessions) sends
all requests from the same client IP to the same pod.

```yaml
spec:
  sessionAffinity: ClientIP
  sessionAffinityConfig:
    clientIP:
      timeoutSeconds: 10800   # 3-hour sticky sessions
```

This is useful for stateful applications that store session data in memory. However, it can
cause uneven load distribution, so stateless applications should avoid it.

---

**Q12: How do you expose a Service externally without a LoadBalancer?**

Several options:
1. **NodePort**: expose on a node port, then put your own load balancer or reverse proxy in
   front of the nodes.
2. **Ingress**: use an Ingress controller (nginx, Traefik, AWS ALB) with a single LoadBalancer
   in front, routing to multiple services by hostname/path.
3. **externalIPs**: set `spec.externalIPs` to static IPs you control — those IPs on any node
   will route to the service (requires you to route those IPs to your nodes).
4. **HostPort**: set `spec.containers[*].ports[*].hostPort` in the pod spec to bind directly
   to the node's IP on a port — essentially making a specific node port route to the pod.

---

## 📂 Navigation

| File | Description |
|------|-------------|
| [Theory.md](./Theory.md) | Services explained |
| [Cheatsheet.md](./Cheatsheet.md) | Quick reference commands |
| [Interview_QA.md](./Interview_QA.md) | You are here — interview questions |
| [Code_Example.md](./Code_Example.md) | Working YAML examples |

**Previous:** [05_Deployments_and_ReplicaSets](../05_Deployments_and_ReplicaSets/Interview_QA.md) |
**Next:** [07_ConfigMaps_and_Secrets](../07_ConfigMaps_and_Secrets/Theory.md)
