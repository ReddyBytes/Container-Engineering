# Module 36 — ValidatingAdmissionPolicy Cheatsheet

## Core Resources

```yaml
# 1. The Policy (defines the CEL rule)
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: my-policy
spec:
  failurePolicy: Fail          # Fail or Ignore
  matchConstraints:
    resourceRules:
    - apiGroups: ["apps"]
      apiVersions: ["v1"]
      operations: ["CREATE", "UPDATE"]
      resources: ["deployments"]
  validations:
  - expression: "object.spec.replicas <= 10"
    message: "Replicas must not exceed 10"

---
# 2. The Binding (applies the policy to a scope)
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: my-policy-binding
spec:
  policyName: my-policy
  validationActions: [Deny]    # Deny, Warn, or Audit
  matchResources:
    namespaceSelector:
      matchLabels:
        env: production
```

---

## Common CEL Expressions

```cel
# Field exists
object.metadata.labels.has('team')

# Field value check
object.spec.replicas <= 10

# All containers have CPU limits
object.spec.containers.all(c,
  c.resources.limits.has('cpu')
)

# All containers have memory limits
object.spec.containers.all(c,
  c.resources.limits.has('memory')
)

# No privileged containers
!object.spec.containers.exists(c,
  c.securityContext.privileged == true
)

# All containers use trusted registry
object.spec.containers.all(c,
  c.image.startsWith('registry.company.com/')
)

# Image not using :latest tag
object.spec.containers.all(c,
  !c.image.endsWith(':latest')
)

# Required label exists
object.metadata.labels.has('app') &&
object.metadata.labels.has('team') &&
object.metadata.labels.has('version')

# Namespace not in exclusion list
!(object.metadata.namespace in
  ['kube-system', 'kube-public', 'monitoring'])

# runAsNonRoot set to true
object.spec.securityContext.runAsNonRoot == true

# No hostPath volumes
!object.spec.volumes.exists(v, v.has('hostPath'))
```

---

## CEL Functions Quick Reference

| Function | Usage |
|----------|-------|
| `.has(field)` | Check if field exists |
| `.all(v, expr)` | All list elements satisfy expr |
| `.exists(v, expr)` | At least one list element satisfies expr |
| `.filter(v, expr)` | Return elements satisfying expr |
| `size(list)` | Length of list |
| `.startsWith(s)` | String starts with s |
| `.endsWith(s)` | String ends with s |
| `.contains(s)` | String contains s |
| `.matches(regex)` | String matches regex |
| `string(x)` | Convert to string |
| `int(x)` | Convert to int |

---

## Validation Actions

| Action | Request outcome | Use case |
|--------|----------------|----------|
| `Deny` | Rejected (4xx error) | Enforcement mode |
| `Warn` | Allowed + warning shown | Policy rollout / soft enforcement |
| `Audit` | Allowed + audit log entry | Visibility without blocking |

```yaml
# Combine actions
validationActions: [Warn, Audit]  # allow but warn + log

# Strict enforcement
validationActions: [Deny]
```

---

## MatchConditions (Pre-filtering)

```yaml
spec:
  matchConditions:
  # Skip kube-system namespace
  - name: not-kube-system
    expression: "object.metadata.namespace != 'kube-system'"
  # Only check pods with the 'app' label
  - name: has-app-label
    expression: "object.metadata.labels.has('app')"
  # Skip pods created by system components
  - name: not-system-pod
    expression: >
      !(object.metadata.labels.has('kubernetes.io/bootstrapping') ||
        object.metadata.labels.has('k8s-app'))
```

---

## Parameterized Policies

```yaml
# Policy with ParamKind
spec:
  paramKind:
    apiVersion: v1
    kind: ConfigMap
  validations:
  - expression: >
      object.spec.replicas <= int(params.data.maxReplicas)
    messageExpression: >
      "Replicas " + string(object.spec.replicas) +
      " exceeds maximum " + params.data.maxReplicas

---
# Binding with paramRef
spec:
  paramRef:
    name: team-a-policy-params     # ConfigMap name
    namespace: team-a
    parameterNotFoundAction: Deny  # Deny or Allow if ConfigMap missing
```

---

## kubectl Commands

```bash
# List all ValidatingAdmissionPolicies
kubectl get validatingadmissionpolicies

# List all bindings
kubectl get validatingadmissionpolicybindings

# Describe a policy (see CEL expressions)
kubectl describe validatingadmissionpolicy require-resource-limits

# Describe a binding
kubectl describe validatingadmissionpolicybinding require-limits-binding

# Delete a policy (binding must be deleted first)
kubectl delete validatingadmissionpolicybinding my-binding
kubectl delete validatingadmissionpolicy my-policy

# Test a policy by trying to create a violating resource
kubectl run test-pod --image=nginx
# If Deny: Error from server: admission webhook... failed: ...
# If Warn: Warning: <your message>
```

---

## VAP vs Webhook Tools Comparison

| | VAP | Kyverno | OPA/Gatekeeper |
|---|---|---|---|
| External server | No | Yes | Yes |
| Policy language | CEL | YAML | Rego |
| Validation | Yes | Yes | Yes |
| Mutation | **No** | Yes | Yes |
| K8s version | 1.30+ GA | Any | Any |
| Latency added | ~0ms | 10–50ms | 10–50ms |
| Learning curve | Low | Low | High |

---

## Version Notes

| Feature | K8s Version |
|---------|-------------|
| VAP alpha | 1.26 |
| VAP beta | 1.28 |
| VAP GA | **1.30 (April 2024)** |
| CEL matchConditions | 1.28 |
| messageExpression | 1.27 |
| ParamKind / paramRef | 1.28 |

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [ValidatingAdmissionPolicy Theory](./Theory.md) |
| Interview Q&A | [ValidatingAdmissionPolicy Interview Q&A](./Interview_QA.md) |
| Code Examples | [ValidatingAdmissionPolicy Code Examples](./Code_Example.md) |
| Next Module | [37 — Native Sidecar Containers](../37_Native_Sidecar_Containers/Theory.md) |
