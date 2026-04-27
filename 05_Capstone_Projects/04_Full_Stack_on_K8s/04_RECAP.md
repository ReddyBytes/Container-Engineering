# 04 — Recap: Full-Stack App on Kubernetes

---

## ## What You Built

You deployed a complete three-tier web application on Kubernetes — a React
frontend, a FastAPI backend, and a PostgreSQL database — wired together with
Services, Secrets, ConfigMaps, and an Ingress that routes traffic by URL path.

More importantly, you treated each tier as an independent deployable unit.
You updated the backend without touching the frontend or database. That
independence is the whole point of microservices on Kubernetes.

---

## ## Key Concepts Reinforced

### Namespace isolation

All resources in `fullstack` are invisible to workloads in other namespaces.
If you deploy a second project to `myproject`, its pods cannot accidentally
reach `postgres.fullstack.svc.cluster.local` — the DNS only resolves within
the same namespace.

### StatefulSet and PVC lifecycle

When you delete a Namespace, the PVC is deleted too. But if you scale down the
StatefulSet to zero and back to one, the same PVC is reattached — postgres-0
sees its existing data. This is the "stable storage" guarantee that makes
StatefulSets suitable for databases.

### Ingress path rewriting

The annotation `nginx.ingress.kubernetes.io/rewrite-target: /$2` uses a regex
capture group from the path rule `(/|$)(.*)`. The second capture group `$2`
strips everything up to and including `/api/`. The backend never knows it was
accessed through a proxy.

### ConfigMap vs Secret

ConfigMap is for non-sensitive configuration: hostnames, ports, log levels.
Secret is for credentials: usernames, passwords, tokens. Both arrive in
the container as environment variables; the difference is that Secrets are
base64-encoded at rest in etcd and can be restricted with RBAC.

---

## ## Step Summary

| Step | What you did                             | Key resource                  |
|------|------------------------------------------|-------------------------------|
| 1    | Started minikube, enabled Ingress addon  | `minikube addons enable`      |
| 2    | Built and loaded Docker images           | `docker build`, `minikube image load` |
| 3    | Created the `fullstack` namespace        | `Namespace`                   |
| 4    | Deployed PostgreSQL with durable storage | `StatefulSet` + `PVC`         |
| 5    | Deployed the backend API                 | `Deployment` + `ConfigMap` + `Secret` |
| 6    | Deployed the frontend                    | `Deployment` + `Service`      |
| 7    | Configured path-based routing            | `Ingress`                     |
| 8    | Tested the full stack end-to-end         | `curl`, browser               |
| 9    | Updated one service independently        | `kubectl set image`           |

---

## ## Extend It

Once the base project is working, try these to deepen your understanding:

1. **Add TLS** — generate a self-signed cert, create a TLS Secret, and add
   `tls:` to the Ingress spec. Access the app over `https://app.local`.

2. **Add a second replica to PostgreSQL** — change the StatefulSet to
   `replicas: 2` and observe that `postgres-1` gets its own PVC. Note that
   this creates two independent databases, not replication — real HA needs
   a Postgres operator.

3. **Add resource limits to all containers** — set `requests` and `limits`
   for CPU and memory. Then run `kubectl top pods` and see actual usage vs limits.

4. **Break the readiness probe intentionally** — change the health endpoint to
   return 503. Watch Kubernetes stop routing traffic to that pod. Then fix it
   and watch traffic resume automatically.

5. **Replace hardcoded Secret values** — look into `external-secrets-operator`
   or `sealed-secrets` for managing secrets in Git safely.

---

⬅️ **Prev:** [03 — Deploy App to Kubernetes](../03_Deploy_App_to_Kubernetes/03_GUIDE.md) &nbsp;&nbsp; ➡️ **Next:** [05 — CI/CD Build Push Deploy](../05_CICD_Build_Push_Deploy/01_MISSION.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
