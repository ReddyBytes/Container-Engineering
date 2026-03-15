# Project 06: Production Kubernetes Cluster

Everything you've built so far has been focused on getting things running. This project is about running things responsibly. Production Kubernetes means access control, automatic scaling, observability, disaster resilience, and a deployment process that doesn't require someone to remember the right kubectl commands at the right time.

By the end of this project, you'll have a cluster that behaves like a real production system: different teams have different levels of access, the app scales automatically under load, you can see what's happening through dashboards, and deployments happen through Git.

---

## What You'll Build

A production-ready Kubernetes configuration covering:

1. **Namespaces** — `dev`, `staging`, `production` for environment isolation
2. **RBAC** — Role-Based Access Control so developers can deploy to dev but not prod
3. **Resource Quotas** — hard limits on CPU and memory per namespace
4. **HPA** — Horizontal Pod Autoscaler scales pods up when CPU exceeds 70%
5. **Prometheus + Grafana** — metrics and dashboards via kube-prometheus-stack Helm chart
6. **ArgoCD** — GitOps: the cluster state is driven by a Git repo, not manual kubectl
7. **NetworkPolicies** — pods can only talk to the services they're supposed to
8. **PodDisruptionBudget** — Kubernetes won't evict all your pods at once during maintenance
9. **Node Affinity** — production pods run on nodes labeled for production

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                         │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  namespace  │  │  namespace  │  │     namespace       │ │
│  │    dev      │  │  staging    │  │    production       │ │
│  │             │  │             │  │                     │ │
│  │  developers │  │  developers │  │  ops team only      │ │
│  │  can deploy │  │  read-only  │  │  + ArgoCD           │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  monitoring namespace                                │    │
│  │  Prometheus + Grafana (kube-prometheus-stack)       │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  argocd namespace                                   │    │
│  │  ArgoCD — syncs manifests from Git repo             │    │
│  └─────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

**GitOps flow with ArgoCD:**

```
Developer pushes YAML → GitHub repo
        │
        ▼
   ArgoCD detects change (~3 minutes)
        │
        ▼
   kubectl apply (ArgoCD applies to cluster)
        │
        ▼
   Cluster matches Git repo state
```

---

## Skills Practiced

- RBAC: Roles, ClusterRoles, RoleBindings, ServiceAccounts
- Resource Quotas and LimitRanges
- Horizontal Pod Autoscaler (HPA)
- Helm chart deployment (kube-prometheus-stack)
- ArgoCD Application manifest
- NetworkPolicy rules
- PodDisruptionBudget
- Node affinity and taints/tolerations

---

## Prerequisites

| Tool      | Version | Notes                                       |
|-----------|---------|---------------------------------------------|
| kubectl   | 1.28+   | Configured for your cluster                 |
| helm      | 3.14+   | `helm version`                              |
| minikube  | 1.32+   | Or any 3-node cluster for node affinity     |
| git       | any     | For the ArgoCD GitOps repo                  |

For HPA to work, you need the Metrics Server installed:

```bash
minikube addons enable metrics-server
```

---

## Folder Structure

```
06_Production_K8s_Cluster/
├── k8s/
│   ├── namespaces.yaml
│   ├── rbac/
│   │   ├── serviceaccounts.yaml
│   │   ├── roles.yaml
│   │   ├── clusterroles.yaml
│   │   └── bindings.yaml
│   ├── quotas/
│   │   └── resource-quotas.yaml
│   ├── autoscaling/
│   │   └── hpa.yaml
│   ├── policies/
│   │   ├── network-policies.yaml
│   │   └── pod-disruption-budget.yaml
│   ├── affinity/
│   │   └── deployment-with-affinity.yaml
│   └── argocd/
│       └── application.yaml
├── helm/
│   └── prometheus-values.yaml
├── Project_Guide.md
├── Step_by_Step.md
└── Code_Example.md
```

---

## What You'll Build — Step Summary

1. Create namespaces (`dev`, `staging`, `production`, `monitoring`, `argocd`)
2. Create RBAC: ServiceAccounts, Roles, RoleBindings
3. Apply ResourceQuotas to each namespace
4. Deploy the app and configure HPA
5. Install Prometheus + Grafana via Helm
6. Install ArgoCD and create an Application manifest
7. Apply NetworkPolicies
8. Apply PodDisruptionBudget
9. Label nodes and apply node affinity rules
10. Verify each component is working

---

## 📂 Navigation

| | |
|---|---|
| Next | [Step_by_Step.md](./Step_by_Step.md) |
| Code | [Code_Example.md](./Code_Example.md) |
| All Projects | [04_Projects/](../) |
