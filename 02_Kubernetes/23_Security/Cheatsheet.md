# Module 23 — Kubernetes Security Cheatsheet

## Pod Security Standards — Namespace Labels

```yaml
metadata:
  labels:
    # Modes: enforce | audit | warn
    # Levels: privileged | baseline | restricted
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

---

## securityContext — Essential Settings

```yaml
# Pod-level
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 3000
    fsGroup: 2000
    seccompProfile:
      type: RuntimeDefault

  # Container-level
  containers:
  - name: app
    securityContext:
      runAsNonRoot: true
      runAsUser: 1000
      readOnlyRootFilesystem: true
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
        add:
        - NET_BIND_SERVICE    # only if needed (port < 1024)
```

---

## Image Security Commands

```bash
# Scan with Trivy
trivy image myapp:1.4.2
trivy image --severity HIGH,CRITICAL myapp:1.4.2
trivy image --exit-code 1 --severity CRITICAL myapp:1.4.2  # fail CI on CRITICAL

# Scan a Dockerfile
trivy config ./Dockerfile

# List image tags (avoid :latest)
docker images myapp

# Get image digest (for immutable references)
docker inspect --format='{{index .RepoDigests 0}}' myapp:1.4.2
```

---

## Kyverno Policy Examples

```yaml
# Install Kyverno
helm repo add kyverno https://kyverno.github.io/kyverno/
helm install kyverno kyverno/kyverno -n kyverno --create-namespace

# Policy: require non-root
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-non-root
spec:
  rules:
  - name: check-non-root
    match:
      resources:
        kinds: ["Pod"]
    validate:
      message: "runAsNonRoot must be true"
      pattern:
        spec:
          containers:
          - securityContext:
              runAsNonRoot: true

---
# Policy: disallow :latest tag
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-latest-tag
spec:
  rules:
  - name: require-image-tag
    match:
      resources:
        kinds: ["Pod"]
    validate:
      message: "Images must not use the :latest tag"
      pattern:
        spec:
          containers:
          - image: "!*:latest"

---
# Policy: require resource limits
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-resource-limits
spec:
  rules:
  - name: check-limits
    match:
      resources:
        kinds: ["Pod"]
    validate:
      message: "CPU and memory limits are required"
      pattern:
        spec:
          containers:
          - resources:
              limits:
                memory: "?*"
                cpu: "?*"
```

---

## OPA Gatekeeper

```bash
# Install Gatekeeper
kubectl apply -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/master/deploy/gatekeeper.yaml

# Check constraint violations
kubectl get constraints
kubectl describe <constraint-name>
```

---

## Secrets Encryption at Rest

```yaml
# /etc/kubernetes/encryption-config.yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
- resources:
  - secrets
  providers:
  - aescbc:
      keys:
      - name: key1
        secret: <base64-32-byte-key>
  - identity: {}

# Add to kube-apiserver:
# --encryption-provider-config=/etc/kubernetes/encryption-config.yaml
```

---

## Falco Installation and Common Rules

```bash
# Install Falco via Helm
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm install falco falcosecurity/falco \
  --namespace falco --create-namespace \
  --set falco.grpc.enabled=true \
  --set falco.grpc_output.enabled=true

# Watch Falco alerts
kubectl logs -f -l app.kubernetes.io/name=falco -n falco
```

Key default rules:
- Shell spawned in container
- Sensitive file opened
- Package management tool executed
- Container attached (kubectl exec)
- Unexpected network outbound

---

## RBAC Security Commands

```bash
# What can a service account do?
kubectl auth can-i --list \
  --as=system:serviceaccount:<ns>:<sa> -n <ns>

# Who has cluster-admin?
kubectl get clusterrolebindings -o json | \
  jq '.items[] | select(.roleRef.name=="cluster-admin") | .subjects'

# Audit all bindings
kubectl get rolebindings,clusterrolebindings -A -o yaml
```

---

## Security Checklist (Quick Reference)

```
Container:
[ ] runAsNonRoot: true
[ ] readOnlyRootFilesystem: true
[ ] allowPrivilegeEscalation: false
[ ] capabilities: drop: ALL
[ ] No privileged: true

Images:
[ ] No :latest in production
[ ] Trivy scan in CI
[ ] Use distroless/minimal base

Cluster:
[ ] PSS: restricted on prod namespaces
[ ] Secrets encrypted at rest
[ ] NetworkPolicies applied
[ ] Admission policies (Kyverno/OPA)
[ ] Falco runtime monitoring
[ ] Audit logging enabled
```

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Security Theory](./Theory.md) |
| Interview Q&A | [Security Interview Q&A](./Interview_QA.md) |
| Next Module | [24 — Service Mesh](../24_Service_Mesh/Theory.md) |
