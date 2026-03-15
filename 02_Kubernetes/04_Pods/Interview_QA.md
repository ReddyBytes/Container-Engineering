# Module 04 — Interview Q&A: Pods

---

**Q1: What is a Pod in Kubernetes?**

A Pod is the smallest deployable unit in Kubernetes — it is a wrapper around one or more
containers that share the same network namespace (IP address and port space) and can share
storage volumes. Containers within a Pod communicate via localhost and are always co-scheduled
on the same node. Pods are ephemeral: when a Pod dies, it is not replaced unless a higher-level
controller (like a Deployment or ReplicaSet) manages it.

---

**Q2: Why does Kubernetes use Pods instead of directly scheduling containers?**

Some applications consist of tightly coupled processes that need to share resources directly —
the same network interface, the same file system paths. Rather than building complex inter-process
communication into the container model, Kubernetes wraps these processes in a Pod that gives them
a shared context. This allows patterns like sidecars (a helper container augmenting the main app)
and adapters (a container transforming output) without modifying the main application.

---

**Q3: What are the phases of a Pod's lifecycle?**

A Pod can be in one of five phases:
- **Pending**: accepted by the cluster but not yet running — waiting for scheduling or image pull
- **Running**: the Pod has been bound to a node and at least one container is running
- **Succeeded**: all containers have exited with status 0 (typical for batch Jobs)
- **Failed**: all containers have exited and at least one exited with non-zero status
- **Unknown**: the Pod's state cannot be determined (usually a node communication problem)

Each container within the Pod also has its own state: Waiting, Running, or Terminated.

---

**Q4: What is the difference between a Pod's Liveness and Readiness probes?**

- **Liveness probe**: answers "is this container alive?" If it fails, kubelet restarts the
  container. Use this to detect processes that are running but stuck (e.g., deadlocked).
- **Readiness probe**: answers "should this container receive traffic?" If it fails, the Pod
  is removed from the Service's endpoints (traffic stops going to it) but the container is NOT
  restarted. Use this for apps that need warm-up time or depend on external resources.

A common mistake is configuring only liveness — this can cause traffic to reach containers that
aren't ready to serve requests. Always configure readiness for services that receive traffic.

---

**Q5: What are the three multi-container Pod patterns?**

- **Sidecar**: a helper container that extends or enhances the main container without modifying
  it. Example: a log shipping container that reads the app's log files and forwards them.
- **Ambassador**: a proxy container that handles external communication on behalf of the main
  container. Example: a Redis proxy that handles connection pooling while the app uses localhost.
- **Adapter**: transforms the main container's output into a format expected by external systems.
  Example: a container that converts proprietary metrics to Prometheus format.

---

**Q6: What is the difference between resource requests and resource limits?**

**Requests** are the minimum resources guaranteed to the container. The Kubernetes scheduler uses
requests to find a node with sufficient available resources — a Pod will only be scheduled on a
node that can satisfy all its requests. Requests do not cap usage.

**Limits** are the maximum resources the container can use. For memory, exceeding the limit causes
an OOMKill (container is restarted). For CPU, exceeding the limit causes throttling (the container
slows down but is not killed).

Best practice: always set both. Without requests, the scheduler makes poor decisions. Without
limits, a misbehaving container can starve other Pods on the same node.

---

**Q7: What is a CrashLoopBackOff status?**

CrashLoopBackOff means the container is repeatedly crashing and Kubernetes is adding increasingly
longer delays between restart attempts (exponential backoff: 10s, 20s, 40s, up to 5 minutes).
It is not a failure state in itself — it's Kubernetes trying to recover while being careful not
to spam restarts.

Common causes:
- Application bug causing immediate crash on startup
- Missing environment variable or configuration the app needs
- Insufficient resources (OOMKilled on startup)
- Application can't connect to a required dependency

Diagnose with: `kubectl describe pod <name>` (check Exit Code in container state) and
`kubectl logs <name> --previous` (logs from the previous crashed instance).

---

**Q8: Why should you usually use a Deployment instead of creating Pods directly?**

A bare Pod has no self-healing. If it crashes, it stays dead. If the node it runs on dies, the
Pod is gone. If you want to update the container image, you have to delete and recreate manually.

A Deployment adds:
- ReplicaSet management — maintains N healthy copies automatically
- Rolling updates — deploy new versions gradually with zero downtime
- Rollback — revert to any previous version with one command
- Revision history — track what was deployed when

Almost all stateless application workloads should use Deployments, not bare Pods.

---

**Q9: What is a static pod?**

A static pod is defined by a YAML file placed in a local directory on the node
(typically `/etc/kubernetes/manifests/`). kubelet watches this directory and runs the pods
directly, without the API server being involved in scheduling. Static pods always have the node
name appended to their name. The Kubernetes control plane components themselves (kube-apiserver,
etcd, kube-scheduler, kube-controller-manager) run as static pods in kubeadm-managed clusters.

---

**Q10: How do containers in the same Pod communicate with each other?**

They communicate via localhost. Because all containers in a Pod share the same network namespace
(the same IP address and loopback interface), container A can reach container B at `localhost:PORT`
where PORT is the port container B is listening on. They can also share data through volumes
mounted at the same path in each container.

---

**Q11: What happens to a Pod when its node fails?**

The node goes into `NotReady` state. After the pod eviction timeout (default 5 minutes), the
node controller marks the Pod for eviction. If the Pod was created by a Deployment or ReplicaSet,
the respective controller creates a new Pod on a healthy node. The original Pod object may linger
in `Terminating` state until the node comes back (or you force-delete it). A bare Pod (not managed
by a controller) is simply lost.

---

**Q12: What is a Pod's restart policy and what are the options?**

`spec.restartPolicy` controls what happens when a container in a Pod exits:
- `Always` (default): restart the container every time it exits, regardless of exit code.
  Use for long-running services.
- `OnFailure`: restart only if the container exits with a non-zero code. Use for batch Jobs
  that should retry on failure but not restart after success.
- `Never`: never restart. The container runs once and stays in Terminated state.
  Use for one-shot tasks.

Note: restart policy applies to the entire Pod, not individual containers.

---

## Navigation

| File | Description |
|------|-------------|
| [Theory.md](./Theory.md) | Pods explained |
| [Cheatsheet.md](./Cheatsheet.md) | Quick reference commands |
| [Interview_QA.md](./Interview_QA.md) | You are here — interview questions |
| [Code_Example.md](./Code_Example.md) | Working YAML examples |

**Previous:** [03_Installation_and_Setup](../03_Installation_and_Setup/Interview_QA.md) |
**Next:** [05_Deployments_and_ReplicaSets](../05_Deployments_and_ReplicaSets/Theory.md)
