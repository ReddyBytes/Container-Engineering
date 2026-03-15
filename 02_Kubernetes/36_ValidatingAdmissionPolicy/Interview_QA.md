# Module 36 — ValidatingAdmissionPolicy Interview Q&A

---

## Q1: What is ValidatingAdmissionPolicy and what problem does it solve compared to webhook-based tools?

**Answer:**

ValidatingAdmissionPolicy (VAP) is a native Kubernetes mechanism for enforcing policies on API requests using **CEL (Common Expression Language)** expressions evaluated directly inside the kube-apiserver. It reached GA in **Kubernetes 1.30** (April 2024).

The problem it solves: previously, policy enforcement required deploying and maintaining an **external webhook server** (OPA/Gatekeeper, Kyverno). These webhook servers:
- Add latency to every API call (a network round-trip to the webhook pod)
- Must be maintained, upgraded, and kept highly available
- Require TLS certificate management
- Can become a single point of failure during incidents

VAP moves policy evaluation **in-process** into the API server using CEL. There's no network round-trip, no external service to maintain, and no certificates to manage. The policy is evaluated as compiled code inside the already-running API server.

---

## Q2: What are the two core resources that make up ValidatingAdmissionPolicy?

**Answer:**

1. **ValidatingAdmissionPolicy**: defines the CEL validation rules, what resources they apply to, and the failure policy. This is the policy definition itself.

2. **ValidatingAdmissionPolicyBinding**: binds the policy to a specific scope (namespaces, label selectors, cluster-wide) and specifies what action to take (Deny, Warn, or Audit). Multiple bindings can reference the same policy.

The separation is intentional: write one policy, apply it with different actions to different scopes. For example:
- Bind to `staging` namespace with `Warn` action (soft rollout)
- Bind to `production` namespace with `Deny` action (enforcement)

---

## Q3: What is CEL and what makes it safe to run inside the API server?

**Answer:**

CEL (Common Expression Language) is a lightweight expression language originally developed by Google. It's used in several Google products and Kubernetes for policy evaluation.

Properties that make it safe for in-process evaluation:

1. **No loops**: CEL cannot express unbounded loops. List comprehensions are supported but are bounded by the list size. This prevents infinite loops from hanging the API server.

2. **No side effects**: CEL expressions cannot write to files, make network calls, or modify state. They only read input data and return a boolean.

3. **Bounded execution time**: because there are no loops, CEL expressions have predictable execution time proportional to the input size.

4. **Type-safe**: CEL is optionally typed, and Kubernetes validates CEL expressions at policy creation time, catching errors before they affect real workloads.

These properties mean a badly-written CEL expression can't crash or hang the API server.

---

## Q4: Explain the difference between Deny, Warn, and Audit validation actions.

**Answer:**

The `validationActions` field in a `ValidatingAdmissionPolicyBinding` controls what happens when a policy validation fails:

- **`Deny`**: The API request is rejected with a 4xx error. The resource is NOT created or updated. The developer sees an error message immediately. Use this for hard enforcement.

- **`Warn`**: The request **succeeds**, but a warning is returned in the API response. `kubectl` displays the warning to the user. The resource is created/updated despite the policy violation. Use this when rolling out new policies to avoid breaking existing workflows.

- **`Audit`**: The request **succeeds**, but a policy violation event is recorded in the Kubernetes audit log. Nothing is shown to the user. Use this for visibility — monitor violations before deciding to enforce.

You can combine actions: `[Warn, Audit]` means the request goes through, the developer sees a warning, and the violation is logged.

**Best practice for rollout**: start with `Audit` (see the blast radius), move to `Warn` (alert developers without blocking), then switch to `Deny` (enforce).

---

## Q5: Write a CEL expression that ensures all containers in a pod have both CPU and memory limits defined.

**Answer:**

```cel
object.spec.containers.all(c,
  c.resources.limits.has('cpu') &&
  c.resources.limits.has('memory')
)
```

Breaking it down:
- `object.spec.containers` — the list of containers in the pod spec
- `.all(c, expr)` — returns true only if every element (called `c`) satisfies the expression
- `c.resources.limits.has('cpu')` — checks if the `cpu` key exists in the limits map
- `&&` — both conditions must be true

To also check init containers:

```cel
object.spec.containers.all(c,
  c.resources.limits.has('cpu') && c.resources.limits.has('memory')
) &&
object.spec.initContainers.all(c,
  c.resources.limits.has('cpu') && c.resources.limits.has('memory')
)
```

---

## Q6: What is ParamKind and why is it useful?

**Answer:**

`ParamKind` allows a ValidatingAdmissionPolicy to accept external parameters from a Kubernetes object (typically a ConfigMap) instead of hard-coding values in the CEL expression. This makes policies **reusable** across teams with different configuration.

Without ParamKind:
```yaml
# Hard-coded — everyone gets 10 replicas max
expression: "object.spec.replicas <= 10"
```

With ParamKind (ConfigMap):
```yaml
# Parameterized — each team configures their own limit
spec:
  paramKind:
    apiVersion: v1
    kind: ConfigMap
validations:
- expression: "object.spec.replicas <= int(params.data.maxReplicas)"
```

Team A's binding references their ConfigMap with `maxReplicas: "10"`. Team B's binding references their ConfigMap with `maxReplicas: "50"`. One policy, different behavior per team.

The `parameterNotFoundAction` field controls what happens if the referenced ConfigMap doesn't exist: `Deny` (fail closed — the safest default) or `Allow` (fail open).

---

## Q7: What are matchConditions and how do they differ from matchConstraints?

**Answer:**

**`matchConstraints`** (on the policy) and **`matchResources`** (on the binding) define which resource types (API group, version, resource name, operation) and which namespaces/labels the policy applies to. These are coarse-grained filters.

**`matchConditions`** are CEL expressions that provide **fine-grained pre-filtering** at evaluation time. If any match condition returns `false`, the validation rules are skipped entirely for that object.

Example:
```yaml
matchConditions:
# Only evaluate if the pod has the 'app' label
- name: has-app-label
  expression: "object.metadata.labels.has('app')"
# Skip pods in system namespaces
- name: not-system-namespace
  expression: >
    !(object.metadata.namespace in ['kube-system', 'kube-public'])
```

Key difference:
- `matchConstraints` operates at the resource type level (what kinds of objects) — evaluated before the CEL expression is even loaded
- `matchConditions` operates on the object's actual data (the content of the object) — evaluated after the object is known but before validation runs

---

## Q8: Why can't ValidatingAdmissionPolicy replace Kyverno or OPA/Gatekeeper entirely?

**Answer:**

VAP is a **validating**-only mechanism. It can approve or reject requests, but it **cannot modify** them. This is a fundamental architectural limitation.

Use cases that require Kyverno or OPA/Gatekeeper:

1. **Mutation**: automatically adding labels, injecting sidecars, setting default values on resources. For example: "if a pod doesn't have a `team` label, add `team=unknown` automatically." VAP cannot do this.

2. **Resource generation**: automatically creating related resources when another resource is created. Kyverno can, for example, automatically create a default NetworkPolicy whenever a new namespace is created. VAP cannot.

3. **Complex policy logic**: while CEL is expressive, very complex policies with multiple lookups, external data sources, or intricate conditional logic may be more naturally expressed in Rego (OPA) or Kyverno's YAML-native syntax.

4. **Multi-cluster policy management**: OPA/Gatekeeper has tooling for centralized policy distribution across multiple clusters.

**Recommendation**: use VAP for validation-only policies on K8s 1.30+, keep Kyverno for mutation and generation.

---

## Q9: How do you roll out a new ValidatingAdmissionPolicy without breaking existing workloads?

**Answer:**

Use a phased rollout leveraging the three validation actions:

**Phase 1: Audit** — bind with `validationActions: [Audit]`
```yaml
validationActions: [Audit]
```
- Requests are allowed through
- Violations are recorded in the audit log
- Monitor audit logs for 1–2 weeks to understand the blast radius
- Fix existing violations before enforcement

**Phase 2: Warn** — switch to `validationActions: [Warn]`
```yaml
validationActions: [Warn]
```
- Requests are allowed through
- kubectl shows warnings to developers
- Teams can see violations and fix them without being blocked
- Monitor for a few days/weeks

**Phase 3: Deny** — switch to `validationActions: [Deny]`
```yaml
validationActions: [Deny]
```
- Violations are rejected
- Enforcement is active

This phased approach prevents surprise outages and gives teams time to remediate.

---

## Q10: How does the admission control pipeline work, and where does VAP fit in?

**Answer:**

The Kubernetes admission control pipeline processes every API write request (create, update, delete) in this order:

1. **Authentication**: verify who is making the request
2. **Authorization (RBAC)**: verify the requester has permission
3. **Mutating admission webhooks**: external webhooks that can modify the object (Kyverno mutation, Istio sidecar injection, etc.)
4. **Schema validation**: validate the object against its CRD/built-in schema
5. **Validating admission webhooks + VAP**: external webhooks and in-process CEL expressions that validate the (potentially mutated) object. If ANY validation fails with Deny, the entire request is rejected.
6. **Persist to etcd**: if all validations pass, the object is stored

VAP runs in step 5, after mutations have already been applied. This is important: if a mutating webhook adds resource limits, the VAP expression sees the limits already added. The order matters.

If `failurePolicy: Fail` is set and the VAP itself encounters an error (not a validation failure, but an actual expression error), the request is denied. If `failurePolicy: Ignore`, the request proceeds.

---

## Q11: Write a VAP that requires all container images to come from a trusted registry.

**Answer:**

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: require-trusted-registry
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
    - apiGroups: [""]
      apiVersions: ["v1"]
      operations: ["CREATE", "UPDATE"]
      resources: ["pods"]
  matchConditions:
  - name: not-system-namespace
    expression: >
      !(object.metadata.namespace in
        ['kube-system', 'kube-public', 'kube-node-lease'])
  validations:
  - expression: >
      object.spec.containers.all(c,
        c.image.startsWith('registry.company.com/') ||
        c.image.startsWith('gcr.io/myproject/')
      )
    message: "All containers must use images from registry.company.com or gcr.io/myproject"
  - expression: >
      object.spec.initContainers.all(c,
        c.image.startsWith('registry.company.com/') ||
        c.image.startsWith('gcr.io/myproject/')
      )
    message: "All init containers must use images from approved registries"
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: require-trusted-registry-binding
spec:
  policyName: require-trusted-registry
  validationActions: [Deny]
  matchResources: {}   # empty = apply cluster-wide
```

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [ValidatingAdmissionPolicy Theory](./Theory.md) |
| Cheatsheet | [ValidatingAdmissionPolicy Cheatsheet](./Cheatsheet.md) |
| Code Examples | [ValidatingAdmissionPolicy Code Examples](./Code_Example.md) |
| Next Module | [37 — Native Sidecar Containers](../37_Native_Sidecar_Containers/Theory.md) |
