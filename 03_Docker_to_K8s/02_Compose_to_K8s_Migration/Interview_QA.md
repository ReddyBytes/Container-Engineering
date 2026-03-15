# Compose to Kubernetes Migration — Interview Q&A

---

## Beginner

**Q1: What is the main structural difference between docker-compose.yml and Kubernetes manifests?**

In Docker Compose, each `service:` entry is a single, self-contained definition that includes what to run (image), how to configure it (env vars), how to expose it (ports), and how to connect it to storage (volumes) — all in one block.

In Kubernetes, these concerns are split into separate objects:
- `Deployment` — what to run and how many replicas
- `Service` — how to reach the running containers
- `ConfigMap` — non-sensitive configuration
- `Secret` — sensitive values
- `PersistentVolumeClaim` — storage

This separation provides flexibility (change routing without changing the deployment, share a ConfigMap across multiple Deployments) but requires more YAML.

---

**Q2: What is Kompose and does docker-compose.yml translate directly to Kubernetes?**

Kompose is a tool that converts Docker Compose files to Kubernetes YAML manifests automatically:

```bash
kompose convert -f docker-compose.yml -o k8s/
```

It generates Deployments, Services, and PersistentVolumeClaims from your Compose file. It's a useful starting point — it saves the mechanical work of translation — but the output always needs review and cleanup before it's production-ready.

Docker Compose doesn't translate 1:1 to Kubernetes. Key differences:
- A Compose service becomes two K8s objects (Deployment + Service)
- `depends_on` has no direct equivalent — use init containers and readiness probes
- `build:` doesn't translate — images must be pre-built and in a registry
- Volumes require StorageClass configuration that doesn't exist in Compose
- Secrets require separate handling — not just `.env` files

---

**Q3: What does Kubernetes use instead of docker-compose's `depends_on`?**

Two mechanisms, depending on what you need:

**`readinessProbe`**: Kubernetes withholds traffic from a Pod until its readiness probe passes. If Service A depends on Service B being healthy, configure Service A with a readiness probe that checks its connection to Service B. Traffic won't route to Service A until it's actually ready.

**`initContainers`**: If you need the main container to not start at all until a condition is met (not just withhold traffic), use an init container. It runs to completion before the main container starts:

```yaml
initContainers:
  - name: wait-for-db
    image: busybox
    command: ['sh', '-c', 'until nc -z postgres 5432; do sleep 2; done']
```

---

**Q4: How do Kubernetes environment variables map from docker-compose.yml?**

In Compose:
```yaml
environment:
  LOG_LEVEL: info         # non-sensitive
  DB_PASSWORD: secret123  # sensitive
```

In Kubernetes, you split these:
```yaml
# ConfigMap for non-sensitive
envFrom:
  - configMapRef:
      name: app-config

# Secret for sensitive values
env:
  - name: DB_PASSWORD
    valueFrom:
      secretKeyRef:
        name: app-secrets
        key: DB_PASSWORD
```

The Compose `env_file:` equivalent is mounting a ConfigMap as environment variables using `envFrom`.

---

**Q5: What happens to named volumes from docker-compose.yml in Kubernetes?**

Named volumes become PersistentVolumeClaims (PVCs). A PVC requests storage from the cluster, and a StorageClass provisions it dynamically:

```yaml
# Compose
volumes:
  pgdata:

# Kubernetes PVC
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-data
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 10Gi
```

The PVC is then mounted in the Pod spec:
```yaml
volumeMounts:
  - name: postgres-data
    mountPath: /var/lib/postgresql/data
volumes:
  - name: postgres-data
    persistentVolumeClaim:
      claimName: postgres-data
```

---

## Intermediate

**Q6: What limitations of kompose's output should you always fix before using it in production?**

Kompose's output is a mechanical translation — it handles the basic structure but misses production concerns:

1. **No resource requests/limits**: Pods with no limits can starve other workloads. Always add `resources.requests` and `resources.limits`.
2. **No probes**: No readiness or liveness probes. Without them, K8s can't tell if your app is actually healthy.
3. **Secrets in ConfigMap**: Sensitive `environment:` values are put in ConfigMaps (unencrypted). Move them to Secrets.
4. **NodePort instead of Ingress**: Port mappings become NodePort Services. For HTTP routing, convert to Ingress.
5. **hostPath volumes or empty PVCs**: Storage may not match your cluster's StorageClass.
6. **No namespace**: Resources land in `default`. Create proper namespaces.
7. **No labels standard**: Add `app.kubernetes.io/name`, `app.kubernetes.io/version` for tooling compatibility.

---

**Q7: How does service networking work differently between Compose and Kubernetes?**

In Docker Compose, services communicate over a Docker bridge network. Each service name becomes a hostname resolvable by other containers on the same Compose project network.

In Kubernetes, each Pod has a unique IP, but these IPs change when Pods are replaced. Kubernetes Services provide stable network identities:
- A Service named `postgres` in namespace `my-app` is reachable at:
  - `postgres` (within the same namespace)
  - `postgres.my-app` (short form across namespaces)
  - `postgres.my-app.svc.cluster.local` (fully qualified)

The key difference: K8s services also load-balance across multiple Pod replicas. A Deployment with 3 replicas of `web` gets a single Service IP that round-robins requests across all 3 Pods.

---

**Q8: How do you handle environment variable migration, including secrets, from Compose to Kubernetes?**

The migration splits config into two types by sensitivity:

**Non-sensitive config → ConfigMap:**
```bash
kubectl create configmap app-config \
  --from-literal=LOG_LEVEL=info \
  --from-literal=PORT=3000
```

**Sensitive values → Secret:**
```bash
kubectl create secret generic app-secrets \
  --from-literal=DB_PASSWORD=supersecret \
  --from-literal=JWT_SECRET=abc123
```

**Reference both in Deployment:**
```yaml
envFrom:
  - configMapRef:
      name: app-config
  - secretRef:
      name: app-secrets
```

Never put secrets in ConfigMaps. Never commit Secret YAML with plain-text values to git — use External Secrets Operator, Sealed Secrets, or Vault for production.

---

**Q9: How do you migrate volumes from Docker Compose to Kubernetes?**

The migration has three parts:

**1. Declare the PVC** (replaces the named volume declaration):
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-data
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: standard
  resources:
    requests:
      storage: 10Gi
```

**2. Mount it in the Pod** (replaces the volume mount):
```yaml
volumes:
  - name: postgres-data
    persistentVolumeClaim:
      claimName: postgres-data
containers:
  - name: postgres
    volumeMounts:
      - name: postgres-data
        mountPath: /var/lib/postgresql/data
```

**3. Migrate the data**: Dump and restore existing data. For PostgreSQL:
```bash
docker exec postgres pg_dump -U myuser mydb > backup.sql
kubectl exec -i postgres-0 -- psql -U myuser mydb < backup.sql
```

---

**Q10: Walk through how a `depends_on: condition: service_healthy` pattern is replicated in Kubernetes.**

In Compose:
```yaml
web:
  depends_on:
    postgres:
      condition: service_healthy
```

In Kubernetes, use an init container that polls until postgres is ready:
```yaml
initContainers:
  - name: wait-for-postgres
    image: busybox:1.36
    command: ['sh', '-c', 'until nc -z postgres 5432; do echo waiting; sleep 2; done']
```

The init container runs to completion before the main `web` container starts. Once the main container starts, a readinessProbe ensures traffic isn't routed to `web` until it itself is healthy:

```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 3000
  initialDelaySeconds: 10
  periodSeconds: 5
```

This combination replicates the `depends_on` + `healthcheck` behavior more robustly because it handles not just startup order but also traffic routing.

---

## Advanced

**Q11: What does Kompose miss that you need to fix manually for full production readiness?**

Beyond resource limits, probes, and secrets, production Kubernetes requires additional work that Kompose never generates:

- **Pod Disruption Budgets**: Prevent all replicas from being removed during cluster upgrades.
- **Anti-affinity rules**: Stop all replicas landing on the same node. Node failure would take down everything.
  ```yaml
  affinity:
    podAntiAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
        - weight: 100
          podAffinityTerm:
            labelSelector:
              matchLabels:
                app: web
            topologyKey: kubernetes.io/hostname
  ```
- **Horizontal Pod Autoscaler**: Kompose doesn't generate HPA at all.
- **SecurityContext**: Run non-root, drop capabilities, set read-only root filesystem.
- **NetworkPolicy**: Kompose assumes a flat network. Production should restrict Pod-to-Pod communication.
- **ServiceAccount with minimal RBAC**: Kompose generates no RBAC configuration.
- **Ingress with TLS**: Port mappings become NodePort, not Ingress with TLS termination.

---

**Q12: How do you handle rolling updates during migration from Compose to Kubernetes?**

Rolling updates are one of the advantages gained in Kubernetes. Configure the rollout strategy in your Deployment:

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1          # Allow 1 extra Pod during update
    maxUnavailable: 0    # Never take a Pod down before a new one is ready
```

Ensure readiness probes gate traffic — new Pods only receive traffic after their probe succeeds.

For the initial Compose-to-K8s migration cutover:
1. Keep Compose running in production
2. Deploy the K8s version in staging and test thoroughly
3. Lower DNS TTL to 60 seconds 24 hours before cutover
4. Cut DNS over to the K8s LoadBalancer/Ingress IP
5. Keep Compose on standby for 24-48 hours as rollback
6. Decommission Compose once K8s is stable

The key risk is data: databases must migrate with zero data loss. Plan for a maintenance window or use database replication to minimize downtime.

---

**Q13: What is the strangler fig pattern and how does it apply to Compose-to-K8s migration?**

The strangler fig is a migration pattern where you gradually replace an old system by routing increasing traffic to the new system, until the old system is fully replaced — like a strangler fig vine that slowly envelops and replaces a host tree.

Applied to Compose-to-K8s migration:

**Phase 1**: Keep Compose running. Deploy K8s version behind a staging URL. Validate with real-world testing.

**Phase 2**: Use a load balancer to route 10% of traffic to K8s, 90% to Compose. Monitor error rates and latency.

**Phase 3**: Gradually shift to 50/50, then 90/10. Fix any issues under real traffic.

**Phase 4**: Route 100% to K8s. Keep Compose available as an emergency rollback for 48 hours.

**Phase 5**: Decommission the Compose deployment.

This is safer than a big-bang cutover because you can detect problems with partial traffic and roll back quickly. It works best for stateless services — stateful services need extra care around data consistency during the transition.

---

## 📂 Navigation

⬅️ **Prev:** [Docker vs Kubernetes](../01_Docker_vs_K8s/Interview_QA.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Image to Deployment Workflow](../03_Image_to_Deployment_Workflow/Theory.md)

| File | Description |
|---|---|
| [Theory.md](./Theory.md) | Compose to K8s Migration — full explanation |
| [Cheatsheet.md](./Cheatsheet.md) | Quick reference commands and mappings |
| [Interview_QA.md](./Interview_QA.md) | You are here — interview questions and answers |
