# 06 — Guide: Production Kubernetes Cluster

This is a "Build Yourself" project. No hints, no answers here. Each step
describes what to build and what the expected output looks like. Write the YAML
yourself. Check your work against the expected outputs. Reference `src/solution.py`
only after you have made a genuine attempt.

---

## ## Step 1 — Create Namespaces

Create five namespaces in a single YAML file: `dev`, `staging`, `production`,
`monitoring`, `argocd`. Label each with `environment` or `purpose`.

```bash
kubectl apply -f k8s/namespaces.yaml
```

Expected:
```
namespace/dev created
namespace/staging created
namespace/production created
namespace/monitoring created
namespace/argocd created
```

Verify: `kubectl get namespaces`

---

## ## Step 2 — Apply RBAC

Create four files in `k8s/rbac/`:

- `serviceaccounts.yaml` — `developer-sa` in `dev`, `ops-sa` in `default`, `ci-sa` in `production`
- `roles.yaml` — `developer-role` (full deploy access, no Secrets) in `dev`; `staging-readonly` (get/list/watch only) in `staging`
- `clusterroles.yaml` — `ops-clusterrole` (full cluster access); `ci-readonly` (read pods/deployments/services)
- `bindings.yaml` — wire the above roles to the service accounts

```bash
kubectl apply -f k8s/rbac/
```

Verify a developer cannot deploy to production:

```bash
kubectl auth can-i create deployments \
  --namespace=production \
  --as=system:serviceaccount:dev:developer-sa
```

Expected: `no`

Verify a developer can deploy to dev:

```bash
kubectl auth can-i create deployments \
  --namespace=dev \
  --as=system:serviceaccount:dev:developer-sa
```

Expected: `yes`

---

## ## Step 3 — Apply Resource Quotas

Create `k8s/quotas/resource-quotas.yaml` with `ResourceQuota` objects for
`dev`, `staging`, and `production`. Add a `LimitRange` in `production` that
sets default CPU/memory requests and limits for pods that do not specify them.

```bash
kubectl apply -f k8s/quotas/resource-quotas.yaml
```

Verify:

```bash
kubectl describe resourcequota dev-quota -n dev
```

Expected: Hard limits for cpu, memory, pods are shown alongside `Used: 0`.

---

## ## Step 4 — Deploy the App and Enable HPA

Create a `Deployment` named `myapi` in `production` with 2 replicas and CPU
resource requests set (HPA requires requests to calculate utilisation).

Create `k8s/autoscaling/hpa.yaml` targeting `deployment/myapi`, min 2 replicas,
max 10, scale up when average CPU exceeds 70%.

```bash
kubectl apply -f k8s/affinity/deployment-with-affinity.yaml -n production
kubectl apply -f k8s/autoscaling/hpa.yaml -n production
kubectl get hpa -n production
```

Expected:
```
NAME       REFERENCE         TARGETS   MINPODS   MAXPODS   REPLICAS
myapi-hpa  Deployment/myapi  2%/70%    2         10        2
```

Simulate load (optional):

```bash
kubectl run load-gen --image=busybox -n production --rm -it -- \
  /bin/sh -c "while true; do wget -q -O- http://myapi-svc:8000/items; done"
```

Watch `kubectl get hpa -n production --watch` — replicas should increase.

---

## ## Step 5 — Install Prometheus and Grafana

Add the Prometheus community Helm repo and install `kube-prometheus-stack`.
Create `helm/prometheus-values.yaml` to set the Grafana admin password,
enable persistence, and configure retention.

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --values helm/prometheus-values.yaml \
  --wait
```

Check all pods are running:

```bash
kubectl get pods -n monitoring
```

Expected: Prometheus, Grafana, AlertManager, and node-exporter pods all `Running`.

Access Grafana:

```bash
kubectl port-forward service/monitoring-grafana 3000:80 -n monitoring
```

Open http://localhost:3000. Navigate to Dashboards → Kubernetes → Compute Resources.

---

## ## Step 6 — Install ArgoCD

Install ArgoCD from the upstream manifests. Wait for the server to be available.
Retrieve the initial admin password. Access the UI via port-forward.

```bash
kubectl apply -n argocd \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl wait --for=condition=available deployment/argocd-server -n argocd --timeout=3m
```

Get admin password:

```bash
kubectl get secret argocd-initial-admin-secret -n argocd \
  -o jsonpath='{.data.password}' | base64 -d
```

Port-forward and log in:

```bash
kubectl port-forward service/argocd-server 8080:443 -n argocd
```

Create `k8s/argocd/application.yaml` pointing ArgoCD at your Git repo. Set
`syncPolicy.automated.prune: true` and `selfHeal: true`.

```bash
kubectl apply -f k8s/argocd/application.yaml
```

Expected in the ArgoCD UI: application appears and syncs to `Synced / Healthy`.

---

## ## Step 7 — Apply NetworkPolicies

Create `k8s/policies/network-policies.yaml` with four policies:

1. `deny-all-default` — deny all ingress and egress for all pods in `production`
2. `allow-frontend-ingress` — allow frontend to receive from ingress-nginx; allow frontend to send to backend on port 8000
3. `allow-frontend-to-backend` — allow backend to receive from frontend; allow backend to connect to postgres on 5432
4. `allow-backend-to-db` — allow postgres to receive from backend on 5432

Remember: all pods need DNS egress (UDP port 53).

```bash
kubectl apply -f k8s/policies/network-policies.yaml -n production
kubectl get networkpolicies -n production
```

Test the deny rule works:

```bash
kubectl run test-pod --image=busybox -n production --rm -it -- \
  /bin/sh -c "nc -zv postgres 5432; echo exit: $?"
```

Expected: `Connection timed out` — the test pod is not labeled `app=backend`.

---

## ## Step 8 — Apply PodDisruptionBudget

Create `k8s/policies/pod-disruption-budget.yaml` for the `myapi` deployment
in `production`. Set `minAvailable: 1` so at least one pod survives node
drain operations.

```bash
kubectl apply -f k8s/policies/pod-disruption-budget.yaml -n production
kubectl get pdb -n production
```

Expected:
```
NAME       MIN AVAILABLE   MAX UNAVAILABLE   ALLOWED DISRUPTIONS
myapi-pdb  1               N/A               1
```

---

## ## Step 9 — Node Affinity

Label your minikube node:

```bash
kubectl label node minikube env=production tier=app
```

Create `k8s/affinity/deployment-with-affinity.yaml` with:
- `requiredDuringSchedulingIgnoredDuringExecution` matching `env=production`
- `preferredDuringSchedulingIgnoredDuringExecution` matching `tier=app`
- `podAntiAffinity` (preferred) spreading replicas across nodes by hostname

```bash
kubectl apply -f k8s/affinity/deployment-with-affinity.yaml -n production
kubectl get pods -n production -o wide
```

The `NODE` column should show the labeled node.

---

## ## Verify Everything

```bash
kubectl get all -n dev
kubectl get all -n staging
kubectl get all -n production
kubectl get all -n monitoring
kubectl get all -n argocd
kubectl get resourcequota --all-namespaces
kubectl get hpa --all-namespaces
kubectl get networkpolicies --all-namespaces
kubectl get pdb --all-namespaces
```

---

## ## Cleanup

```bash
kubectl delete namespace dev staging production monitoring argocd
helm uninstall monitoring -n monitoring
kubectl label node minikube env- tier-
```

---

⬅️ **Prev:** [05 — CI/CD Build Push Deploy](../05_CICD_Build_Push_Deploy/01_MISSION.md) &nbsp;&nbsp; ➡️ **Next:** [07 — JWT Auth API Docker](../../05_Capstone_Projects/README.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
