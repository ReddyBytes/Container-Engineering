# Kubernetes Practice Questions — 100 Questions from Basics to Mastery

> Test yourself across the full Kubernetes curriculum. Answers hidden until clicked.

---

## How to Use This File

1. **Read the question** — attempt your answer before opening the hint
2. **Use the framework** — run through the 5-step thinking process first
3. **Check your answer** — click "Show Answer" only after you've tried

---

## How to Think: 5-Step Framework

1. **Restate** — what is this question actually asking?
2. **Identify the concept** — which Kubernetes concept is being tested?
3. **Recall the rule** — what is the exact behaviour or rule?
4. **Apply to the case** — trace through the scenario step by step
5. **Sanity check** — does the result make sense? What edge cases exist?

---

## Progress Tracker

- [ ] **Tier 1 — Basics** (Q1–Q33): Fundamentals and core commands
- [ ] **Tier 2 — Intermediate** (Q34–Q66): Advanced features and real patterns
- [ ] **Tier 3 — Advanced** (Q67–Q75): Deep internals and edge cases
- [ ] **Tier 4 — Interview / Scenario** (Q76–Q90): Explain-it, compare-it, real-world problems
- [ ] **Tier 5 — Critical Thinking** (Q91–Q100): Predict output, debug, design decisions

---

## Question Type Legend

| Tag | Meaning |
|---|---|
| `[Normal]` | Recall + apply |
| `[Thinking]` | Requires reasoning about internals |
| `[Logical]` | Predict output or trace execution |
| `[Critical]` | Tricky gotcha or edge case |
| `[Interview]` | Explain or compare in interview style |
| `[Debug]` | Find and fix the broken code/config |
| `[Design]` | Architecture or approach decision |

---

## 🟢 Tier 1 — Basics

---

### Q1 · [Normal] · `what-is-k8s`

> **What problem does Kubernetes solve? What are the 3 core things it manages: scheduling, scaling, and self-healing?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Kubernetes solves the problem of running containerized applications reliably at scale across many machines. Without it, you'd have to manually decide where to run containers, scale them up and down by hand, and restart them when they crash.

The 3 core things Kubernetes manages:

1. **Scheduling** — decides which node a container runs on based on available CPU, memory, and constraints
2. **Scaling** — increases or decreases the number of running container replicas based on load or manual instruction
3. **Self-healing** — detects failed containers and replaces them automatically without human intervention

**How to think through this:**
1. Think of Kubernetes as an operations team that never sleeps — it constantly watches what's running and acts to match your declared desired state
2. Scheduling = placement decisions; Scaling = count decisions; Self-healing = failure recovery
3. All three reduce the manual toil of running distributed systems

**Key takeaway:** Kubernetes is a desired-state engine — you declare what you want, and it continuously works to make reality match that declaration.

</details>

📖 **Theory:** [what-is-k8s](./01_What_is_Kubernetes/Theory.md#module-01--what-is-kubernetes)


---

### Q2 · [Normal] · `k8s-vs-docker`

> **What is the difference between Docker and Kubernetes? Can Kubernetes run without Docker?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Docker is a container runtime — it builds and runs containers on a single machine. Kubernetes is an orchestrator — it manages containers across many machines.

The analogy: Docker is a shipping container. Kubernetes is the port authority that decides which ship carries which container, tracks where everything is, and reroutes if a ship sinks.

**How to think through this:**
1. Docker answers: "How do I package and run this application in a container?"
2. Kubernetes answers: "How do I run hundreds of containers across dozens of machines reliably?"
3. They operate at different levels — Docker is node-local; Kubernetes is cluster-wide

**Can Kubernetes run without Docker?**
Yes. Kubernetes uses the **Container Runtime Interface (CRI)** to talk to container runtimes. Docker is one option, but containerd and CRI-O are now more common. In fact, Docker support was deprecated in Kubernetes v1.20 and removed in v1.24 — most clusters now use containerd directly.

**Key takeaway:** Docker builds and runs containers; Kubernetes orchestrates them across a cluster — and Kubernetes no longer requires Docker specifically.

</details>

📖 **Theory:** [k8s-vs-docker](./01_What_is_Kubernetes/Theory.md#without-k8s-vs-with-k8s)


---

### Q3 · [Normal] · `k8s-architecture`

> **Describe the Kubernetes architecture: control plane and worker nodes. Name the components in each.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A Kubernetes cluster has two tiers: the **control plane** (the brain) and **worker nodes** (the muscle).

```
┌─────────────────────────────────────────────┐
│              CONTROL PLANE                  │
│  kube-apiserver  │  etcd  │  kube-scheduler │
│  kube-controller-manager  │  cloud-controller│
└────────────────────┬────────────────────────┘
                     │ API calls
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   ┌─────────┐  ┌─────────┐  ┌─────────┐
   │ Worker  │  │ Worker  │  │ Worker  │
   │ Node 1  │  │ Node 2  │  │ Node 3  │
   │ kubelet │  │ kubelet │  │ kubelet │
   │kube-proxy│ │kube-proxy│ │kube-proxy│
   │ runtime │  │ runtime │  │ runtime │
   └─────────┘  └─────────┘  └─────────┘
```

**Control plane components:** kube-apiserver, etcd, kube-scheduler, kube-controller-manager

**Worker node components:** kubelet, kube-proxy, container runtime (containerd/CRI-O)

**How to think through this:**
1. The control plane holds all cluster state and makes all decisions — it never runs your application workloads
2. Worker nodes are where your Pods actually run
3. Every component on a worker node talks back to the control plane via the kube-apiserver

**Key takeaway:** Control plane = decision-making brain; worker nodes = execution muscle — all communication flows through the API server.

</details>

📖 **Theory:** [k8s-architecture](./02_K8s_Architecture/Theory.md#module-02--kubernetes-architecture)


---

### Q4 · [Normal] · `control-plane`

> **What are the 4 control plane components: kube-apiserver, etcd, kube-scheduler, kube-controller-manager? What does each do?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**

| Component | Role |
|---|---|
| **kube-apiserver** | The front door — all cluster communication goes through it. Exposes the Kubernetes REST API. Validates and processes requests. |
| **etcd** | The database — stores all cluster state as key-value pairs. If etcd is lost, the cluster has no memory. |
| **kube-scheduler** | The placement engine — watches for new Pods with no assigned node and picks the best node based on resources, taints, and affinity rules. |
| **kube-controller-manager** | The reconciliation loop — runs controllers (Deployment, Node, ReplicaSet, etc.) that constantly compare desired state to actual state and act to close the gap. |

**How to think through this:**
1. Think of the API server as a receptionist — every request goes through it, nothing bypasses it
2. etcd is the single source of truth — lose it, lose everything
3. The scheduler only decides *where* to place a Pod; it does not start it
4. The controller manager is a bundle of control loops, each watching one resource type

**Key takeaway:** The API server is the hub; etcd is the memory; the scheduler places work; the controller manager keeps desired state and actual state in sync.

</details>

📖 **Theory:** [control-plane](./02_K8s_Architecture/Theory.md#the-two-halves-control-plane-and-worker-nodes)


---

### Q5 · [Normal] · `worker-nodes`

> **What runs on a Kubernetes worker node: kubelet, kube-proxy, container runtime? What does each do?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**

| Component | Role |
|---|---|
| **kubelet** | The node agent — talks to the API server, ensures the containers described in PodSpecs are running and healthy on its node. Reports node and Pod status back. |
| **kube-proxy** | The network rule manager — maintains iptables/IPVS rules on each node to implement Service routing. Directs traffic to the correct Pod IPs. |
| **Container runtime** | The actual engine that runs containers — containerd or CRI-O. The kubelet talks to it via the CRI (Container Runtime Interface). |

**How to think through this:**
1. kubelet = the local supervisor. It receives work orders from the control plane and makes sure containers are running
2. kube-proxy = the traffic director. It doesn't proxy traffic directly anymore (on most setups) — it just programs kernel-level rules
3. The container runtime does the actual low-level work: pulling images, creating namespaces, starting processes

**Key takeaway:** kubelet manages Pod lifecycle, kube-proxy manages network rules, and the container runtime actually runs containers.

</details>

📖 **Theory:** [worker-nodes](./02_K8s_Architecture/Theory.md#the-two-halves-control-plane-and-worker-nodes)


---

### Q6 · [Normal] · `etcd`

> **What is etcd? What is stored in it? Why is etcd backup critical for disaster recovery?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**etcd** is a distributed, strongly consistent key-value store. It is the sole persistent storage backend for a Kubernetes cluster.

**What is stored in etcd:**
- All Kubernetes object state: Pods, Deployments, Services, ConfigMaps, Secrets, RBAC rules, namespaces — everything
- Cluster membership information
- The current and desired state for every resource

**Why backup is critical:**
If etcd is lost without a backup, the cluster has no record of what was running, what configuration existed, or what users and permissions were defined. The cluster cannot recover — it starts from a blank state. There is no other copy of this data.

**How to think through this:**
1. etcd is the only stateful component of the control plane — everything else can be restarted and reconnects
2. Losing etcd = losing the entire cluster's brain
3. Best practice: snapshot etcd regularly with `etcdctl snapshot save` and store snapshots off-cluster

**Key takeaway:** etcd is the single source of truth for all cluster state — without a backup, a failed etcd means a complete cluster rebuild from scratch.

</details>

📖 **Theory:** [etcd](./02_K8s_Architecture/Theory.md#etcd)


---

### Q7 · [Normal] · `kubectl-basics`

> **What do these kubectl commands do: `get`, `describe`, `apply`, `delete`, `logs`, `exec`?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**

| Command | What it does |
|---|---|
| `kubectl get` | Lists resources. `kubectl get pods` shows all pods with basic status. |
| `kubectl describe` | Shows detailed info about a resource: events, conditions, spec, status. Best for debugging. |
| `kubectl apply` | Creates or updates resources from a YAML/JSON file. Declarative — the cluster reconciles to match the file. |
| `kubectl delete` | Removes a resource. Can target by name, label, or file. |
| `kubectl logs` | Streams stdout/stderr from a container in a Pod. Add `-f` to follow, `-c` to pick a container. |
| `kubectl exec` | Runs a command inside a running container. `kubectl exec -it pod-name -- /bin/sh` opens an interactive shell. |

**How to think through this:**
1. `get` and `describe` are read-only — safe to run anytime
2. `apply` is idempotent — running it twice with the same file produces the same result
3. `logs` and `exec` are debug tools — attach to a live running container

**Key takeaway:** `get`/`describe` for observing, `apply`/`delete` for changing state, `logs`/`exec` for debugging live containers.

</details>

📖 **Theory:** [kubectl-basics](./03_Installation_and_Setup/Theory.md#kubectl-the-swiss-army-knife)


---

### Q8 · [Normal] · `kubeconfig`

> **What is a kubeconfig file? What are contexts? How do you switch between clusters with kubectl?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A **kubeconfig** file (`~/.kube/config` by default) is a YAML file that tells kubectl how to connect to one or more Kubernetes clusters. It contains:

- **Clusters** — API server URLs and CA certificates
- **Users** — credentials (tokens, client certs) for authenticating
- **Contexts** — a named pairing of a cluster + user + namespace

A **context** is a shortcut: "when I use context `prod`, connect to this cluster as this user in this namespace."

**How to switch contexts:**
```bash
kubectl config get-contexts          # list all contexts
kubectl config current-context       # show active context
kubectl config use-context <name>    # switch to a context
```

**How to think through this:**
1. Think of kubeconfig like a browser bookmark file — each bookmark (context) points to a different server with different login credentials
2. You can have dozens of clusters in one kubeconfig and switch between them instantly
3. `KUBECONFIG` env var can point to multiple files merged at runtime

**Key takeaway:** Contexts in kubeconfig let you switch between clusters and identities in one command without editing any files.

</details>

📖 **Theory:** [kubeconfig](./03_Installation_and_Setup/Theory.md#then-copy-the-kubeconfig)


---

### Q9 · [Normal] · `pods-basics`

> **What is a Pod? Can a Pod have multiple containers? How do containers in the same Pod communicate?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A **Pod** is the smallest deployable unit in Kubernetes. It wraps one or more containers that are always scheduled together on the same node and share the same network namespace and storage volumes.

**Can a Pod have multiple containers?**
Yes. The most common pattern is a single main container, but multi-container Pods are used for sidecar patterns — e.g., a log shipper alongside a web server.

**How containers in the same Pod communicate:**
- **Network:** They share the same network namespace, so they communicate via `localhost`. Container A can call container B on `localhost:8080`.
- **Storage:** They can share volumes mounted at different paths inside each container.
- They do NOT share the filesystem by default — only explicitly shared volumes.

**How to think through this:**
1. Think of a Pod as a logical host — containers inside it behave like processes on the same machine
2. Sharing localhost is what makes sidecar patterns (log shippers, proxies) work cleanly
3. A Pod gets one IP address — traffic to that IP reaches the Pod's network namespace, not a specific container

**Key takeaway:** A Pod is a shared execution environment — containers inside share localhost and volumes, making them tightly coupled co-located processes.

</details>

📖 **Theory:** [pods-basics](./04_Pods/Theory.md#module-04--pods)


---

### Q10 · [Normal] · `pod-lifecycle`

> **What are the Pod phases: Pending, Running, Succeeded, Failed, Unknown? What causes each?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**

| Phase | Meaning | Common causes |
|---|---|---|
| **Pending** | Pod accepted by the cluster but not yet running | Waiting for scheduling (no node fits), image pull in progress, PVC not yet bound |
| **Running** | Pod bound to a node, at least one container is running | Normal operating state |
| **Succeeded** | All containers exited with code 0 and won't restart | Batch jobs or one-off tasks that completed cleanly |
| **Failed** | All containers have exited, at least one with non-zero code | Application crash, OOMKill, container error |
| **Unknown** | Pod state cannot be determined | Node communication lost — kubelet stopped reporting |

**How to think through this:**
1. Pending is often a scheduling or resource issue — `kubectl describe pod` shows events that explain why
2. Running doesn't mean healthy — containers could be crashing and restarting (CrashLoopBackOff shows in container status, not pod phase)
3. Unknown almost always means a node problem, not an application problem

**Key takeaway:** Pod phase is high-level — always check container-level status and events for the real diagnosis.

</details>

📖 **Theory:** [pod-lifecycle](./04_Pods/Theory.md#pod-lifecycle)


---

### Q11 · [Debug] · `pod-spec`

> **Write a minimal Pod spec YAML that runs an nginx container with a CPU limit of 100m and memory limit of 128Mi.**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers:
  - name: nginx
    image: nginx:latest
    resources:
      limits:
        cpu: "100m"
        memory: "128Mi"
```

<details>
<summary>💡 Show Answer</summary>

**Answer:**
The YAML above is correct. Key points:

- `apiVersion: v1` — Pods are a core API resource
- `kind: Pod` — not Deployment, just a bare Pod
- `resources.limits` sets the maximum CPU and memory the container can use
- `100m` = 100 millicores = 0.1 of one CPU core
- `128Mi` = 128 mebibytes of RAM

**How to think through this:**
1. Always include `apiVersion`, `kind`, `metadata.name`, and `spec.containers`
2. `resources.limits` caps usage — if the container exceeds the memory limit, it gets OOMKilled
3. You can also set `resources.requests` (guaranteed allocation) separately from limits

**Key takeaway:** A minimal Pod spec needs 4 things: apiVersion, kind, metadata.name, and spec.containers with at least a name and image.

</details>

📖 **Theory:** [pod-spec](./04_Pods/Theory.md#module-04--pods)


---

### Q12 · [Normal] · `deployments`

> **What is a Deployment? What does it add on top of a Pod spec? What does `kubectl rollout undo` do?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A **Deployment** is a higher-level abstraction that manages a set of identical Pods. You declare the desired state (how many replicas, what image, what update strategy), and the Deployment controller continuously reconciles toward it.

**What it adds on top of a raw Pod:**
- **ReplicaSet management** — ensures N replicas are always running
- **Rolling updates** — replaces Pods gradually with zero downtime when you change the image
- **Rollback history** — keeps previous ReplicaSet versions so you can roll back
- **Self-healing** — if a Pod dies, the Deployment replaces it automatically

**`kubectl rollout undo`:**
Rolls the Deployment back to its previous revision. It re-activates the previous ReplicaSet (with the old image/config) and scales down the current one. You can also target a specific revision: `kubectl rollout undo deployment/my-app --to-revision=2`.

**How to think through this:**
1. You almost never create bare Pods in production — Deployments are the standard for stateless workloads
2. Rolling updates create new Pods before removing old ones — traffic is never fully interrupted
3. `kubectl rollout history deployment/my-app` shows available revisions to roll back to

**Key takeaway:** A Deployment wraps Pods with replica management, rolling updates, and rollback — it's the standard unit for running stateless applications in Kubernetes.

</details>

📖 **Theory:** [deployments](./05_Deployments_and_ReplicaSets/Theory.md#module-05--deployments-and-replicasets)


---

### Q13 · [Normal] · `replicasets`

> **What is a ReplicaSet? Why do you rarely create one directly? What maintains the desired pod count?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A **ReplicaSet** ensures that a specified number of Pod replicas are running at any given time. It uses a label selector to identify which Pods it owns, and creates or deletes Pods to match the desired count.

**Why you rarely create one directly:**
A Deployment manages ReplicaSets for you. When you update a Deployment, it creates a new ReplicaSet with the new Pod template and gradually shifts traffic from the old one. If you create a ReplicaSet directly, you lose rolling updates and rollback capability. There's almost no reason to manage ReplicaSets by hand.

**What maintains the desired pod count:**
The **ReplicaSet controller** inside kube-controller-manager runs a reconciliation loop. It continuously compares the number of running Pods matching the selector against the desired replica count, and creates or deletes Pods accordingly.

**How to think through this:**
1. ReplicaSet = "keep exactly N of these Pods running"
2. Deployment = "keep N Pods running AND manage how they get updated"
3. A Deployment owning a ReplicaSet is the standard pattern — you configure the Deployment and let it manage the ReplicaSet

**Key takeaway:** ReplicaSets provide replica guarantees, but Deployments wrap them with update management — always use Deployments for stateless workloads, not raw ReplicaSets.

</details>

📖 **Theory:** [replicasets](./05_Deployments_and_ReplicaSets/Theory.md#module-05--deployments-and-replicasets)


---

### Q14 · [Normal] · `rolling-updates`

> **What is a rolling update? What do `maxSurge` and `maxUnavailable` control?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A **rolling update** replaces running Pods incrementally with new ones rather than all at once. Old Pods are taken down gradually as new Pods become healthy, ensuring the application stays available throughout the update.

**`maxSurge`:** The maximum number of Pods that can be created above the desired replica count during an update. If you have 10 replicas and maxSurge=2, up to 12 Pods can exist at once.

**`maxUnavailable`:** The maximum number of Pods that can be unavailable during the update. If maxUnavailable=1, at least 9 of 10 Pods must be healthy at all times.

**How to think through this:**
1. Both values can be absolute numbers or percentages (`25%` is the default for both)
2. maxSurge controls speed (higher = faster update, more resource usage)
3. maxUnavailable controls safety (lower = fewer dropped requests, slower rollout)
4. Setting maxUnavailable=0 and maxSurge=1 means no downtime but slightly higher resource usage

**Key takeaway:** maxSurge and maxUnavailable are the two levers that trade off update speed against resource usage and availability risk.

</details>

📖 **Theory:** [rolling-updates](./05_Deployments_and_ReplicaSets/Theory.md#rolling-update-strategy)


---

### Q15 · [Normal] · `services-basics`

> **What is a Kubernetes Service? Why do you need one instead of connecting directly to a Pod IP?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A **Service** is a stable network endpoint that provides consistent access to a set of Pods. It selects Pods by label and load-balances traffic across them.

**Why not connect directly to a Pod IP:**
Pod IPs are ephemeral — every time a Pod is restarted, replaced, or rescheduled, it gets a new IP address. If your application hardcodes a Pod IP, it breaks the moment that Pod is replaced. A Service provides:

- A stable virtual IP (ClusterIP) that never changes
- Automatic load balancing across all healthy Pods matching the selector
- DNS resolution via the cluster DNS (`my-service.my-namespace.svc.cluster.local`)

**How to think through this:**
1. Think of a Service as a phone number that always reaches the right department, even as staff changes
2. The Service's label selector continuously tracks which Pods are healthy and available
3. kube-proxy programs network rules on every node so that traffic to the Service IP gets routed to a real Pod

**Key takeaway:** Services provide stable DNS names and virtual IPs that abstract away Pod churn — without them, any Pod restart would break connectivity.

</details>

📖 **Theory:** [services-basics](./06_Services/Theory.md#module-06--services)


---

### Q16 · [Normal] · `clusterip-nodeport-lb`

> **What are the 3 main Service types: ClusterIP, NodePort, LoadBalancer? When do you use each?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**

| Type | What it does | When to use |
|---|---|---|
| **ClusterIP** | Assigns a virtual IP reachable only inside the cluster | Internal service-to-service communication. Default type. |
| **NodePort** | Exposes the service on a static port (30000–32767) on every node's IP | Development, on-prem clusters without a cloud LB, or when you control external routing yourself |
| **LoadBalancer** | Provisions a cloud load balancer (AWS ALB/NLB, GCP LB, etc.) and routes external traffic to the service | Production workloads on cloud providers where you need external internet access |

**How to think through this:**
1. ClusterIP is the building block — NodePort and LoadBalancer build on top of it
2. NodePort is rarely used in production because it exposes ports directly on nodes and requires firewall management
3. LoadBalancer is the most common for production but creates a cloud LB per service, which can get expensive — Ingress solves this by sharing one LB across many services

**Key takeaway:** ClusterIP for internal, NodePort for simple external access, LoadBalancer for production cloud deployments — most teams use ClusterIP + Ingress to avoid proliferating cloud LBs.

</details>

📖 **Theory:** [clusterip-nodeport-lb](./06_Services/Theory.md#clusterip-default)


---

### Q17 · [Normal] · `service-discovery`

> **How does Kubernetes DNS work? How does a Pod in namespace A resolve a service in namespace B?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Kubernetes runs a cluster DNS server (CoreDNS) that automatically creates DNS records for every Service. Each Service gets a DNS name in the format:

```
<service-name>.<namespace>.svc.cluster.local
```

**Within the same namespace:** A Pod can reach a Service using just the service name: `curl http://my-service`

**Across namespaces:** The short name doesn't resolve. You must use the fully qualified form: `curl http://my-service.namespace-b.svc.cluster.local`

Or the shorter cross-namespace form: `curl http://my-service.namespace-b`

**How to think through this:**
1. CoreDNS watches the API server for new Services and automatically adds DNS records
2. Every Pod's `/etc/resolv.conf` is configured at creation to use CoreDNS and search the local namespace first
3. The search path in resolv.conf explains why short names work within a namespace — the full domain is appended automatically

**Key takeaway:** Kubernetes DNS gives every Service a stable DNS name — short names work within a namespace, full FQDN required across namespaces.

</details>

📖 **Theory:** [service-discovery](./06_Services/Theory.md#module-06--services)


---

### Q18 · [Normal] · `configmaps`

> **What is a ConfigMap? How do you mount one as environment variables vs as a file volume?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A **ConfigMap** stores non-sensitive configuration data as key-value pairs. It decouples configuration from the container image, so you can change config without rebuilding the image.

**Mounting as environment variables:**
```yaml
envFrom:
- configMapRef:
    name: my-config
```
This injects every key in the ConfigMap as an environment variable in the container.

**Mounting as a file volume:**
```yaml
volumes:
- name: config-vol
  configMap:
    name: my-config
containers:
- volumeMounts:
  - name: config-vol
    mountPath: /etc/config
```
Each key in the ConfigMap becomes a file at `/etc/config/<key-name>` with the value as file content.

**How to think through this:**
1. Env vars are simpler but require a Pod restart to pick up changes
2. Volume mounts are updated automatically when the ConfigMap changes (with a short delay) — no restart needed
3. Use volumes when the application reads config from files (e.g., nginx.conf, app.properties)

**Key takeaway:** ConfigMaps decouple config from images — inject as env vars for simplicity, or as volume files when you need live updates or file-based config.

</details>

📖 **Theory:** [configmaps](./07_ConfigMaps_and_Secrets/Theory.md#module-07--configmaps-and-secrets)


---

### Q19 · [Normal] · `secrets`

> **What is a Kubernetes Secret? How is it different from a ConfigMap? What is its main limitation (hint: base64)?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A **Secret** stores sensitive data such as passwords, API keys, and TLS certificates. It works similarly to a ConfigMap but is intended for confidential values.

**Differences from ConfigMap:**

| | ConfigMap | Secret |
|---|---|---|
| Purpose | Non-sensitive config | Sensitive credentials |
| Storage encoding | Plain text | base64 encoded |
| RBAC | Standard | Can be restricted separately |
| Mounted behavior | Files or env vars | Same, but tmpfs mount by default |

**Main limitation — base64 is NOT encryption:**
Secrets are only base64 encoded, not encrypted by default. Anyone with access to etcd or sufficient RBAC permissions can decode them trivially: `echo "dXNlcm5hbWU=" | base64 -d`. In practice, you need to enable **encryption at rest** in etcd and use tools like Sealed Secrets or Vault for real secret management.

**How to think through this:**
1. base64 is encoding, not encryption — it provides no security on its own
2. The real protection comes from RBAC (who can read the Secret) and etcd encryption at rest
3. For production, most teams use an external secrets manager (AWS Secrets Manager, HashiCorp Vault) and sync values into Kubernetes Secrets

**Key takeaway:** Kubernetes Secrets are base64-encoded, not encrypted — treat them as a delivery mechanism, not a security boundary, and always enable etcd encryption at rest.

</details>

📖 **Theory:** [secrets](./07_ConfigMaps_and_Secrets/Theory.md#module-07--configmaps-and-secrets)


---

### Q20 · [Debug] · `env-from-config`

> **Write a Pod spec snippet that injects all keys from a ConfigMap as environment variables.**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
  - name: app
    image: my-app:latest
    envFrom:
    - configMapRef:
        name: my-configmap
```

<details>
<summary>💡 Show Answer</summary>

**Answer:**
The YAML above is correct. `envFrom` with `configMapRef` injects every key-value pair in the named ConfigMap as an environment variable inside the container.

**Variations:**
- Inject a single key: use `env[].valueFrom.configMapKeyRef` instead of `envFrom`
- Inject from a Secret: replace `configMapRef` with `secretRef`
- Add a prefix to all keys: use `envFrom[].prefix: "APP_"` to namespace the variables

**How to think through this:**
1. `envFrom` is the bulk import — all keys become env vars in one block
2. Individual `env[].valueFrom` gives you fine-grained control over which keys to inject and what to name them
3. Env vars injected at Pod creation time — changes to the ConfigMap don't reflect until the Pod is restarted

**Key takeaway:** `envFrom.configMapRef` bulk-injects all ConfigMap keys as env vars — use individual `valueFrom.configMapKeyRef` when you need selective injection or renaming.

</details>

📖 **Theory:** [env-from-config](./07_ConfigMaps_and_Secrets/Theory.md#separate-config-from-code)


---

### Q21 · [Normal] · `namespaces`

> **What are Kubernetes namespaces? What resources are namespace-scoped vs cluster-scoped?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**Namespaces** are virtual partitions within a Kubernetes cluster. They group resources logically and are the primary mechanism for organizing workloads, applying resource quotas, and scoping RBAC permissions.

**Namespace-scoped resources** (live inside a namespace):
- Pods, Deployments, Services, ConfigMaps, Secrets, PersistentVolumeClaims, ServiceAccounts, Roles, RoleBindings

**Cluster-scoped resources** (exist at the cluster level, no namespace):
- Nodes, PersistentVolumes, StorageClasses, ClusterRoles, ClusterRoleBindings, Namespaces themselves

**Default namespaces in a fresh cluster:**
- `default` — where resources go when no namespace is specified
- `kube-system` — Kubernetes system components (CoreDNS, kube-proxy, etc.)
- `kube-public` — publicly readable data
- `kube-node-lease` — node heartbeat objects

**How to think through this:**
1. If a resource exists on a node (Node) or affects the whole cluster (PV, StorageClass), it's cluster-scoped
2. If a resource is part of an application workload, it's almost always namespace-scoped
3. Namespaces are free to create — use them liberally for teams, environments, and applications

**Key takeaway:** Namespaces scope most workload resources; nodes, cluster-wide storage, and cluster roles are scoped to the cluster and exist outside namespaces.

</details>

📖 **Theory:** [namespaces](./08_Namespaces/Theory.md#module-08--namespaces)


---

### Q22 · [Thinking] · `namespace-isolation`

> **How do namespaces provide isolation? What isolation do they NOT provide (hint: not network)?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**What namespaces DO provide:**
- **Name isolation** — two Deployments named `frontend` can coexist in `namespace-a` and `namespace-b` without conflict
- **RBAC scope** — Roles and RoleBindings apply within a namespace, letting you grant team A access to only their namespace
- **Resource quotas** — LimitRanges and ResourceQuotas apply per namespace, preventing one team from consuming all cluster resources
- **Soft organizational boundaries** — logical grouping for humans and tooling

**What namespaces do NOT provide:**
- **Network isolation** — by default, Pods in any namespace can talk to Pods in any other namespace. A Pod in `team-a` can freely call a Service in `team-b`. You need **NetworkPolicies** to restrict cross-namespace traffic.
- **Security isolation** — namespaces don't prevent privilege escalation. A container with root access can potentially escape to the node.
- **Hard multi-tenancy** — for true tenant isolation (untrusted workloads), you need separate clusters or stronger sandboxing (gVisor, Kata Containers).

**How to think through this:**
1. Namespaces are an organizational tool, not a security boundary
2. Network isolation requires NetworkPolicy objects — namespaces alone provide zero network separation
3. For teams sharing a cluster, combine namespaces + RBAC + NetworkPolicy + ResourceQuota for meaningful isolation

**Key takeaway:** Namespaces provide naming and RBAC scope, not network isolation — add NetworkPolicies explicitly if you need traffic separation between namespaces.

</details>

📖 **Theory:** [namespace-isolation](./08_Namespaces/Theory.md#module-08--namespaces)


---

### Q23 · [Normal] · `ingress-basics`

> **What is an Ingress? What is an Ingress Controller? What does the Ingress itself define vs what does the controller do?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
An **Ingress** is a Kubernetes API object that defines HTTP/HTTPS routing rules: which hostnames and URL paths should route to which Services.

An **Ingress Controller** is the actual software that reads those rules and implements them. Without a controller, Ingress objects do nothing — they're just declarations.

**What the Ingress object defines:**
- Hostnames (`api.example.com`, `app.example.com`)
- URL path routing (`/api` → backend-service, `/` → frontend-service)
- TLS certificate references
- Annotations for controller-specific behavior

**What the Ingress Controller does:**
- Watches the API server for Ingress objects
- Configures itself (nginx, Envoy, HAProxy, AWS ALB) to implement the routing rules
- Terminates TLS
- Proxies traffic to the correct ClusterIP Services

**How to think through this:**
1. The analogy: Ingress object = the menu listing what's available; Ingress Controller = the kitchen that actually fulfills orders
2. One controller handles many Ingress objects — this is how you share a single load balancer across many services
3. You must install an Ingress Controller separately — it doesn't ship with Kubernetes

**Key takeaway:** Ingress objects are routing declarations; the Ingress Controller is the reverse proxy that enforces them — you need both for HTTP routing to work.

</details>

📖 **Theory:** [ingress-basics](./09_Ingress/Theory.md#module-09--ingress)


---

### Q24 · [Normal] · `ingress-controller`

> **Name 3 popular Ingress Controllers. How do you route traffic to different services based on the URL path?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**3 popular Ingress Controllers:**
1. **ingress-nginx** — NGINX-based, the most widely used open source controller
2. **AWS Load Balancer Controller** — provisions AWS ALBs/NLBs natively using Ingress annotations
3. **Traefik** — cloud-native reverse proxy with built-in Kubernetes support and a dashboard

Others: HAProxy Ingress, Istio Gateway, Contour (Envoy-based).

**Path-based routing example:**
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
spec:
  rules:
  - host: example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 8080
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
```

**How to think through this:**
1. Rules are matched top to bottom — more specific paths should come first
2. `pathType: Prefix` means `/api` matches `/api`, `/api/users`, `/api/v2/...`
3. `pathType: Exact` matches only the exact path string

**Key takeaway:** Path-based routing in Ingress uses ordered rules with `pathType: Prefix` or `Exact` — more specific paths must precede catch-all paths.

</details>

📖 **Theory:** [ingress-controller](./09_Ingress/Theory.md#ingress-resource-vs-ingress-controller)


---

### Q25 · [Normal] · `tls-ingress`

> **How do you configure TLS termination in an Ingress? What is cert-manager and what does it automate?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**TLS termination in an Ingress:**
Reference a TLS Secret (containing `tls.crt` and `tls.key`) in the Ingress spec:

```yaml
spec:
  tls:
  - hosts:
    - example.com
    secretName: example-tls-secret
  rules:
  - host: example.com
    ...
```

The Ingress Controller reads the Secret and terminates TLS at the load balancer. Traffic from the controller to backend Services is typically plain HTTP within the cluster.

**cert-manager:**
cert-manager is a Kubernetes add-on that automates the full lifecycle of TLS certificates. It:
- Watches for Ingress objects with the `cert-manager.io/cluster-issuer` annotation
- Automatically requests certificates from Let's Encrypt (or another CA) via ACME challenges
- Stores the issued certificate in the referenced Secret
- Renews certificates before they expire — no manual rotation needed

**How to think through this:**
1. Without cert-manager: create a CSR, get a cert from a CA, create a Secret manually, repeat every 90 days
2. With cert-manager: add one annotation to the Ingress and cert-manager handles everything end-to-end
3. cert-manager supports Let's Encrypt (free), Vault, and custom CAs

**Key takeaway:** TLS Ingress needs a Secret with the cert/key pair; cert-manager automates certificate issuance and renewal so you never manually rotate TLS certs again.

</details>

📖 **Theory:** [tls-ingress](./09_Ingress/Theory.md#module-09--ingress)


---

### Q26 · [Normal] · `persistent-volumes`

> **What is a PersistentVolume (PV)? What is a PersistentVolumeClaim (PVC)? What is the binding process?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A **PersistentVolume (PV)** is a cluster-scoped storage resource provisioned by an admin (or dynamically by a StorageClass). It represents actual storage — an EBS volume, NFS share, or local disk.

A **PersistentVolumeClaim (PVC)** is a namespace-scoped request for storage by a user. It specifies the required size, access mode, and optionally a StorageClass. A PVC does not care which specific PV it gets — it just needs its requirements met.

**The binding process:**
1. A PVC is created with a storage request (e.g., 10Gi, ReadWriteOnce)
2. Kubernetes finds a compatible PV (matching size, access mode, StorageClass)
3. The PV is **bound** to the PVC — a 1:1 relationship. No other PVC can use that PV.
4. The Pod references the PVC in its spec and mounts the volume

**How to think through this:**
1. The PV/PVC separation is an abstraction layer: admins manage PVs, developers request storage via PVCs
2. Binding is one-to-one — a PV can only be bound to one PVC at a time
3. With dynamic provisioning, the PV is created automatically when the PVC is submitted — no admin needed

**Key takeaway:** PV = the actual storage resource; PVC = the claim/request — Kubernetes binds them in a 1:1 match, decoupling storage provisioning from application configuration.

</details>

📖 **Theory:** [persistent-volumes](./10_Persistent_Volumes/Theory.md#module-10-persistent-volumes)


---

### Q27 · [Debug] · `pvc`

> **Write a PVC spec that requests 10Gi of ReadWriteOnce storage. How does it get bound to a PV?**

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: my-pvc
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: standard
```

<details>
<summary>💡 Show Answer</summary>

**Answer:**
The YAML above is correct.

**How it gets bound:**
1. The PVC is submitted to the API server and enters `Pending` state
2. The Kubernetes PV controller scans existing PVs for one that satisfies: access mode `ReadWriteOnce`, size >= 10Gi, matching StorageClass
3. If a matching PV exists: it's bound immediately — both PV and PVC enter `Bound` state
4. If no matching PV exists and the StorageClass supports dynamic provisioning: a new PV is created automatically (e.g., an EBS volume in AWS), then bound

**Access mode meanings:**
- `ReadWriteOnce` (RWO) — one node can mount read/write
- `ReadOnlyMany` (ROX) — many nodes can mount read-only
- `ReadWriteMany` (RWX) — many nodes can mount read/write (requires NFS or similar)

**Key takeaway:** A PVC enters Pending until a compatible PV is found or dynamically provisioned — check PVC events with `kubectl describe pvc` if it stays in Pending.

</details>

📖 **Theory:** [pvc](./10_Persistent_Volumes/Theory.md#persistentvolumeclaim-pvc)


---

### Q28 · [Normal] · `storage-classes`

> **What is a StorageClass? What does dynamic provisioning mean? What is the `reclaimPolicy`?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A **StorageClass** defines a class of storage with specific properties — the provisioner (AWS EBS, GCE PD, NFS), performance tier (SSD vs HDD), and reclaim behavior. It's the template that dynamic provisioning uses to create PVs.

**Dynamic provisioning:**
When a PVC references a StorageClass and no existing PV matches, Kubernetes automatically creates a new PV by calling the provisioner (e.g., creating an EBS volume in AWS). The PV is created on demand and immediately bound to the PVC. No admin intervention needed.

Without a StorageClass (static provisioning): admins pre-create PVs manually.

**`reclaimPolicy`:** Determines what happens to the PV (and underlying storage) when the PVC is deleted:
- **`Delete`** (default for dynamic) — the PV and the underlying storage are deleted. Storage is gone.
- **`Retain`** — the PV stays in a `Released` state. Data is preserved. Admin must manually reclaim it.
- **`Recycle`** (deprecated) — wipes the volume and makes it available again.

**How to think through this:**
1. Use `Delete` for ephemeral workloads where you don't need the data after the PVC is gone
2. Use `Retain` for databases or anything where accidental data loss would be catastrophic
3. The default StorageClass is used when PVCs don't specify one — check with `kubectl get storageclass`

**Key takeaway:** StorageClass is the provisioner template that enables on-demand PV creation — `reclaimPolicy: Retain` protects data when PVCs are deleted; `Delete` cleans up automatically.

</details>

📖 **Theory:** [storage-classes](./10_Persistent_Volumes/Theory.md#the-story-the-hotel-without-storage-lockers)


---

### Q29 · [Normal] · `rbac-basics`

> **What is RBAC in Kubernetes? What are the 4 objects: Role, ClusterRole, RoleBinding, ClusterRoleBinding?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**RBAC (Role-Based Access Control)** is Kubernetes' authorization system. It controls who (subjects) can do what (verbs) on which resources.

**The 4 objects:**

| Object | Scope | Purpose |
|---|---|---|
| **Role** | Namespace | Defines permissions for resources within one namespace |
| **ClusterRole** | Cluster-wide | Defines permissions for cluster-scoped resources or across all namespaces |
| **RoleBinding** | Namespace | Grants a Role (or ClusterRole) to a subject within a namespace |
| **ClusterRoleBinding** | Cluster-wide | Grants a ClusterRole to a subject across the entire cluster |

**Subjects** that can be granted roles: Users, Groups, ServiceAccounts.

**How to think through this:**
1. Role + RoleBinding = "this ServiceAccount can read Pods in the `staging` namespace"
2. ClusterRole + ClusterRoleBinding = "this user can read Pods in ALL namespaces"
3. You can bind a ClusterRole with a RoleBinding to limit it to one namespace — useful for reusable permission templates

**Key takeaway:** Roles define permissions; Bindings assign them to subjects — namespace-scoped for isolated access, cluster-scoped for cluster-wide or cross-namespace access.

</details>

📖 **Theory:** [rbac-basics](./11_RBAC/Theory.md#module-11-rbac--role-based-access-control)


---

### Q30 · [Thinking] · `roles-clusterroles`

> **What is the difference between a Role and a ClusterRole? When do you need a ClusterRole?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**

| | Role | ClusterRole |
|---|---|---|
| Scope | Single namespace | Entire cluster |
| Can access namespace resources | Yes, within its namespace | Yes, across all namespaces |
| Can access cluster-scoped resources | No | Yes |

**You need a ClusterRole when:**
1. **Accessing cluster-scoped resources** — Nodes, PersistentVolumes, StorageClasses, ClusterRoles, Namespaces. These don't belong to any namespace, so a Role can never grant access to them.
2. **Cross-namespace access** — A monitoring system (like Prometheus) needs to read Pods in all namespaces. A ClusterRole + ClusterRoleBinding grants this.
3. **Reusable permission templates** — You define a ClusterRole once and bind it in multiple namespaces via RoleBindings. This avoids duplicating Role definitions in every namespace.

**How to think through this:**
1. If the resource appears in `kubectl api-resources --namespaced=false`, you need a ClusterRole
2. If you want to grant the same permissions in 10 namespaces, define one ClusterRole and create 10 RoleBindings pointing to it
3. Binding a ClusterRole with a RoleBinding (not ClusterRoleBinding) restricts it to that namespace only — even though the role is cluster-scoped

**Key takeaway:** Use ClusterRole for cluster-scoped resources (Nodes, PVs), cross-namespace access, or as reusable templates — Roles are bounded to a single namespace.

</details>

📖 **Theory:** [roles-clusterroles](./11_RBAC/Theory.md#2-roles-and-clusterroles--the-what)


---

### Q31 · [Normal] · `service-accounts`

> **What is a ServiceAccount? How does a Pod use it to authenticate with the Kubernetes API?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A **ServiceAccount** is a Kubernetes identity for processes running in Pods. Just as human users have user accounts, Pods use ServiceAccounts to authenticate with the Kubernetes API server.

**How a Pod uses it:**
1. Every Pod is assigned a ServiceAccount (the `default` SA in its namespace if none is specified)
2. Kubernetes automatically mounts a JWT token for the SA into the Pod at `/var/run/secrets/kubernetes.io/serviceaccount/token`
3. When the Pod's application calls the Kubernetes API, it presents this token in the `Authorization: Bearer <token>` header
4. The API server validates the token and applies RBAC rules for that ServiceAccount

**Common use case:**
A Deployment controller or custom operator running inside the cluster needs to call the Kubernetes API to create/update resources. It does this using its ServiceAccount's token, with permissions granted via RoleBinding.

**How to think through this:**
1. In Kubernetes 1.22+, tokens are time-limited and audience-bound (via projected service account tokens) — no long-lived static tokens by default
2. Best practice: create a dedicated ServiceAccount per workload with minimal permissions (least privilege)
3. `automountServiceAccountToken: false` in the Pod spec disables auto-mounting if the Pod doesn't need API access

**Key takeaway:** ServiceAccounts give Pods an identity for API authentication — use dedicated SAs with least-privilege RBAC rather than relying on the default SA.

</details>

📖 **Theory:** [service-accounts](./21_Service_Accounts/Theory.md#module-21--service-accounts)


---

### Q32 · [Normal] · `daemonsets`

> **What is a DaemonSet? Name 3 use cases where you'd deploy a DaemonSet instead of a Deployment.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A **DaemonSet** ensures that one Pod runs on every node (or every node matching a selector). When new nodes join the cluster, the DaemonSet automatically schedules a Pod on them. When nodes are removed, those Pods are garbage collected.

Unlike a Deployment where you control replica count, a DaemonSet's replica count is always equal to the number of matching nodes.

**3 use cases for DaemonSets:**

1. **Log collection agents** — Fluentd, Filebeat, or Fluent Bit must run on every node to collect container logs from the node's filesystem (`/var/log`). A Deployment can't guarantee per-node coverage.

2. **Node monitoring / metrics** — Prometheus Node Exporter must run on every node to scrape node-level CPU, memory, disk, and network metrics. One instance per node is exactly what a DaemonSet provides.

3. **Network plugins / CNI agents** — Calico, Cilium, Weave Net, and other CNI plugins run as DaemonSets because they need to configure networking at the OS level on every single node.

**How to think through this:**
1. If the use case is "I need exactly one of these per node," DaemonSet is the right choice
2. DaemonSets respect taints — by default they don't run on control plane nodes unless you add a toleration
3. You can scope a DaemonSet to a subset of nodes using `nodeSelector` or `nodeAffinity`

**Key takeaway:** DaemonSets guarantee one Pod per node — use them for node-level infrastructure concerns like logging, monitoring, and networking agents.

</details>

📖 **Theory:** [daemonsets](./13_DaemonSets_and_StatefulSets/Theory.md#module-13-daemonsets-and-statefulsets)


---

### Q33 · [Normal] · `statefulsets`

> **What is a StatefulSet? What 3 guarantees does it provide that a Deployment doesn't?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A **StatefulSet** manages stateful applications where Pods need stable identities and ordered lifecycle management. Databases, message queues, and distributed systems like Kafka, Zookeeper, and Cassandra use StatefulSets.

**3 guarantees a StatefulSet provides that a Deployment doesn't:**

1. **Stable, persistent network identities** — Each Pod gets a predictable, stable DNS name: `pod-name-0`, `pod-name-1`, `pod-name-2`. These names don't change when Pods restart. A Headless Service provides DNS resolution so `my-db-0.my-service.namespace.svc.cluster.local` always reaches the same logical instance.

2. **Stable, persistent storage** — Each Pod gets its own PersistentVolumeClaim. When Pod `my-db-0` is rescheduled to a different node, it reattaches to the same PVC (same data). In a Deployment, all Pods share volumes or get fresh ephemeral storage on restart.

3. **Ordered, graceful deployment and scaling** — Pods are created, scaled, and deleted in order (0, 1, 2...). Pod `my-db-1` is not started until `my-db-0` is Running and Ready. Scaling down happens in reverse order. This matters for distributed databases that need an initialization sequence.

**How to think through this:**
1. Deployments are for stateless apps where any Pod can handle any request and Pods are interchangeable
2. StatefulSets are for apps where Pods have identity (primary vs replica), own their data, and have initialization dependencies
3. The ordered startup guarantee is critical for Zookeeper-style quorum systems that can't have two Pods starting simultaneously

**Key takeaway:** StatefulSets provide stable identities, stable storage, and ordered lifecycle — use them whenever Pods are NOT interchangeable and need to remember who they are across restarts.

</details>

📖 **Theory:** [statefulsets](./13_DaemonSets_and_StatefulSets/Theory.md#module-13-daemonsets-and-statefulsets)


---

## 🟡 Tier 2 — Intermediate

### Q34 · [Normal] · `health-probes`

> **What are liveness, readiness, and startup probes? What happens when each fails?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Kubernetes provides three probe types to monitor container health:

- **Liveness probe** — checks if the container is alive. If it fails, kubelet kills and restarts the container (subject to restartPolicy).
- **Readiness probe** — checks if the container is ready to serve traffic. If it fails, the pod is removed from Service endpoints — it is NOT restarted.
- **Startup probe** — checks if the container has finished initializing. While it is running, liveness and readiness probes are disabled. If it fails beyond `failureThreshold`, the container is killed and restarted.

**How to think through this:**
1. Think of liveness as "is this process still sane?" — a hung app should be restarted.
2. Think of readiness as "is this process ready for customers?" — a warming cache should not receive traffic yet.
3. Think of startup as a one-time gate that protects slow-starting apps from being killed by liveness before they finish booting.

**Key takeaway:** Liveness restarts containers, readiness gates traffic, startup protects slow initialization.

</details>

📖 **Theory:** [health-probes](./14_Health_Probes/Theory.md#module-14-health-probes)


---

### Q35 · [Normal] · `liveness-readiness`

> **When would a liveness probe pass but a readiness probe fail? Write a readiness probe that checks HTTP GET /health on port 8080.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A liveness probe passes but a readiness probe fails when the container process is alive and not hung, but is not yet ready to handle requests. Common scenarios:

- Application is still warming up a cache or loading configuration after startup.
- A downstream dependency (database, API) is temporarily unavailable and the app has flagged itself as not ready.
- A rolling deployment where new pods are starting but the app needs time to connect to services.

Readiness probe YAML:

```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 10
  failureThreshold: 3
```

**How to think through this:**
1. The process is running (liveness passes) but it has logic that returns a non-2xx from /health.
2. Kubernetes removes the pod from the Service endpoint slice — no new requests routed to it.
3. Once /health returns 2xx again, the pod is re-added to endpoints automatically.

**Key takeaway:** Readiness failure is a traffic gate, not a restart trigger — the pod stays alive but receives no requests.

</details>

📖 **Theory:** [liveness-readiness](./14_Health_Probes/Theory.md#1-liveness-probe--is-it-still-alive)


---

### Q36 · [Normal] · `startup-probe`

> **What problem does a startup probe solve that a liveness probe cannot? Write a startup probe for a slow-starting JVM application.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A liveness probe begins checking immediately (after `initialDelaySeconds`). For a JVM application that takes 2–3 minutes to start, you would need a very high `initialDelaySeconds` or a very lenient `failureThreshold` on the liveness probe — both of which make the liveness probe less effective after startup.

A **startup probe** solves this by acting as a one-time boot gate. Liveness and readiness probes are paused until the startup probe succeeds. You can give the startup probe a long timeout window without compromising the sensitivity of the liveness probe post-boot.

```yaml
startupProbe:
  httpGet:
    path: /actuator/health
    port: 8080
  failureThreshold: 30
  periodSeconds: 10
```

This allows up to 30 × 10 = 300 seconds (5 minutes) for the JVM to start. Once it succeeds, the startup probe is done and liveness takes over with its own tighter settings.

**How to think through this:**
1. A JVM with Spring Boot may take 60–180 seconds to initialize.
2. A liveness probe with `initialDelaySeconds: 180` means after boot, a hung pod won't be caught for 3 minutes.
3. Startup probe + tight liveness probe = safe slow start + fast hung-process detection.

**Key takeaway:** Startup probes decouple slow initialization from ongoing liveness sensitivity.

</details>

📖 **Theory:** [startup-probe](./14_Health_Probes/Theory.md#3-startup-probe--has-it-finished-starting-up)


---

### Q37 · [Normal] · `deployment-strategies`

> **Compare Recreate and RollingUpdate deployment strategies. When would Recreate be acceptable?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**Recreate** terminates all existing pods before creating new ones. This causes downtime but guarantees that only one version of the app runs at a time.

**RollingUpdate** incrementally replaces old pods with new ones. Controlled by:
- `maxUnavailable` — how many pods can be unavailable during the rollout (default 25%)
- `maxSurge` — how many extra pods can exist above desired count (default 25%)

This avoids downtime but means two versions run simultaneously during the rollout.

**When Recreate is acceptable:**
- The application cannot tolerate two versions running at the same time (e.g., database schema migration tied to app version).
- The app holds exclusive locks on resources (e.g., a single-writer job).
- During development or staging where brief downtime is irrelevant.
- The workload is a background worker where a short gap in processing is acceptable.

**How to think through this:**
1. Ask: can two versions coexist? If no (due to schema, protocol, or lock changes), use Recreate.
2. Ask: is downtime acceptable? If yes, Recreate is simpler and avoids compatibility concerns.
3. In production user-facing services, RollingUpdate is almost always preferred.

**Key takeaway:** RollingUpdate is zero-downtime but runs two versions simultaneously; Recreate has downtime but ensures version isolation.

</details>

📖 **Theory:** [deployment-strategies](./15_Deployment_Strategies/Theory.md#module-15-deployment-strategies)


---

### Q38 · [Normal] · `blue-green-canary`

> **How do you implement a blue-green or canary deployment in Kubernetes without a service mesh?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**Blue-Green without a service mesh:**
Run two Deployments side by side — `app-blue` and `app-green`. A single Service uses a label selector to point to one at a time. To switch traffic, patch the Service selector:

```
Service selector: app=blue  →  patch to app=green
```

All traffic flips instantly. To rollback, patch back to `app=blue`. The blue Deployment stays running until you're confident in green.

**Canary without a service mesh:**
Use replica count to split traffic proportionally. Run a stable Deployment with 9 replicas and a canary Deployment with 1 replica, both matching the same Service selector label (e.g., `app: myapp`). Kubernetes will route roughly 10% of traffic to the canary.

To increase canary traffic: scale up canary replicas and scale down stable replicas.

**Limitations without a service mesh:**
- Traffic splitting is approximate (pod-count-based, not request-percentage-based).
- No header-based routing, no session stickiness, no exact percentage control.
- A service mesh (Istio, Linkerd) or Gateway API with traffic weighting gives precise control.

**How to think through this:**
1. Blue-green = full cutover via Service selector patch.
2. Canary = proportional replica split, approximate traffic percentage.
3. For fine-grained control, use Argo Rollouts or a service mesh.

**Key takeaway:** Blue-green and canary are achievable natively via label selectors and replica counts, but traffic splitting is approximate without a service mesh.

</details>

📖 **Theory:** [blue-green-canary](./15_Deployment_Strategies/Theory.md#strategy-3-bluegreen-instant-cutover)


---

### Q39 · [Normal] · `sidecar-containers`

> **What is a sidecar container pattern? Give 3 real-world examples (logging, proxy, sync).**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A **sidecar container** runs alongside the main application container in the same pod, sharing the pod's network namespace and optionally its volumes. It augments or supports the main container without modifying it.

Sidecars are useful because they allow separation of concerns — the app container does one thing, the sidecar handles cross-cutting infrastructure concerns.

**3 real-world examples:**

1. **Logging (Fluentd/Filebeat sidecar):** The app writes logs to a shared volume (`/var/log/app`). A Fluentd sidecar reads from that volume and ships logs to Elasticsearch or a centralized logging backend. The app needs no logging SDK changes.

2. **Proxy (Envoy/Istio sidecar):** Istio injects an Envoy proxy sidecar automatically. All inbound and outbound traffic for the main container flows through Envoy, which handles mTLS, retries, circuit breaking, and telemetry without any app code changes.

3. **Config sync (git-sync sidecar):** A `git-sync` sidecar periodically pulls a Git repository into a shared volume. The main container (e.g., an nginx serving static files, or an Airflow DAG runner) reads from that volume and always has up-to-date files without needing a CI/CD redeploy.

**How to think through this:**
1. Sidecars share the pod's localhost network, so they can proxy traffic transparently.
2. Shared `emptyDir` volumes allow file-based communication between containers.
3. The pattern enables polyglot infrastructure — the app can be any language while the sidecar handles ops concerns.

**Key takeaway:** Sidecars extend a pod's capabilities without modifying the main application image.

</details>

📖 **Theory:** [sidecar-containers](./16_Sidecar_Containers/Theory.md#module-16-sidecar-containers)


---

### Q40 · [Normal] · `init-containers`

> **What are init containers? How do they differ from regular containers? When do they complete?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**Init containers** are specialized containers that run to completion before any regular (app) containers start in a pod. They run sequentially — each must succeed before the next starts. If any init container fails, kubelet restarts it (per restartPolicy) until it succeeds.

**Differences from regular containers:**

| Aspect | Init Container | Regular Container |
|---|---|---|
| Lifecycle | Runs once, to completion | Runs continuously |
| Order | Sequential, blocking | Start in parallel |
| Probes | No liveness/readiness probes | Support all probes |
| Purpose | Setup tasks | Application workload |

**They complete** when the process exits with code 0. Only after all init containers have exited 0 does kubelet start the regular containers.

**Common use cases:**
- Wait for a database to be reachable before the app starts.
- Pre-populate a shared volume (download config, run schema migrations).
- Register the pod with an external system before the app begins serving.
- Clone a Git repo into a volume before the app reads from it.

**How to think through this:**
1. Think of init containers as a pre-flight checklist — all checks must pass before takeoff.
2. They share volumes with regular containers, making them useful for setup tasks that produce artifacts.
3. Because they run to completion, retry logic is simpler than in long-running containers.

**Key takeaway:** Init containers run sequentially to completion before app containers start, ideal for dependency checks and setup tasks.

</details>

📖 **Theory:** [init-containers](./16_Sidecar_Containers/Theory.md#init-containers-vs-sidecar-containers)


---

### Q41 · [Normal] · `jobs-cronjobs`

> **What is a Kubernetes Job? What is a CronJob? What does `completions` and `parallelism` control?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A **Job** creates one or more pods and ensures a specified number of them successfully complete. Unlike a Deployment, a Job is for finite work — it runs until done, then stops.

A **CronJob** creates Jobs on a schedule, defined using standard cron syntax (e.g., `"0 2 * * *"` for 2am daily). Each scheduled run creates a new Job object.

**`completions`** — the total number of pods that must successfully complete for the Job to be considered done. Default is 1.

**`parallelism`** — the maximum number of pods that can run simultaneously at any time. Default is 1.

Examples:
- `completions: 10, parallelism: 2` → 10 pods must succeed, at most 2 run at once. Good for parallel batch processing.
- `completions: 1, parallelism: 1` → classic single-run job.
- `completions: 5, parallelism: 5` → all 5 run simultaneously.

**How to think through this:**
1. `completions` answers "how much total work?" and `parallelism` answers "how fast can we go?"
2. Jobs are useful for database migrations, report generation, data processing pipelines.
3. CronJobs should set `concurrencyPolicy` (Allow/Forbid/Replace) to control what happens when the previous run hasn't finished.

**Key takeaway:** `completions` sets total work units, `parallelism` sets concurrent workers — together they define a Job's throughput.

</details>

📖 **Theory:** [jobs-cronjobs](./17_Jobs_and_CronJobs/Theory.md#module-17-jobs-and-cronjobs)


---

### Q42 · [Normal] · `hpa`

> **What is a HorizontalPodAutoscaler? What metrics can it scale on? What is the minimum requirement for CPU-based HPA?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A **HorizontalPodAutoscaler (HPA)** automatically scales the number of pod replicas in a Deployment, ReplicaSet, or StatefulSet based on observed metrics. It runs a control loop (default every 15 seconds) comparing current metric values to target values.

**Metrics HPA can scale on:**
- **Resource metrics** — CPU and memory utilization (as a percentage of requests).
- **Custom metrics** — application-defined metrics exposed via the custom metrics API (e.g., requests per second, queue depth).
- **External metrics** — metrics from outside the cluster (e.g., cloud queue length, external API rate) via the external metrics API.

**Minimum requirement for CPU-based HPA:**
The pods being scaled **must have CPU resource requests defined**. HPA calculates CPU utilization as a percentage of the request. Without a CPU request, HPA cannot compute utilization and the metric will be unavailable.

Additionally, the **Metrics Server** must be installed in the cluster (it provides the resource metrics API).

**How to think through this:**
1. HPA reads metrics → computes desired replicas → patches the target's `spec.replicas`.
2. CPU request is the denominator: `utilization% = actual_cpu / requested_cpu * 100`.
3. No request = no denominator = HPA cannot function for CPU scaling.

**Key takeaway:** CPU-based HPA requires CPU requests on pods and Metrics Server installed in the cluster.

</details>

📖 **Theory:** [hpa](./18_HPA_VPA_Autoscaling/Theory.md#module-18-hpa-vpa-and-autoscaling)


---

### Q43 · [Normal] · `vpa`

> **What is a VerticalPodAutoscaler? What are its 3 modes: Off, Initial, Auto? When is VPA dangerous?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A **VerticalPodAutoscaler (VPA)** automatically adjusts CPU and memory requests (and optionally limits) for containers based on historical usage. Instead of adding more pods (HPA), it makes each pod bigger or smaller.

**3 modes:**

- **Off** — VPA only provides recommendations. It updates the VPA object's `status.recommendation` field but makes no changes to pods. Useful for capacity planning and understanding right-sizing.

- **Initial** — VPA applies recommendations only when new pods are created (e.g., after a rollout or node reschedule). It does not modify running pods. Safe for production use.

- **Auto** — VPA can evict and recreate running pods to apply updated resource recommendations. This is the "fully automated" mode.

**When is VPA dangerous:**
- **Auto mode** causes pod evictions, which can cause brief unavailability — dangerous for single-replica Deployments or StatefulSets with persistent connections.
- **VPA and HPA cannot both scale on CPU/memory simultaneously** for the same workload — they conflict. Use HPA for scaling and VPA for right-sizing only (Off or Initial mode).
- Evictions during business hours can trigger unintended restarts in production.

**How to think through this:**
1. VPA = right-size the pod; HPA = right-count the pods.
2. Start with Off mode to learn what VPA recommends before committing to Auto.
3. Use PodDisruptionBudgets alongside VPA Auto to limit simultaneous evictions.

**Key takeaway:** VPA Auto mode evicts pods to resize them — dangerous for single-replica workloads and incompatible with CPU/memory-based HPA on the same target.

</details>

📖 **Theory:** [vpa](./18_HPA_VPA_Autoscaling/Theory.md#module-18-hpa-vpa-and-autoscaling)


---

### Q44 · [Normal] · `resource-quotas`

> **What is a ResourceQuota? Write a ResourceQuota that limits a namespace to 4 CPUs and 8Gi memory total.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A **ResourceQuota** sets hard limits on the total amount of compute resources (CPU, memory) or object counts (pods, services, PVCs) that can be consumed within a namespace. It prevents a single team or application from monopolizing cluster resources.

When a ResourceQuota is active in a namespace, every pod must specify resource requests and limits — otherwise the API server will reject the pod (unless a LimitRange provides defaults).

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: namespace-quota
  namespace: my-team
spec:
  hard:
    requests.cpu: "4"
    requests.memory: 8Gi
    limits.cpu: "8"
    limits.memory: 16Gi
```

The `requests.*` fields cap the sum of all container resource requests in the namespace. The `limits.*` fields cap the sum of all container limits.

**How to think through this:**
1. ResourceQuota is enforced at admission time — new pods that would exceed the quota are rejected.
2. Existing pods are not evicted if quota is lowered after the fact.
3. Use `kubectl describe resourcequota -n my-team` to see used vs hard limits.

**Key takeaway:** ResourceQuota enforces aggregate namespace-level resource ceilings, requiring all pods to declare requests and limits.

</details>

📖 **Theory:** [resource-quotas](./19_Resource_Quotas_and_Limits/Theory.md#module-19-resource-quotas-and-limits)


---

### Q45 · [Normal] · `resource-limits`

> **What is the difference between resource requests and limits? What happens when a container exceeds its memory limit vs CPU limit?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**Requests** are what the container is guaranteed. The scheduler uses requests to decide which node has enough capacity to place the pod. A node is "full" when the sum of all pod requests equals its allocatable capacity.

**Limits** are the maximum the container is allowed to use. A container can use more than its request (up to its limit) if the node has idle capacity — this is called "burstable" behavior.

**Exceeding memory limit:**
Memory cannot be compressed. If a container exceeds its memory limit, the kernel OOM killer terminates the container process. Kubernetes then restarts the container (if restartPolicy allows). You will see `OOMKilled` as the termination reason.

**Exceeding CPU limit:**
CPU is compressible. If a container tries to use more CPU than its limit, the Linux CFS scheduler throttles it — it doesn't get more CPU time. The container continues running but runs slower. There is no restart, no kill — just reduced throughput.

**How to think through this:**
1. Memory: hard cap → OOMKill → restart. Watch for `CrashLoopBackOff` with `OOMKilled` exit code 137.
2. CPU: soft cap → throttle → performance degradation. Watch for high CPU throttling in metrics.
3. Setting CPU limits too low is a common production mistake that causes latency spikes without obvious error signals.

**Key takeaway:** Exceeding memory limit kills the container; exceeding CPU limit throttles it — one causes restarts, the other causes silent slowdowns.

</details>

📖 **Theory:** [resource-limits](./19_Resource_Quotas_and_Limits/Theory.md#module-19-resource-quotas-and-limits)


---

### Q46 · [Normal] · `network-policies`

> **What is a NetworkPolicy? What is the default behavior without any NetworkPolicy applied?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A **NetworkPolicy** is a Kubernetes resource that controls ingress (incoming) and egress (outgoing) traffic to pods using label selectors, namespace selectors, and IP blocks. It is enforced by the CNI plugin (Calico, Cilium, Weave, etc.) — not all CNI plugins support NetworkPolicy.

**Default behavior without any NetworkPolicy:**
All pods can communicate with all other pods in all namespaces, and all egress traffic is allowed. There is no isolation — the default is fully open. This is by design for simplicity but is a security concern in multi-tenant clusters.

**How NetworkPolicy works:**
- Once a NetworkPolicy selects a pod (via `podSelector`), that pod is isolated for the policy type (ingress, egress, or both).
- Only traffic explicitly allowed by a matching policy is permitted for that direction.
- Multiple NetworkPolicies are additive — if any policy allows traffic, it is allowed.

Example: a "deny all ingress" policy:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all-ingress
spec:
  podSelector: {}
  policyTypes:
  - Ingress
```

**How to think through this:**
1. No NetworkPolicy = no isolation = fully open east-west traffic.
2. Adding a NetworkPolicy that selects a pod makes that pod isolated — you must explicitly allow what you need.
3. Start with a default-deny-all and add allow rules — defense in depth.

**Key takeaway:** Without NetworkPolicy, all pods can reach all pods by default; NetworkPolicy shifts to an explicit-allow model once applied.

</details>

📖 **Theory:** [network-policies](./20_Network_Policies/Theory.md#module-20--network-policies)


---

### Q47 · [Normal] · `pod-security`

> **What is a Pod Security Standard (restricted, baseline, privileged)? What did PodSecurityPolicy do and why was it removed?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**Pod Security Standards (PSS)** are a set of predefined security policies enforced by the Pod Security Admission controller (built into Kubernetes since 1.25):

- **Privileged** — no restrictions. Pods can run as root, mount host paths, use host network. For trusted system components (e.g., CNI plugins).
- **Baseline** — minimal restrictions. Prevents known privilege escalations. Allows most workloads. Blocks host network, host PID, privileged containers, most host volume mounts.
- **Restricted** — heavily restricted, follows security best practices. Requires non-root user, drops all capabilities, requires `seccompProfile`, disallows privilege escalation. For security-sensitive workloads.

Standards are applied at the namespace level via labels:
```
pod-security.kubernetes.io/enforce: restricted
```

**PodSecurityPolicy (PSP):**
PSP was a cluster-wide admission controller that evaluated pod security settings against a policy resource. It was powerful but notoriously complex — difficult to configure correctly, required RBAC bindings to policies, and had confusing interaction with service accounts. It was deprecated in Kubernetes 1.21 and removed in 1.25, replaced by Pod Security Admission and PSS.

**How to think through this:**
1. PSS is simpler — three named profiles, applied per namespace via labels.
2. PSP required creating policy objects and binding them to service accounts — easy to misconfigure.
3. For more fine-grained policy (e.g., OPA Gatekeeper, Kyverno), use a policy engine on top of PSS.

**Key takeaway:** Pod Security Standards replaced PSP with three simple named profiles applied at namespace scope via admission labels.

</details>

📖 **Theory:** [pod-security](./23_Security/Theory.md#layer-1-pod-security-standards)


---

### Q48 · [Normal] · `custom-resources`

> **What is a CustomResourceDefinition (CRD)? What is the relationship between CRDs and Operators?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A **CustomResourceDefinition (CRD)** extends the Kubernetes API by registering a new resource type. Once a CRD is installed, users can create, read, update, and delete instances of that custom resource using `kubectl` and the API, just like built-in resources (Pods, Services, etc.).

CRDs define:
- The group, version, and kind (e.g., `apps.example.com/v1alpha1`, kind: `MyApp`)
- The schema (OpenAPI v3) for validation
- Whether the resource is namespaced or cluster-scoped

**Relationship with Operators:**
A CRD is just the schema — it defines what a custom resource looks like but does nothing with it. An **Operator** is a controller that watches instances of a custom resource and takes action to reconcile the cluster's actual state with the desired state declared in the custom resource.

The pattern:
- CRD = the vocabulary (new API type)
- Operator = the logic (reconciliation controller)
- Custom Resource instance = the intent (what the user wants)

Example: The Prometheus Operator defines a `ServiceMonitor` CRD. When you create a `ServiceMonitor` resource, the Operator reads it and configures Prometheus scrape targets automatically.

**How to think through this:**
1. CRD alone is inert — you can create instances but nothing happens.
2. Operators bring CRDs to life by watching and acting on them.
3. Together, they allow encoding operational knowledge into Kubernetes controllers.

**Key takeaway:** CRDs define custom API types; Operators are controllers that act on those types to automate complex operational tasks.

</details>

📖 **Theory:** [custom-resources](./12_Custom_Resources/Theory.md#module-12-custom-resources--extending-kubernetes)

---

### Q49 · [Normal] · `operators`

> **What is a Kubernetes Operator pattern? Name 3 popular operators and what they manage.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
The **Operator pattern** extends Kubernetes with application-specific operational knowledge encoded as a controller. An Operator watches custom resources (via CRDs) and reconciles the cluster state to match the declared desired state — automating tasks that would otherwise require human expertise (provisioning, scaling, backups, upgrades, failover).

The pattern follows the Kubernetes control loop: observe current state → compare to desired state → act to close the gap → repeat.

**3 popular Operators:**

1. **Prometheus Operator** — manages Prometheus, Alertmanager, and related monitoring infrastructure. Introduces CRDs like `ServiceMonitor`, `PrometheusRule`, and `Alertmanager`. Automatically configures Prometheus scrape targets from `ServiceMonitor` resources.

2. **cert-manager** — manages TLS certificates. Watches `Certificate` CRDs and automatically provisions, renews, and stores certificates from ACME (Let's Encrypt), Vault, or custom issuers. Injects certs into Secrets that pods consume.

3. **Strimzi (Kafka Operator)** — manages Apache Kafka clusters on Kubernetes. Handles provisioning brokers, topics (`KafkaTopic` CRD), users (`KafkaUser` CRD), rolling upgrades, and scaling without manual intervention.

**How to think through this:**
1. Operators encode "Day 2" operational runbooks into code.
2. The more stateful and complex the workload, the more valuable an Operator becomes.
3. OperatorHub.io catalogs hundreds of community and vendor Operators.

**Key takeaway:** Operators combine CRDs with reconciliation controllers to automate complex stateful workload management that generic Kubernetes controllers cannot handle.

</details>

📖 **Theory:** [operators](./12_Custom_Resources/Theory.md#writing-operators-frameworks-and-tools)


---

### Q50 · [Normal] · `monitoring-logging`

> **What is the standard Kubernetes monitoring stack? What is the difference between metrics (Prometheus) and logs (Loki/EFK)?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**Standard Kubernetes monitoring stack (kube-prometheus-stack):**
- **Prometheus** — scrapes and stores time-series metrics. Deployed via Prometheus Operator.
- **Grafana** — dashboards and visualization for Prometheus metrics.
- **Alertmanager** — routes and deduplicates alerts from Prometheus.
- **kube-state-metrics** — exposes Kubernetes object state as metrics (pod phase, deployment replicas, etc.).
- **node-exporter** — exposes host-level metrics (CPU, disk, memory) from each node.

**Metrics vs Logs:**

| Aspect | Metrics (Prometheus) | Logs (Loki / EFK) |
|---|---|---|
| Data type | Numeric time-series (counters, gauges, histograms) | Unstructured or structured text events |
| Storage | Compressed, efficient for aggregation | Larger, indexed by label or full-text |
| Query | PromQL — aggregate, rate, alert | LogQL / Kibana KQL — search, filter, tail |
| Use case | "What is my error rate over 5m?" | "What was the exact error message at 14:03?" |
| Cardinality | Must control label cardinality | High cardinality is acceptable |

**Loki** (Grafana stack) stores logs indexed only by labels — cheap storage, LogQL queries. **EFK** (Elasticsearch + Fluentd + Kibana) indexes full log content — powerful search but more expensive.

**How to think through this:**
1. Metrics tell you something is wrong (alert). Logs tell you why.
2. Prometheus is not for logs — it is for numbers over time.
3. A complete observability stack combines metrics, logs, and traces (OpenTelemetry → Jaeger/Tempo).

**Key takeaway:** Metrics track numeric signals over time for alerting; logs capture discrete events for diagnosis — both are necessary for production observability.

</details>

📖 **Theory:** [monitoring-logging](./22_Monitoring_and_Logging/Theory.md#module-22--monitoring-and-logging)


---

### Q51 · [Normal] · `service-mesh`

> **What is a service mesh? What does Istio add that Kubernetes Services don't provide natively?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A **service mesh** is an infrastructure layer that handles service-to-service communication within a cluster. It is typically implemented by injecting a sidecar proxy (Envoy) into every pod, creating a data plane. A control plane (Istiod) configures those proxies centrally.

**What Kubernetes Services provide natively:**
- DNS-based service discovery
- Basic L4 load balancing (round-robin across pod IPs)
- Port forwarding to healthy pods
- No encryption, no retries, no observability

**What Istio adds on top:**

| Capability | Kubernetes Native | Istio |
|---|---|---|
| mTLS between services | No | Yes, automatic |
| Traffic splitting (canary %) | Approximate (replica count) | Exact percentage-based |
| Retries and timeouts | No | Yes, per-route config |
| Circuit breaking | No | Yes |
| Distributed tracing | No | Yes (auto-inject trace headers) |
| Request-level metrics | No | Yes (golden signals per service) |
| Authorization policies | NetworkPolicy (IP/port) | JWT, service identity, header-based |

Istio's **VirtualService** and **DestinationRule** CRDs expose fine-grained traffic management. **PeerAuthentication** enforces mTLS cluster-wide.

**How to think through this:**
1. Services = "find the pod and forward the packet." Istio = "manage the entire conversation."
2. mTLS means even if someone gets inside the cluster, pod-to-pod traffic is encrypted and authenticated.
3. The trade-off is added complexity, latency (sidecar hop), and operational overhead.

**Key takeaway:** Istio adds mTLS, precise traffic control, retries, circuit breaking, and L7 observability that Kubernetes Services don't provide.

</details>

📖 **Theory:** [service-mesh](./24_Service_Mesh/Theory.md#module-24--service-mesh)


---

### Q52 · [Normal] · `helm-basics`

> **What is Helm? What is a chart, release, and values.yaml? What does `helm upgrade --install` do?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**Helm** is the package manager for Kubernetes. It templates Kubernetes manifests and manages their lifecycle as versioned packages.

**Chart** — a collection of files that describe a set of Kubernetes resources. It contains:
- `Chart.yaml` — metadata (name, version, description)
- `templates/` — Go-template YAML manifests
- `values.yaml` — default configuration values
- Optionally `charts/` — sub-chart dependencies

**Release** — a deployed instance of a chart in a cluster. You can install the same chart multiple times in different namespaces, each as a separate named release. Helm tracks release history in Kubernetes Secrets.

**values.yaml** — the default values file. Users override defaults with `--values custom.yaml` or `--set key=value` at install/upgrade time. Templates reference values via `{{ .Values.key }}`.

**`helm upgrade --install`** — a combined command: if the release does not exist, it installs it; if it exists, it upgrades it. Ideal for CI/CD pipelines where you don't know if it's a first deploy or an update. Equivalent to "upsert" for Helm releases.

**How to think through this:**
1. Chart = the package (code). Release = the running instance (process). Values = the config.
2. `helm install` fails if the release exists; `helm upgrade` fails if it doesn't. `upgrade --install` handles both.
3. `helm rollback <release> <revision>` redeploys a previous release version using Helm's stored history.

**Key takeaway:** Helm packages Kubernetes manifests as charts; a release is a running chart instance; `upgrade --install` is the idempotent deploy command.

</details>

📖 **Theory:** [helm-basics](./26_Helm_Charts/Theory.md#module-26--helm-charts)


---

### Q53 · [Normal] · `helm-charts`

> **What is the difference between `helm install` and `helm upgrade`? What does `helm rollback` do?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**`helm install <release-name> <chart>`** — creates a brand new release. Fails if a release with that name already exists in the namespace.

**`helm upgrade <release-name> <chart>`** — updates an existing release with new chart version, values, or both. Fails if the release does not exist (unless `--install` flag is added). Helm renders the new templates, applies them to the cluster, and stores the new state as the next revision number.

Key differences:

| Command | Release must exist? | Creates new? | Increments revision? |
|---|---|---|---|
| `helm install` | No — fails if exists | Yes | Yes (starts at 1) |
| `helm upgrade` | Yes — fails if not exists | No | Yes |
| `helm upgrade --install` | Either | Yes if needed | Yes |

**`helm rollback <release-name> <revision>`** — redeploys a previous revision of the release. Helm retrieves the stored manifest from that revision (kept in cluster Secrets) and re-applies it. The rollback itself is stored as a new revision — it does not delete history.

For example: if you're on revision 5 and run `helm rollback myapp 3`, you get the config from revision 3 applied, stored as revision 6.

**How to think through this:**
1. Helm stores every revision's rendered manifests as Secrets in the release namespace.
2. Rollback is deterministic — it's not re-running old values through templates, it's applying the stored rendered output.
3. Use `helm history <release>` to see all revisions and their status.

**Key takeaway:** `helm install` creates, `helm upgrade` updates, and `helm rollback` re-applies a specific historical revision as a new revision.

</details>

📖 **Theory:** [helm-charts](./26_Helm_Charts/Theory.md#module-26--helm-charts)


---

### Q54 · [Normal] · `gitops-cicd`

> **What is GitOps? How does ArgoCD implement it? What is the reconciliation loop?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**GitOps** is an operational model where the desired state of a system (infrastructure + applications) is declaratively stored in Git as the single source of truth. Changes to the system are made via Git commits — not direct `kubectl apply` or manual changes. Automation continuously ensures the cluster matches what Git declares.

**ArgoCD** is a GitOps continuous delivery tool for Kubernetes. It implements GitOps by:
1. Connecting to one or more Git repositories containing Kubernetes manifests (plain YAML, Helm charts, Kustomize).
2. Comparing the desired state in Git to the actual state in the cluster.
3. Syncing the cluster to match Git — either automatically or on manual trigger.
4. Surfacing diff, health status, and sync status in a UI and CLI.

**The reconciliation loop:**
ArgoCD runs a control loop (default every 3 minutes, or immediately on Git webhook):
1. Fetch the latest manifests from Git.
2. Render the final YAML (run Helm, Kustomize, etc.).
3. Compare rendered YAML to live cluster state using a 3-way diff.
4. If drifted and auto-sync is enabled, apply the diff to bring the cluster back in line.

Any manual change to the cluster (e.g., `kubectl scale`) is detected as drift and reverted on next sync.

**How to think through this:**
1. Git PR = change request. Merge = deployment trigger. Git history = deployment audit log.
2. ArgoCD eliminates "configuration drift" — the cluster always matches the Git state.
3. Secrets management (e.g., Sealed Secrets, External Secrets Operator) is the main complexity — you can't store plain secrets in Git.

**Key takeaway:** GitOps uses Git as the source of truth; ArgoCD's reconciliation loop continuously detects and corrects drift between Git state and cluster state.

</details>

📖 **Theory:** [gitops-cicd](./25_GitOps_and_CICD/Theory.md#module-25--gitops-and-cicd)


---

### Q55 · [Normal] · `advanced-scheduling`

> **What are nodeSelector, nodeAffinity, and podAffinity? How do they differ in expressiveness?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
All three influence which nodes pods are scheduled onto (or co-located with other pods), but with increasing expressiveness:

**nodeSelector** — the simplest form. A map of label key-value pairs. The pod is only scheduled on nodes that have all specified labels. No operators, no preferences — binary match only.

```yaml
nodeSelector:
  disktype: ssd
```

**nodeAffinity** — a more expressive node selection mechanism. Supports:
- `requiredDuringSchedulingIgnoredDuringExecution` — hard requirement (like nodeSelector but with operators).
- `preferredDuringSchedulingIgnoredDuringExecution` — soft preference with weights.
- Operators: `In`, `NotIn`, `Exists`, `DoesNotExist`, `Gt`, `Lt`.

```yaml
nodeAffinity:
  requiredDuringSchedulingIgnoredDuringExecution:
    nodeSelectorTerms:
    - matchExpressions:
      - key: topology.kubernetes.io/zone
        operator: In
        values: [us-east-1a, us-east-1b]
```

**podAffinity / podAntiAffinity** — schedule pods relative to other pods (not nodes). Uses `topologyKey` to define the scope (e.g., same node, same zone).
- podAffinity: place this pod near pods matching a selector.
- podAntiAffinity: spread this pod away from pods matching a selector. Common for HA — prevent all replicas from landing on the same node.

**How to think through this:**
1. nodeSelector = simple label match.
2. nodeAffinity = nodeSelector with expressions, operators, and weighted preferences.
3. podAffinity = "schedule near/away from these other pods" — topology-aware placement.

**Key takeaway:** nodeSelector is a simple label filter; nodeAffinity adds operators and preferences; podAffinity controls placement relative to other pods.

</details>

📖 **Theory:** [advanced-scheduling](./27_Advanced_Scheduling/Theory.md#module-27--advanced-scheduling)


---

### Q56 · [Normal] · `taints-tolerations`

> **What are taints and tolerations? Write a taint that prevents all pods from scheduling on a node except those with a specific toleration.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**Taints** are applied to nodes. They repel pods from being scheduled onto that node unless the pod has a matching toleration. Taints are the inverse of nodeAffinity — instead of pods selecting nodes, nodes reject pods.

A taint has three parts: `key=value:effect`

**Effects:**
- `NoSchedule` — new pods without a matching toleration will not be scheduled on the node. Existing pods are unaffected.
- `PreferNoSchedule` — the scheduler tries to avoid the node but may place pods there if no other option exists.
- `NoExecute` — new pods cannot be scheduled AND existing pods without a matching toleration are evicted.

**Toleration** — added to a pod spec, allows the pod to be scheduled onto a tainted node. A toleration does not guarantee the pod goes there — it only removes the repulsion.

**Taint a node to repel all pods except those with a matching toleration:**

```bash
kubectl taint nodes gpu-node-1 dedicated=gpu:NoSchedule
```

Pod with matching toleration:

```yaml
tolerations:
- key: "dedicated"
  operator: "Equal"
  value: "gpu"
  effect: "NoSchedule"
```

Pods without this toleration cannot be scheduled on `gpu-node-1`. Only GPU workloads with this toleration can land there.

**How to think through this:**
1. Taints = "nodes push pods away." Tolerations = "pods opt in to tainted nodes."
2. For dedicated node pools (GPU, high-memory), combine taints + nodeAffinity: taint ensures only opted-in pods land there, nodeAffinity ensures opted-in pods actually go there.
3. `NoExecute` with `tolerationSeconds` is used to evict pods from unhealthy nodes gracefully.

**Key takeaway:** Taints repel pods from nodes; tolerations allow specific pods to bypass the repulsion — used together to create dedicated node pools.

</details>

📖 **Theory:** [taints-tolerations](./27_Advanced_Scheduling/Theory.md#taints-and-tolerations-dedicated-nodes)


---

### Q57 · [Normal] · `node-affinity`

> **What is the difference between requiredDuringSchedulingIgnoredDuringExecution and preferredDuringSchedulingIgnoredDuringExecution?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Both are node affinity rules that apply at scheduling time. The "IgnoredDuringExecution" part means neither rule evicts a pod if node labels change after the pod is already running.

**requiredDuringSchedulingIgnoredDuringExecution:**
A hard requirement. The pod will only be scheduled on nodes that satisfy all the specified node selector terms. If no node matches, the pod remains Pending — it will never be placed on a non-matching node.

Use when: the pod absolutely cannot run on certain nodes (e.g., must be on a node with a GPU, must be in a specific zone for data locality).

**preferredDuringSchedulingIgnoredDuringExecution:**
A soft preference with a weight (1–100). The scheduler scores matching nodes higher, but if no matching node is available, the pod is still scheduled on a non-matching node. It will not stay Pending.

Use when: you want to influence placement without blocking it. For example, prefer pods in zone us-east-1a for lower latency but allow placement in other zones if 1a is full.

```yaml
preferredDuringSchedulingIgnoredDuringExecution:
- weight: 80
  preference:
    matchExpressions:
    - key: topology.kubernetes.io/zone
      operator: In
      values: [us-east-1a]
```

**How to think through this:**
1. Required = hard gate. Preferred = scoring hint.
2. Required risks pods stuck in Pending if cluster capacity is limited.
3. Combine both: required for critical constraints, preferred for optimization.

**Key takeaway:** Required affinity is a hard scheduling gate that causes Pending if unmet; preferred affinity is a weighted hint that the scheduler uses but ignores when necessary.

</details>

📖 **Theory:** [node-affinity](./27_Advanced_Scheduling/Theory.md#nodeaffinity-flexible-node-matching)


---

### Q58 · [Normal] · `cluster-management`

> **What is node drain vs cordon? When do you use each? What does `kubectl drain --ignore-daemonsets` do?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**Cordon** marks a node as unschedulable. New pods will not be scheduled on it. Existing pods continue running undisturbed. The node is still in the cluster and part of the API — just not accepting new workloads.

```bash
kubectl cordon node-1
```

Use cordon when: you want to stop new pods from landing on a node while you investigate it, but you don't want to disrupt running workloads yet.

**Drain** cordons the node AND gracefully evicts all running pods. Pods are terminated and rescheduled on other nodes. The node is left in a cordoned state after draining completes.

```bash
kubectl drain node-1 --ignore-daemonsets --delete-emptydir-data
```

Use drain when: you are about to do maintenance (kernel upgrade, node replacement, decommissioning).

**`--ignore-daemonsets`:** DaemonSet pods are not evicted by drain — they are tied to the node by design (e.g., node-exporter, kube-proxy, Fluentd). Without this flag, `kubectl drain` fails if DaemonSet pods exist on the node. The flag tells drain to proceed and simply skip DaemonSet pods.

**`--delete-emptydir-data`:** Needed if any pod uses an `emptyDir` volume (temporary local storage). Without it, drain refuses to evict those pods because eviction would delete the data. This flag acknowledges data loss is acceptable.

**How to think through this:**
1. Cordon = stop new arrivals. Drain = cordon + evict existing.
2. After drain, `kubectl uncordon node-1` makes the node schedulable again.
3. PodDisruptionBudgets are respected during drain — it will wait if evicting a pod would violate the PDB.

**Key takeaway:** Cordon blocks new scheduling; drain evicts existing pods too — use cordon for investigation, drain for maintenance.

</details>

📖 **Theory:** [cluster-management](./28_Cluster_Management/Theory.md#module-28--cluster-management)


---

### Q59 · [Normal] · `backup-dr`

> **What is Velero? What does it back up? What is the RPO for a Kubernetes cluster using Velero with hourly snapshots?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**Velero** is an open-source tool for backing up and restoring Kubernetes cluster resources and persistent volumes. It runs as a Deployment in the cluster and integrates with cloud storage (S3, GCS, Azure Blob) for backup storage and cloud snapshot APIs for volume snapshots.

**What Velero backs up:**
- Kubernetes API objects — all or filtered by namespace, label, or resource type (Deployments, Services, ConfigMaps, Secrets, CRDs, etc.). Stored as JSON in object storage.
- Persistent Volume data — via cloud provider volume snapshots (e.g., EBS snapshots on AWS) or via Restic/Kopia for file-level backups of PV contents.

**What Velero does NOT back up by default:**
- etcd directly (it works via the API server, not etcd).
- Node-level configuration.
- In-memory state or application-level data not in PVs.

**RPO with hourly snapshots:**
**RPO (Recovery Point Objective)** is the maximum data loss window. With hourly Velero schedules, the RPO is up to 1 hour — in the worst case, you lose up to 59 minutes of changes made since the last backup completed.

If the backup takes 5 minutes to run, the effective RPO window is up to 65 minutes between the end of one backup and the start of the next.

**How to think through this:**
1. RPO = "how much data can we afford to lose?" Hourly schedule = up to 1 hour of data loss.
2. For lower RPO, increase backup frequency or use application-level replication (database streaming replication).
3. Velero restores are namespace-scoped — useful for accidental deletion or migration, not just full DR.

**Key takeaway:** Velero backs up Kubernetes objects and PV snapshots to object storage; hourly schedules give an RPO of up to 1 hour.

</details>

📖 **Theory:** [backup-dr](./29_Backup_and_DR/Theory.md#module-29--backup-and-disaster-recovery)


---

### Q60 · [Normal] · `cost-optimization`

> **What are 5 Kubernetes cost optimization techniques? (Resource requests, VPA, Karpenter, spot nodes, namespace quotas)**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Kubernetes cost optimization targets two areas: right-sizing workloads and right-sizing infrastructure.

**1. Right-size resource requests:**
Oversized requests waste node capacity — a pod requesting 4 CPUs on a 4-CPU node blocks that node for other pods even if the app only uses 0.5 CPUs. Use actual usage metrics (from Prometheus or cloud monitoring) to set requests close to p95 usage. This is the highest-leverage single change.

**2. VPA for automatic right-sizing:**
Deploy VPA in `Off` or `Initial` mode to get recommendations without disrupting running pods. Use recommendations to update request values in Helm values or manifests. VPA automates the discovery work of finding the right request values.

**3. Karpenter for node right-sizing:**
Karpenter selects the smallest node type that fits pending pods, rather than always launching the same instance type. It bins packs pods efficiently and consolidates underutilized nodes. Cluster Autoscaler only scales existing node groups; Karpenter dynamically picks the optimal instance.

**4. Spot / preemptible nodes:**
Run stateless, fault-tolerant workloads (web services, batch jobs, workers) on spot instances (AWS) or preemptible VMs (GCP). Spot instances are 60–90% cheaper than on-demand. Use taints/tolerations to direct spot-tolerant workloads to spot node pools and keep critical stateful workloads on on-demand nodes.

**5. Namespace ResourceQuotas:**
Prevent individual teams from over-provisioning by capping namespace-level CPU and memory requests. Without quotas, developers naturally over-request "just to be safe," leading to cluster-wide waste. Quotas combined with a LimitRange (which sets defaults) ensure every pod has sensible requests.

**How to think through this:**
1. Start with requests audit — it's free and often reveals 30–50% waste immediately.
2. Spot nodes are the most impactful cost reduction for batch and stateless workloads.
3. Karpenter + spot + right-sized requests is the standard "mature" optimization stack on AWS.

**Key takeaway:** Right-size requests first (highest leverage), then automate with VPA, use Karpenter for intelligent node selection, run non-critical workloads on spot, and enforce quotas to prevent waste.

</details>

📖 **Theory:** [cost-optimization](./30_Cost_Optimization/Theory.md#module-30--cost-optimization)


---

### Q61 · [Normal] · `gateway-api`

> **What is the Kubernetes Gateway API? How does it improve on Ingress? What are Gateway, HTTPRoute, and GRPCRoute?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
The **Kubernetes Gateway API** is a next-generation API for managing ingress and routing traffic into and within a Kubernetes cluster. It was designed to replace the limitations of the Ingress resource and is now GA (as of Kubernetes 1.28 for stable resources).

**How it improves on Ingress:**

| Aspect | Ingress | Gateway API |
|---|---|---|
| Protocol support | HTTP/HTTPS only | HTTP, HTTPS, gRPC, TCP, TLS |
| Traffic splitting | Non-standard (annotations) | Native, precise weight-based |
| Role separation | Single resource, no RBAC separation | Separated: infra team manages Gateway, app team manages Routes |
| Extensibility | Vendor-specific annotations | First-class extension points |
| Backend flexibility | Services only | Services, custom backends |

**Core resources:**

- **Gateway** — represents a load balancer or proxy. Defines listeners (port, protocol, TLS). Managed by the cluster infrastructure team. References a `GatewayClass` (the controller implementation, e.g., Envoy Gateway, nginx, Istio).

- **HTTPRoute** — attaches to a Gateway and defines HTTP routing rules: path matching, header matching, traffic splitting across backends, redirects, rewrites. Managed by the application team.

- **GRPCRoute** — like HTTPRoute but for gRPC traffic. Routes based on gRPC service and method names.

**How to think through this:**
1. Gateway API separates "who configures the load balancer" (infra) from "who configures the routes" (app teams) — a key enterprise need.
2. Ingress required annotations for anything beyond basic path routing; Gateway API makes all of that first-class.
3. Migration path: Gateway API is the long-term replacement for Ingress. Ingress is not being removed but will not gain new features.

**Key takeaway:** Gateway API replaces Ingress with first-class multi-protocol routing, role-based separation of concerns, and native traffic splitting via HTTPRoute and GRPCRoute.

</details>

📖 **Theory:** [gateway-api](./31_Gateway_API/Theory.md#module-31-kubernetes-gateway-api)


---

### Q62 · [Normal] · `keda`

> **What is KEDA? What problem does it solve that HPA cannot? Give an example: scaling a Deployment based on SQS queue depth.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**KEDA (Kubernetes Event-Driven Autoscaling)** is a Kubernetes autoscaler that scales workloads based on external event sources and metrics beyond what the standard HPA supports. It acts as an external metrics provider and can scale Deployments, StatefulSets, and Jobs — including scaling to zero.

**Problem HPA cannot solve:**
Standard HPA scales on CPU, memory, and custom/external metrics — but wiring up external metrics (like SQS queue depth, Kafka consumer lag, Redis list length) requires implementing a custom metrics adapter. KEDA ships with 60+ built-in **scalers** (event source connectors) that expose external metrics to HPA automatically. KEDA also enables **scale-to-zero**, which HPA cannot do (HPA minimum is 1 replica).

**Example: scale on SQS queue depth:**

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: sqs-consumer-scaler
spec:
  scaleTargetRef:
    name: sqs-consumer-deployment
  minReplicaCount: 0
  maxReplicaCount: 20
  triggers:
  - type: aws-sqs-queue
    metadata:
      queueURL: https://sqs.us-east-1.amazonaws.com/123456789/my-queue
      queueLength: "10"
      awsRegion: us-east-1
```

This scales the `sqs-consumer-deployment` from 0 to 20 replicas. When the queue has 100 messages and `queueLength` target is 10, KEDA drives HPA to maintain ~10 replicas (100/10 = 10 needed). When the queue is empty, it scales to zero.

**How to think through this:**
1. KEDA creates a HorizontalPodAutoscaler under the hood — it extends HPA rather than replacing it.
2. Scale-to-zero is the killer feature for batch/event-driven workloads — no idle cost.
3. KEDA scalers cover Kafka, RabbitMQ, Redis, Prometheus, Azure Service Bus, Google PubSub, and more.

**Key takeaway:** KEDA extends HPA with 60+ event source scalers and adds scale-to-zero, making it ideal for event-driven and queue-processing workloads.

</details>

📖 **Theory:** [keda](./32_KEDA_Event_Driven_Autoscaling/Theory.md#module-32-keda--kubernetes-event-driven-autoscaling)


---

### Q63 · [Normal] · `karpenter`

> **What is Karpenter? How does it differ from the Cluster Autoscaler? What is a NodePool?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**Karpenter** is an open-source Kubernetes node autoscaler that automatically provisions the right nodes for pending pods. It was created by AWS and is now a CNCF project. It replaces the Cluster Autoscaler on AWS EKS and is also available on other clouds.

**Karpenter vs Cluster Autoscaler:**

| Aspect | Cluster Autoscaler | Karpenter |
|---|---|---|
| Node provisioning | Scales pre-defined node groups (ASGs) | Directly launches EC2 instances — no node groups needed |
| Instance selection | Fixed instance type per node group | Dynamically selects cheapest/best-fit instance from a broad list |
| Bin packing | Limited — adds nodes based on group config | Efficient bin packing — picks smallest node that fits pending pods |
| Consolidation | Basic scale-down by draining underutilized nodes | Active consolidation — replaces multiple underutilized nodes with one smaller node |
| Speed | Slower (ASG launch + scale-in delays) | Faster provisioning, direct API calls |
| Spot handling | Requires separate spot node groups | Native spot instance support with fallback |

**NodePool** — the primary Karpenter CRD. It defines constraints for nodes that Karpenter can provision: allowed instance families, architectures (amd64/arm64), operating systems, availability zones, capacity types (on-demand/spot), and taints/labels to apply to provisioned nodes.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values: ["spot", "on-demand"]
      - key: kubernetes.io/arch
        operator: In
        values: ["amd64"]
  limits:
    cpu: "1000"
```

**How to think through this:**
1. Cluster Autoscaler is constrained by node group definitions. Karpenter has a blank canvas.
2. Karpenter's consolidation loop actively replaces underutilized nodes, reducing waste continuously.
3. NodePool replaces the old `Provisioner` CRD in Karpenter v1.

**Key takeaway:** Karpenter dynamically selects and provisions the optimal node type per workload, eliminating the need for pre-configured node groups and enabling aggressive cost optimization.

</details>

📖 **Theory:** [karpenter](./33_Karpenter_Node_Autoprovisioning/Theory.md#module-33-karpenter--next-generation-node-autoprovisioning)


---

### Q64 · [Normal] · `ebpf-cilium`

> **What is eBPF? How does Cilium use it? What advantage does Cilium have over traditional kube-proxy?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**eBPF (extended Berkeley Packet Filter)** is a Linux kernel technology that allows sandboxed programs to run inside the kernel without modifying kernel source code or loading kernel modules. eBPF programs are event-driven, JIT-compiled, and verified for safety. They can hook into kernel events: network packets, system calls, function calls, tracepoints.

**How Cilium uses eBPF:**
Cilium is a Kubernetes CNI plugin that uses eBPF for all networking, security, and observability:
- **Networking** — instead of iptables rules, Cilium attaches eBPF programs to network interfaces to handle packet forwarding, NAT, and load balancing at the kernel level.
- **Security** — enforces NetworkPolicy using eBPF maps (hash tables in kernel space) — O(1) lookup vs iptables O(n) chain traversal.
- **Observability** — Hubble (Cilium's observability layer) uses eBPF to capture L3/L4/L7 flow data without any sidecar or tap — zero-overhead flow visibility.

**Advantages over traditional kube-proxy:**

| Aspect | kube-proxy (iptables) | Cilium (eBPF) |
|---|---|---|
| Rule lookup | O(n) — linear chain traversal | O(1) — hash map lookup |
| Scale | Degrades with 10k+ services | Scales to 100k+ services |
| Sidecar required for L7 | Yes (Istio Envoy) | No — eBPF handles L7 directly |
| Connection tracking | iptables conntrack | eBPF socket-level (lower overhead) |
| kube-proxy replacement | N/A | Yes — Cilium can run without kube-proxy |

Cilium in kube-proxy replacement mode (`kubeProxyReplacement: true`) handles Service load balancing entirely in eBPF, bypassing iptables completely.

**How to think through this:**
1. iptables was designed for firewalls, not cloud-scale service meshes. eBPF was designed for programmable kernel networking.
2. eBPF programs are attached per-socket and per-interface, making them far more efficient than per-packet iptables traversal.
3. Cilium + eBPF is the direction for Kubernetes networking at scale — major cloud providers (AWS, GKE, Azure) now offer it.

**Key takeaway:** Cilium replaces iptables-based kube-proxy with eBPF kernel programs, giving O(1) service lookup, no sidecars for L7 policy, and zero-overhead observability.

</details>

📖 **Theory:** [ebpf-cilium](./34_eBPF_and_Cilium/Theory.md#module-34-ebpf-and-cilium)


---

### Q65 · [Normal] · `ephemeral-containers`

> **What are ephemeral containers? How do you use `kubectl debug` to attach one to a running pod?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**Ephemeral containers** are a special type of container that can be added to an already-running pod for debugging purposes. Unlike regular containers, they:
- Cannot be defined in the pod spec at creation time — they are added to running pods via the API.
- Have no resource guarantees or limits enforcement in the same way.
- Cannot be restarted once exited.
- Are not included in the pod's restart count.
- Are specifically designed for interactive debugging and will never be restarted.

They solve the problem of debugging minimal production images (distroless, scratch-based) that have no shell, no debugging tools, and no way to `kubectl exec` into them usefully.

**Using `kubectl debug`:**

Attach an ephemeral container to a running pod:
```bash
kubectl debug -it my-pod --image=busybox --target=main-container
```

- `--image` specifies the debug image (use `busybox`, `nicolaka/netshoot`, `ubuntu`, etc.).
- `--target` shares the process namespace of the specified container, so you can see its processes with `ps`.
- `-it` opens an interactive terminal.

Copy a pod with a new debug image (useful when the pod is crashed):
```bash
kubectl debug my-pod -it --image=busybox --copy-to=my-pod-debug
```

Debug a node by launching a privileged pod on it:
```bash
kubectl debug node/node-1 -it --image=busybox
```

**How to think through this:**
1. Distroless images have no shell — `kubectl exec` gives "no such file or directory." Ephemeral containers solve this.
2. `--target` process namespace sharing is the key — you can `ls /proc/<pid>/root` to inspect the main container's filesystem.
3. Ephemeral containers are not visible in `kubectl get pods -o wide` but are visible in `kubectl describe pod`.

**Key takeaway:** Ephemeral containers let you attach a debug-ready container to a running pod without modifying the original image — essential for debugging minimal production containers.

</details>

📖 **Theory:** [ephemeral-containers](./35_Ephemeral_Containers_and_Debug/Theory.md#module-35--ephemeral-containers-and-debugging)


---

### Q66 · [Normal] · `service-accounts`

> **What is the difference between a ServiceAccount, a Role, and a RoleBinding? Write the 3 YAML objects needed to give a pod read-only access to ConfigMaps.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**ServiceAccount** — an identity for processes running in a pod. When a pod authenticates to the Kubernetes API server, it uses its ServiceAccount's token. Every namespace has a `default` ServiceAccount, but best practice is to create dedicated ones per workload. A ServiceAccount by itself has no permissions.

**Role** — defines a set of permissions (rules) within a single namespace. Rules specify `apiGroups`, `resources`, and `verbs` (get, list, watch, create, update, patch, delete). A Role grants no access until it is bound to a subject.

**RoleBinding** — binds a Role to a subject (ServiceAccount, User, or Group) within a namespace. This is what actually grants the permissions defined in the Role to the specified identity.

The three objects needed for pod read-only access to ConfigMaps:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: configmap-reader
  namespace: my-namespace
```

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: configmap-read-role
  namespace: my-namespace
rules:
- apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["get", "list", "watch"]
```

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: configmap-read-binding
  namespace: my-namespace
subjects:
- kind: ServiceAccount
  name: configmap-reader
  namespace: my-namespace
roleRef:
  kind: Role
  name: configmap-read-role
  apiGroup: rbac.authorization.k8s.io
```

The pod spec must reference the ServiceAccount:
```yaml
spec:
  serviceAccountName: configmap-reader
```

**How to think through this:**
1. ServiceAccount = who. Role = what. RoleBinding = link who to what.
2. Use `ClusterRole` and `ClusterRoleBinding` for cluster-scoped resources or cross-namespace access.
3. `kubectl auth can-i list configmaps --as=system:serviceaccount:my-namespace:configmap-reader` verifies the binding.

**Key takeaway:** ServiceAccount is the pod identity, Role defines permitted actions, RoleBinding connects them — all three are required to grant namespace-scoped API access.

</details>

📖 **Theory:** [service-accounts](./21_Service_Accounts/Theory.md#module-21--service-accounts)


---

## 🟠 Tier 3 — Advanced

### Q67 · [Thinking] · `keda`

> **Walk through a complete KEDA ScaledObject configuration that scales a Deployment from 0 to 20 replicas based on an SQS queue depth metric.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
KEDA (Kubernetes Event-Driven Autoscaling) extends the HPA by adding external event source triggers. It introduces two CRDs: `ScaledObject` (for Deployments/StatefulSets) and `ScaledJob` (for batch workloads). The key capability over native HPA is scale-to-zero and scale-from-zero.

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: sqs-scaledobject
  namespace: workers
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sqs-consumer
  minReplicaCount: 0        # scale to zero when queue empty
  maxReplicaCount: 20
  pollingInterval: 30       # seconds between metric checks
  cooldownPeriod: 300       # seconds to wait before scaling to zero
  triggers:
    - type: aws-sqs-queue
      authenticationRef:
        name: keda-aws-credentials
      metadata:
        queueURL: https://sqs.us-east-1.amazonaws.com/123456789/my-queue
        queueLength: "10"   # target: 1 pod per 10 messages
        awsRegion: us-east-1
---
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: keda-aws-credentials
  namespace: workers
spec:
  podIdentity:
    provider: aws  # uses IRSA — no static keys
```

**How to think through this:**
1. `scaleTargetRef` points to the Deployment KEDA controls. KEDA creates and manages an HPA object behind the scenes — you don't create the HPA directly.
2. `minReplicaCount: 0` enables scale-to-zero. The `cooldownPeriod` prevents flapping — KEDA waits 300 seconds of empty queue before dropping to zero.
3. `queueLength: "10"` is the target messages-per-replica. With 100 messages in the queue, KEDA targets 10 replicas. With 200 messages, it targets 20 (capped at maxReplicaCount).
4. Authentication via `TriggerAuthentication` with IRSA (IAM Roles for Service Accounts) is the production pattern — avoids embedding AWS keys in the ScaledObject.
5. KEDA's operator polls SQS every `pollingInterval` seconds, calculates desired replicas, and patches the HPA's `desiredReplicas`.

**Key takeaway:** KEDA wraps the HPA with event-source awareness — the ScaledObject defines the trigger and bounds, KEDA handles metric translation and scale-to-zero logic.

</details>

📖 **Theory:** [keda](./32_KEDA_Event_Driven_Autoscaling/Theory.md#module-32-keda--kubernetes-event-driven-autoscaling)


---

### Q68 · [Thinking] · `karpenter`

> **How does Karpenter's bin-packing work? What is a NodeClaim? How does it handle spot instance interruptions?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Karpenter is a just-in-time node provisioner that replaces the Cluster Autoscaler. Instead of scaling pre-defined node groups, Karpenter watches unschedulable pods and provisions exactly the right node shape for them.

**Bin-packing:**
Karpenter aggregates all pending pods, sums their resource requests, and selects the smallest instance type that fits all pending pods — not one pod at a time. It evaluates multiple instance families (e.g., m5.xlarge vs c5.xlarge) and picks the most cost-efficient. This is fundamentally different from Cluster Autoscaler, which scales existing node groups by +1.

**NodeClaim:**
A `NodeClaim` is the internal CRD Karpenter creates to represent a node it intends to provision. The lifecycle is:
1. Karpenter creates a `NodeClaim` with the required instance type/capacity type.
2. The cloud provider (AWS EC2) receives the launch request.
3. When the node registers with the cluster, the `NodeClaim` is bound to the `Node` object.
4. On termination, Karpenter deletes the `NodeClaim` and the node drains.

**Spot interruption handling:**
Karpenter listens to AWS EC2 interruption notices via EventBridge (2-minute warning for spot). On receiving an interruption notice:
1. Karpenter cordons the node immediately.
2. Begins provisioning a replacement node proactively.
3. Drains workloads from the interrupted node before the 2-minute window expires.
4. The `NodePool` spec defines `disruption.consolidationPolicy` and spot fallback to on-demand.

**How to think through this:**
1. Karpenter's unit of work is a batch of unschedulable pods, not individual nodes — this is the bin-packing advantage.
2. NodeClaim is the reconcilable object — Karpenter's controller ensures actual nodes match declared NodeClaims.
3. Spot handling relies on proactive replacement, not reactive rescue — Karpenter starts a new node before the old one dies.

**Key takeaway:** Karpenter provisions right-sized nodes on demand using bin-packing across multiple instance types, with NodeClaims as the reconcilable unit and proactive replacement for spot interruptions.

</details>

📖 **Theory:** [karpenter](./33_Karpenter_Node_Autoprovisioning/Theory.md#module-33-karpenter--next-generation-node-autoprovisioning)


---

### Q69 · [Thinking] · `ebpf-cilium`

> **What is the eBPF data path? How does Cilium bypass iptables? What is Hubble in the Cilium ecosystem?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**eBPF data path:**
eBPF (extended Berkeley Packet Filter) lets you run sandboxed programs in the Linux kernel without changing kernel source or loading kernel modules. Cilium attaches eBPF programs to network hooks (TC ingress/egress, XDP) on each network interface. When a packet arrives, the kernel executes the eBPF program directly — no userspace round-trip, no iptables chain traversal.

**How Cilium bypasses iptables:**
Traditional kube-proxy uses iptables NAT rules for Service load balancing. Every new connection traverses an O(n) iptables chain where n = number of rules. At 10,000 services this becomes a serious latency bottleneck.

Cilium replaces kube-proxy entirely:
- Service VIPs are resolved in eBPF maps (hash lookups, O(1)) attached at the socket layer (BPF sockops/sk_msg).
- Packets are redirected directly between pod network namespaces using BPF redirect — they never traverse the full network stack.
- Network policies are enforced in eBPF programs at the TC hook, not via iptables FORWARD rules.

Result: no iptables, no conntrack for pod-to-pod traffic, ~3x lower latency at scale.

**Hubble:**
Hubble is Cilium's observability layer. It is built directly on the eBPF data path — since all packets pass through eBPF programs, Hubble can record flow metadata (src/dst IP, port, protocol, DNS query, HTTP method, drop reason) with zero additional overhead. Components:
- `hubble-relay`: aggregates flow data from all nodes.
- `hubble-ui`: service map and flow inspector in the browser.
- `hubble-cli`: `hubble observe` for real-time flow queries.

**How to think through this:**
1. eBPF programs execute in kernel context at attach points — think of them as programmable fast paths.
2. iptables bypass works because eBPF maps replace rule chains with hash lookups, and BPF redirect skips the routing stack.
3. Hubble is "free" observability — the eBPF programs were already running, Hubble just taps their output.

**Key takeaway:** Cilium moves packet processing into eBPF programs attached to kernel hooks, achieving O(1) service lookup and zero-overhead observability via Hubble by instrumenting the same code path.

</details>

📖 **Theory:** [ebpf-cilium](./34_eBPF_and_Cilium/Theory.md#module-34-ebpf-and-cilium)


---

### Q70 · [Thinking] · `gateway-api-advanced`

> **What is the role separation in Gateway API: infrastructure provider, cluster operator, application developer? How does this differ from Ingress?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Gateway API introduces a three-tier ownership model that maps to real organizational boundaries.

**The three roles:**

| Role | Object | Owns |
|---|---|---|
| Infrastructure Provider | `GatewayClass` | Defines which controller (e.g., AWS ALB, Envoy) handles a class of Gateways |
| Cluster Operator | `Gateway` | Provisions a specific load balancer: ports, TLS termination, allowed namespaces |
| Application Developer | `HTTPRoute` / `GRPCRoute` | Defines routing rules: paths, headers, backends, traffic splitting |

**How this plays out in practice:**
- The infra team installs the Gateway controller and creates one `GatewayClass` named `internal-alb`.
- The platform team creates a `Gateway` in `namespace: infra` that listens on port 443, terminates TLS with a wildcard cert, and allows `HTTPRoute` objects from any namespace.
- App teams create `HTTPRoute` objects in their own namespaces that attach to the shared `Gateway` — they never touch TLS or load balancer config.

**Ingress comparison:**
Ingress collapses all three roles into a single object. The `Ingress` resource mixes infra config (annotations for ALB settings), cluster-level config (TLS cert), and app routing (path rules) — all owned by whoever deploys the app. This leads to annotation sprawl and inconsistent behavior across controllers. Gateway API enforces separation at the API level with explicit `parentRef` attachment and namespace-scoped `ReferenceGrant` for cross-namespace trust.

**How to think through this:**
1. Ask who should own each decision: load balancer type (infra), TLS (platform), routing (app).
2. Ingress has no mechanism to prevent app developers from setting dangerous controller annotations.
3. `ReferenceGrant` is the explicit trust delegation — a `Gateway` in namespace `infra` must grant permission before an `HTTPRoute` in `team-a` can attach.

**Key takeaway:** Gateway API enforces organizational role separation across GatewayClass, Gateway, and HTTPRoute objects, replacing Ingress's single-object model that mixed infrastructure and application concerns.

</details>

📖 **Theory:** [gateway-api-advanced](./31_Gateway_API/Theory.md#module-31-kubernetes-gateway-api)


---

### Q71 · [Thinking] · `service-mesh-advanced`

> **What does Istio's sidecar injection do? How does mTLS work between services? What is the overhead?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**Sidecar injection:**
When a pod is scheduled in a namespace labeled `istio-injection: enabled`, Istio's mutating webhook fires before the pod is created. It injects two containers:
1. `istio-init` (initContainer): runs `iptables` rules that redirect all inbound (port 15006) and outbound (port 15001) TCP traffic to the Envoy proxy. The application container never knows about the proxy.
2. `istio-proxy` (sidecar): the Envoy proxy that handles all traffic. It receives xDS config (routes, clusters, listeners) from Istiod (the control plane).

**mTLS between services:**
Istio implements mTLS transparently via the SPIFFE/X.509 identity model:
1. Istiod issues a short-lived X.509 certificate to each proxy, encoding the pod's service account as a SPIFFE URI (e.g., `spiffe://cluster.local/ns/default/sa/my-service`).
2. When Service A calls Service B, A's Envoy initiates a TLS handshake with B's Envoy — both present and verify certificates.
3. The application code makes a plain HTTP call on localhost; the sidecar handles TLS upgrade transparently.
4. `PeerAuthentication` policy controls whether mTLS is `STRICT` (required), `PERMISSIVE` (allowed but optional), or disabled.

**Overhead:**
- CPU: ~0.5 vCPU per 1000 req/s per proxy (Envoy is efficient but not free).
- Latency: 1–3ms added per hop for TLS handshake amortized over keep-alive connections; typically <1ms per request in steady state.
- Memory: ~50–100MB per sidecar container.
- The init container requires `NET_ADMIN` capability to set iptables rules — a security consideration in locked-down environments.

**How to think through this:**
1. Injection is a mutating webhook — it happens at admission time, not at runtime, so the kubelet sees the final pod spec with proxy containers already present.
2. mTLS works because iptables capture means all traffic flows through the proxy — the app is never involved.
3. Overhead is real but predictable; the bigger cost is operational complexity of managing certificates and PeerAuthentication policies.

**Key takeaway:** Istio's sidecar proxy captures all pod traffic via iptables and implements transparent mTLS using SPIFFE identities issued by Istiod, adding ~1ms latency and ~50-100MB memory per pod.

</details>

📖 **Theory:** [service-mesh-advanced](./24_Service_Mesh/Theory.md#module-24--service-mesh)


---

### Q72 · [Thinking] · `etcd-operations`

> **How do you back up and restore etcd? What is the etcdctl snapshot save/restore process?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
etcd is the single source of truth for all cluster state. Losing etcd without a backup means losing the entire cluster configuration.

**Taking a snapshot:**
```bash
ETCDCTL_API=3 etcdctl snapshot save /backup/etcd-snapshot.db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key

# Verify the snapshot
etcdctl snapshot status /backup/etcd-snapshot.db --write-out=table
```

**Restore process (single-node control plane):**
```bash
# 1. Stop the API server (prevents writes during restore)
mv /etc/kubernetes/manifests/kube-apiserver.yaml /tmp/

# 2. Stop etcd
mv /etc/kubernetes/manifests/etcd.yaml /tmp/

# 3. Restore snapshot to a new data directory
ETCDCTL_API=3 etcdctl snapshot restore /backup/etcd-snapshot.db \
  --data-dir=/var/lib/etcd-restored \
  --name=master \
  --initial-cluster=master=https://127.0.0.1:2380 \
  --initial-advertise-peer-urls=https://127.0.0.1:2380

# 4. Update etcd manifest to point to new data dir
# Edit --data-dir in etcd.yaml from /var/lib/etcd to /var/lib/etcd-restored

# 5. Restore manifests
mv /tmp/etcd.yaml /etc/kubernetes/manifests/
mv /tmp/kube-apiserver.yaml /etc/kubernetes/manifests/
```

**Key operational considerations:**
- Snapshots should be taken every 30 minutes in production and stored off-cluster (S3, GCS).
- Snapshot includes all keys at a point in time — restoring is a hard reset to that moment.
- In multi-node etcd clusters, all members must be restored from the same snapshot with their individual `--name` and `--initial-cluster` values.
- The `--data-dir` must be empty or non-existent before restore — etcdctl will not overwrite.

**How to think through this:**
1. Stop writes first (move API server manifest) — etcd is a static pod, removing the manifest stops the pod.
2. Restore creates a new data directory — never restore over the live data directory.
3. etcd's cluster membership is encoded in the snapshot, so `--initial-cluster` must match the original topology.

**Key takeaway:** etcd backup is a `etcdctl snapshot save` with TLS creds; restore requires stopping the API server and etcd, restoring to a fresh data directory, then updating the etcd manifest to point to it.

</details>

📖 **Theory:** [etcd-operations](./02_K8s_Architecture/Theory.md#etcd)


---

### Q73 · [Thinking] · `cluster-upgrades`

> **Walk through upgrading a Kubernetes cluster from 1.29 to 1.30. What is the safe order of operations?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Kubernetes supports a maximum skew of one minor version between control plane and nodes. You must upgrade control plane before nodes, and you cannot skip minor versions.

**Pre-upgrade checklist:**
1. Read the 1.30 changelog for deprecated APIs — check if any resources in the cluster use APIs removed in 1.30.
2. Back up etcd.
3. Check add-on compatibility: CoreDNS, CNI, CSI drivers, metrics-server must support 1.30.
4. Test in a staging cluster first.

**Control plane upgrade (kubeadm):**
```bash
# 1. Upgrade kubeadm on the control plane node
apt-get update && apt-get install -y kubeadm=1.30.0-00

# 2. Verify the upgrade plan
kubeadm upgrade plan

# 3. Apply the upgrade (upgrades kube-apiserver, controller-manager, scheduler, etcd)
kubeadm upgrade apply v1.30.0

# 4. Upgrade kubelet and kubectl on the control plane node
apt-get install -y kubelet=1.30.0-00 kubectl=1.30.0-00
systemctl daemon-reload && systemctl restart kubelet
```

**Node upgrade (repeat for each worker):**
```bash
# 1. Cordon and drain the node
kubectl cordon node-1
kubectl drain node-1 --ignore-daemonsets --delete-emptydir-data

# 2. SSH to node-1
apt-get install -y kubeadm=1.30.0-00
kubeadm upgrade node  # upgrades kubelet config only (no control plane components)
apt-get install -y kubelet=1.30.0-00
systemctl daemon-reload && systemctl restart kubelet

# 3. Uncordon
kubectl uncordon node-1
```

**Post-upgrade:**
- Verify: `kubectl get nodes` shows 1.30 for all nodes.
- Upgrade add-ons: `kubeadm upgrade apply` upgrades CoreDNS and kube-proxy automatically.
- Update CNI and CSI plugins manually if not managed by kubeadm.

**How to think through this:**
1. The skew policy means a 1.29 kubelet talking to a 1.30 API server is supported — this is what allows rolling node upgrades without downtime.
2. `kubeadm upgrade node` on workers only updates the kubelet configuration (KubeletConfiguration), not the control plane binaries.
3. Drain before kubelet upgrade ensures no new pods land on the node during the upgrade window.

**Key takeaway:** Upgrade control plane first via `kubeadm upgrade apply`, then upgrade each worker node sequentially using cordon/drain/upgrade-kubelet/uncordon, never skipping minor versions.

</details>

📖 **Theory:** [cluster-upgrades](./28_Cluster_Management/Theory.md#managed-cluster-upgrades)


---

### Q74 · [Thinking] · `custom-controllers`

> **What is the reconciliation loop in a Kubernetes controller? What are the key interfaces: Reconciler, Informer, WorkQueue?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A Kubernetes controller is a control loop that watches the current state of the cluster and takes actions to move it toward a desired state. Think of it as a thermostat: it observes temperature (current state), compares to the setpoint (desired state), and turns on heat or cooling (actions).

**The reconciliation loop:**
```
Watch API → Event → WorkQueue → Dequeue → Reconcile() → API call → Watch API
```
The loop is *level-triggered*, not edge-triggered. The Reconcile function is called with a `NamespacedName` (namespace/name), not an event. It should always read the current state from the API (or cache) and compute what needs to change — it must be idempotent.

**Informer:**
An Informer is a cached, watch-based client that maintains a local in-memory store of a resource type. It:
1. Does an initial List of all objects.
2. Opens a Watch stream for changes.
3. Syncs changes into an in-memory `Indexer` (the cache).
4. Calls registered `EventHandler` functions (OnAdd, OnUpdate, OnDelete) which typically push a key into the WorkQueue.

This means your controller reads from cache (fast, no API server hit) but writes to the API server.

**WorkQueue:**
The WorkQueue is a rate-limited, deduplicating queue. Key properties:
- **Deduplication:** if the same key is added 5 times before being processed, it only reconciles once.
- **Rate limiting:** uses exponential backoff on requeue to handle transient errors.
- **Processing guarantee:** an item is not removed from the queue until `Done()` is called, preventing concurrent processing of the same key.

**Reconciler interface (controller-runtime):**
```go
type Reconciler interface {
    Reconcile(ctx context.Context, req Request) (Result, error)
}
// Request contains: NamespacedName{Namespace, Name}
// Result controls requeue: Result{RequeueAfter: 30*time.Second}
```

**How to think through this:**
1. Informers decouple watching from processing — events are batched and deduplicated before hitting your Reconcile function.
2. Reconcile must be idempotent — it will be called multiple times for the same object (on restart, on resync interval).
3. Return an error to requeue with backoff; return `Result{RequeueAfter: ...}` to schedule a future check.

**Key takeaway:** Controllers use Informers to cache watched objects, a WorkQueue to deduplicate and rate-limit events, and an idempotent Reconcile function that reads current state and drives it toward desired state.

</details>

📖 **Theory:** [custom-controllers](./12_Custom_Resources/Theory.md#module-12-custom-resources--extending-kubernetes)


---

### Q75 · [Thinking] · `validating-admission`

> **What is a ValidatingAdmissionPolicy (CEL-based)? How does it replace ValidatingWebhookConfiguration for simple rules?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
`ValidatingAdmissionPolicy` (VAP) was introduced in Kubernetes 1.26 (stable in 1.30) as a native in-process admission mechanism using CEL (Common Expression Language). It eliminates the need to run a webhook server for simple validation rules.

**Traditional webhook problem:**
`ValidatingWebhookConfiguration` requires: a running HTTPS server, TLS cert management, a Deployment, a Service, correct `caBundle`, and handling timeouts. For a rule like "all Deployments must have resource limits set," this is massive overhead.

**ValidatingAdmissionPolicy:**
```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: require-resource-limits
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
      - apiGroups: ["apps"]
        apiVersions: ["v1"]
        operations: ["CREATE", "UPDATE"]
        resources: ["deployments"]
  validations:
    - expression: >
        object.spec.template.spec.containers.all(c,
          has(c.resources) &&
          has(c.resources.limits) &&
          has(c.resources.limits.cpu) &&
          has(c.resources.limits.memory)
        )
      message: "All containers must have CPU and memory limits set."
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: require-resource-limits-binding
spec:
  policyName: require-resource-limits
  validationActions: [Deny]
  matchResources:
    namespaceSelector:
      matchLabels:
        environment: production
```

**Advantages over webhooks:**
- No external server — evaluated in-process by the API server.
- No network round-trip — lower latency, no timeout risk.
- Policy and Binding separation — one policy, multiple bindings with different selectors.
- CEL is sandboxed and has a cost budget — no infinite loops possible.

**Limitations:** CEL cannot make external calls, cannot mutate objects (use MutatingAdmissionPolicy for that), and is limited to logic expressible in CEL.

**How to think through this:**
1. VAP evaluates `object` (the incoming resource) and `oldObject` (for updates) using CEL expressions.
2. The Binding object controls where the policy applies — same policy can be bound to prod namespaces with Deny and dev namespaces with Warn.
3. For complex logic requiring external data (e.g., checking an external registry), webhooks are still necessary.

**Key takeaway:** ValidatingAdmissionPolicy lets you enforce admission rules as CEL expressions running in-process in the API server, eliminating webhook infrastructure for simple validation logic.

</details>

📖 **Theory:** [validating-admission](./36_ValidatingAdmissionPolicy/Theory.md#module-36--validatingadmissionpolicy)


---

## 🔵 Tier 4 — Interview / Scenario

### Q76 · [Interview] · `explain-pods-junior`

> **A junior engineer asks why Kubernetes uses Pods instead of running containers directly. Explain the rationale.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Think of a Pod as a shared apartment. Containers in the same Pod share the apartment's address (IP) and common areas (volumes), but each container has its own room (process space). Kubernetes schedules the apartment as a unit — it would be awkward to schedule individual rooms on different floors.

**The technical rationale:**

1. **Shared network namespace:** All containers in a Pod share one IP address and port space. This enables the sidecar pattern — a proxy container (e.g., Envoy, Istio) can intercept localhost traffic from the app container without any application changes.

2. **Shared volumes:** Containers in a Pod can mount the same volume. The classic example: an init container writes a config file to a shared volume; the main container reads it at startup.

3. **Co-scheduling guarantee:** Kubernetes schedules all containers in a Pod to the same node atomically. If you have an app and a log collector that must run together, a Pod guarantees co-location. Scheduling individual containers would require complex affinity rules.

4. **Lifecycle coupling:** Containers in a Pod start and stop together. This is intentional — if the sidecar and app have different lifecycles, they should be separate Pods.

5. **The pause container:** There's actually a hidden third container — the `pause` (infra) container. It holds the network namespace open so that if the app container restarts, it gets back the same IP. The Pod's identity persists across container restarts.

**How to think through this:**
1. Docker runs individual containers. Kubernetes's unit is the Pod because real applications are rarely a single process.
2. The sidecar pattern (service mesh, log shipping, secrets injection) requires shared network/filesystem — that's the Pod's core value.
3. Scheduling a group of containers atomically is simpler than managing affinity between individual containers.

**Key takeaway:** Pods exist to group tightly-coupled containers that share a network namespace, volumes, and must be co-scheduled — enabling the sidecar pattern and simplifying co-location requirements.

</details>

📖 **Theory:** [explain-pods-junior](./04_Pods/Theory.md#module-04--pods)


---

### Q77 · [Interview] · `compare-deployment-statefulset`

> **Compare Deployments and StatefulSets. When must you use a StatefulSet? Can you convert one to the other?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Think of a Deployment as a fleet of identical rental cars — any car can replace any other, license plates don't matter. A StatefulSet is a fleet of personalized vehicles where each car has a specific owner, a permanent license plate, and always parks in the same spot.

**Deployment:**
- Pods are interchangeable — no stable identity.
- Pod names are random (e.g., `web-7d9f4b-xkz2p`).
- PVCs are not attached to specific pods — if a pod is rescheduled, it may get a different PVC or none.
- Rolling updates replace pods in any order.
- Suited for: stateless services (web servers, API services, workers).

**StatefulSet:**
- Pods have stable, ordered identities: `db-0`, `db-1`, `db-2`.
- Stable network identity: each pod gets a predictable DNS name via headless Service: `db-0.db-svc.namespace.svc.cluster.local`.
- Stable storage: `volumeClaimTemplates` creates a dedicated PVC per pod that survives pod rescheduling. `db-0` always gets its PVC back.
- Ordered startup/shutdown: pods start `0 → 1 → 2` and shut down `2 → 1 → 0` by default.
- Suited for: databases (MySQL, PostgreSQL, Cassandra), distributed systems (Kafka, ZooKeeper, etcd), any app where each instance has unique state.

**When you must use StatefulSet:**
- The app requires stable hostname/IP (peer discovery in Kafka/etcd uses hostnames).
- Each replica has unique persistent data that must survive rescheduling.
- Startup order matters (e.g., primary must start before replicas).

**Converting between them:**
There is no `kubectl convert`. The migration process is:
1. Scale the Deployment to 0 (stop writes).
2. Create the StatefulSet manifest with `volumeClaimTemplates` that match existing PVC names (if any).
3. Delete the Deployment, create the StatefulSet.
4. Manually bind existing PVCs to the StatefulSet pods if needed.
This is a manual, risky operation — plan for downtime.

**How to think through this:**
1. Ask: does each instance have unique data or identity? If yes, StatefulSet.
2. `volumeClaimTemplates` is the decisive feature — it creates per-pod PVCs that outlive the pod.
3. The headless Service is what provides stable DNS — it's not optional for StatefulSets.

**Key takeaway:** Use StatefulSets when pods need stable identity, ordered operations, or per-pod persistent storage; Deployments for stateless, interchangeable replicas — and there is no automated conversion path between them.

</details>

📖 **Theory:** [compare-deployment-statefulset](./13_DaemonSets_and_StatefulSets/Theory.md#daemonset-vs-statefulset-vs-deployment)


---

### Q78 · [Interview] · `explain-services`

> **Explain why Kubernetes Services are needed even though Pods have IP addresses. What problem does a Service's stable DNS name solve?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Pod IPs are ephemeral. Every time a pod is rescheduled, crashes and restarts, or a rolling update replaces it, the pod gets a new IP address. If Service A hardcodes Service B's pod IP, it breaks every time B restarts. This is the fundamental problem Services solve.

**What a Service provides:**
1. **Stable virtual IP (ClusterIP):** A Service gets a VIP from the cluster's Service CIDR that never changes as long as the Service exists. kube-proxy programs iptables/IPVS rules to load balance from the VIP to all healthy pod endpoints.

2. **Stable DNS name:** CoreDNS creates an A record: `my-service.my-namespace.svc.cluster.local → ClusterIP`. Application code uses this DNS name instead of IPs. The DNS name is stable across pod restarts, node failures, and rolling deployments.

3. **Endpoint management:** The `EndpointSlice` controller watches pods matching the Service's `selector` and maintains the list of healthy pod IPs. As pods come and go, the endpoint list updates automatically. Critically, pods failing their readiness probe are removed from endpoints — traffic stops flowing to unhealthy pods without any application code changes.

4. **Load balancing:** kube-proxy distributes connections across all healthy endpoints (round-robin by default in iptables mode; weighted in IPVS mode).

**The DNS name value:**
```
# Without Service: hardcoded, breaks on every pod restart
http://10.244.3.17:8080/api

# With Service: stable, works across deployments, scaling, failures
http://payments-service.finance.svc.cluster.local/api
# or within same namespace:
http://payments-service/api
```

**How to think through this:**
1. Pods are cattle — they die and are replaced. Services are pets — they have stable names.
2. The selector is the glue: the Service continuously queries "which pods match my labels?" and updates endpoints.
3. Readiness probe + Service = automatic traffic management. Unhealthy pods are automatically removed from rotation.

**Key takeaway:** Services solve the ephemeral pod IP problem by providing a stable ClusterIP and DNS name backed by dynamic endpoint discovery via label selectors, with readiness-aware load balancing.

</details>

📖 **Theory:** [explain-services](./06_Services/Theory.md#module-06--services)


---

### Q79 · [Interview] · `compare-configmap-secret`

> **Compare ConfigMaps and Secrets. What is the difference in how they're stored? What are best practices for production secrets?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
ConfigMaps and Secrets both inject configuration into pods, but they differ in intent, storage, and access controls.

**ConfigMap:**
- Stores non-sensitive configuration: environment variables, config files, command-line arguments.
- Stored in etcd as plaintext.
- No special access restrictions by default.
- Values are strings (or binary data as base64).

**Secret:**
- Intended for sensitive data: passwords, tokens, TLS certs, SSH keys.
- Stored in etcd as base64-encoded values — **this is NOT encryption, it is encoding**. Anyone who can read etcd or the Secret object sees the plaintext.
- Access controlled via RBAC: you can grant `get` on ConfigMaps without granting `get` on Secrets.
- Mounted into pods as tmpfs (in-memory filesystem) — not written to node disk.
- kubelet does not write Secret data to node disk.

**The base64 misconception:**
A common interview trap: "Secrets are encrypted." They are not by default. `echo -n "mypassword" | base64` is trivially reversible. Real encryption requires enabling **Encryption at Rest** in the API server configuration (`EncryptionConfiguration`), which encrypts Secret values in etcd using AES-CBC or AES-GCM.

**Production best practices:**
1. **Enable Encryption at Rest** — configure `EncryptionConfiguration` with an AES key or KMS provider (AWS KMS, GCP KMS).
2. **Use external secret management** — integrate with Vault (via vault-agent sidecar or vault-secrets-operator), AWS Secrets Manager (via External Secrets Operator), or similar. Secrets are never stored in Kubernetes etcd at all.
3. **RBAC least privilege** — service accounts should only have `get` on the specific Secrets they need, not `list`/`watch` (which would expose all secrets in a namespace).
4. **Never commit Secrets to git** — use sealed-secrets or SOPS for GitOps workflows.
5. **Short TTL secrets** — rotate regularly; use dynamic secrets from Vault where possible.

**How to think through this:**
1. The only meaningful security difference between ConfigMap and Secret is RBAC granularity and tmpfs mounting — not encryption (by default).
2. External Secrets Operator is the production pattern: the Kubernetes Secret is a short-lived copy pulled from a real secret store.
3. `list` on Secrets is dangerous — it exposes every secret in the namespace. RBAC should grant `get` on specific secrets by name.

**Key takeaway:** Secrets differ from ConfigMaps primarily in RBAC granularity and tmpfs mounting, not in encryption — production environments require either Encryption at Rest or an External Secrets Operator backed by a real secret management system.

</details>

📖 **Theory:** [compare-configmap-secret](./07_ConfigMaps_and_Secrets/Theory.md#module-07--configmaps-and-secrets)


---

### Q80 · [Interview] · `explain-rbac`

> **Explain Kubernetes RBAC to a developer who only knows file permissions. Walk through creating a read-only role for a CI/CD service account.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Linux file permissions say: "this user can read/write/execute this file." Kubernetes RBAC says: "this service account can get/list/watch these resources in this namespace." The mental model maps cleanly:

| Linux | Kubernetes |
|---|---|
| User/Group | ServiceAccount |
| File/Directory | Resource (pods, secrets, deployments) |
| read/write/execute | verbs (get, list, watch, create, update, patch, delete) |
| chmod/chown | Role + RoleBinding |
| sudo | ClusterRole + ClusterRoleBinding |

**The four objects:**
- **Role**: defines what verbs are allowed on what resources, scoped to one namespace.
- **ClusterRole**: same but cluster-wide (or for non-namespaced resources like nodes).
- **RoleBinding**: binds a Role to a subject (ServiceAccount, User, Group) in a namespace.
- **ClusterRoleBinding**: binds a ClusterRole cluster-wide.

**Creating read-only access for a CI/CD service account:**
```yaml
# 1. Create the ServiceAccount
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ci-deployer
  namespace: production
---
# 2. Define what it can do (read-only on relevant resources)
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: ci-read-only
  namespace: production
rules:
  - apiGroups: ["apps"]
    resources: ["deployments", "replicasets"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["pods", "pods/log", "services", "configmaps"]
    verbs: ["get", "list", "watch"]
---
# 3. Bind the Role to the ServiceAccount
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: ci-read-only-binding
  namespace: production
subjects:
  - kind: ServiceAccount
    name: ci-deployer
    namespace: production
roleRef:
  kind: Role
  name: ci-read-only
  apiGroup: rbac.authorization.k8s.io
```

**Verify with:**
```bash
kubectl auth can-i list pods --namespace=production \
  --as=system:serviceaccount:production:ci-deployer
# yes

kubectl auth can-i delete pods --namespace=production \
  --as=system:serviceaccount:production:ci-deployer
# no
```

**How to think through this:**
1. Always prefer Role over ClusterRole unless cross-namespace access is required — least privilege.
2. `""` in apiGroups means the core API group (pods, services, configmaps). `"apps"` covers deployments.
3. `list` without `get` is nearly useless — grant both together for read access.

**Key takeaway:** Kubernetes RBAC maps users/groups to file-permission concepts via Role (what) and RoleBinding (who), with `kubectl auth can-i` as the verification tool for least-privilege validation.

</details>

📖 **Theory:** [explain-rbac](./11_RBAC/Theory.md#module-11-rbac--role-based-access-control)


---

### Q81 · [Design] · `scenario-pod-crashloop`

> **A Pod is in CrashLoopBackOff. Walk through your complete diagnostic process step by step.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
CrashLoopBackOff means the container starts, crashes, and Kubernetes keeps retrying with exponential backoff (10s → 20s → 40s → up to 5 minutes). The container is crashing — the question is why.

**Step 1 — Get the exit code:**
```bash
kubectl describe pod <pod-name> -n <namespace>
# Look for: Last State, Exit Code, Reason
# Exit 0: app exited cleanly — misconfigured entrypoint?
# Exit 1: application error
# Exit 137: OOMKilled (SIGKILL from kernel, memory limit exceeded)
# Exit 143: SIGTERM (graceful shutdown signal — probe timeout?)
```

**Step 2 — Read the logs:**
```bash
# Logs from the crashing container (current attempt)
kubectl logs <pod-name> -n <namespace>

# Logs from the PREVIOUS container instance (often more useful)
kubectl logs <pod-name> -n <namespace> --previous
```
This is often the most informative step — stack traces, config errors, and connection failures appear here.

**Step 3 — Check events:**
```bash
kubectl describe pod <pod-name> -n <namespace>
# Look for Events section at the bottom
# Common: Liveness probe failed, OOMKilled, Failed to pull image, Back-off restarting
```

**Step 4 — Inspect the container spec:**
```bash
kubectl get pod <pod-name> -n <namespace> -o yaml
# Check: command/args, env vars, volumeMounts, resource limits, probes
```

**Step 5 — Common causes and diagnosis:**

| Exit Code / Reason | Likely Cause | Fix |
|---|---|---|
| Exit 1, app error in logs | Config error, missing env var, DB connection failed | Fix env/secret/config |
| Exit 137, OOMKilled | Memory limit too low | Increase `resources.limits.memory` |
| Exit 0 | Entrypoint exits immediately | App needs a foreground process |
| Liveness probe failed | App takes too long to start | Increase `initialDelaySeconds` |
| CrashLoop + no logs | initContainer failing | Check `kubectl logs <pod> -c <init-container>` |

**Step 6 — Interactive debugging:**
```bash
# If the container starts briefly, exec in before it crashes
kubectl debug <pod-name> -n <namespace> --copy-to=debug-pod \
  --container=<container> -- /bin/sh

# Or override the command to keep it running
kubectl run debug --image=<same-image> --command -- sleep 3600
```

**How to think through this:**
1. `--previous` logs are the most valuable — the current attempt may not have had time to log anything before crashing.
2. Exit code 137 = OOM, Exit code 1 = app error, Exit code 0 = wrong command. These three cover 90% of cases.
3. If no logs appear, check initContainers — they run before the main container and their failure causes CrashLoop.

**Key takeaway:** Diagnose CrashLoopBackOff by checking the exit code in `describe`, reading `--previous` logs, and matching the exit code to common causes — OOMKilled (137), app error (1), or immediate exit (0).

</details>

📖 **Theory:** [scenario-pod-crashloop](./14_Health_Probes/Theory.md#the-story-the-pod-that-lied)


---

### Q82 · [Design] · `scenario-service-unreachable`

> **A Service returns connection refused. The Pods are running. Walk through diagnosing the issue (endpoints, selectors, network policies).**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
"Connection refused" means the TCP connection was rejected at the destination — the port is not listening. This is different from a timeout (no route) or DNS failure (resolution failed). Work from DNS → Service → Endpoints → Pod → Network Policy.

**Step 1 — Verify DNS resolution:**
```bash
kubectl run debug --image=busybox --rm -it --restart=Never -- \
  nslookup my-service.my-namespace.svc.cluster.local
# Should return the ClusterIP
# If NXDOMAIN: Service doesn't exist or wrong namespace
```

**Step 2 — Check Service and its selector:**
```bash
kubectl get service my-service -n my-namespace -o yaml
# Check: spec.selector, spec.ports[].port, spec.ports[].targetPort
```

**Step 3 — Check Endpoints:**
```bash
kubectl get endpoints my-service -n my-namespace
# If ADDRESS column is empty: NO pods match the selector
# If addresses present but still connection refused: problem is in the pod

kubectl describe endpoints my-service -n my-namespace
# Shows: NotReadyAddresses (pods failing readiness probe)
```

**Step 4 — Verify selector matches pod labels:**
```bash
kubectl get pods -n my-namespace --show-labels
# Compare pod labels to Service selector
# Common mistake: Service selector: app=myapp, Pod label: App=myapp (case sensitive)
```

**Step 5 — Test direct pod connectivity:**
```bash
# Get a pod IP from endpoints
kubectl get pods -n my-namespace -o wide

# Test direct connection to pod
kubectl run debug --image=nicolaka/netshoot --rm -it --restart=Never -- \
  curl http://10.244.3.17:8080/health
# If this fails: app is not listening on expected port
# If this succeeds: Service routing is the problem
```

**Step 6 — Check targetPort matches container port:**
```bash
# Service targetPort must match the port the container actually listens on
# spec.ports[].targetPort: 8080 must match containerPort: 8080 in pod spec
# Can also use named port: targetPort: http → containerPort with name: http
```

**Step 7 — Check NetworkPolicies:**
```bash
kubectl get networkpolicy -n my-namespace
# If any NetworkPolicy exists, default becomes deny-all for selected pods
# Check if ingress rules allow traffic from the source namespace/pod
```

**How to think through this:**
1. Empty endpoints = selector mismatch (check label case sensitivity).
2. NotReadyAddresses = pods exist but readiness probe is failing.
3. Direct pod connection works but Service doesn't = targetPort mismatch or kube-proxy issue.
4. NetworkPolicy is often the silent culprit — any NetworkPolicy with a podSelector makes that pod's default deny.

**Key takeaway:** Diagnose service connectivity by checking endpoints first (selector mismatch = empty endpoints), then direct pod connectivity (targetPort mismatch), then NetworkPolicy (implicit deny with any policy present).

</details>

📖 **Theory:** [scenario-service-unreachable](./06_Services/Theory.md#module-06--services)


---

### Q83 · [Design] · `scenario-pvc-pending`

> **A PVC is stuck in Pending state. What are the 4 most common causes and how do you diagnose each?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A PVC in Pending state means Kubernetes cannot bind it to a PersistentVolume. Start with `kubectl describe pvc <name>` — the Events section almost always tells you the reason.

**Cause 1: No matching StorageClass**
```bash
kubectl get pvc my-pvc -n my-namespace -o yaml
# Check: spec.storageClassName

kubectl get storageclass
# Is the named StorageClass present?
# Is there a default StorageClass (annotated with storageclass.kubernetes.io/is-default-class: "true")?
```
If `storageClassName` is set to a class that doesn't exist, the PVC stays Pending indefinitely. If it's empty and there's no default StorageClass, same result.

**Cause 2: No PV matches the access mode or capacity**
For statically provisioned PVs (no StorageClass provisioner):
```bash
kubectl get pv
# Check: CAPACITY, ACCESS MODES, STATUS
# PVC requests 10Gi ReadWriteOnce → must find PV with >= 10Gi and RWO access mode
# A 5Gi PV will not bind to a 10Gi PVC
```
Access mode mismatch (RWO vs RWX) is a common mistake — EBS only supports RWO, EFS supports RWX.

**Cause 3: StorageClass provisioner is not running**
```bash
kubectl describe pvc my-pvc
# Event: "waiting for a volume to be created either by the external provisioner..."

kubectl get pods -n kube-system | grep provisioner
# Is the CSI driver / provisioner pod running?
kubectl logs -n kube-system <provisioner-pod>
```
If the EBS CSI driver or NFS provisioner pod is not running or has permission errors, dynamic provisioning stalls.

**Cause 4: Topology / zone constraints**
```bash
kubectl describe pvc my-pvc
# Event: "0/3 nodes are available: 3 node(s) had volume node affinity conflict"

kubectl get pv <pv-name> -o yaml | grep -A5 nodeAffinity
# EBS volumes are zone-specific (us-east-1a)
# If the PV is in us-east-1a but the pod is scheduled to us-east-1b: binding fails
```
This also affects WaitForFirstConsumer binding mode — the PV is not provisioned until the pod is scheduled, so the PVC appears Pending until a pod that uses it is created.

**How to think through this:**
1. `kubectl describe pvc` Events section is almost always sufficient to identify the cause.
2. `WaitForFirstConsumer` is expected — PVC stays Pending until a Pod is scheduled. This is not a bug.
3. Zone affinity issues are common with EBS in multi-AZ clusters — use topology-aware provisioning.

**Key takeaway:** PVC Pending causes are: missing/wrong StorageClass, no matching PV (capacity/access mode), provisioner not running, or topology/zone affinity conflict — all diagnosable via `kubectl describe pvc` events.

</details>

📖 **Theory:** [scenario-pvc-pending](./10_Persistent_Volumes/Theory.md#persistentvolumeclaim-pvc)


---

### Q84 · [Design] · `scenario-hpa-not-scaling`

> **An HPA is configured but pods never scale up even under load. Walk through 5 possible causes.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**Step 1 — Check HPA status:**
```bash
kubectl describe hpa my-hpa -n my-namespace
# Look for: Conditions, Current/Desired replicas, metric values
# "AbleToScale: False" → check ScaleDown stabilization or maxReplicas already hit
# "ScalingActive: False" → metric not available
```

**Cause 1: metrics-server not running or not scraping**
HPA relies on metrics-server for CPU/memory. If metrics-server is down:
```bash
kubectl top pods -n my-namespace
# If this returns error: metrics-server is the problem
kubectl get pods -n kube-system | grep metrics-server
kubectl logs -n kube-system <metrics-server-pod>
```

**Cause 2: Resource requests not set on the target container**
HPA calculates CPU utilization as `current_usage / request`. If no CPU request is set, HPA cannot compute a percentage and marks the metric as unknown.
```bash
kubectl get deployment my-deployment -o yaml | grep -A5 resources
# containers[].resources.requests.cpu must be set
```

**Cause 3: Already at maxReplicas**
```bash
kubectl describe hpa my-hpa
# Current replicas == maxReplicas → HPA is working, cluster capacity is the limit
# Increase maxReplicas if appropriate
```

**Cause 4: Scale-up stabilization window (scale-up cooldown)**
HPA has a default `scaleUp.stabilizationWindowSeconds` of 0s (immediate), but if custom HPA behavior is configured with a long window, it may delay action. More commonly, the `--horizontal-pod-autoscaler-sync-period` (default 15s) means HPA only evaluates every 15 seconds.

**Cause 5: Metric value is already below the target threshold**
The load test may not be reaching the CPU threshold. Check actual vs target:
```bash
kubectl describe hpa my-hpa
# "cpu: 15%/50%" means current is 15%, target is 50% → not scaling is correct
# Verify the load is actually hitting the right pods
kubectl top pods -n my-namespace
```

**Bonus Cause: Target Deployment has a paused rollout or minReplicas = maxReplicas**
If `minReplicas == maxReplicas`, the HPA is effectively disabled — no scaling room exists.

**How to think through this:**
1. `kubectl describe hpa` shows the computed metric values — if they look low, the load isn't reaching pods.
2. Missing resource requests is the most common cause in new deployments.
3. metrics-server is required for CPU/memory HPA; custom metrics require the Prometheus adapter or KEDA.

**Key takeaway:** HPA scaling failures most commonly stem from missing metrics-server, absent CPU resource requests on pods, already hitting maxReplicas, or load not actually reaching the targeted pods.

</details>

📖 **Theory:** [scenario-hpa-not-scaling](./18_HPA_VPA_Autoscaling/Theory.md#module-18-hpa-vpa-and-autoscaling)


---

### Q85 · [Design] · `scenario-node-pressure`

> **A node enters NotReady state and pods start evicting. How do you triage: check node conditions, disk/memory pressure, and safely drain?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
NotReady means the kubelet on the node is not reporting healthy status to the API server. Pods begin eviction after the `pod-eviction-timeout` (default 5 minutes for node failure).

**Step 1 — Check node conditions:**
```bash
kubectl describe node <node-name>
# Look for Conditions section:
# Type              Status
# MemoryPressure    True    ← evicts BestEffort pods first
# DiskPressure      True    ← evicts pods based on imagefs/nodefs usage
# PIDPressure       True    ← too many processes
# Ready             False   ← kubelet not reporting
```

**Step 2 — Check specific pressure causes:**
```bash
# SSH to the node
ssh ec2-user@<node-ip>

# Memory pressure
free -h
# Check for memory leak: top -o %MEM

# Disk pressure — kubelet has two eviction thresholds:
df -h
# nodefs (/) and imagefs (/var/lib/docker or /var/lib/containerd)
# If /var/lib/containerd is >85% full → DiskPressure triggers

# Clean up unused images (on node)
crictl rmi --prune
# Or
docker system prune -f
```

**Step 3 — Check kubelet logs:**
```bash
journalctl -u kubelet -n 100 --no-pager
# Look for: eviction manager, image GC, OOM kills, connection errors
```

**Step 4 — If node is recoverable, safely drain:**
```bash
# Cordon prevents new pods from scheduling here
kubectl cordon <node-name>

# Drain evicts all pods (respects PodDisruptionBudgets)
kubectl drain <node-name> \
  --ignore-daemonsets \        # don't evict DaemonSet pods
  --delete-emptydir-data \     # ok to lose emptyDir volumes
  --grace-period=60            # give pods time to shutdown cleanly

# After maintenance, uncordon
kubectl uncordon <node-name>
```

**Step 5 — Check PodDisruptionBudgets:**
```bash
kubectl get pdb -A
# If drain hangs: a PDB may be blocking eviction
# "Cannot evict pod as it would violate the pod's disruption budget"
# Option: --disable-eviction flag (bypasses PDB — use cautiously in emergencies)
```

**Eviction order:**
1. BestEffort pods (no requests/limits) → first evicted.
2. Burstable pods (requests < limits, over request) → second.
3. Guaranteed pods (requests == limits) → last evicted.

**How to think through this:**
1. Cordon immediately — stop new work from landing on a sick node before you understand the problem.
2. Disk pressure is the most common production cause — log accumulation and unused container images.
3. Drain respects PDBs — if drain hangs, check `kubectl describe pdb -A` for the blocking policy.

**Key takeaway:** Triage NotReady nodes by checking Conditions in `kubectl describe node`, cordon immediately, investigate disk/memory/kubelet logs via SSH, then drain respecting PodDisruptionBudgets before maintenance.

</details>

📖 **Theory:** [scenario-node-pressure](./28_Cluster_Management/Theory.md#node-conditions-look-for-memorypressure-diskpressure-pidpressure)


---

### Q86 · [Interview] · `compare-ingress-gateway`

> **Compare Kubernetes Ingress and Gateway API. Why is the community moving to Gateway API?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**Ingress (the old model):**
Ingress was introduced in Kubernetes 1.1 and became stable in 1.19. It was designed for a simple use case: HTTP/HTTPS routing from an external load balancer to backend Services. Its design has three fundamental problems:

1. **Controller-specific annotations:** Core Ingress only supports host and path routing. Any advanced feature (TLS termination, rate limiting, timeouts, authentication) requires controller-specific annotations (`nginx.ingress.kubernetes.io/rate-limit`, `alb.ingress.kubernetes.io/scheme`, etc.). These are not portable — switching from NGINX to ALB breaks all annotations.

2. **No role separation:** One object mixes infrastructure config (TLS certs, load balancer type) with application routing (paths, backends). App developers must touch infra-level settings.

3. **Limited protocol support:** Ingress is HTTP/HTTPS only. TCP, UDP, gRPC, and WebSocket routing require workarounds or separate CRDs.

**Gateway API (the new model):**
Developed by the SIG-Network community as Ingress's successor, stable in 1.28:

1. **Role separation:** GatewayClass (infra provider) → Gateway (cluster operator) → HTTPRoute/GRPCRoute/TCPRoute (app developer). Each team owns their layer.

2. **Portable, standardized features:** Traffic splitting, header-based routing, request mirroring, and timeout configuration are first-class fields — not annotations. These work the same across all conformant implementations (Envoy Gateway, NGINX Gateway, Istio, AWS ALB).

3. **Protocol-aware routes:** `HTTPRoute`, `GRPCRoute`, `TLSRoute`, `TCPRoute`, `UDPRoute` — each has semantics appropriate to its protocol.

4. **Cross-namespace routing:** An `HTTPRoute` in a tenant namespace can attach to a `Gateway` in the infra namespace via `ReferenceGrant` — controlled delegation without sharing namespace.

**Why the community is moving:**
The Ingress API is essentially frozen — new features won't be added. Gateway API is where all active development is happening. Major controllers (Envoy Gateway is the CNCF reference implementation, Istio, Contour, NGINX) have all implemented Gateway API conformance.

**How to think through this:**
1. If you're starting a new cluster today, use Gateway API.
2. Migration from Ingress is incremental — most controllers support both simultaneously.
3. The annotation portability problem is the strongest argument: a team that builds Ingress expertise is locked to one controller.

**Key takeaway:** Gateway API replaces Ingress by enforcing role separation across three objects, providing portable standardized features as first-class fields instead of controller-specific annotations, and supporting protocols beyond HTTP.

</details>

📖 **Theory:** [compare-ingress-gateway](./31_Gateway_API/Theory.md#migration-from-ingress-to-gateway-api)


---

### Q87 · [Interview] · `compare-hpa-vpa-keda`

> **Compare HPA, VPA, and KEDA. When would you use each? Can you use HPA and VPA together?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Think of three different levers for scaling: more workers (HPA), bigger workers (VPA), and smarter workers triggered by events (KEDA).

**HPA (Horizontal Pod Autoscaler):**
- Adds or removes pod replicas based on metrics (CPU, memory, custom metrics).
- Reactive to current load — scales out when utilization exceeds target.
- Best for: stateless, horizontally scalable workloads (web servers, API services, workers).
- Limitation: cannot scale-to-zero natively; minimum 1 replica.

**VPA (Vertical Pod Autoscaler):**
- Adjusts CPU and memory requests/limits on individual pods based on historical usage.
- Operates in three modes: `Off` (recommendation only), `Initial` (set at pod creation), `Auto` (evict and recreate pods with new resources).
- Best for: stateful workloads that can't scale horizontally, or right-sizing resource requests to reduce waste.
- Limitation: `Auto` mode requires pod restart to apply new resource values — causes disruption.

**KEDA (Kubernetes Event-Driven Autoscaler):**
- Extends HPA with external event source triggers (SQS depth, Kafka lag, Prometheus queries, cron schedules).
- Supports scale-to-zero and scale-from-zero.
- Best for: event-driven consumers, batch jobs, workloads with predictable event patterns.
- Works by creating/managing an HPA behind the scenes; adds the missing external metric source.

**Can HPA and VPA run together?**
Using HPA (CPU/memory mode) and VPA (Auto mode) together on the same deployment is **not recommended and can cause conflicts**:
- HPA scales out based on current CPU usage.
- VPA evicts pods to resize them.
- Both trying to act on the same pods simultaneously creates a fight: HPA sees high CPU → scales out; VPA evicts a pod → HPA scales back in.

**Safe combinations:**
- HPA (CPU-based) + VPA (Off or Initial mode): VPA provides recommendations without acting.
- HPA (custom metric / KEDA) + VPA (Auto mode): safe if HPA is not CPU/memory based.
- KEDA + VPA (Auto): generally safe — KEDA uses external metrics, not CPU.

**Decision guide:**
| Scenario | Use |
|---|---|
| Web API under variable HTTP load | HPA (CPU) |
| Long-running DB process, hard to scale horizontally | VPA |
| Queue consumer, scale to zero overnight | KEDA |
| Right-size resource requests without scaling | VPA (Off mode) |
| Scheduled burst + right-sizing | KEDA + VPA (Initial) |

**How to think through this:**
1. HPA = how many pods; VPA = how big each pod. They solve orthogonal problems.
2. The conflict only exists when both react to CPU/memory — use KEDA to free HPA from CPU metrics.
3. VPA in `Off` mode is always safe and valuable for capacity planning.

**Key takeaway:** HPA scales pod count based on real-time metrics, VPA adjusts pod resources based on history, and KEDA enables event-driven and scale-to-zero autoscaling — combine KEDA with VPA safely, but avoid HPA+VPA Auto on the same CPU metrics.

</details>

📖 **Theory:** [compare-hpa-vpa-keda](./32_KEDA_Event_Driven_Autoscaling/Theory.md#keda-vs-hpa-comparison)


---

### Q88 · [Design] · `scenario-secret-rotation`

> **How do you rotate a database password stored in a Kubernetes Secret without restarting pods?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
The naive answer is: update the Secret and restart the pods. But the question asks for no restart, which requires understanding how Kubernetes delivers Secrets to pods and what "hot reload" looks like.

**Method 1: Mounted Secret volume (automatic propagation)**
When a Secret is mounted as a volume (not injected as an env var), Kubernetes automatically updates the file in the pod's filesystem within the `kubelet` sync period (default 60 seconds) when the Secret changes:

```yaml
# In pod spec - mount as volume, not env var
volumes:
  - name: db-credentials
    secret:
      secretName: db-password
volumeMounts:
  - name: db-credentials
    mountPath: /etc/secrets
    readOnly: true
```

When you run `kubectl create secret generic db-password --from-literal=password=newpass --dry-run=client -o yaml | kubectl apply -f -`, the file at `/etc/secrets/password` in running pods updates within ~60-90 seconds.

**Requirement:** The application must actively re-read the file. Environment variables are snapshotted at container start — they never update. The app must:
1. Not cache the password in memory indefinitely.
2. Periodically re-read `/etc/secrets/password` or re-read it on connection failure.

**Method 2: External Secrets Operator + Secrets Store CSI Driver**
```yaml
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: db-password-aws
spec:
  provider: aws
  parameters:
    objects: |
      - objectName: "prod/db/password"
        objectType: "secretsmanager"
  # Optional: sync to K8s Secret
  secretObjects:
    - secretName: db-password-k8s
      type: Opaque
      data:
        - objectName: prod/db/password
          key: password
```
The CSI driver rotates the secret file in the pod when the upstream secret (AWS Secrets Manager) changes — no restart needed. Rotation period is controlled by `rotationPollInterval` in the CSI driver config.

**What doesn't work without restart:**
- `envFrom` / `env.valueFrom.secretKeyRef` — injected at container start, never updated.
- Application code that reads the password once at startup and never re-reads.

**Rotation procedure:**
1. Update the secret in the source (AWS Secrets Manager or `kubectl apply`).
2. Wait for the CSI driver or kubelet to propagate (up to 60–90s).
3. Verify the file is updated: `kubectl exec <pod> -- cat /etc/secrets/password`.
4. Verify the application picks up the new credential (check app logs for reconnection).
5. Revoke the old password in the database.

**How to think through this:**
1. Volume-mounted secrets update automatically; env vars do not. This is the key distinction.
2. The application must cooperate — it needs to re-read on connection failure, not just at startup.
3. CSI driver + external secret store is the production pattern for true zero-restart rotation.

**Key takeaway:** Secret rotation without pod restart requires mounting secrets as volumes (not env vars) and an application that re-reads credentials on use or failure — external secrets via the Secrets Store CSI Driver automates the propagation.

</details>

📖 **Theory:** [scenario-secret-rotation](./07_ConfigMaps_and_Secrets/Theory.md#module-07--configmaps-and-secrets)


---

### Q89 · [Design] · `scenario-zero-downtime-deploy`

> **What combination of settings (PodDisruptionBudget, rolling update params, readiness probe) guarantees zero downtime during a deployment?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Zero downtime requires three layers to work together: the load balancer stops sending traffic before the pod is terminated, the rolling update never takes down more pods than the service can tolerate, and disruption budgets prevent external forces (node drains, cluster upgrades) from causing outages.

**Layer 1: Readiness Probe**
The readiness probe tells Kubernetes when a pod is ready to receive traffic. A pod is removed from Service endpoints the moment its readiness probe fails — before termination.

```yaml
readinessProbe:
  httpGet:
    path: /health/ready
    port: 8080
  initialDelaySeconds: 10    # wait before first check
  periodSeconds: 5
  failureThreshold: 3        # 3 consecutive failures → not ready
  successThreshold: 1
```

During rolling update: new pods don't receive traffic until readiness probe passes. Old pods stay in rotation until the new pod is verified healthy.

**Layer 2: Rolling Update Parameters**
```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1           # create 1 extra pod before removing old ones
    maxUnavailable: 0     # NEVER remove a pod until replacement is ready
```

`maxUnavailable: 0` is the critical setting. It means Kubernetes will never terminate an old pod until the new pod has passed its readiness probe. Combined with `maxSurge: 1`, the deployment temporarily runs replicas+1 pods during the update.

**Layer 3: Graceful Shutdown (preStop + terminationGracePeriodSeconds)**
When a pod is removed from endpoints, in-flight requests may still be routed to it for a few seconds (kube-proxy propagation lag). A `preStop` hook adds a delay before SIGTERM:

```yaml
lifecycle:
  preStop:
    exec:
      command: ["sh", "-c", "sleep 5"]   # wait for kube-proxy to drain
terminationGracePeriodSeconds: 60         # must be > preStop duration + shutdown time
```

**Layer 4: PodDisruptionBudget**
Prevents voluntary disruptions (drains, upgrades) from taking down too many pods:
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
spec:
  minAvailable: 2    # always keep at least 2 pods running
  selector:
    matchLabels:
      app: web
```

**Complete zero-downtime checklist:**
- `maxUnavailable: 0` + `maxSurge: >= 1`
- Readiness probe with appropriate `initialDelaySeconds`
- `preStop: sleep 5` to drain in-flight requests
- `terminationGracePeriodSeconds` > app shutdown time
- PodDisruptionBudget with `minAvailable >= 1`

**How to think through this:**
1. `maxUnavailable: 0` guarantees at least `replicas` healthy pods at all times during the update.
2. Without `preStop` sleep, kube-proxy may still route requests to a pod that has already received SIGTERM.
3. PDB protects against external disruption; rolling update params protect against the deployment itself.

**Key takeaway:** Zero-downtime deployments require `maxUnavailable: 0` to prevent premature termination, a readiness probe to gate traffic, a `preStop` sleep to drain in-flight requests, and a PDB to guard against external disruptions.

</details>

📖 **Theory:** [scenario-zero-downtime-deploy](./15_Deployment_Strategies/Theory.md#module-15-deployment-strategies)


---

### Q90 · [Design] · `scenario-multi-tenant`

> **Design a multi-tenant Kubernetes cluster for 5 teams. What isolation do you provide: namespaces, RBAC, network policies, resource quotas?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Multi-tenancy in Kubernetes is "soft" isolation — tenants share the kernel and kubelet. For strong isolation (different security profiles), use separate clusters. For team-level isolation with shared infrastructure costs, a single cluster with layered controls works well.

**Namespace strategy:**
```
cluster
├── team-alpha-dev
├── team-alpha-staging
├── team-alpha-prod
├── team-beta-dev
├── team-beta-prod
├── shared-infra          # monitoring, ingress controllers
└── kube-system
```
One namespace per team per environment. Namespace = unit of isolation for all subsequent controls.

**RBAC design:**
```yaml
# Per-team ClusterRole (reusable)
kind: ClusterRole
metadata:
  name: team-developer
rules:
  - apiGroups: ["apps", ""]
    resources: ["deployments", "services", "configmaps", "pods", "pods/log", "pods/exec"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
  - apiGroups: [""]
    resources: ["secrets"]
    verbs: ["get", "list"]   # can read but not create/delete secrets
---
# Bound per namespace per team group
kind: RoleBinding
metadata:
  name: team-alpha-dev-binding
  namespace: team-alpha-dev
subjects:
  - kind: Group
    name: team-alpha          # maps to IdP group via OIDC
roleRef:
  kind: ClusterRole
  name: team-developer
```
Platform team gets `cluster-admin` on `shared-infra` and read-only on other namespaces.

**Network Policies (default deny per namespace):**
```yaml
# Applied to every team namespace
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: team-alpha-prod
spec:
  podSelector: {}
  policyTypes: ["Ingress", "Egress"]
---
# Allow intra-namespace traffic
kind: NetworkPolicy
metadata:
  name: allow-same-namespace
  namespace: team-alpha-prod
spec:
  podSelector: {}
  ingress:
    - from:
      - podSelector: {}     # any pod in same namespace
  egress:
    - to:
      - podSelector: {}
    - ports:                # allow DNS
      - port: 53
        protocol: UDP
---
# Allow ingress from ingress controller namespace
kind: NetworkPolicy
metadata:
  name: allow-ingress-controller
  namespace: team-alpha-prod
spec:
  podSelector: {}
  ingress:
    - from:
      - namespaceSelector:
          matchLabels:
            name: shared-infra
```

**Resource Quotas:**
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-alpha-quota
  namespace: team-alpha-prod
spec:
  hard:
    requests.cpu: "20"
    requests.memory: 40Gi
    limits.cpu: "40"
    limits.memory: 80Gi
    count/pods: "50"
    count/services: "20"
    persistentvolumeclaims: "10"
---
# LimitRange ensures every pod has requests set (required for HPA and Quotas)
apiVersion: v1
kind: LimitRange
metadata:
  name: team-alpha-limits
  namespace: team-alpha-prod
spec:
  limits:
    - type: Container
      default:
        cpu: "500m"
        memory: "512Mi"
      defaultRequest:
        cpu: "100m"
        memory: "128Mi"
      max:
        cpu: "4"
        memory: "8Gi"
```

**Additional isolation layers:**
- **OPA Gatekeeper / Kyverno policies:** Enforce image registry allowlists, required labels, prohibited privileged containers.
- **Priority Classes:** Platform-critical pods get higher priority; team pods get medium priority to prevent starvation.
- **Node taints:** Dedicate node pools to specific teams with taints + tolerations for sensitive workloads.
- **Pod Security Standards:** Apply `restricted` profile to team namespaces via namespace label.

**How to think through this:**
1. Namespace + RBAC + NetworkPolicy + ResourceQuota are the four pillars — all four required for real isolation.
2. Default deny NetworkPolicy + explicit allow rules means teams can't accidentally (or maliciously) reach each other's services.
3. LimitRange is the "tax collector" — without it, teams deploy pods with no requests and starve the node.

**Key takeaway:** Multi-tenant isolation requires all four layers: namespaces for scope, RBAC for access control, default-deny NetworkPolicies for traffic isolation, and ResourceQuotas + LimitRanges for fair resource sharing.

</details>

📖 **Theory:** [scenario-multi-tenant](./08_Namespaces/Theory.md#module-08--namespaces)


---

## 🔴 Tier 5 — Critical Thinking

### Q91 · [Logical] · `predict-pod-restart`

> **A Pod's liveness probe fails 3 times. What happens? What does the restart count become? When does Kubernetes apply exponential backoff?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
The liveness probe failure threshold is configurable (`failureThreshold`, default 3). Once the threshold is crossed, the kubelet kills the container and restarts it. The pod itself is not recreated — only the container within the pod is restarted.

**What happens step by step:**
1. Liveness probe fires every `periodSeconds` (default 10s).
2. After `failureThreshold` consecutive failures (default 3), kubelet sends SIGTERM to the container.
3. Container is given `terminationGracePeriodSeconds` (default 30s) to exit cleanly, then SIGKILL.
4. Container is restarted (not the pod). The pod's `restartCount` increments by 1.
5. The pod's `status.phase` stays `Running` — the pod object is not replaced.

**Restart count:**
After the first liveness probe failure → restart → `restartCount: 1`.
If it keeps failing: `restartCount: 2, 3, 4...` continuing.
The restart count never resets (it counts cumulative restarts for the container's lifetime in this pod).

**Exponential backoff — when it applies:**
Backoff applies to CrashLoopBackOff, not to liveness probe restarts per se. The distinction:
- **Liveness probe failure:** kubelet kills and immediately restarts. No initial backoff.
- **CrashLoopBackOff:** if the container exits quickly (crashes before probes start), backoff applies: 10s → 20s → 40s → 80s → 160s → capped at 300s (5 minutes).

If the liveness probe triggers a restart and the container crashes again before liveness succeeds, the CrashLoopBackOff backoff kicks in. The `restartCount` is what triggers the backoff — not the probe failure count itself. The backoff counter resets if the container runs successfully for 10 minutes.

**The edge case:**
`failureThreshold: 1` with `periodSeconds: 10` means a single transient probe failure (brief GC pause, slow startup) immediately kills the container. This is why `failureThreshold: 3` and a `startupProbe` for slow-starting apps are best practices.

**How to think through this:**
1. Liveness probe → container restart. Not pod restart. Pod stays, container is killed and restarted.
2. CrashLoopBackOff backoff is triggered by rapid successive container crashes, not by probe failures themselves.
3. `restartCount` accumulates forever — use it to see how often a container has failed, but 0 doesn't mean healthy.

**Key takeaway:** After `failureThreshold` liveness probe failures, the container (not pod) is restarted and `restartCount` increments; CrashLoopBackOff exponential backoff (10s→300s) applies when the container crashes rapidly, not directly from probe failures.

</details>

📖 **Theory:** [predict-pod-restart](./14_Health_Probes/Theory.md#the-story-the-pod-that-lied)


---

### Q92 · [Logical] · `predict-service-routing`

> **A Service has 3 Pod endpoints. One Pod has its readiness probe failing. How many endpoints does kube-proxy route to? What happens to in-flight requests?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
When a pod's readiness probe fails, the Endpoints controller removes it from the `EndpointSlice` for that Service. kube-proxy watches `EndpointSlice` objects and updates its iptables/IPVS rules to reflect the change.

**Answer: kube-proxy routes to 2 endpoints.**

The timeline:
1. Pod 3's readiness probe fails `failureThreshold` times (default 3 failures, 30 seconds with default settings).
2. The `endpoints-controller` updates the `EndpointSlice` — Pod 3's IP is moved from `addresses` to `notReadyAddresses`.
3. kube-proxy (running on each node) receives the EndpointSlice update via its watch.
4. kube-proxy updates iptables rules (or IPVS table) — Pod 3's IP is removed from the load balancing set.
5. New connections are routed only to Pod 1 and Pod 2.

**What happens to in-flight requests:**
In-flight requests to Pod 3 that were accepted before the iptables update are **not interrupted**. kube-proxy only affects new connection establishment, not existing TCP connections. HTTP/1.1 long-lived connections or gRPC streams already established to Pod 3 continue until they complete or the pod terminates.

This creates a window where Pod 3 is "not ready" from the Service's perspective, but existing connections to it continue to be served. This is usually desirable — you don't want to hard-terminate active requests.

**The propagation gap:**
There is a delay between the readiness probe failing and iptables being updated:
- Probe failure detection: `periodSeconds * failureThreshold` (default 30s).
- Controller reconciliation: ~1-2 seconds.
- kube-proxy sync: up to `--iptables-sync-period` (default 30s, but usually faster via watch events).

During this window, some new connections may still be routed to the unhealthy pod. This is why `preStop` sleep is used during deployment — it allows time for this propagation before the pod begins shutting down.

**How to think through this:**
1. readiness probe failure → endpoint removal → iptables update. Each step has latency.
2. "How many endpoints" = 2 (the healthy ones), but this takes up to 30+ seconds to take full effect.
3. In-flight vs new connections: iptables changes affect new connection routing via NAT, not established sessions.

**Key takeaway:** A failing readiness probe removes the pod from EndpointSlice routing after `periodSeconds * failureThreshold` seconds, reducing active endpoints to 2; in-flight TCP connections to the unhealthy pod continue until completion because iptables only affects new connection NAT decisions.

</details>

📖 **Theory:** [predict-service-routing](./06_Services/Theory.md#see-which-pods-a-service-is-routing-to)


---

### Q93 · [Logical] · `predict-rolling-update`

> **A Deployment has 10 replicas with maxSurge=2, maxUnavailable=1. During a rolling update, what is the minimum and maximum number of pods running at any point?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Rolling update parameters define the bounds of the transition:
- `maxSurge: 2` — can create up to 2 extra pods above the desired replica count.
- `maxUnavailable: 1` — can have up to 1 pod unavailable (not ready) below the desired count.

**Calculations:**
- Desired replicas: 10
- Maximum pods (surge ceiling): 10 + 2 = **12 pods maximum**
- Minimum pods (unavailable floor): 10 - 1 = **9 pods minimum**

**Minimum = 9, Maximum = 12**

**Walking through a step of the update:**
1. Start: 10 old pods running.
2. Kubernetes creates 2 new pods (maxSurge=2) → 12 pods total (10 old + 2 new).
3. Once the 2 new pods pass readiness, Kubernetes terminates up to 1 old pod (maxUnavailable=1).
   - Wait — actually it can now terminate 3 old pods (2 new ready + 1 unavailable allowance):
   - 2 new ready pods replace 2 old pods + 1 unavailable allowance = can remove 3 old pods.
4. After removing 3 old: 7 old + 2 new = 9 running (minimum).
5. Create 2 more surge pods: 7 old + 4 new = 11 total.
6. Continue until all 10 are new version.

**The invariants:**
```
At all times:
  total pods ≤ desired + maxSurge    = 10 + 2 = 12
  ready pods ≥ desired - maxUnavailable = 10 - 1 = 9
```

**Practical implication:**
With `maxSurge=2, maxUnavailable=1`, the update proceeds in batches of 3 pod replacements (2 surge + 1 unavailable) — faster than `maxSurge=1, maxUnavailable=0` which replaces one at a time, but requires capacity for 12 pods at peak.

**How to think through this:**
1. Maximum = desired + maxSurge (simple addition).
2. Minimum = desired - maxUnavailable (simple subtraction).
3. The actual step size is maxSurge + maxUnavailable = 3 pods replaced per cycle — faster updates with higher values, but more temporary resource usage.

**Key takeaway:** With 10 replicas, maxSurge=2, maxUnavailable=1: minimum running = 9 (10-1), maximum running = 12 (10+2), with the update proceeding in batches of 3 pod replacements per cycle.

</details>

📖 **Theory:** [predict-rolling-update](./05_Deployments_and_ReplicaSets/Theory.md#rolling-update-strategy)


---

### Q94 · [Debug] · `debug-imagepullbackoff`

> **A Pod shows `ImagePullBackOff`. List 5 distinct causes and how you diagnose each one.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
`ImagePullBackOff` means the kubelet tried to pull the container image and failed. It backs off exponentially (10s → 20s → 40s → ...) between retries. `ErrImagePull` is the initial failure; `ImagePullBackOff` is the retry state.

```bash
# Start here
kubectl describe pod <pod-name> -n <namespace>
# Events section shows the exact error message from the container runtime
```

**Cause 1: Image does not exist (wrong tag or typo)**
```
Event: Failed to pull image "myapp:latestt": rpc error: ... manifest unknown
```
```bash
# Verify the image exists
docker pull myapp:latestt
# Or check registry directly
aws ecr describe-images --repository-name myapp --image-ids imageTag=latestt
```
Fix: correct the image tag in the Deployment spec. Never use `latest` in production — use immutable digest or explicit version tags.

**Cause 2: Private registry — missing or wrong imagePullSecret**
```
Event: Failed to pull image: unauthorized: authentication required
```
```bash
kubectl get pod <pod-name> -o yaml | grep -A3 imagePullSecrets
# Should reference a secret with registry credentials

kubectl get secret <pull-secret-name> -n <namespace>
# Should exist and be type: kubernetes.io/dockerconfigjson

# Test the credentials
kubectl create secret docker-registry test-pull \
  --docker-server=<registry> --docker-username=<user> --docker-password=<pass> \
  --dry-run=client -o yaml
```

**Cause 3: ECR token expired (AWS-specific)**
ECR tokens expire every 12 hours. If using static imagePullSecrets from ECR, they expire.
```bash
# Check secret age
kubectl get secret ecr-creds -n <namespace> -o yaml | grep creationTimestamp

# Solution: use ECR credential helper (eks-anywhere) or 
# amazon-ecr-credential-helper DaemonSet that rotates tokens automatically
```

**Cause 4: Registry rate limiting (Docker Hub)**
```
Event: toomanyrequests: You have reached your pull rate limit
```
Docker Hub limits anonymous pulls (100/6hr) and authenticated free tier (200/6hr).
```bash
# Check if pull is anonymous: pods without imagePullSecrets pull anonymously
# Fix: add Docker Hub credentials as imagePullSecret
# OR: mirror images to ECR/GCR/Artifact Registry
```

**Cause 5: Network connectivity — node cannot reach registry**
```
Event: Failed to pull image: dial tcp: i/o timeout
```
```bash
# SSH to the node where the pod is scheduled
ssh ec2-user@<node-ip>
curl -v https://registry-1.docker.io/v2/
# Should return 401 (auth required) — if timeout, networking issue

# Check: security group rules, NAT gateway, VPC endpoint for ECR
# For ECR in private VPC: need VPC endpoint for ecr.api and ecr.dkr
```

**How to think through this:**
1. The `kubectl describe pod` event message usually contains the exact error — read it carefully before guessing.
2. `unauthorized` = auth problem. `manifest unknown` = tag doesn't exist. `i/o timeout` = network problem.
3. ECR token expiration is the most common cause in AWS environments with static pull secrets.

**Key takeaway:** ImagePullBackOff is diagnosed via the exact error message in pod events: `unauthorized` means missing/wrong credentials, `manifest unknown` means wrong tag, `i/o timeout` means network/firewall issue, and `toomanyrequests` means rate limiting.

</details>

📖 **Theory:** [debug-imagepullbackoff](./04_Pods/Theory.md#module-04--pods)


---

### Q95 · [Debug] · `debug-pending-pod`

> **A Pod is stuck in Pending state. kubectl describe shows "0/3 nodes are available: 3 Insufficient memory". The nodes have plenty of memory. What else could cause this?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
"Insufficient memory" in the scheduler message means the scheduler's feasibility check failed for memory — but the reason may not be actual physical memory. The scheduler operates on **requested** resources, not actual usage.

**Cause 1: Requested memory exceeds available allocatable memory**
Nodes don't expose all their memory to pods. Kubernetes reserves memory for system processes (kubelet, OS) via `--kube-reserved` and `--system-reserved`. A 16GB node might only have 14GB allocatable.
```bash
kubectl describe node <node-name>
# Look for:
# Allocatable:
#   memory: 14Gi   ← this is what scheduler sees, not 16Gi
# Allocated resources:
#   memory 13.5Gi/14Gi   ← almost full from existing pods
```
The node has "plenty of memory" by `free -h`, but the sum of all pod memory *requests* already exceeds allocatable.

**Cause 2: Pod requests enormous memory (LimitRange default)**
A `LimitRange` with a `defaultRequest` may be injecting a large memory request automatically.
```bash
kubectl describe limitrange -n <namespace>
# If defaultRequest.memory: 8Gi and nodes only have 14Gi allocatable,
# every pod without explicit requests gets 8Gi request injected
```

**Cause 3: Node has taints the pod doesn't tolerate**
Taints don't show up in the "Insufficient memory" message directly, but if all 3 nodes are tainted:
```bash
kubectl describe node <node-name> | grep Taint
# Taint: dedicated=gpu-workload:NoSchedule
# Pod needs toleration for this taint
```

**Cause 4: Node affinity / nodeSelector mismatch**
```bash
kubectl describe pod <pod-name>
# Check: Node-Selectors, Tolerations, Affinity
# "0/3 nodes are available: 3 node(s) didn't match Pod's node affinity/selector"
# Sometimes combined messages appear
```

**Cause 5: ResourceQuota at namespace level is exhausted**
```bash
kubectl describe resourcequota -n <namespace>
# If requests.memory is at the quota limit, new pods can't be scheduled
# even if nodes have capacity
```

**Cause 6: DaemonSet pods consuming requests on each node**
DaemonSets run on every node and consume their requested resources. If a new DaemonSet with large memory requests was deployed, it reduces available allocatable memory on every node.
```bash
kubectl get daemonset -A
# Check recently added DaemonSets
kubectl describe node <node-name> | grep -A30 "Allocated resources"
```

**How to think through this:**
1. "Insufficient memory" = scheduled memory requests fill allocatable capacity, not physical RAM.
2. `kubectl describe node` → Allocatable and Allocated resources sections are the ground truth.
3. LimitRange injecting default requests is the sneaky cause — added by a platform team, invisible to developers.

**Key takeaway:** "Insufficient memory" means pod memory requests exceed node allocatable capacity (not physical RAM) — investigate ResourceQuota exhaustion, LimitRange injecting large defaults, node reservations, and DaemonSet requests consuming per-node allocatable.

</details>

📖 **Theory:** [debug-pending-pod](./27_Advanced_Scheduling/Theory.md#use-nodeselector-in-pod-spec)


---

### Q96 · [Debug] · `debug-oomkilled`

> **A container keeps restarting with exit code 137 (OOMKilled). The developer says "the app only uses 200MB". What do you investigate?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Exit code 137 = 128 + 9 (SIGKILL). The Linux kernel's OOM killer (or cgroup memory controller) sent SIGKILL because the container exceeded its memory limit. The developer's "200MB" measurement is almost certainly incomplete.

**Step 1: Check the actual limit set**
```bash
kubectl describe pod <pod-name> -n <namespace>
# Look for:
# Limits:
#   memory: 256Mi   ← if limit is 256Mi and app peaks at 300MB, this explains it
# Last State: Terminated
#   Reason: OOMKilled
#   Exit Code: 137
```

**Step 2: Check actual peak memory usage, not steady-state**
The developer measures steady-state memory. OOM kills happen at peak:
```bash
# If the pod is currently running (briefly before next crash)
kubectl top pod <pod-name> -n <namespace>

# Prometheus query for historical max (if available)
container_memory_working_set_bytes{pod="<pod>", container="<container>"}
```
Memory usage at startup (loading JVM, loading ML models, cache warming) is often 2-5x higher than steady-state.

**Step 3: Identify what "memory usage" means to the developer**
Developers often measure application heap (e.g., JVM `-Xmx200m`). The container's total memory includes:
- JVM heap (what developer measured)
- JVM non-heap (Metaspace, CodeCache, Direct Buffers): often 200-400MB for JVM apps
- OS page cache
- Shared libraries / native code
- Sidecar containers (if present)

```bash
# On a running pod, check actual process memory breakdown
kubectl exec <pod> -- cat /proc/self/status | grep -E "VmRSS|VmPeak|VmSize"
```

**Step 4: Check for memory leaks**
If the container runs for hours then OOMKills, it's a leak, not a limit misconfiguration:
```bash
# Track memory over time
kubectl top pod <pod> -n <namespace> --watch
```

**Step 5: Check JVM-specific issues (if Java app)**
JVM doesn't respect cgroup memory limits by default in older versions:
```bash
# Java < 8u191 ignores container memory limits
# Check Java version
kubectl exec <pod> -- java -version

# Solution: use -XX:MaxRAMPercentage=75.0 instead of -Xmx
# This sets heap to 75% of container memory limit
```

**Step 6: Check for forked processes (shell scripts)**
If the container entrypoint is a shell script that forks subprocesses, each subprocess has its own memory that counts toward the cgroup limit.

**How to think through this:**
1. Always ask: "200MB measured how, when, and of what?" Developer tools often miss JVM non-heap, native libs, and startup spikes.
2. Compare the limit in the pod spec to what you observe in `kubectl top` — if the limit is too close to steady-state, any spike kills it.
3. For JVM apps, set limits at 2x the expected heap + non-heap overhead, or use MaxRAMPercentage.

**Key takeaway:** OOMKilled exit 137 means the container hit its memory limit — investigate by comparing the limit to actual peak usage (not steady-state), checking JVM non-heap overhead, startup spikes, and whether the app is using cgroup-aware JVM flags.

</details>

📖 **Theory:** [debug-oomkilled](./19_Resource_Quotas_and_Limits/Theory.md#oomkilled-explained)


---

### Q97 · [Design] · `design-production-cluster`

> **Design a production-grade Kubernetes cluster architecture: number of control plane nodes, node groups, networking, storage, observability stack.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**Control Plane — HA topology:**
- 3 control plane nodes (odd number for etcd quorum). Never 2 — losing one of 2 loses quorum.
- Spread across 3 availability zones (one per AZ).
- Dedicated nodes — no workloads scheduled on control plane (taint: `node-role.kubernetes.io/control-plane:NoSchedule`).
- etcd co-located on control plane nodes for clusters up to ~500 nodes. External etcd cluster for larger scale.
- Control plane sits behind an NLB/ALB with health checks on `/healthz`.

**Node Groups:**
```
system          → DaemonSets, CoreDNS, metrics-server, cluster-autoscaler
                  m5.large x3, spot-ineligible
general         → Most application workloads
                  m5.xlarge to m5.4xlarge, mixed on-demand + spot
gpu             → ML inference/training
                  g4dn.xlarge, on-demand (spot for training)
memory-optimized → Caches, JVM-heavy apps
                  r5.2xlarge, on-demand
```
Karpenter manages general/GPU/memory pools. System pool is fixed size (Cluster Autoscaler or static).

**Networking:**
- VPC CNI (AWS) or Cilium — choose based on eBPF requirements and policy complexity.
- Pod CIDR: `/16` for pods (65536 IPs, sufficient for 500+ nodes with 100 pods each).
- Service CIDR: `/20` (4096 services).
- Private API server endpoint — kubectl access via bastion or VPN only.
- Network policies: default deny all, explicit allow per namespace.
- Calico or Cilium for network policy enforcement.
- Ingress: AWS ALB Ingress Controller or Envoy Gateway for L7 routing.

**Storage:**
- Default StorageClass: AWS EBS gp3 (better price/performance than gp2).
- `WaitForFirstConsumer` binding mode to avoid AZ cross-zone attachment failures.
- ReadWriteMany: EFS via AWS EFS CSI driver for shared storage.
- Velero for backup: daily snapshots of PVs + etcd backup to S3.

**Observability stack:**
```
Metrics:     Prometheus (Victoria Metrics for scale) → Grafana
Logging:     Fluent Bit DaemonSet → OpenSearch or CloudWatch Logs
Tracing:     OpenTelemetry Collector → Jaeger or Tempo
Alerting:    AlertManager → PagerDuty / Slack
Dashboards:  Grafana (cluster overview, per-namespace, per-team)
```

**Security baseline:**
- Pod Security Standards: `restricted` for application namespaces, `baseline` for infra.
- Kyverno or OPA Gatekeeper for policy enforcement.
- IRSA for all pod AWS API access — no static AWS credentials.
- Falco for runtime security monitoring.
- CIS Benchmark scanning via kube-bench.

**How to think through this:**
1. Start with the control plane: HA = 3 nodes across 3 AZs, always.
2. Node groups should map to workload characteristics, not team ownership.
3. Observability is not optional — Prometheus + Grafana + alerting from day 1.
4. "Production grade" means you can lose an AZ and keep running — design every layer for that.

**Key takeaway:** Production clusters need 3 control plane nodes across 3 AZs, workload-differentiated node groups, Prometheus/Grafana/alerting from day 1, EBS gp3 default storage with EFS for RWX, and security layered via PSS, IRSA, and network policies.

</details>

📖 **Theory:** [design-production-cluster](./28_Cluster_Management/Theory.md#module-28--cluster-management)


---

### Q98 · [Design] · `design-microservices-k8s`

> **You have 10 microservices that communicate with each other. Design the Service topology, namespace strategy, and network policies.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**Namespace strategy:**
Don't put all 10 services in one namespace — but also don't create a namespace per service. Group by domain boundary and environment:
```
payments-prod         → payment-api, payment-processor, payment-ledger
orders-prod           → order-api, order-fulfillment
catalog-prod          → catalog-api, catalog-search
shared-prod           → auth-service, notification-service, api-gateway
```
This reflects domain ownership (DDD bounded contexts) and maps to team RBAC boundaries.

**Service topology:**
Each microservice gets:
```yaml
# ClusterIP Service for internal service-to-service communication
kind: Service
metadata:
  name: payment-api
  namespace: payments-prod
spec:
  type: ClusterIP
  selector:
    app: payment-api
  ports:
    - port: 80
      targetPort: 8080
```

External-facing services get an additional Ingress/HTTPRoute pointing to their ClusterIP:
```
Internet → ALB → api-gateway (shared-prod) → payment-api (payments-prod)
                                            → order-api (orders-prod)
                                            → catalog-api (catalog-prod)
```
The API Gateway pattern centralizes authentication, rate limiting, and TLS termination.

**Service discovery:**
Services call each other using DNS:
```
payment-api calling order-api:
  http://order-api.orders-prod.svc.cluster.local/orders/{id}
  
# Within same namespace (payment namespace calling payment-processor):
  http://payment-processor/process
```

**Network Policies — layered approach:**

```yaml
# Layer 1: Default deny all in each namespace
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: payments-prod
spec:
  podSelector: {}
  policyTypes: ["Ingress", "Egress"]
---
# Layer 2: Allow DNS egress (required for all pods)
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: payments-prod
spec:
  podSelector: {}
  egress:
    - ports:
        - port: 53
          protocol: UDP
        - port: 53
          protocol: TCP
      to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
---
# Layer 3: Allow ingress from API Gateway
kind: NetworkPolicy
metadata:
  name: allow-from-gateway
  namespace: payments-prod
spec:
  podSelector:
    matchLabels:
      app: payment-api   # only the entry-point service
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: shared-prod
          podSelector:
            matchLabels:
              app: api-gateway
---
# Layer 4: Allow intra-domain communication
kind: NetworkPolicy
metadata:
  name: allow-intra-domain
  namespace: payments-prod
spec:
  podSelector: {}
  ingress:
    - from:
        - podSelector: {}   # any pod in payments-prod
  egress:
    - to:
        - podSelector: {}
---
# Layer 5: Allow specific cross-domain calls
# payment-processor needs to call notification-service in shared-prod
kind: NetworkPolicy
metadata:
  name: allow-to-notifications
  namespace: payments-prod
spec:
  podSelector:
    matchLabels:
      app: payment-processor
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: shared-prod
          podSelector:
            matchLabels:
              app: notification-service
      ports:
        - port: 80
```

**Service mesh consideration:**
For 10+ services with complex auth and observability requirements, add Istio or Linkerd:
- mTLS between all services automatically.
- Traffic policies (retries, circuit breaking) via VirtualService/DestinationRule.
- Distributed tracing via Jaeger without code changes.
- `AuthorizationPolicy` for service-to-service RBAC.

**How to think through this:**
1. Namespace per domain, not per service — 4 namespaces for 10 services is manageable.
2. Network policies are additive allow rules on top of default deny — model the actual call graph.
3. The API gateway namespace needs special ingress access grants from all domain namespaces.
4. Cross-namespace calls require NetworkPolicy on both sides: egress from caller, ingress to receiver.

**Key takeaway:** Group 10 microservices into domain namespaces with ClusterIP Services, an API Gateway entry point, default-deny NetworkPolicies with explicit cross-namespace allow rules for the actual call graph, and optionally a service mesh for mTLS and traffic management at scale.

</details>

📖 **Theory:** [design-microservices-k8s](./24_Service_Mesh/Theory.md#module-24--service-mesh)


---

### Q99 · [Critical] · `edge-case-headless-service`

> **What is a headless Service (clusterIP: None)? When does DNS return multiple A records instead of the VIP? How do StatefulSets use this?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A regular Kubernetes Service has a ClusterIP — a virtual IP that kube-proxy load balances across pod endpoints. A headless Service (`clusterIP: None`) has no VIP. CoreDNS handles it differently: instead of returning the single VIP, it returns multiple A records — one per ready pod endpoint.

**What DNS returns:**
```bash
# Regular ClusterIP Service: one A record → VIP
nslookup my-service.default.svc.cluster.local
# → 10.96.0.100 (the ClusterIP)

# Headless Service: multiple A records → pod IPs
nslookup my-headless-service.default.svc.cluster.local
# → 10.244.1.5
# → 10.244.2.7
# → 10.244.3.2
```
The client receives all IPs and chooses one (or all). This is DNS-based service discovery, not kube-proxy load balancing. The client library or application is responsible for load balancing.

**When to use headless Services:**
1. **StatefulSets** — primary use case (see below).
2. **Client-side load balancing** — gRPC, Cassandra drivers, Kafka clients that want all pod IPs to open multiple connections.
3. **Service discovery without load balancing** — Prometheus scraping each pod individually, not a load-balanced target.

**How StatefulSets use headless Services:**
StatefulSets require a headless Service (the `serviceName` field) to provide stable, individual DNS names per pod:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: cassandra
spec:
  clusterIP: None
  selector:
    app: cassandra
  ports:
    - port: 9042
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: cassandra
spec:
  serviceName: cassandra   # references the headless Service
  replicas: 3
```

This creates per-pod DNS records:
```
cassandra-0.cassandra.default.svc.cluster.local → 10.244.1.5
cassandra-1.cassandra.default.svc.cluster.local → 10.244.2.7
cassandra-2.cassandra.default.svc.cluster.local → 10.244.3.2
```

Format: `<pod-name>.<service-name>.<namespace>.svc.cluster.local`

This is how Cassandra nodes discover each other as seeds, how Kafka brokers register their listeners, and how etcd members form a cluster — they use their own stable DNS name as their advertised address.

**The subtlety — selector-less headless Service:**
A headless Service without a selector returns no A records from DNS. Used when you want to manually define endpoints (e.g., pointing to an external database):
```yaml
kind: Service
spec:
  clusterIP: None
  # no selector
# Paired with an Endpoints object pointing to external IPs
```

**How to think through this:**
1. Regular Service = VIP + kube-proxy load balancing. Headless = no VIP, DNS returns pod IPs directly.
2. The pod-specific DNS records (`pod-0.svc-name.ns.svc.cluster.local`) only exist for StatefulSets with a headless `serviceName`.
3. Deployments with headless Services get round-robin DNS records per pod, but those records use generated pod names that change on restart — not stable.

**Key takeaway:** A headless Service (clusterIP: None) causes CoreDNS to return individual pod IP A records instead of a VIP; StatefulSets use this to generate stable per-pod DNS names (`pod-0.svc.ns.svc.cluster.local`) that survive pod rescheduling and enable distributed system peer discovery.

</details>

📖 **Theory:** [edge-case-headless-service](./06_Services/Theory.md#headless-services)


---

### Q100 · [Critical] · `edge-case-termination`

> **A Pod receives SIGTERM but takes 45 seconds to shut down. The terminationGracePeriodSeconds is 30. What happens? How do you fix this without just increasing the timeout?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**What happens:**
1. Kubernetes sends SIGTERM to the container.
2. The `terminationGracePeriodSeconds` (30s) countdown begins simultaneously.
3. The application is still handling connections and taking 45 seconds to shut down cleanly.
4. At T=30s, Kubernetes sends **SIGKILL** — the container is forcefully terminated immediately.
5. In-flight requests being processed at T=30s are hard-killed: connections are dropped, transactions may be left incomplete, data may be corrupted if mid-write.
6. `restartCount` does not increment — the pod completed (Exit Code 137 for SIGKILL on termination).

This is the gap: the app needs 45 seconds to drain, but has a 30-second limit. Simply increasing `terminationGracePeriodSeconds` to 60 works but doesn't fix the root cause.

**Fix 1: Improve shutdown logic in the application**
The root cause is usually that the application is waiting on something it could handle faster:
- Not closing the HTTP listener immediately on SIGTERM (new requests still arriving).
- Waiting for a fixed sleep instead of checking connection drain status.
- Long-running batch operations that should be checkpointed, not completed.

The correct shutdown sequence:
```
SIGTERM received
  → Step 1: Stop accepting new requests (close listener)
  → Step 2: Wait for in-flight requests to complete (with a deadline)
  → Step 3: Close database connections
  → Step 4: Flush logs/metrics
  → Step 5: Exit 0
```
A well-implemented HTTP server should drain in 5-10 seconds, not 45.

**Fix 2: preStop hook to decouple from kube-proxy drain**
The `terminationGracePeriodSeconds` budget starts when the pod is marked for deletion — but the `preStop` hook runs before SIGTERM. Use `preStop` for Service endpoint drain, freeing the grace period for actual app shutdown:

```yaml
lifecycle:
  preStop:
    exec:
      command: ["sh", "-c", "sleep 10"]  # wait for kube-proxy to stop routing
terminationGracePeriodSeconds: 45        # now 45s for actual shutdown
```
But note: `preStop` time counts against `terminationGracePeriodSeconds` — total budget = preStop duration + app shutdown time.

**Fix 3: Reduce what needs to happen at shutdown**
If 45 seconds is spent on database connection cleanup, connection pooling should handle this more gracefully:
- Use connection pool max lifetime to naturally cycle connections before shutdown.
- Implement graceful drain via `/shutdown` endpoint that triggers pre-SIGTERM drain (used by `preStop` exec hook).

```yaml
lifecycle:
  preStop:
    httpGet:
      path: /admin/shutdown      # tell the app to stop accepting new work
      port: 8081
```

**Fix 4: If the 30s window is non-negotiable**
Some platforms cap `terminationGracePeriodSeconds`. In that case:
- Design the application for partial shutdown — in-flight requests use a deadline context.
- Use circuit breakers at the caller side to retry on connection failure.
- Accept that some requests will fail during shutdown and design the client for retry.

**The general principle — `terminationGracePeriodSeconds` sizing:**
```
terminationGracePeriodSeconds >= preStop duration + max(request processing time) + buffer
```
For a web API: preStop=5s + max request=10s + buffer=5s = 20s is typically sufficient.
For batch processors: preStop=0 + checkpoint time + buffer — often 60-120s is appropriate.

**How to think through this:**
1. SIGKILL at T=30s is not a bug — it is the designed behavior. The grace period is a hard limit.
2. "Just increase the timeout" fixes the symptom, not the cause. The real fix is faster shutdown logic.
3. The `preStop` hook is often conflated with shutdown — it's actually for pre-shutdown preparation (endpoint drain), not the shutdown itself.
4. Ask: what is the app doing for 45 seconds? Debug with `kubectl exec` or add shutdown logging to find the slow step.

**Key takeaway:** When `terminationGracePeriodSeconds` (30s) expires before the app shuts down (45s), SIGKILL is sent and in-flight requests are dropped — fix by improving application shutdown logic to drain connections faster rather than just raising the timeout, using `preStop` hooks for endpoint drain and deadline contexts for in-flight request bounds.

</details>

📖 **Theory:** [edge-case-termination](./04_Pods/Theory.md#module-04--pods)
