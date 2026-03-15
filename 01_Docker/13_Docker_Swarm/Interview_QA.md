# Docker Swarm — Interview Q&A

---

## Beginner

**Q1: What is Docker Swarm and what problem does it solve?**

Docker Swarm is Docker's built-in container orchestration system. It solves the limitations of running containers on a single machine:

- **High availability**: If one machine goes down, containers restart on other machines automatically
- **Horizontal scaling**: Spread containers across multiple machines and scale with one command
- **Zero-downtime deployments**: Rolling updates replace old containers with new ones gradually
- **Unified management**: Manage many machines as if they were one

It's included with Docker — no separate installation needed.

---

**Q2: What is the difference between a manager node and a worker node in Swarm?**

**Manager nodes** are the control plane. They maintain cluster state (stored in a distributed Raft log), schedule services onto nodes, and expose the Swarm API. All `docker service` and `docker stack` commands talk to a manager. In production, you run an odd number of managers (1, 3, or 5) for Raft fault tolerance — with 3 managers, the cluster can survive 1 manager failure.

**Worker nodes** run containers (tasks) assigned to them by the scheduler. They report task status back to managers but don't participate in scheduling decisions or cluster state management.

---

**Q3: What is a Swarm service, and how is it different from running a container?**

A `docker run` command creates a single container on the local machine — it's a one-off operation with no self-healing or distribution.

A **service** describes a desired state: run this image, with N replicas, exposed on these ports, with this resource limit. Swarm continuously reconciles actual state with desired state. If a container dies, Swarm starts a replacement automatically. You describe what you want; Swarm makes it happen.

```bash
# Single container (unmanaged)
docker run -d nginx:1.25

# Service (Swarm manages it)
docker service create --name web --replicas 3 nginx:1.25
```

---

**Q4: What is a Swarm stack?**

A stack is a group of services deployed together using a Docker Compose file. It's the Swarm-native equivalent of `docker compose up` but executed across the entire cluster. The Compose file uses the same syntax with an additional `deploy` section for Swarm-specific settings like replica count and update strategy.

```bash
docker stack deploy -c docker-compose.yml my-app
```

---

**Q5: How do containers in different Swarm services communicate with each other?**

Through **overlay networks**. When you attach services to the same overlay network, they can reach each other by service name regardless of which physical nodes they're on. DNS resolution for service names is built into Swarm.

A web service calling the API service uses the hostname `api` — Swarm resolves it and load-balances across all `api` replicas, transparent to the caller.

---

## Intermediate

**Q6: How do rolling updates work in Docker Swarm?**

Swarm replaces replicas one at a time (or in batches) rather than all at once:

```bash
docker service update \
  --image my-app:v2.0.0 \
  --update-parallelism 1 \
  --update-delay 10s \
  --update-failure-action rollback \
  my-app
```

- `--update-parallelism 1`: update 1 replica at a time
- `--update-delay 10s`: wait 10 seconds between each replica update
- `--update-failure-action rollback`: if a new replica fails health checks, automatically roll back

With `order: start-first` in the Compose `update_config`, the new replica starts and becomes healthy before the old one is stopped — true zero-downtime updates.

---

**Q7: How does Swarm handle high availability for manager nodes?**

Swarm managers use the **Raft consensus algorithm** to maintain a consistent cluster state. To tolerate N manager failures, you need 2N+1 managers:

| Managers | Fault tolerance |
|----------|----------------|
| 1 | 0 (single point of failure) |
| 3 | 1 manager can fail |
| 5 | 2 managers can fail |
| 7 | 3 managers can fail |

Even numbers of managers are not recommended — a 4-manager cluster can only tolerate 1 failure, same as 3 managers. Use 3 for most setups, 5 for critical production.

---

**Q8: How are Swarm secrets more secure than environment variables?**

Swarm secrets are:
1. **Encrypted at rest** using AES-256-GCM in the Raft log
2. **Encrypted in transit** between manager and worker over TLS
3. **Mounted as files** at `/run/secrets/<name>` — not in environment variables visible in `docker inspect`
4. **Only distributed to tasks that need them** — Swarm only sends the secret to nodes running a service that declares it
5. **Revocable** — remove a secret and Swarm redeploys affected services without it

```bash
echo "password" | docker secret create db_pass -
docker service create --secret db_pass my-app
# Inside container: cat /run/secrets/db_pass → password
```

---

**Q9: What is the difference between `docker service scale` and updating the replica count in the Compose file?**

Both achieve the same end result but through different workflows:

```bash
# Imperative: directly tells Swarm to change the count
docker service scale web=5

# Declarative: update the Compose file, re-deploy the stack
# In docker-compose.yml, set replicas: 5
docker stack deploy -c docker-compose.yml my-app
```

In production, the declarative approach (Compose file in version control, `stack deploy`) is preferred — it's auditable, reviewable, and repeatable. The imperative `scale` command is useful for quick testing or emergency scaling.

---

**Q10: How would you drain a node for maintenance in Swarm?**

```bash
# 1. Drain the node — Swarm moves all tasks off it
docker node update --availability drain worker-1

# 2. Verify all tasks have moved to other nodes
docker service ps my-service

# 3. Do your maintenance (upgrades, reboots, etc.)

# 4. Re-activate the node
docker node update --availability active worker-1

# 5. Swarm may or may not rebalance tasks to this node automatically
# To force rebalancing:
docker service update --force my-service
```

---

## Advanced

**Q11: When would you choose Swarm over Kubernetes in a new project?**

Choose Swarm when:
- The team is small (1–5 engineers) and Kubernetes operational overhead is too high
- The application is relatively simple — a handful of services with basic scaling needs
- You want to deploy today with minimal infrastructure investment
- You're already comfortable with Docker Compose and want a natural upgrade
- You're running on-premises without a managed Kubernetes offering

Kubernetes becomes necessary when:
- You need autoscaling based on custom metrics
- You need fine-grained RBAC, network policies, and namespace isolation
- You have many teams with independent deployments (GitOps, ArgoCD)
- You need a service mesh for mTLS between services
- You're running 50+ microservices

Many teams successfully run Swarm in production. The common path is to start with Swarm and migrate to Kubernetes when specific features become blockers.

---

**Q12: How does Swarm's ingress routing mesh work?**

Swarm has a built-in routing mesh that means any node in the Swarm can accept incoming connections for a published port — even if that node isn't running the service:

```bash
docker service create --name web --replicas 3 --publish 80:80 nginx
```

A request to port 80 on any node (manager or worker) is automatically routed to one of the 3 nginx replicas, wherever in the Swarm they happen to be running. This is implemented using iptables rules and IPVS (IP Virtual Server).

For production, you typically place a load balancer (Nginx, HAProxy, or a cloud LB) in front of all Swarm nodes. Each node can receive traffic, and the routing mesh distributes it internally.

---

**Q13: What are the limitations of Docker Swarm compared to Kubernetes that would cause you to migrate?**

1. **No Horizontal Pod Autoscaler** — Swarm cannot auto-scale services based on CPU/memory metrics; you scale manually or via external scripts
2. **No built-in ingress controller** — Swarm's routing mesh doesn't support hostname/path-based routing; you must add Traefik or Nginx separately
3. **No namespace isolation** — all stacks share the same namespace; in Kubernetes you get hard tenant isolation
4. **Limited storage orchestration** — Swarm's volume support is basic; Kubernetes has StorageClass, CSI drivers, dynamic provisioning
5. **No StatefulSet equivalent** — Swarm has no ordered, stable-identity deployment for databases or stateful apps
6. **No Custom Resource Definitions** — you can't extend the API for custom controllers/operators
7. **Smaller ecosystem** — most cloud-native tooling (ArgoCD, Flux, Istio, Keda) targets Kubernetes

---

## 📂 Navigation

| | Link |
|---|---|
| Previous | [12 · Docker Security](../12_Docker_Security/Interview_QA.md) |
| Theory | [Swarm Theory](./Theory.md) |
| Cheatsheet | [Swarm Cheatsheet](./Cheatsheet.md) |
| Code Examples | [Swarm Code Examples](./Code_Example.md) |
| Next | [14 · Docker in CI/CD](../14_Docker_in_CICD/Interview_QA.md) |
