# Container Engineering — Topic Recap

> One-line summary of every module. Use this to quickly review what each section covers before diving deeper.

---

## 00 — Learning Guide

| Topic | Summary |
|---|---|
| How to Use This Repo | Navigation guide, file types, and recommended learning order |
| Learning Paths | Beginner / intermediate / advanced progression through Docker and Kubernetes |
| Progress Tracker | Personal checklist to mark completed modules |

---

## 01 — Docker

| Topic | Summary |
|---|---|
| Virtualization vs Containers | VMs vs containers — isolation tradeoffs, why containers won for app delivery |
| Docker Architecture | Daemon, client, registry — how Docker components talk to each other |
| Images & Layers | Union filesystem, copy-on-write, layer caching, image reuse |
| Dockerfile | FROM, RUN, COPY, CMD, ENTRYPOINT — building reproducible images |
| Container Lifecycle | docker run, start, stop, kill, rm — managing container state |
| Volumes & Bind Mounts | Persisting data outside containers, named volumes vs bind mounts |
| Networking | Bridge, host, overlay networks — container-to-container communication |
| Docker Compose | Multi-container apps, service definitions, depends_on, health checks |
| Registry & Pushing | docker push/pull, Docker Hub, ECR, private registries |
| Multi-Stage Builds | Smaller production images — build stage vs runtime stage pattern |
| Docker Security | Non-root users, read-only filesystems, secrets, image scanning |
| Docker Swarm | Native clustering, services, replicas, rolling updates |
| CI/CD with Docker | Build-tag-push pipeline, GitHub Actions, layer cache in CI |
| Best Practices | .dockerignore, minimal base images, one process per container |
| BuildKit | Advanced build features — cache mounts, secret mounts, parallel stages |
| Debugging Containers | docker exec, logs, inspect, nsenter, ephemeral debug containers |

---

## 02 — Kubernetes

| Topic | Summary |
|---|---|
| What is Kubernetes | Container orchestration — scheduling, healing, scaling at cluster level |
| Architecture | Control plane (API server, etcd, scheduler, controller manager) vs worker nodes |
| Installation | minikube, kind, kubeadm, managed clusters (EKS/GKE/AKS) |
| Pods | Smallest deployable unit — one or more containers sharing network and storage |
| Deployments | Declarative rollouts, replica sets, rolling updates, rollback |
| Services | ClusterIP, NodePort, LoadBalancer — stable endpoints for pods |
| ConfigMaps & Secrets | Externalizing config and credentials from container images |
| Namespaces | Logical isolation, resource quotas, multi-team cluster sharing |
| Ingress | HTTP routing, host/path rules, TLS termination, ingress controllers |
| Persistent Volumes | PV, PVC, StorageClass — decoupling storage from pod lifecycle |
| RBAC | Roles, ClusterRoles, bindings — who can do what in the cluster |
| Custom Resources | CRDs, operators — extending Kubernetes with domain-specific objects |
| DaemonSets | Run one pod per node — log collectors, monitoring agents |
| Health Probes | Liveness, readiness, startup probes — keeping pods healthy |
| Deployment Strategies | Rolling, blue-green, canary — zero-downtime release patterns |
| Jobs & CronJobs | One-off and scheduled batch tasks |
| Autoscaling | HPA, VPA, KEDA — scaling pods and nodes based on metrics |
| Resource Quotas | CPU/memory requests and limits, LimitRange, namespace quotas |
| Network Policies | Pod-level firewall rules — control ingress/egress between pods |
| Security | Pod security standards, seccomp, AppArmor, image signing |
| Service Mesh | Istio, Linkerd — mutual TLS, traffic management, observability |
| GitOps | ArgoCD, Flux — declarative cluster state from Git |
| Helm | Package manager for K8s — charts, values, templating, repositories |
| Advanced Scheduling | Taints/tolerations, node affinity, pod anti-affinity, priority classes |
| Cluster Management | Upgrade strategies, etcd backup, multi-cluster federation |
| Backup & DR | Velero, volume snapshots, disaster recovery runbooks |
| Cost Optimization | Right-sizing, spot nodes, Karpenter, cluster autoscaler |
| Gateway API | Next-gen Ingress — HTTPRoute, GRPCRoute, TCPRoute |
| KEDA | Event-driven autoscaling — scale to zero based on queue depth |
| Karpenter | Node provisioner — just-in-time node creation from any instance type |
| eBPF & Cilium | Kernel-level networking — Cilium CNI, network policy, Hubble observability |
| Ephemeral Containers | Debug running pods without restart using kubectl debug |
| Admission Policies | Validating/mutating webhooks, OPA Gatekeeper, Kyverno |
| Native Sidecars | Kubernetes 1.28+ sidecar containers — init container lifecycle change |

---

## 03 — Docker to Kubernetes

| Topic | Summary |
|---|---|
| Docker vs Kubernetes | When to use each — single host vs cluster, Compose vs manifests |
| Compose to K8s Migration | Kompose tool, mapping services/volumes/networks to K8s objects |
| Image to Deployment | Build image → push to registry → write Deployment → expose via Service |

---

## 04 — Projects

| Project | Summary |
|---|---|
| Dockerize a Python App | Write Dockerfile, build image, run container, handle env vars |
| Multi-Container App with Compose | Flask + Redis + Postgres wired together with docker-compose |
| Deploy to Kubernetes | Take Compose app, write K8s manifests, deploy to minikube |
| Full-Stack on K8s | Frontend + backend + database — Deployments, Services, Ingress, Secrets |
| CI/CD Build-Push-Deploy | GitHub Actions pipeline: build image → push ECR → kubectl rollout |
| Production K8s Cluster | HPA, PDB, resource limits, network policies, Helm chart packaging |

---

*Total modules: 4 · Last updated: 2026-04-21*
