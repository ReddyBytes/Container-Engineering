# Docker Compose vs Kubernetes — Full Comparison

## Feature-by-Feature Side-by-Side

| Feature | Docker Compose | Kubernetes |
|---|---|---|
| **Purpose** | Multi-container apps on one host | Container orchestration across many hosts |
| **Scale** | Single machine | Multi-node clusters (1 to thousands) |
| **Self-healing** | `restart: unless-stopped` (restarts crashes) | Automatically replaces failed Pods, on any node |
| **Horizontal scaling** | `docker compose scale web=3` (same host) | `kubectl scale deployment/web --replicas=3` (any nodes) |
| **Auto-scaling** | Not supported | HPA scales on CPU/memory/custom metrics |
| **Rolling updates** | Limited (`docker compose up` re-creates) | Deployment rollout: configurable parallelism, delay, failure action |
| **Zero-downtime deploys** | Not guaranteed | Built-in with `RollingUpdate` strategy |
| **Rollback** | Manual — change image tag, re-up | `kubectl rollout undo deployment/web` |
| **Load balancing** | None (single host, all containers share ports) | Service load-balancing across Pod replicas |
| **Service discovery** | Service name as hostname within Compose network | Service name as DNS within namespace |
| **Health checks** | `healthcheck:` block, affects `depends_on` | `readinessProbe`, `livenessProbe`, `startupProbe` |
| **Node failure** | No recovery — containers stay dead | Re-schedules Pods to healthy nodes automatically |
| **Networking** | Bridge network, optional overlay | Flat pod network, Services, Ingress, NetworkPolicy |
| **HTTP routing (Ingress)** | Not supported natively | Ingress controllers (nginx, traefik) with host/path routing |
| **TLS termination** | Not built in | cert-manager + Ingress TLS |
| **Storage** | Named volumes, bind mounts | PersistentVolumeClaim, StorageClass, CSI drivers |
| **Dynamic storage provisioning** | No | Yes — PVCs automatically provision storage |
| **Secrets** | Environment variables or files | K8s Secrets (base64 encoded, RBAC controlled) |
| **ConfigMaps** | Not a concept — use env_file | ConfigMap mounted as env vars or volume files |
| **Multi-tenancy** | No isolation between apps | Namespaces with RBAC |
| **RBAC** | No access control | Full RBAC: Roles, ClusterRoles, RoleBindings |
| **Namespaces** | Not supported | Full namespace isolation |
| **Init containers** | `depends_on` with condition | `initContainers`: ordered, must complete before main |
| **Sidecar containers** | Multiple services in one compose file | Sidecar pattern within a single Pod |
| **Daemon-style workloads** | Not supported | DaemonSet: one Pod per node |
| **Stateful workloads** | Manual | StatefulSet: ordered startup, stable network identity, stable storage |
| **Batch jobs** | Not supported | Job (run once), CronJob (scheduled) |
| **Custom resources** | No | CRDs: extend the K8s API |
| **Operators** | No | Operators: automate complex stateful applications |
| **Service mesh** | No | Istio, Linkerd: mTLS, traffic control, observability |
| **Monitoring integration** | None built in | Prometheus annotations, kube-state-metrics, metrics-server |
| **Log aggregation** | `docker compose logs` | kubectl logs; integrates with EFK/Loki/CloudWatch |
| **GitOps** | Not applicable | ArgoCD, Flux: git-driven reconciliation |
| **Helm packages** | docker-compose.yml per app | Helm charts: reusable, parameterized app packages |
| **Multi-cloud portability** | Single machine only | Runs on any K8s cluster (EKS, GKE, AKS, on-prem) |
| **Learning curve** | Low — 30 min to productive | High — weeks to months for full fluency |
| **Operational overhead** | Minimal | Significant (managed K8s reduces it) |
| **Local development** | Excellent | Possible with minikube/kind, but heavier |
| **Config format** | `docker-compose.yml` (single file) | Multiple YAML manifests or Helm charts |
| **Deployment tool** | `docker compose up -d` | `kubectl apply -f`, Helm, ArgoCD |

---

## When Each Tool Wins

### Docker Compose Wins When:
- Single-server deployments
- Local development environment
- Small teams with simple applications
- Internal tools where high availability isn't critical
- Projects where Kubernetes learning curve is not justified
- Rapid prototyping

### Kubernetes Wins When:
- Multi-server deployments for scale or availability
- High availability requirements (no single point of failure)
- Auto-scaling based on load
- Multiple teams deploying to shared infrastructure
- Complex microservice architectures
- Production workloads that cannot afford downtime
- Compliance requirements needing namespace isolation and RBAC

---

## Concept Mapping Table

| Docker Compose | Kubernetes |
|---|---|
| `services:` | Deployment + Service |
| `image:` | `spec.containers[].image` |
| `ports:` | Service spec (NodePort/LoadBalancer) |
| `environment:` | ConfigMap or Secret (env vars) |
| `volumes:` | PersistentVolumeClaim |
| `networks:` | K8s Service + optional NetworkPolicy |
| `depends_on:` | `initContainers` or readinessProbe |
| `replicas:` | `spec.replicas` in Deployment |
| `restart:` | Pod `restartPolicy` |
| `healthcheck:` | `livenessProbe` / `readinessProbe` |
| `deploy.resources.limits` | `resources.limits` in container spec |
| `secrets:` | K8s Secret mounted as volume |
| `.env` file | ConfigMap |

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Docker vs K8s Theory](./Theory.md) |
| Interview Q&A | [Docker vs K8s Q&A](./Interview_QA.md) |
| Next | [02 · Compose to K8s Migration](../02_Compose_to_K8s_Migration/Theory.md) |
| Section Home | [Section 03 — Docker to K8s](../README.md) |
