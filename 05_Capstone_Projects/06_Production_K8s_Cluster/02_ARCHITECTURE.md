# 06 — Architecture: Production Kubernetes Cluster

---

## ## The Big Picture

Think of a cluster with no governance as an open-plan office where everyone
shares one electrical circuit, no department has locked cabinets, any employee
can walk into the server room, and nobody monitors the power draw. One bad actor
— or one bad config — brings everything down.

This project adds the infrastructure that a real organisation needs before
trusting a cluster with production traffic.

---

## ## Cluster Layout

```
+-------------------------------------------------------------------+
|                    Kubernetes Cluster                              |
|                                                                   |
|  +-------------+  +-------------+  +------------------------+   |
|  | namespace   |  | namespace   |  | namespace              |   |
|  | dev         |  | staging     |  | production             |   |
|  |             |  |             |  |                        |   |
|  | developers  |  | developers  |  | ops + ArgoCD only      |   |
|  | can deploy  |  | read-only   |  | (RBAC enforced)        |   |
|  | ResourceQuota| ResourceQuota|  | ResourceQuota          |   |
|  +-------------+  +-------------+  | HPA + PDB              |   |
|                                     | NetworkPolicies        |   |
|                                     | Node Affinity          |   |
|                                     +------------------------+   |
|                                                                   |
|  +---------------------------------------------------------+      |
|  | namespace: monitoring                                    |      |
|  | Prometheus (metrics scrape)                             |      |
|  | Grafana (dashboards, alerts)                            |      |
|  | AlertManager (routing rules)                            |      |
|  +---------------------------------------------------------+      |
|                                                                   |
|  +---------------------------------------------------------+      |
|  | namespace: argocd                                        |      |
|  | ArgoCD server (GitOps controller)                       |      |
|  | Polls GitHub repo every 3 minutes                       |      |
|  | Applies diff: cluster state = git state                 |      |
|  +---------------------------------------------------------+      |
+-------------------------------------------------------------------+
```

---

## ## RBAC Model

```
ServiceAccount: developer-sa (namespace: dev)
  |
  +-- RoleBinding (dev namespace)  --> Role: developer-role
  |     verbs: get, list, watch, create, update, patch, delete
  |     resources: pods, services, deployments, configmaps, ...
  |
  +-- RoleBinding (staging namespace) --> Role: staging-readonly
        verbs: get, list, watch only

ServiceAccount: ops-sa (namespace: default)
  |
  +-- ClusterRoleBinding --> ClusterRole: ops-clusterrole
        verbs: * (all resources, all namespaces)

ServiceAccount: ci-sa (namespace: production)
  |
  +-- RoleBinding (production) --> ClusterRole: ci-readonly
        verbs: get, list, watch
        resources: pods, deployments, services
```

The key constraints:
- `developer-sa` cannot create/delete anything in `production` (no binding)
- `developer-sa` cannot read Secrets in any namespace (explicitly excluded)
- `ci-sa` can only read, never write (safe for CI pipelines checking rollout status)

---

## ## Resource Quota Strategy

```
Namespace      CPU request  CPU limit  Memory req  Memory limit  Pods
-----------    -----------  ---------  ----------  ------------  ----
dev            4            8          8Gi         16Gi          20
staging        8            16         16Gi        32Gi          30
production     16           32         32Gi        64Gi          50
```

A **LimitRange** in `production` sets default requests/limits for pods that
do not specify them. Without this, a pod with no resource spec would bypass
the ResourceQuota entirely (quota only counts against declared resources).

---

## ## HPA Scaling Behaviour

```
Normal load: CPU = 15%  -> 2 replicas (minReplicas)
             |
             | traffic spike
             v
Load: CPU = 95%  -> HPA calculates: ceil(2 * 95/70) = 3
             |    -> scales up by 2 pods (policy: max 2 per 60s)
             v
Load: CPU = 50%  -> 4 replicas (still above threshold, added 2 more)
             |
             | load drops
             v
Load: CPU = 10%  -> HPA wants to scale down
             |    -> stabilizationWindowSeconds: 300 (wait 5 min)
             |    -> then remove 1 pod per 60s
             v
Normal: CPU = 8%  -> back to 2 replicas
```

Scale-up is fast (30s stabilisation window). Scale-down is slow (5min window).
This prevents "flapping" where the HPA oscillates up and down under bursty load.

---

## ## GitOps Flow (ArgoCD)

```
Developer:
  1. Edits k8s/affinity/deployment-with-affinity.yaml
  2. git push origin main

GitHub repo updated
         |
         | ArgoCD polls every 3 minutes
         v
ArgoCD detects: cluster state != git state
         |
         | syncPolicy.automated = true
         v
ArgoCD runs: kubectl apply -f k8s/affinity/
         |
         | prune: true -> removes resources deleted from git
         | selfHeal: true -> reverts manual kubectl changes
         v
Cluster state = git state
```

The critical property: `selfHeal: true`. If someone runs `kubectl delete deployment myapi`
directly, ArgoCD recreates it within 3 minutes. Git is the source of truth.

---

## ## NetworkPolicy: Default-Deny + Allowlist

```
Without NetworkPolicy:
  Any pod  -->  any pod  (open by default in K8s)

After applying deny-all-default:
  Any pod  -X->  any pod  (all blocked)

After applying specific allow rules:
  frontend  -->  backend:8000   (allowed)
  backend   -->  postgres:5432  (allowed)
  *         -X-> postgres:5432  (blocked — not backend)
  frontend  <--  ingress-nginx  (allowed ingress)

DNS (UDP 53) is always allowed — pods need it to resolve service names
```

The order matters: apply the deny-all first, then build up the allowlist.
Testing the policy requires a test pod that is NOT labeled `app=backend`.
That pod should time out connecting to Postgres.

---

## ## Tech Stack

| Component      | Technology                              | K8s Object                    |
|----------------|-----------------------------------------|-------------------------------|
| Access control | RBAC                                    | Role, ClusterRole, RoleBinding|
| Resource limits| Quotas                                  | ResourceQuota, LimitRange     |
| Autoscaling    | HPA v2                                  | HorizontalPodAutoscaler       |
| Observability  | Prometheus + Grafana (Helm chart)       | Deployed via Helm             |
| GitOps         | ArgoCD                                  | Application CRD               |
| Network rules  | NetworkPolicy (calico/cilium CNI)       | NetworkPolicy                 |
| Resilience     | PodDisruptionBudget                     | PodDisruptionBudget           |
| Scheduling     | Node affinity + pod anti-affinity       | affinity block in Pod spec    |

---

⬅️ **Prev:** [05 — CI/CD Build Push Deploy](../05_CICD_Build_Push_Deploy/01_MISSION.md) &nbsp;&nbsp; ➡️ **Next:** [07 — JWT Auth API Docker](../../05_Capstone_Projects/README.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
