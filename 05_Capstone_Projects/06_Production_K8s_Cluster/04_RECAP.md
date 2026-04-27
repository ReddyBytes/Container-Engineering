# 06 — Recap: Production Kubernetes Cluster

---

## ## What You Built

You configured a Kubernetes cluster the way a real platform engineering team
would: with access control that keeps developers out of production, resource
limits that prevent any one service from consuming the whole cluster, automatic
scaling under load, complete observability through dashboards, GitOps-driven
deployments that cannot drift from the desired state, and network rules that
enforce least-privilege communication between services.

Each of the nine components addresses a real category of production incident.
Together they form a baseline that most organisations take months to implement
incrementally.

---

## ## Key Concepts Reinforced

### RBAC: least privilege by design

You did not give developers a restricted version of `cluster-admin`. You defined
exactly what they can do (deploy to `dev`) and exactly what they cannot
(anything in `production`). The default is deny. Permissions are additive.
This is the correct mental model for production RBAC.

### ResourceQuota + LimitRange work together

A ResourceQuota without a LimitRange has a gap: pods that do not declare
`resources:` are not counted against the quota. The LimitRange fills that gap
by injecting defaults. Always deploy both in the same namespace.

### HPA requires resource requests

The HPA calculates utilisation as `actual_cpu / requested_cpu`. If pods have
no CPU request, the denominator is undefined and HPA cannot scale. Setting
`requests.cpu` is not optional when you use HPA.

### ArgoCD selfHeal is a discipline, not just a feature

With `selfHeal: true`, manual `kubectl` changes are reverted within 3 minutes.
This sounds strict, but it enforces a discipline: all changes go through Git.
If you need to make an emergency change, you commit it. The history shows who
changed what, when, and why. Without selfHeal, manual changes accumulate as
undocumented drift.

### NetworkPolicy: default-deny is a mindset

The first policy you applied blocked everything. Then you built up the
allowlist from scratch. This forces you to think about communication paths
explicitly. Most clusters run with no NetworkPolicies at all — every pod
can reach every other pod. A compromised frontend pod in such a cluster can
query the database directly. Default-deny closes that attack surface.

---

## ## Component Summary

| Component          | File                               | What it does                            |
|--------------------|------------------------------------|------------------------------------------|
| Namespaces         | `k8s/namespaces.yaml`              | 5 isolated environments                  |
| RBAC               | `k8s/rbac/`                        | Least-privilege access per team          |
| ResourceQuota      | `k8s/quotas/resource-quotas.yaml`  | Hard CPU/memory/pod caps                 |
| LimitRange         | (same file)                        | Default requests for quota compliance    |
| HPA                | `k8s/autoscaling/hpa.yaml`         | Auto-scale on CPU utilisation            |
| Prometheus+Grafana | `helm/prometheus-values.yaml`      | Cluster-wide metrics and dashboards      |
| ArgoCD             | `k8s/argocd/application.yaml`      | Git-driven state reconciliation          |
| NetworkPolicy      | `k8s/policies/network-policies.yaml`| Default-deny + explicit allow paths     |
| PDB                | `k8s/policies/pod-disruption-budget.yaml` | Survive node drain           |
| Node Affinity      | `k8s/affinity/deployment-with-affinity.yaml` | Placement control        |

---

## ## Extend It

1. **Add taints and tolerations** — taint production nodes with
   `kubectl taint node <node> env=production:NoSchedule`. Add a matching
   toleration to the production deployment. Dev pods cannot land on
   production nodes even without affinity rules.

2. **Add Grafana alerts** — in the Grafana UI, create an alert that fires
   when any namespace's CPU usage exceeds 80% of its quota. Route it to a
   Slack webhook via AlertManager.

3. **Replace the static kubeconfig with IRSA** — on AWS EKS, use IAM Roles
   for Service Accounts so pods assume IAM roles directly. No long-lived
   credentials stored in Secrets.

4. **Add OPA/Gatekeeper policies** — install Gatekeeper and write a
   ConstraintTemplate that rejects any Deployment without resource limits.
   This enforces the LimitRange requirement at admission time.

5. **Simulate a GitOps round trip** — modify a Deployment YAML in your Git
   repo, push it, and watch ArgoCD apply the change automatically.
   Then run `kubectl delete deployment myapi -n production` and watch
   ArgoCD recreate it. That is `selfHeal` in action.

---

⬅️ **Prev:** [05 — CI/CD Build Push Deploy](../05_CICD_Build_Push_Deploy/01_MISSION.md) &nbsp;&nbsp; ➡️ **Next:** [07 — JWT Auth API Docker](../../05_Capstone_Projects/README.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
