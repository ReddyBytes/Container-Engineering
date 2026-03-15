# Module 21 — Service Accounts Interview Q&A

---

## Q1: What is a Service Account in Kubernetes, and how does it differ from a user account?

**Answer:**

A Service Account is a Kubernetes object that provides an identity for processes running inside Pods. It is namespace-scoped and stored in etcd.

A User Account is for humans (developers, admins) who access the cluster via kubectl or API. Kubernetes does not manage user accounts internally — they come from external systems like X.509 certificates, OIDC providers, or LDAP.

Key differences:
- Service Accounts are namespaced; user accounts are cluster-wide
- Service Accounts have tokens auto-injected into pods; user accounts use kubeconfig credentials
- Service Accounts are created with `kubectl create serviceaccount`; user accounts are not created in K8s

---

## Q2: What happens if you don't specify a `serviceAccountName` in a Pod spec?

**Answer:**

The Pod uses the `default` Service Account of the namespace it's running in. Kubernetes automatically mounts the default SA token into the pod at `/var/run/secrets/kubernetes.io/serviceaccount/token`.

This is a security concern because every pod gets a credential by default. If the pod is compromised, the attacker has an API token. Best practice is to create a dedicated SA per app and set `automountServiceAccountToken: false` on pods that don't need API access.

---

## Q3: What changed about Service Account tokens in Kubernetes 1.21?

**Answer:**

Before 1.21, SA tokens were long-lived JWTs stored as Secrets in etcd. They never expired and were not bound to any specific pod.

In 1.21+, tokens became **projected volume tokens** — short-lived JWTs managed by the kubelet that:
- Have an expiry (default 1 hour)
- Are rotated automatically by the kubelet before expiry
- Are bound to the pod (contain pod name, UID, namespace)
- Are not stored as Secrets in etcd

This significantly reduces the risk of token leakage — a stolen token is only valid for a short window.

---

## Q4: How do you give a Pod read access to ConfigMaps in its namespace?

**Answer:**

Three steps:
1. Create a ServiceAccount
2. Create a Role with read permissions on ConfigMaps
3. Create a RoleBinding linking the SA to the Role

Then set `serviceAccountName` in the Pod spec to use the new SA.

```yaml
# Role
rules:
- apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["get", "list", "watch"]
```

The SA identity in RBAC is `system:serviceaccount:<namespace>:<sa-name>`.

---

## Q5: What is IRSA and when would you use it?

**Answer:**

IRSA (IAM Roles for Service Accounts) is an AWS EKS feature that links a Kubernetes Service Account to an AWS IAM Role, allowing pods to assume that role and call AWS APIs (S3, DynamoDB, SQS, etc.) without storing AWS credentials as K8s Secrets.

You use it when a pod needs to interact with AWS services. The workflow:
1. EKS cluster has an OIDC provider configured
2. IAM Role has a trust policy allowing the K8s SA to assume it
3. SA has an annotation: `eks.amazonaws.com/role-arn: arn:aws:iam::...:role/RoleName`
4. The AWS SDK in the pod automatically picks up the projected token and exchanges it for temporary credentials

The equivalent on GKE is Workload Identity.

---

## Q6: What does `automountServiceAccountToken: false` do, and where can you set it?

**Answer:**

It prevents Kubernetes from automatically mounting the SA token into the pod. This reduces the attack surface for pods that don't need to talk to the API server (most application pods).

It can be set at two levels:
- **On the ServiceAccount**: applies to all pods using that SA by default
- **On the Pod spec**: overrides the SA-level setting for that specific pod

The Pod-level setting takes precedence over the SA-level setting.

---

## Q7: How would you verify what permissions a Service Account has?

**Answer:**

Use `kubectl auth can-i` with the `--as` flag:

```bash
kubectl auth can-i list pods \
  --as=system:serviceaccount:production:myapp-sa \
  -n production

# List ALL permissions of an SA
kubectl auth can-i --list \
  --as=system:serviceaccount:production:myapp-sa \
  -n production
```

You can also inspect the RoleBindings and ClusterRoleBindings that reference the SA:

```bash
kubectl get rolebindings,clusterrolebindings -A \
  -o json | jq '... | select(.subjects[]?.name == "myapp-sa")'
```

---

## Q8: What is the difference between a Role + RoleBinding and a ClusterRole + ClusterRoleBinding for Service Accounts?

**Answer:**

- **Role + RoleBinding**: grants permissions scoped to a single namespace. The SA can only act on resources in that namespace.
- **ClusterRole + ClusterRoleBinding**: grants cluster-wide permissions. The SA can act on resources in any namespace, including non-namespaced resources like Nodes.

You can also use a **ClusterRole + RoleBinding** — this lets you define a reusable set of rules once (ClusterRole) and grant them to an SA within a specific namespace (RoleBinding). This is useful for standard roles like "can read ConfigMaps" that you want to apply per-namespace.

---

## Q9: A pod is getting 403 Forbidden errors when calling the K8s API. How do you debug this?

**Answer:**

Step-by-step debugging:

1. Identify which SA the pod uses: `kubectl describe pod <pod> -n <ns> | grep ServiceAccount`
2. Check what the SA can do: `kubectl auth can-i --list --as=system:serviceaccount:<ns>:<sa> -n <ns>`
3. Check if there are RoleBindings: `kubectl get rolebindings -n <ns> -o yaml`
4. Look at the API server audit logs for the denied request (if audit logging is enabled)
5. Check if `automountServiceAccountToken: false` is set — the pod might not have a token at all
6. Try the specific permission: `kubectl auth can-i <verb> <resource> --as=system:serviceaccount:<ns>:<sa>`

Fix: add the missing permission to the Role, or bind the SA to an existing Role that grants the needed access.

---

## Q10: Why is it dangerous to bind `cluster-admin` to a Service Account?

**Answer:**

`cluster-admin` is the most powerful ClusterRole in Kubernetes — it grants full control over all resources in the cluster (create, delete, update anything including RBAC itself).

If a pod with `cluster-admin` is compromised (via a remote code execution vulnerability, supply chain attack, etc.), the attacker can:
- Create new admin users or SAs
- Read all Secrets in the cluster (including other apps' credentials)
- Delete workloads or namespaces
- Escalate to the underlying infrastructure

The principle of least privilege applies strictly here. Applications should get only the exact permissions they need — `get configmaps` not `*` on `*`.

---

## Q11: How do projected volume tokens differ from legacy secret-based SA tokens in terms of security?

**Answer:**

| Property | Legacy Secret Token | Projected Volume Token |
|---|---|---|
| Expiry | Never | Configurable (default 1h) |
| Auto-rotation | No | Yes (kubelet) |
| Bound to pod | No | Yes (pod UID, name) |
| Stored in etcd | Yes (as Secret) | No |
| Audience-bound | No | Yes |

Projected tokens are more secure because: if leaked, they expire quickly; they can't be used from a different pod; they're not discoverable by listing Secrets in etcd.

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Service Accounts Theory](./Theory.md) |
| Cheatsheet | [Service Accounts Cheatsheet](./Cheatsheet.md) |
| Next Module | [22 — Monitoring and Logging](../22_Monitoring_and_Logging/Theory.md) |
