# Step-by-Step: Production Kubernetes Cluster

Build up each component one at a time, verifying each piece before adding the next.

---

## Step 1 — Create Namespaces

```bash
kubectl apply -f k8s/namespaces.yaml
```

**Expected:**
```
namespace/dev created
namespace/staging created
namespace/production created
namespace/monitoring created
namespace/argocd created
```

Verify:

```bash
kubectl get namespaces
```

You should see all five new namespaces alongside the built-in ones (`default`, `kube-system`, etc.).

---

## Step 2 — Apply RBAC

Create all RBAC resources:

```bash
kubectl apply -f k8s/rbac/
```

**Expected:**
```
serviceaccount/developer-sa created
serviceaccount/ops-sa created
serviceaccount/ci-sa created
role.rbac.authorization.k8s.io/developer-role created
clusterrole.rbac.authorization.k8s.io/ops-clusterrole created
clusterrole.rbac.authorization.k8s.io/ci-readonly created
rolebinding.rbac.authorization.k8s.io/developer-dev-binding created
rolebinding.rbac.authorization.k8s.io/developer-staging-readonly-binding created
clusterrolebinding.rbac.authorization.k8s.io/ops-binding created
rolebinding.rbac.authorization.k8s.io/ci-binding created
```

Verify a developer cannot access production:

```bash
kubectl auth can-i create deployments \
  --namespace=production \
  --as=system:serviceaccount:dev:developer-sa
```

**Expected:**
```
no
```

Verify a developer CAN deploy to dev:

```bash
kubectl auth can-i create deployments \
  --namespace=dev \
  --as=system:serviceaccount:dev:developer-sa
```

**Expected:**
```
yes
```

---

## Step 3 — Apply Resource Quotas

```bash
kubectl apply -f k8s/quotas/resource-quotas.yaml
```

**Expected:**
```
resourcequota/dev-quota created
resourcequota/staging-quota created
resourcequota/production-quota created
```

Verify quotas are active:

```bash
kubectl describe resourcequota dev-quota -n dev
```

**Expected output shows hard limits and current usage:**
```
Name:            dev-quota
Namespace:       dev
Resource         Used   Hard
--------         ----   ----
cpu              0      4
memory           0      8Gi
pods             0      20
```

---

## Step 4 — Deploy the App and Enable HPA

Deploy the app to production:

```bash
kubectl apply -f k8s/affinity/deployment-with-affinity.yaml -n production
```

Apply the Horizontal Pod Autoscaler:

```bash
kubectl apply -f k8s/autoscaling/hpa.yaml -n production
```

Check the HPA:

```bash
kubectl get hpa -n production
```

**Expected:**
```
NAME      REFERENCE         TARGETS   MINPODS   MAXPODS   REPLICAS   AGE
myapi-hpa  Deployment/myapi  2%/70%    2         10        2          30s
```

The `TARGETS` column shows current CPU usage vs the 70% threshold. When CPU exceeds 70%, the HPA scales up.

Simulate load to trigger scaling (in a second terminal):

```bash
# Start a load generator pod
kubectl run load-gen --image=busybox -n production --rm -it -- \
  /bin/sh -c "while true; do wget -q -O- http://myapi-svc:8000/items > /dev/null; done"
```

Watch the HPA react:

```bash
kubectl get hpa -n production --watch
```

**Expected (after ~1-2 minutes):**
```
NAME       REFERENCE         TARGETS    MINPODS   MAXPODS   REPLICAS
myapi-hpa  Deployment/myapi  8%/70%     2         10        2
myapi-hpa  Deployment/myapi  95%/70%    2         10        2
myapi-hpa  Deployment/myapi  95%/70%    2         10        4
myapi-hpa  Deployment/myapi  85%/70%    2         10        6
```

Kill the load generator (`Ctrl+C`) and watch replicas scale back down over 5 minutes (HPA default cooldown).

---

## Step 5 — Install Prometheus and Grafana

Add the Prometheus Community Helm repo:

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
```

Install the kube-prometheus-stack with your custom values:

```bash
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --values helm/prometheus-values.yaml \
  --wait
```

**This takes 2-3 minutes.** The `--wait` flag blocks until all pods are ready.

**Expected (when done):**
```
NAME: monitoring
STATUS: deployed
REVISION: 1
```

Check all monitoring pods are running:

```bash
kubectl get pods -n monitoring
```

**Expected:**
```
NAME                                                  READY   STATUS    RESTARTS
alertmanager-monitoring-kube-prometheus-alertmanager-0   2/2     Running   0
monitoring-grafana-xxx-yyy                             3/3     Running   0
monitoring-kube-prometheus-operator-xxx-yyy             1/1     Running   0
monitoring-kube-state-metrics-xxx-yyy                   1/1     Running   0
monitoring-prometheus-node-exporter-xxx                 1/1     Running   0
prometheus-monitoring-kube-prometheus-prometheus-0      2/2     Running   0
```

Access Grafana:

```bash
kubectl port-forward service/monitoring-grafana 3000:80 -n monitoring
```

Open http://localhost:3000 in your browser.

Default credentials (set in `prometheus-values.yaml`):
- Username: `admin`
- Password: `admin123`

Navigate to: Dashboards → Browse → Kubernetes → Compute Resources → Namespace.

You'll see live CPU and memory usage for every namespace.

---

## Step 6 — Install ArgoCD

Install ArgoCD:

```bash
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

Wait for ArgoCD to be ready:

```bash
kubectl wait --for=condition=available deployment/argocd-server -n argocd --timeout=3m
```

Get the initial admin password:

```bash
kubectl get secret argocd-initial-admin-secret -n argocd \
  -o jsonpath='{.data.password}' | base64 -d
```

Port-forward the ArgoCD UI:

```bash
kubectl port-forward service/argocd-server 8080:443 -n argocd
```

Open https://localhost:8080 (accept the self-signed cert warning).
Login: `admin` / (the password from above).

Apply the Application manifest that points ArgoCD at your Git repo:

```bash
kubectl apply -f k8s/argocd/application.yaml
```

In the ArgoCD UI, you'll see your application appear. ArgoCD will sync it from Git every 3 minutes, or immediately when you click "Sync."

---

## Step 7 — Apply NetworkPolicies

```bash
kubectl apply -f k8s/policies/network-policies.yaml -n production
```

Verify NetworkPolicies are active:

```bash
kubectl get networkpolicies -n production
```

**Expected:**
```
NAME                    POD-SELECTOR       AGE
allow-frontend-to-backend  app=backend      10s
allow-backend-to-db        app=postgres     10s
deny-all-default           <none>           10s
```

Test that a random pod cannot reach the database directly:

```bash
# Start a test pod
kubectl run test-pod --image=busybox -n production --rm -it -- \
  /bin/sh -c "nc -zv postgres 5432; echo exit: $?"
```

**Expected:**
```
nc: connect to postgres port 5432 (tcp) failed: Connection timed out
exit: 1
```

The network policy blocks it. Only pods with label `app=backend` can reach Postgres.

---

## Step 8 — Apply PodDisruptionBudget

```bash
kubectl apply -f k8s/policies/pod-disruption-budget.yaml -n production
```

Verify:

```bash
kubectl get pdb -n production
```

**Expected:**
```
NAME        MIN AVAILABLE   MAX UNAVAILABLE   ALLOWED DISRUPTIONS   AGE
myapi-pdb   1               N/A               1                     5s
```

Now if you drain a node (`kubectl drain <node>`), Kubernetes will respect the PDB and ensure at least 1 pod stays running. It will not evict the last pod, blocking the drain until another pod is scheduled elsewhere.

---

## Step 9 — Node Affinity

Label your nodes. In a real cluster you'd have dedicated production nodes. For minikube, we simulate this:

```bash
# Minikube has a single node. Label it.
kubectl label node minikube env=production tier=app
```

Verify the label:

```bash
kubectl get nodes --show-labels | grep env=production
```

Apply the deployment that has node affinity rules:

```bash
kubectl apply -f k8s/affinity/deployment-with-affinity.yaml -n production
```

Verify pods were scheduled on the labeled node:

```bash
kubectl get pods -n production -o wide
```

The `NODE` column should show the node with the `env=production` label. If no nodes match the affinity rule, pods stay `Pending`.

---

## Verify Everything

Get a full overview:

```bash
# All namespaces
kubectl get all -n dev
kubectl get all -n staging
kubectl get all -n production
kubectl get all -n monitoring
kubectl get all -n argocd

# RBAC summary
kubectl get roles,rolebindings,clusterroles,clusterrolebindings | grep -v system

# Quotas
kubectl get resourcequota --all-namespaces

# HPA
kubectl get hpa --all-namespaces

# Network policies
kubectl get networkpolicies --all-namespaces

# PDBs
kubectl get pdb --all-namespaces
```

---

## Cleanup

```bash
# Delete project namespaces
kubectl delete namespace dev staging production monitoring argocd

# Uninstall Helm release
helm uninstall monitoring -n monitoring

# Remove node labels
kubectl label node minikube env- tier-
```

---

## 📂 Navigation

| | |
|---|---|
| Guide | [Project_Guide.md](./Project_Guide.md) |
| Code | [Code_Example.md](./Code_Example.md) |
| All Projects | [04_Projects/](../) |
