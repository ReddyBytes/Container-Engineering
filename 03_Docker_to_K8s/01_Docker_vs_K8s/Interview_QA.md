# Docker vs Kubernetes — Interview Q&A

---

## Beginner

**Q1: What is the fundamental difference between Docker and Kubernetes?**

Docker runs containers on a single machine. Kubernetes orchestrates containers across many machines.

Docker answers: "How do I package and run this application?" Kubernetes answers: "How do I run this application reliably at scale, across a cluster, with self-healing and auto-scaling?"

You still use Docker (or similar tools) to build images. Kubernetes then pulls and runs those images across its cluster.

---

**Q2: When should you use Docker alone vs Kubernetes?**

**Use Docker alone when:**
- You're building and testing images locally
- You're running a single-container tool or one-off task
- You're in a CI/CD pipeline step that just builds and pushes

**Use Docker Compose when:**
- You have a multi-container app running on a single server
- You want simplicity — one file, one command, done
- Your team is small and manual restarts are acceptable

**Use Kubernetes when:**
- You need to run across multiple machines
- Downtime is unacceptable and self-healing is required
- You need to auto-scale based on traffic
- Multiple teams deploy independently to shared infrastructure

Many teams start with Compose and migrate to K8s when they hit its limits. That's the right approach.

---

**Q3: What does Kubernetes add that Docker doesn't have?**

Kubernetes adds the "cluster layer" — the ability to treat many machines as one:

1. **Multi-node scheduling**: Spreads containers across a fleet of machines. Docker runs on one machine.
2. **Self-healing**: If a Pod crashes or a node goes down, K8s automatically creates a replacement.
3. **Auto-scaling**: The Horizontal Pod Autoscaler adjusts replicas based on CPU, memory, or custom metrics.
4. **Rolling updates**: Deploy a new version with zero downtime — new Pods come up, old ones go down gracefully.
5. **Service discovery at scale**: DNS-based routing that works across nodes, not just one machine's network.
6. **Advanced storage**: Dynamic provisioning of cloud volumes via StorageClass + PVC.
7. **Multi-tenancy**: Namespaces with RBAC let teams share a cluster safely.

---

**Q4: Can you use Kubernetes without Docker?**

Yes. Kubernetes doesn't use Docker directly — it uses a container runtime that implements the Container Runtime Interface (CRI). Common CRI runtimes include:

- **containerd** — the most common (Docker uses this internally too)
- **CRI-O** — lightweight, developed by Red Hat
- **Docker Engine** — was the default before K8s 1.20, deprecated in K8s 1.24

You still build images with Docker (`docker build`, `docker push`). K8s just doesn't run `docker run` to start them — it calls containerd directly.

---

**Q5: Does moving to Kubernetes mean you stop writing Dockerfiles?**

No. Dockerfiles are still how you build container images. The workflow is the same:
```
Write code → docker build → docker push → (K8s pulls) → kubectl apply
```

Kubernetes consumes OCI-compliant container images. You build them with Docker, Buildah, or any compliant tool, push to a registry, and K8s pulls from that registry. The Dockerfile doesn't change — only the deployment step changes.

---

## Intermediate

**Q6: What is the mental model shift when moving from Docker to Kubernetes?**

With Docker, you think about **individual containers** on a single machine. You say "run this container with these settings" and Docker does it, right here, right now.

With Kubernetes, you shift to **declaring desired state**. You say "I want 3 replicas of this app running at all times" and K8s figures out where to put them, keeps them running, and replaces them if they fail. You never say "run this container on this machine" — you say "this is what I want" and K8s makes it happen.

This is the declarative vs imperative shift:
- Docker is **imperative**: you issue commands and things happen
- Kubernetes is **declarative**: you describe the desired state in YAML and the control loop reconciles reality to match

The other shift is from **local awareness to cluster awareness**. In Docker, you know exactly what's running where. In K8s, you often don't know — and you don't need to.

---

**Q7: How are Docker networks different from Kubernetes Services?**

**Docker networks** are local bridge networks on a single host. Services in the same Compose project can reach each other by service name because they're on the same Docker network. This only works on one machine.

**Kubernetes Services** are cluster-wide network abstractions. A Service gets a stable DNS name (`my-service.namespace.svc.cluster.local`) and a virtual IP. When you send traffic to that IP, K8s load-balances it across all healthy Pods matching the Service's label selector — across any node in the cluster.

Key differences:
| Aspect | Docker Network | Kubernetes Service |
|---|---|---|
| Scope | Single host only | Across all cluster nodes |
| Discovery | Hostname within Compose project | DNS name cluster-wide |
| Load balancing | None (single container) | Across all matching Pods |
| Stability | Container-lifetime | Stable even as Pods restart |
| External access | Port mapping (`-p 80:80`) | NodePort, LoadBalancer, or Ingress |

---

**Q8: What capabilities does Kubernetes provide that Docker Compose fundamentally cannot?**

1. **Multi-node scheduling**: K8s distributes containers across a fleet of machines. Compose runs on one machine.
2. **Node failure recovery**: If a K8s node dies, its Pods are rescheduled on other nodes. Compose has no concept of nodes.
3. **Auto-scaling (HPA)**: K8s adjusts replica count based on CPU/memory/custom metrics. Compose requires manual scaling.
4. **True zero-downtime rolling updates**: K8s's Deployment rollout starts new Pods before killing old ones, with configurable health checks before traffic switches. Compose re-creates containers, which causes a gap.
5. **Network isolation**: K8s Namespaces and NetworkPolicies provide multi-tenant isolation. Compose has a single network per project.
6. **Advanced storage**: PVCs with StorageClass allow dynamic provisioning of cloud storage (EBS, GCE PD, Azure Disk). Compose only supports static volume mounts.

---

**Q9: How does service discovery work differently in Docker Compose vs Kubernetes?**

**Docker Compose**: Services resolve by service name within the Compose network. If you have a service named `db`, other services reach it at hostname `db`. This is a bridge network on one host.

**Kubernetes**: Pods reach other services via DNS entries in the format `<service-name>.<namespace>.svc.cluster.local`. Within the same namespace, short names work: `db` resolves to `db.default.svc.cluster.local`. K8s CoreDNS handles all resolution. Services load-balance across all healthy Pods matching the selector.

The key difference: K8s service discovery works across nodes. It's network-level routing, not just local hostname resolution.

---

**Q10: What is a Kubernetes Pod and how does it differ from a Docker container?**

A Docker container is a single isolated process with its own filesystem, network namespace, and process namespace.

A Kubernetes Pod is the smallest deployable unit in K8s, and it can contain one or more containers. Containers within a Pod share:
- The same network namespace (same IP, same ports — they can communicate via localhost)
- The same storage volumes
- The same lifecycle (scheduled together, die together)

In practice, most Pods run one container. Multi-container Pods are used for sidecar patterns: a main app container + a logging agent container, or a main container + an Envoy proxy sidecar.

---

## Advanced

**Q11: What happens to your Docker knowledge when you move to Kubernetes?**

Your Docker knowledge remains valuable and directly applicable — it just moves to a different layer of the stack.

What carries over:
- **Dockerfile skills**: You still write Dockerfiles and build images the same way
- **Image optimization**: Multi-stage builds, layer caching, minimal base images — all still matter
- **Container debugging**: `kubectl exec` works the same as `docker exec`; log reading is the same
- **Registry management**: Same registries, same authentication patterns
- **Networking fundamentals**: Understanding ports, protocols, and container networking helps you understand K8s Services and Ingress

What changes:
- **How you run things**: You stop using `docker run` and write YAML manifests instead
- **How you think about placement**: You stop caring which machine a container runs on
- **How you handle secrets**: K8s Secrets replace `.env` files and `docker secret`
- **How you scale**: Auto-scaling replaces manual `docker-compose up --scale`

Think of it as: Docker taught you to drive. Kubernetes teaches you to manage a fleet. The driving skills still matter.

---

**Q12: How do you decide what level of orchestration you need?**

Work through these questions in order:

**1. How many machines do you need?**
- One machine → Compose is fine
- Multiple machines → you need K8s or a managed alternative

**2. What is your tolerance for downtime?**
- Manual restarts acceptable → Compose + `restart: unless-stopped`
- Zero downtime required → K8s rolling updates + self-healing

**3. Do you need to scale automatically?**
- Traffic is predictable and stable → manual scaling works
- Traffic spikes unpredictably → K8s HPA

**4. How many teams are deploying?**
- One team, one app → Compose works
- Multiple teams, shared infrastructure → K8s namespaces + RBAC

**5. What is your operational capacity?**
- K8s has real operational overhead: upgrades, networking, storage, RBAC
- If your team can't support it, Compose on a reliable server is better than a poorly managed K8s cluster

A poorly managed K8s cluster is worse than a well-managed Compose deployment. Choose based on your actual needs and operational maturity.

---

**Q13: When is Kubernetes overkill?**

K8s is overkill when:

- **You have one server and low traffic**: A single node K8s cluster adds overhead without the multi-node benefits. Run Compose instead.
- **You're in early product development**: Kubernetes slows iteration. When you're figuring out product-market fit, Compose lets you move faster.
- **Your team has no K8s experience**: Kubernetes has a steep learning curve. A misconfigured K8s cluster can be less reliable than Compose.
- **Your app rarely changes**: If you deploy once a month and uptime SLAs are relaxed, K8s's rolling update capabilities add no value.
- **Small internal tools**: Admin dashboards, internal tooling, dev environments — Compose is the right tool.

The honest benchmark: if you can run your app on one server with `docker-compose up`, and losing that server for 5 minutes once a year is acceptable, K8s is almost certainly overkill. Use the simplest tool that meets your requirements.

---

**Q14: Explain the "self-healing" capability of Kubernetes that Docker lacks.**

Docker alone has no concept of cluster state. If a container crashes, it stays crashed (unless you've configured `restart: unless-stopped` in Compose, which only restarts on the same machine).

Kubernetes maintains a **desired state** for every Deployment. A Deployment says "always run 3 replicas of this Pod." The controller loop constantly compares the actual state to the desired state. If a Pod crashes, the controller notices the discrepancy and creates a replacement — possibly on a different node.

If a node dies entirely, K8s detects it (kubelet stops reporting), evicts all its Pods, and reschedules them on other healthy nodes — automatically, without human intervention.

---

**Q15: What is the CRI (Container Runtime Interface) and why did Kubernetes move away from direct Docker integration?**

The CRI is a plugin interface that allows K8s to support different container runtimes without modifying core K8s code. Before CRI, K8s had a hard dependency on Docker through "dockershim" — a compatibility layer that translated K8s API calls into Docker API calls.

Kubernetes deprecated dockershim in 1.20 and removed it in 1.24 for several reasons:
1. **Overhead**: Each container operation went through: kubelet → dockershim → Docker daemon → containerd. Direct kubelet → containerd removes two hops.
2. **Maintenance burden**: The dockershim code was complex and required K8s maintainers to keep up with Docker's API changes.
3. **Unnecessary features**: Docker adds features (image building, swarm) that K8s doesn't need. containerd is a smaller, focused runtime.
4. **Security**: The Docker daemon runs as root. containerd supports rootless operation.

Images built with `docker build` continue to work perfectly — Docker outputs OCI-compliant images that containerd runs natively.

---

## 📂 Navigation

⬅️ **Prev:** [Docker - Best Practices](../../01_Docker/17_Docker_Init_and_Debug/Interview_QA.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Compose to K8s Migration](../02_Compose_to_K8s_Migration/Theory.md)

| File | Description |
|---|---|
| [Theory.md](./Theory.md) | Docker vs Kubernetes — full explanation |
| [Cheatsheet.md](./Cheatsheet.md) | Quick reference and command equivalents |
| [Interview_QA.md](./Interview_QA.md) | You are here — interview questions and answers |
