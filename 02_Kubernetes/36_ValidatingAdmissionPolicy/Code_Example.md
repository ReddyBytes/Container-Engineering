# Module 36 — ValidatingAdmissionPolicy Code Examples

## Example 1: Require All Pods to Have Resource Limits (CEL)

```yaml
# vap-require-resource-limits.yaml
# Ensures every container in every pod defines CPU and memory limits.
# Without limits, a single buggy pod can exhaust an entire node.

apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: require-resource-limits
  annotations:
    description: "All containers must define CPU and memory limits"
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
    - apiGroups: [""]
      apiVersions: ["v1"]
      operations: ["CREATE", "UPDATE"]
      resources: ["pods"]
  # Pre-filter: skip system namespaces to avoid breaking cluster components
  matchConditions:
  - name: not-system-namespace
    expression: >
      !(object.metadata.namespace in
        ['kube-system', 'kube-public', 'kube-node-lease'])
  validations:
  # Check regular containers
  - expression: >
      object.spec.containers.all(c,
        c.resources.limits.has('cpu') &&
        c.resources.limits.has('memory')
      )
    message: "All containers must define both CPU and memory limits"
  # Check init containers too
  - expression: >
      object.spec.initContainers.all(c,
        c.resources.limits.has('cpu') &&
        c.resources.limits.has('memory')
      )
    message: "All init containers must define both CPU and memory limits"
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: require-resource-limits-binding
spec:
  policyName: require-resource-limits
  validationActions: [Deny]       # Hard enforcement
  matchResources:
    namespaceSelector:
      matchExpressions:
      - key: kubernetes.io/metadata.name
        operator: NotIn
        values: [kube-system, kube-public, kube-node-lease]
```

```bash
# Apply the policy and binding
kubectl apply -f vap-require-resource-limits.yaml

# Test: try creating a pod without limits (should be DENIED)
kubectl run no-limits --image=nginx
# Error from server (Forbidden): admission webhook denied the request:
# All containers must define both CPU and memory limits

# Test: create a pod WITH limits (should SUCCEED)
kubectl run with-limits \
  --image=nginx \
  --requests='cpu=100m,memory=128Mi' \
  --limits='cpu=500m,memory=256Mi'
# pod/with-limits created
```

---

## Example 2: Require Specific Labels on All Namespaces

```yaml
# vap-require-namespace-labels.yaml
# Ensures every namespace has required organizational labels.
# Essential for cost allocation, team ownership, and compliance tracking.

apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: require-namespace-labels
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
    - apiGroups: [""]
      apiVersions: ["v1"]
      operations: ["CREATE", "UPDATE"]
      resources: ["namespaces"]
  validations:
  - expression: "object.metadata.labels.has('team')"
    message: "Namespace must have a 'team' label"
  - expression: "object.metadata.labels.has('cost-center')"
    message: "Namespace must have a 'cost-center' label"
  - expression: "object.metadata.labels.has('env')"
    message: "Namespace must have an 'env' label (e.g., dev, staging, production)"
  - expression: >
      object.metadata.labels.env in
      ['dev', 'staging', 'production', 'test']
    messageExpression: >
      "'env' label '" + object.metadata.labels.env +
      "' is not valid. Must be one of: dev, staging, production, test"
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: require-namespace-labels-binding
spec:
  policyName: require-namespace-labels
  validationActions: [Deny]
  matchResources:
    # Exclude system namespaces — they don't need org labels
    namespaceSelector:
      matchExpressions:
      - key: kubernetes.io/metadata.name
        operator: NotIn
        values: [kube-system, kube-public, kube-node-lease, default]
```

```bash
# Apply
kubectl apply -f vap-require-namespace-labels.yaml

# Test: create namespace without labels (DENIED)
kubectl create namespace my-team-ns
# Error: Namespace must have a 'team' label

# Test: create with required labels (SUCCEEDS)
kubectl create namespace my-team-ns \
  --dry-run=client -o yaml | \
kubectl label -f - team=backend cost-center=cc-1234 env=dev | \
kubectl apply -f -

# Or use a manifest:
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Namespace
metadata:
  name: my-team-ns
  labels:
    team: backend
    cost-center: cc-1234
    env: dev
EOF
```

---

## Example 3: Deny Privileged Containers

```yaml
# vap-deny-privileged.yaml
# Prevents any container from running with privileged: true.
# Privileged containers have near-complete access to the host kernel —
# effectively root on the node. This is a critical security control.

apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: deny-privileged-containers
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
    - apiGroups: [""]
      apiVersions: ["v1"]
      operations: ["CREATE", "UPDATE"]
      resources: ["pods"]
    - apiGroups: ["apps"]
      apiVersions: ["v1"]
      operations: ["CREATE", "UPDATE"]
      resources: ["deployments", "statefulsets", "daemonsets"]
  matchConditions:
  - name: not-kube-system
    expression: "object.metadata.namespace != 'kube-system'"
  validations:
  # Check containers — safely access nested optional fields
  - expression: >
      object.spec.containers.all(c,
        !c.securityContext.has('privileged') ||
        c.securityContext.privileged == false
      )
    message: "Privileged containers are not allowed"
  # Check init containers
  - expression: >
      object.spec.initContainers.all(c,
        !c.securityContext.has('privileged') ||
        c.securityContext.privileged == false
      )
    message: "Privileged init containers are not allowed"
  # Also block hostPID and hostNetwork (related escalations)
  - expression: >
      !object.spec.has('hostPID') || object.spec.hostPID == false
    message: "hostPID is not allowed"
  - expression: >
      !object.spec.has('hostNetwork') || object.spec.hostNetwork == false
    message: "hostNetwork is not allowed"
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: deny-privileged-binding
spec:
  policyName: deny-privileged-containers
  validationActions: [Deny]
  matchResources: {}    # Apply cluster-wide (except excluded namespaces above)
```

---

## Example 4: Require Images from Trusted Registry

```yaml
# vap-trusted-registry.yaml
# All container images must come from an approved registry.
# Prevents pulling images from untrusted sources (Docker Hub, etc.)
# that may contain malware or unscanned vulnerabilities.

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
        c.image.startsWith('123456789.dkr.ecr.us-east-1.amazonaws.com/')
      )
    messageExpression: >
      "Container '" + c.name + "' uses untrusted image '" + c.image + "'. " +
      "Images must come from registry.company.com or company ECR."
  # Bonus: also deny :latest tag (forces explicit versioning)
  - expression: >
      object.spec.containers.all(c,
        !c.image.endsWith(':latest') &&
        !c.image.matches('^[^:]+$')
      )
    message: >
      "Images must use an explicit tag (not :latest and not untagged). " +
      "Example: registry.company.com/myapp:v1.2.3"
  # Same checks for init containers
  - expression: >
      object.spec.initContainers.all(c,
        c.image.startsWith('registry.company.com/') ||
        c.image.startsWith('123456789.dkr.ecr.us-east-1.amazonaws.com/')
      )
    message: "Init containers must also use images from approved registries"
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: require-trusted-registry-binding
spec:
  policyName: require-trusted-registry
  validationActions: [Deny]
  matchResources: {}
```

---

## Example 5: Parameterized Policy — Max Replicas Per Team

```yaml
# vap-max-replicas-policy.yaml
# A single reusable policy where each team provides their own max replicas
# via a ConfigMap. One policy definition, multiple team configurations.

apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: max-replicas
spec:
  failurePolicy: Fail
  # Declare that parameters come from a ConfigMap
  paramKind:
    apiVersion: v1
    kind: ConfigMap
  matchConstraints:
    resourceRules:
    - apiGroups: ["apps"]
      apiVersions: ["v1"]
      operations: ["CREATE", "UPDATE"]
      resources: ["deployments"]
  validations:
  - expression: >
      object.spec.replicas <= int(params.data.maxReplicas)
    messageExpression: >
      "Deployment '" + object.metadata.name + "' has " +
      string(object.spec.replicas) + " replicas, but the maximum " +
      "allowed in this namespace is " + params.data.maxReplicas +
      ". Update your team's ConfigMap to request a higher limit."
```

```yaml
# vap-team-configs.yaml
# Each team has their own ConfigMap with their specific limits

# Team Alpha: small team, conservative limits
apiVersion: v1
kind: ConfigMap
metadata:
  name: policy-params
  namespace: team-alpha
data:
  maxReplicas: "10"
---
# Team Beta: larger team with high-traffic services
apiVersion: v1
kind: ConfigMap
metadata:
  name: policy-params
  namespace: team-beta
data:
  maxReplicas: "50"
---
# Platform team: no limit needed (they manage infrastructure)
apiVersion: v1
kind: ConfigMap
metadata:
  name: policy-params
  namespace: platform
data:
  maxReplicas: "200"
```

```yaml
# vap-max-replicas-bindings.yaml
# One binding per namespace, each pointing to its own ConfigMap

apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: max-replicas-team-alpha
spec:
  policyName: max-replicas
  validationActions: [Deny]
  paramRef:
    name: policy-params          # ConfigMap name
    namespace: team-alpha        # ConfigMap namespace
    parameterNotFoundAction: Deny  # Fail closed if ConfigMap is missing
  matchResources:
    namespaceSelector:
      matchLabels:
        kubernetes.io/metadata.name: team-alpha
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: max-replicas-team-beta
spec:
  policyName: max-replicas
  validationActions: [Deny]
  paramRef:
    name: policy-params
    namespace: team-beta
    parameterNotFoundAction: Deny
  matchResources:
    namespaceSelector:
      matchLabels:
        kubernetes.io/metadata.name: team-beta
```

```bash
# Apply all resources
kubectl apply -f vap-max-replicas-policy.yaml
kubectl apply -f vap-team-configs.yaml
kubectl apply -f vap-max-replicas-bindings.yaml

# Test: team-alpha tries to deploy 15 replicas (exceeds their limit of 10)
kubectl -n team-alpha create deployment big-deploy \
  --image=nginx --replicas=15
# Error: Deployment 'big-deploy' has 15 replicas, but the maximum
# allowed in this namespace is 10.

# Test: team-beta deploys 30 replicas (within their limit of 50)
kubectl -n team-beta create deployment normal-deploy \
  --image=nginx --replicas=30
# deployment.apps/normal-deploy created
```

---

## Example 6: Audit Mode — Roll Out Policy Safely

```yaml
# vap-audit-rollout.yaml
# Phase 1: Audit mode — see violations without blocking anything.
# After 1-2 weeks, switch validationActions to [Warn], then [Deny].

apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: require-security-context
spec:
  failurePolicy: Ignore          # During audit phase, don't block on errors
  matchConstraints:
    resourceRules:
    - apiGroups: [""]
      apiVersions: ["v1"]
      operations: ["CREATE", "UPDATE"]
      resources: ["pods"]
  validations:
  - expression: >
      object.spec.securityContext.has('runAsNonRoot') &&
      object.spec.securityContext.runAsNonRoot == true
    message: "Pods must set securityContext.runAsNonRoot: true"
  - expression: >
      object.spec.containers.all(c,
        c.securityContext.has('readOnlyRootFilesystem') &&
        c.securityContext.readOnlyRootFilesystem == true
      )
    message: "All containers must set readOnlyRootFilesystem: true"
---
# Phase 1: Audit — requests go through, violations logged only
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: require-security-context-binding
spec:
  policyName: require-security-context
  validationActions: [Audit]    # <-- Change to [Warn] then [Deny] in later phases
  matchResources:
    namespaceSelector:
      matchExpressions:
      - key: kubernetes.io/metadata.name
        operator: NotIn
        values: [kube-system, kube-public]
```

```bash
# Apply in audit mode
kubectl apply -f vap-audit-rollout.yaml

# Check the audit log for violations
# (Requires audit logging configured in your cluster)
# In the audit log, look for:
# "responseStatus": {"code": 200}  — request allowed
# "annotations": {"validation.policy.admission.k8s.io/violation": "..."}

# After audit period, switch to Warn:
kubectl patch validatingadmissionpolicybinding require-security-context-binding \
  --type='json' \
  -p='[{"op":"replace","path":"/spec/validationActions","value":["Warn"]}]'

# After warning period, switch to Deny:
kubectl patch validatingadmissionpolicybinding require-security-context-binding \
  --type='json' \
  -p='[{"op":"replace","path":"/spec/validationActions","value":["Deny"]}]'

# View all VAP policies
kubectl get validatingadmissionpolicies

# View all VAP bindings
kubectl get validatingadmissionpolicybindings

# Describe a policy to see its CEL expressions
kubectl describe validatingadmissionpolicy require-security-context
```

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [ValidatingAdmissionPolicy Theory](./Theory.md) |
| Cheatsheet | [ValidatingAdmissionPolicy Cheatsheet](./Cheatsheet.md) |
| Interview Q&A | [ValidatingAdmissionPolicy Interview Q&A](./Interview_QA.md) |
| Next Module | [37 — Native Sidecar Containers](../37_Native_Sidecar_Containers/Theory.md) |
