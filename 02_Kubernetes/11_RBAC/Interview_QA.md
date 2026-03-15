# RBAC — Interview Q&A

---

**Q1: What does RBAC stand for and what problem does it solve?**

RBAC stands for Role-Based Access Control. It solves the authorization problem in Kubernetes: given that a request is authenticated (we know who you are), is this subject allowed to perform this action on this resource? Before RBAC, Kubernetes had simpler but coarser authorization modes. RBAC allows fine-grained, auditable permission grants following the principle of least privilege.

---

**Q2: What is the difference between a Role and a ClusterRole?**

A Role is namespaced — it grants permissions only within a single namespace. A ClusterRole is cluster-scoped and can grant permissions either cluster-wide or be reused across multiple namespaces via RoleBindings. ClusterRoles are required for cluster-scoped resources like nodes, persistent volumes, and namespaces, which have no namespace context.

---

**Q3: What is the difference between a RoleBinding and a ClusterRoleBinding?**

A RoleBinding attaches a Role or ClusterRole to a subject within a specific namespace. A ClusterRoleBinding attaches a ClusterRole to a subject for the entire cluster. An important trick: a RoleBinding can reference a ClusterRole, which lets you define a role once as a ClusterRole and reuse it across namespaces via separate RoleBindings — without duplicating the role definition.

---

**Q4: What are the three types of subjects in RBAC?**

1. **User** — a human identity, typically from an external identity provider (certificates, OIDC, LDAP). Kubernetes does not store user objects internally.
2. **Group** — a collection of users. Kubernetes has system groups like `system:masters` and `system:authenticated`.
3. **ServiceAccount** — a Kubernetes object that provides an identity for workloads (pods) running inside the cluster.

---

**Q5: A pod needs to call the Kubernetes API to list other pods. How do you set this up?**

You need three things:
1. Create a dedicated **ServiceAccount** for the pod.
2. Create a **Role** (or ClusterRole) that grants `get`, `list`, `watch` on `pods`.
3. Create a **RoleBinding** that binds the ServiceAccount to the Role.
4. Set `serviceAccountName` in the pod/deployment spec.

Avoid reusing the `default` ServiceAccount, and set `automountServiceAccountToken: false` on pods that do not need API access.

---

**Q6: How do you test whether a specific service account has permission to do something?**

Use `kubectl auth can-i` with the `--as` flag:

```bash
kubectl auth can-i list pods \
  --as=system:serviceaccount:my-namespace:my-service-account \
  -n my-namespace
```

Use `--list` to enumerate all permissions a subject has in a namespace:

```bash
kubectl auth can-i --list --as=system:serviceaccount:default:my-sa -n default
```

---

**Q7: What is the principle of least privilege and why does it matter in Kubernetes?**

The principle of least privilege means granting a subject only the minimum permissions required to perform its function. In Kubernetes this matters because:
- Compromised pods with broad permissions can exfiltrate secrets, modify workloads, or take down the cluster.
- Misconfigured automation can accidentally delete production resources.
- Auditing is cleaner when each workload has a named, scoped identity.

For example, a pod that only reads ConfigMaps should not have permission to delete Secrets.

---

**Q8: What is an aggregated ClusterRole?**

An aggregated ClusterRole is one that automatically collects permissions from other ClusterRoles using label selectors. The built-in `view`, `edit`, and `admin` ClusterRoles use this pattern. If a custom operator labels its own ClusterRole with `rbac.authorization.k8s.io/aggregate-to-view: "true"`, the `view` ClusterRole will automatically include those permissions cluster-wide. This allows operator developers to extend default roles without cluster administrators having to manually edit them.

---

**Q9: What happens if you bind a ClusterRole using a RoleBinding instead of a ClusterRoleBinding?**

The permissions are scoped to the namespace of the RoleBinding — not the entire cluster. This is intentional and useful: define a ClusterRole once (e.g., `pod-reader`) and create RoleBindings in different namespaces to grant the same permissions namespace-by-namespace. The ClusterRole itself is cluster-scoped (as an object), but the effective permissions granted by a RoleBinding are limited to that namespace.

---

**Q10: What are some common RBAC security mistakes to avoid?**

1. **Granting `cluster-admin`** to non-admin workloads — this bypasses all RBAC checks.
2. **Using wildcard resources or verbs** (`"*"`) in roles that are not admin roles.
3. **Not creating dedicated ServiceAccounts** — leaving pods using the `default` ServiceAccount makes auditing impossible.
4. **Forgetting namespace scope** — a RoleBinding in namespace A does not help a pod in namespace B.
5. **Not setting `automountServiceAccountToken: false`** on pods that never call the Kubernetes API, leaving credentials unnecessarily exposed.

---

**Q11: Can a ClusterRoleBinding reference a Role (not a ClusterRole)?**

No. A ClusterRoleBinding can only reference a **ClusterRole**. A RoleBinding can reference either a Role or a ClusterRole (but the permissions are scoped to the namespace). This is a common exam question: ClusterRoleBinding → ClusterRole only. RoleBinding → Role or ClusterRole.

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Theory.md](./Theory.md) |
| Cheatsheet | [Cheatsheet.md](./Cheatsheet.md) |
| Code Example | [Code_Example.md](./Code_Example.md) |
| Module Home | [11_RBAC](../) |
