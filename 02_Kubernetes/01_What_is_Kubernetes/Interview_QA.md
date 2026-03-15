# Module 01 — Interview Q&A: What is Kubernetes?

---

**Q1: What is Kubernetes and what problem does it solve?**

Kubernetes is an open-source container orchestration platform. It solves the problem of running
containers reliably at scale — across multiple machines — without manual intervention. Before
Kubernetes, teams had to manually decide where to run each container, restart crashed containers,
balance load, and manage deployments. Kubernetes automates all of this. You declare what you want
(e.g., "5 replicas of this service"), and Kubernetes continuously ensures reality matches that
declaration.

---

**Q2: What is the difference between Docker and Kubernetes?**

Docker is a container runtime — it builds and runs individual containers on a single machine.
Kubernetes is a container orchestrator — it manages hundreds or thousands of containers across
many machines. They complement each other: Docker (or another runtime like containerd) runs
containers on each node, and Kubernetes decides which node to use, how many containers to run,
and what to do when things go wrong. A common analogy: Docker is a single shipping container;
Kubernetes is the cargo ship and port system that manages thousands of containers.

---

**Q3: Explain the declarative model in Kubernetes.**

In the declarative model, you describe the *desired state* of your system — not the steps to get
there. For example, "I want 3 replicas of my nginx container." Kubernetes compares this desired
state to the actual state of the cluster. If they differ, it takes action to reconcile them —
creating a pod, restarting a crashed container, or rescheduling work onto healthy nodes. This
reconciliation loop runs continuously, making the system self-healing without human intervention.

---

**Q4: What does "self-healing" mean in Kubernetes?**

Self-healing means Kubernetes automatically detects and recovers from failures. If a container
crashes, Kubernetes restarts it. If a node (server) fails, Kubernetes reschedules all the
containers that were running on it onto healthy nodes. If a container fails its health check
repeatedly, Kubernetes replaces it. All of this happens automatically, 24/7, without requiring
anyone to be paged.

---

**Q5: What is the origin of the name "Kubernetes" and why is it sometimes called K8s?**

Kubernetes comes from the Greek word for "helmsman" or "pilot" — the person who steers a ship.
The abbreviation K8s comes from replacing the 8 middle letters (ubernete) with the number 8.
This shorthand is common in tech (i18n for internationalization, a11y for accessibility).

---

**Q6: Who created Kubernetes and who maintains it now?**

Kubernetes was created by Joe Beda, Brendan Burns, and Craig McLuckie at Google, based on lessons
from Google's internal container system called Borg. It was open-sourced in 2014 and donated to
the Cloud Native Computing Foundation (CNCF) in 2016. Today it is maintained by a large community
of contributors from hundreds of companies.

---

**Q7: What are the main features of Kubernetes?**

The main features are:
- **Self-healing**: automatic restart and rescheduling of failed containers
- **Horizontal scaling**: automatically add or remove replicas based on load
- **Service discovery and load balancing**: stable DNS names and virtual IPs for groups of containers
- **Rolling updates and rollbacks**: deploy new versions gradually with zero downtime
- **Secret and config management**: inject passwords and configuration at runtime
- **Storage orchestration**: automatically mount cloud volumes, network storage, or local disks
- **Bin packing**: efficiently schedule containers based on resource requirements

---

**Q8: When would you NOT use Kubernetes?**

Kubernetes adds significant operational complexity. You should avoid it when:
- You have a small team (fewer than 3–4 engineers) without Kubernetes expertise
- Your application is simple (a single service or a few services)
- You are in early-stage development focused on product-market fit
- A managed PaaS (Heroku, Render, Fly.io) would meet your needs with less overhead
- The cost of learning and operating K8s outweighs the benefits

The right tool depends on your scale and team maturity.

---

**Q9: What is the CNCF and why does it matter for Kubernetes?**

The Cloud Native Computing Foundation (CNCF) is a vendor-neutral open-source foundation under
the Linux Foundation. Google donated Kubernetes to the CNCF in 2016 to ensure no single company
controlled it. The CNCF now hosts over 150 cloud-native projects, including Prometheus (monitoring),
Envoy (service proxy), Helm (package manager), and many others. CNCF governance means Kubernetes
evolves based on community consensus, not a single company's roadmap.

---

**Q10: What is the difference between imperative and declarative configuration?**

**Imperative** means issuing step-by-step commands:
`kubectl run nginx --image=nginx` — "run this container right now."

**Declarative** means defining desired state in a file and applying it:
`kubectl apply -f deployment.yaml` — "ensure the cluster matches this specification."

The declarative approach is preferred in production because it is reproducible (the YAML file is
the source of truth), version-controllable (store it in Git), and idempotent (applying the same
file twice has no additional effect).

---

**Q11: What is a Pod in Kubernetes at a high level?**

A Pod is the smallest deployable unit in Kubernetes — it wraps one or more containers that share
the same network namespace (same IP address and port space) and can share storage volumes. Pods
are typically created and managed by higher-level abstractions like Deployments, not directly.
Think of a Pod as a logical host for your container(s).

---

**Q12: How does Kubernetes handle application updates without downtime?**

Kubernetes uses a rolling update strategy by default. When you update a Deployment (e.g., change
the container image), Kubernetes gradually replaces old pods with new ones — creating a new pod,
waiting for it to become healthy, then removing an old pod, and repeating. At no point are all
old pods removed simultaneously. If the new version is unhealthy, you can run `kubectl rollout
undo` to revert to the previous version instantly.

---

## Navigation

| File | Description |
|------|-------------|
| [Theory.md](./Theory.md) | What is Kubernetes? Full explanation |
| [Cheatsheet.md](./Cheatsheet.md) | Quick reference commands |
| [Interview_QA.md](./Interview_QA.md) | You are here — interview questions |

**Previous:** [01_Docker](../../01_Docker/) |
**Next:** [02_K8s_Architecture](../02_K8s_Architecture/Theory.md)
