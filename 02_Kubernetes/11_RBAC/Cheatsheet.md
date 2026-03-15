# RBAC Cheatsheet

## Core Concepts Quick Reference

| Concept         | Namespaced? | Grants to           |
|-----------------|-------------|---------------------|
| Role            | Yes         | Resources in one namespace |
| ClusterRole     | No          | Resources cluster-wide or reusable |
| RoleBinding     | Yes         | Subject → Role/ClusterRole in one namespace |
| ClusterRoleBinding | No       | Subject → ClusterRole cluster-wide |

---

## kubectl Commands

```bash
# --- Viewing RBAC Objects ---

# List all roles in a namespace
kubectl get roles -n <namespace>

# List all cluster roles
kubectl get clusterroles

# List all role bindings in a namespace
kubectl get rolebindings -n <namespace>

# List all cluster role bindings
kubectl get clusterrolebindings

# View details of a role
kubectl describe role <role-name> -n <namespace>

# View details of a cluster role binding
kubectl describe clusterrolebinding <name>

# Get all roles and bindings across all namespaces
kubectl get rolebindings,clusterrolebindings -A

# --- Creating RBAC Objects (imperative) ---

# Create a service account
kubectl create serviceaccount <name> -n <namespace>

# Create a role that can get/list/watch pods
kubectl create role pod-reader \
  --verb=get,list,watch \
  --resource=pods \
  -n <namespace>

# Create a cluster role
kubectl create clusterrole node-reader \
  --verb=get,list,watch \
  --resource=nodes

# Bind a role to a user in a namespace
kubectl create rolebinding <name> \
  --role=<role-name> \
  --user=<username> \
  -n <namespace>

# Bind a cluster role to a service account
kubectl create clusterrolebinding <name> \
  --clusterrole=<clusterrole-name> \
  --serviceaccount=<namespace>:<sa-name>

# Bind built-in view role to a user in a namespace
kubectl create rolebinding viewer-binding \
  --clusterrole=view \
  --user=alice \
  -n staging

# --- Debugging & Auditing ---

# Check if current user can do something
kubectl auth can-i delete pods
kubectl auth can-i create deployments -n production

# Check permissions as another user
kubectl auth can-i list secrets --as=bob -n staging

# Check permissions as a service account
kubectl auth can-i list nodes \
  --as=system:serviceaccount:monitoring:prometheus

# List ALL actions a user can perform in a namespace
kubectl auth can-i --list --as=alice -n staging

# List ALL actions current user can perform cluster-wide
kubectl auth can-i --list

# Who can do what to pods? (requires kubectl 1.17+)
kubectl who-can get pods -n default  # if kubectl-who-can plugin installed

# --- Service Accounts ---

# Get service accounts in a namespace
kubectl get serviceaccounts -n <namespace>

# Describe a service account (see mounted secrets)
kubectl describe serviceaccount <name> -n <namespace>

# Get the token for a service account (K8s 1.24+)
kubectl create token <sa-name> -n <namespace>

# Get token with custom expiry
kubectl create token <sa-name> --duration=24h -n <namespace>

# --- Cleanup ---
kubectl delete role <name> -n <namespace>
kubectl delete clusterrole <name>
kubectl delete rolebinding <name> -n <namespace>
kubectl delete clusterrolebinding <name>
kubectl delete serviceaccount <name> -n <namespace>
```

---

## RBAC Verb Quick Reference

| Verb              | Meaning                        | Read-only? |
|-------------------|--------------------------------|------------|
| `get`             | Read a single resource         | Yes |
| `list`            | List all resources of a type   | Yes |
| `watch`           | Stream real-time changes       | Yes |
| `create`          | Create a new resource          | No |
| `update`          | Full replace of a resource     | No |
| `patch`           | Partial update                 | No |
| `delete`          | Delete one resource            | No |
| `deletecollection`| Delete multiple resources      | No |

---

## Common Patterns

```bash
# Grant a ServiceAccount read-only access to pods+services in one namespace
kubectl create role app-reader \
  --verb=get,list,watch \
  --resource=pods,services,endpoints \
  -n my-app

kubectl create rolebinding app-reader-binding \
  --role=app-reader \
  --serviceaccount=my-app:my-app-sa \
  -n my-app

# Grant cluster-wide read-only (for monitoring tools)
kubectl create clusterrolebinding monitoring-view \
  --clusterrole=view \
  --serviceaccount=monitoring:prometheus

# Test the binding immediately
kubectl auth can-i list pods \
  --as=system:serviceaccount:my-app:my-app-sa \
  -n my-app
```

---

## Built-in ClusterRoles

| ClusterRole     | Use case                                    |
|-----------------|---------------------------------------------|
| `cluster-admin` | Full access — use only for admins           |
| `admin`         | Full namespace access, no RBAC management   |
| `edit`          | Read/write most resources, no RBAC          |
| `view`          | Read-only access to most resources          |
| `system:node`   | Used by kubelet nodes                       |

---

## 📂 Navigation

| | Link |
|---|---|
| Previous | [Theory.md](./Theory.md) |
| Next | [Interview_QA.md](./Interview_QA.md) |
| Code Example | [Code_Example.md](./Code_Example.md) |
| Module Home | [11_RBAC](../) |
