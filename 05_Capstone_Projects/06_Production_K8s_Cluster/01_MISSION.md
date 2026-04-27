# 06 — Production Kubernetes Cluster

**Difficulty:** 🔴 Build Yourself

---

## 🎯 The Mission

Running containers in Kubernetes is the easy part. Running them *responsibly*
is the hard part.

Think of a production Kubernetes cluster as a city with laws. Without laws:
anyone can build anywhere, consume unlimited power, and a single car fire can
take down the whole grid. With laws: zoning ordinances keep residential and
industrial separate, fuse boxes prevent one bad appliance from cutting power to
the whole block, and traffic lights keep cars from smashing into each other.

In this project, you are the city planner. You will implement access control,
resource governance, auto-scaling, observability, GitOps, and network security.
No hints. No answers. Just requirements and the tools to meet them.

---

## What You Will Build

A production-ready Kubernetes configuration covering nine areas:

1. **Namespaces** — `dev`, `staging`, `production`, `monitoring`, `argocd`
2. **RBAC** — developers deploy to `dev`, read-only in `staging`, no access to `production`
3. **Resource Quotas** — hard CPU/memory/pod limits per namespace
4. **HPA** — Horizontal Pod Autoscaler scales pods when CPU exceeds 70%
5. **Prometheus + Grafana** — metrics collection and dashboards via Helm
6. **ArgoCD** — GitOps: cluster state driven by a Git repo
7. **NetworkPolicies** — default-deny, then allowlist only required communication paths
8. **PodDisruptionBudget** — guarantee at least 1 pod survives node drain/maintenance
9. **Node Affinity** — production pods scheduled only on nodes labeled `env=production`

---

## Why This Matters

Each of these nine areas maps to a category of production incident:

| Area              | Incident it prevents                                        |
|-------------------|-------------------------------------------------------------|
| RBAC              | Developer accidentally deletes a production Secret         |
| Resource Quotas   | One runaway service starves the rest of the namespace      |
| HPA               | Traffic spike kills the app; manual scaling too slow        |
| Prometheus        | Nobody knows the cluster is unhealthy until users complain |
| ArgoCD            | "Works on my kubectl" — manual drift from desired state    |
| NetworkPolicy     | Compromised frontend pod reads the database directly       |
| PDB               | Node drain kills all pods simultaneously                   |
| Node Affinity     | Dev workload scheduled on production node, stealing resources |

---

## ## Skills Practiced

- **RBAC**: Roles, ClusterRoles, RoleBindings, ServiceAccounts
- **Resource Quotas** and LimitRanges
- **Horizontal Pod Autoscaler** (HPA v2 API)
- **Helm** chart deployment (kube-prometheus-stack)
- **ArgoCD** Application manifest and GitOps sync policy
- **NetworkPolicy** rules (default-deny + allowlist)
- **PodDisruptionBudget**
- **Node affinity** (required and preferred rules) and pod anti-affinity

---

## Prerequisites

| Tool     | Version | Notes                                        |
|----------|---------|----------------------------------------------|
| kubectl  | 1.28+   | Configured for your cluster                  |
| helm     | 3.14+   | Verify with `helm version`                   |
| minikube | 1.32+   | Or any cluster for node affinity tests       |
| git      | any     | For the ArgoCD GitOps repo                   |

Enable the metrics-server addon for HPA:

```bash
minikube addons enable metrics-server
```

---

## Folder Structure You Will Create

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
└── src/
    ├── starter.py
    └── solution.py
```

---

## This Is a "Build Yourself" Project

There are no collapsible hints or answers in `03_GUIDE.md`. The guide gives you
the steps and expected outputs; you write all the YAML.

Refer to the Kubernetes documentation and the concepts you have practiced in
earlier projects. The full reference implementations are in `src/solution.py`
as YAML embedded in docstrings.

---

⬅️ **Prev:** [05 — CI/CD Build Push Deploy](../05_CICD_Build_Push_Deploy/01_MISSION.md) &nbsp;&nbsp; ➡️ **Next:** [07 — JWT Auth API Docker](../../05_Capstone_Projects/README.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
