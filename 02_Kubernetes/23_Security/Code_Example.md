# Kubernetes Security — Code Examples

All examples are production-quality with detailed comments explaining every decision.

---

## 1. securityContext — Hardening a Container Step by Step

```yaml
# secure-pod.yaml
# A production-hardened pod that applies all recommended securityContext settings
# Each setting removes a specific attack vector

apiVersion: v1
kind: Pod
metadata:
  name: hardened-api
  namespace: production
spec:
  # Pod-level security context: applies to ALL containers in the pod
  securityContext:
    runAsNonRoot: true                   # ← reject the pod if the image runs as UID 0 (root)
    runAsUser: 10001                     # ← run as a specific non-root UID
    runAsGroup: 10001                    # ← run as a specific GID
    fsGroup: 10001                       # ← volume ownership: mounted volumes owned by this GID
    seccompProfile:
      type: RuntimeDefault               # ← enable the default seccomp profile (syscall filter)
      # RuntimeDefault blocks ~100 uncommon syscalls that are common in kernel exploits

  containers:
  - name: api
    image: myapp:1.4.2                   # ← pinned version, never :latest
    imagePullPolicy: Always              # ← always pull to avoid stale cached images
    ports:
    - containerPort: 8080

    # Container-level security context: overrides or extends the pod-level settings
    securityContext:
      allowPrivilegeEscalation: false    # ← prevents sudo/setuid binaries from gaining more privileges
      readOnlyRootFilesystem: true       # ← the container filesystem is read-only
      # If the process is compromised, the attacker cannot write malware to disk
      capabilities:
        drop:
        - ALL                            # ← drop every Linux capability (raw sockets, chown, mknod, etc.)
        add:
        - NET_BIND_SERVICE               # ← only add back what's strictly needed (binding to port <1024)
        # Most apps need nothing from capabilities — just drop ALL

    resources:
      requests:
        cpu: "100m"
        memory: "128Mi"
      limits:
        cpu: "500m"
        memory: "256Mi"

    # When readOnlyRootFilesystem is true, writable directories must be explicit emptyDir mounts
    volumeMounts:
    - name: tmp-dir
      mountPath: /tmp                    # ← /tmp must be writable for most apps
    - name: cache-dir
      mountPath: /var/cache/myapp        # ← app-specific writable cache

  volumes:
  - name: tmp-dir
    emptyDir: {}                         # ← ephemeral, node-local storage; wiped when pod is deleted
  - name: cache-dir
    emptyDir: {}
```

```bash
kubectl apply -f secure-pod.yaml

# Verify the security settings are in effect
kubectl get pod hardened-api -n production -o yaml | grep -A 20 "securityContext:"

# Confirm the process is NOT running as root
kubectl exec hardened-api -n production -- id
# uid=10001 gid=10001 groups=10001   ← not root

# Confirm the filesystem is read-only
kubectl exec hardened-api -n production -- touch /test-file 2>&1
# touch: cannot touch '/test-file': Read-only file system   ← correct

# Confirm /tmp is writable (explicit emptyDir mount)
kubectl exec hardened-api -n production -- touch /tmp/test-file
# (success)
```

---

## 2. Pod Security Standards — Enforce at the Namespace Level

```yaml
# pss-namespaces.yaml
# Apply Pod Security Standards labels to namespaces
# The built-in PodSecurity admission controller enforces these labels automatically

---
# Production: enforce restricted policy (most secure)
# Any pod violating the policy is REJECTED at admission
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    # enforce: reject pods that violate the policy
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: latest
    # audit: allow pods but log violations to the audit log
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: latest
    # warn: allow pods but display a warning in kubectl output
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: latest

---
# Staging: warn only — good for testing the impact before enforcing
apiVersion: v1
kind: Namespace
metadata:
  name: staging
  labels:
    pod-security.kubernetes.io/enforce: baseline  # ← baseline: less strict, a good starting point
    pod-security.kubernetes.io/warn: restricted   # ← warn when staging would fail restricted

---
# System components (CNI, CSI drivers): need privileged access — no restrictions
apiVersion: v1
kind: Namespace
metadata:
  name: kube-system
  labels:
    pod-security.kubernetes.io/enforce: privileged  # ← no restrictions; system components need this
```

```bash
kubectl apply -f pss-namespaces.yaml

# Test: try to create a pod that runs as root in the restricted production namespace
kubectl run root-pod \
  --image=nginx:1.25 \
  -n production \
  --restart=Never
# Error from server (Forbidden): pods "root-pod" is forbidden:
# violates PodSecurity "restricted:latest":
#   allowPrivilegeEscalation != false, runAsNonRoot != true, ...

# Dry-run an existing Deployment against the restricted policy without changing anything
kubectl apply -n production \
  --dry-run=server \
  -f deployment.yaml
# Warns if the Deployment would violate the policy

# Simulate PSS enforcement against existing workloads in a namespace
# (shows what would break if you enforced the restricted policy today)
kubectl label namespace production \
  pod-security.kubernetes.io/enforce=restricted \
  --dry-run=server
```

---

## 3. Kyverno Policy — Enforce Security Best Practices at Admission

```yaml
# kyverno-policies.yaml
# Kyverno is a Kubernetes-native policy engine — policies are pure YAML, no Rego needed
# Install Kyverno first: helm install kyverno kyverno/kyverno -n kyverno --create-namespace

---
# Policy 1: Block containers running as root
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-non-root-user
spec:
  validationFailureAction: Enforce       # ← Enforce = reject; Audit = log only
  rules:
  - name: check-runAsNonRoot
    match:
      any:
      - resources:
          kinds: ["Pod"]
    validate:
      message: "Containers must set runAsNonRoot: true. Running as root is not allowed."
      pattern:
        spec:
          containers:
          - securityContext:
              runAsNonRoot: true         # ← every container must have this set

---
# Policy 2: Require resource requests and limits on every container
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-resource-limits
spec:
  validationFailureAction: Enforce
  rules:
  - name: check-resources
    match:
      any:
      - resources:
          kinds: ["Pod"]
    exclude:
      any:
      - resources:
          namespaces:
          - kube-system                  # ← exclude system namespaces
          - monitoring
    validate:
      message: "CPU and memory requests and limits are required on all containers."
      pattern:
        spec:
          containers:
          - resources:
              requests:
                memory: "?*"             # ← "?*" means: non-empty string required
                cpu: "?*"
              limits:
                memory: "?*"
                cpu: "?*"

---
# Policy 3: Mutate — automatically add the team label if it's missing
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: add-default-labels
spec:
  rules:
  - name: add-team-label
    match:
      any:
      - resources:
          kinds: ["Pod"]
    mutate:                              # ← mutate: modify the resource before it's stored
      patchStrategicMerge:
        metadata:
          labels:
            +(managed-by): kyverno      # ← "+" prefix: only add if the label doesn't exist
```

```bash
# Install Kyverno
helm repo add kyverno https://kyverno.github.io/kyverno/
helm repo update
helm install kyverno kyverno/kyverno \
  --namespace kyverno \
  --create-namespace

kubectl apply -f kyverno-policies.yaml

# Test the non-root policy: this should be rejected
kubectl run root-test \
  --image=nginx:1.25 \
  --restart=Never
# Error: admission webhook "validate.kyverno.svc" denied the request:
# Containers must set runAsNonRoot: true.

# Check Kyverno policy reports for existing violations
kubectl get policyreport -A

# View violations in detail
kubectl describe policyreport -n production
```

---

## 4. Image Scanning With Trivy Before Deployment

```bash
# trivy-scanning.sh
# Scan container images for CVEs before pushing to your registry
# Trivy is the most popular open-source scanner — install: brew install trivy

# Scan an image and show all vulnerabilities
trivy image nginx:1.25

# Scan only for HIGH and CRITICAL severity vulnerabilities (CI/CD mode)
trivy image --severity HIGH,CRITICAL nginx:1.25

# Exit with non-zero code if HIGH or CRITICAL CVEs are found
# Use this in CI/CD to block deployments of vulnerable images
trivy image \
  --severity HIGH,CRITICAL \
  --exit-code 1 \                        # ← fail the CI job if vulnerabilities found
  myapp:1.4.2

# Scan a local Dockerfile before building
trivy config --severity HIGH,CRITICAL ./Dockerfile

# Scan a local directory for misconfigured IaC files (K8s YAML, Helm charts)
trivy config --severity HIGH,CRITICAL ./k8s/

# Output as JSON for parsing in CI pipelines
trivy image \
  --format json \
  --output trivy-report.json \
  myapp:1.4.2

# Scan an image by digest (immutable — exactly what you deployed)
trivy image myapp@sha256:abc123def456...
```

```yaml
# ci-pipeline-scan.yaml
# Example: GitHub Actions step that blocks merges if critical CVEs are found
# (Illustrative — adapt to your CI system)

# In your .github/workflows/ci.yml:
# - name: Scan image for vulnerabilities
#   uses: aquasecurity/trivy-action@master
#   with:
#     image-ref: myapp:${{ github.sha }}
#     format: table
#     exit-code: '1'
#     severity: HIGH,CRITICAL
#     ignore-unfixed: true               # ← skip CVEs with no fix available yet
```

---

## 5. Secrets Encryption and External Secrets Operator

```yaml
# external-secrets.yaml
# External Secrets Operator (ESO) syncs secrets from AWS Secrets Manager into K8s Secrets
# Install ESO: helm install external-secrets external-secrets/external-secrets -n external-secrets-system

---
# SecretStore: defines HOW to connect to the external secret backend (AWS Secrets Manager)
# Uses IRSA (pod's IAM role) — no static credentials stored in the cluster
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secretsmanager
  namespace: production
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: eso-sa                 # ← Service Account with IRSA annotation pointing to IAM role

---
# ExternalSecret: maps specific keys from AWS Secrets Manager to a K8s Secret
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: database-credentials
  namespace: production
spec:
  refreshInterval: 1h                    # ← re-sync from AWS Secrets Manager every hour
  secretStoreRef:
    name: aws-secretsmanager
    kind: SecretStore
  target:
    name: database-credentials           # ← name of the K8s Secret that will be created/updated
    creationPolicy: Owner                # ← ESO owns this secret; it's deleted when the ExternalSecret is
  data:
  - secretKey: DB_PASSWORD               # ← key name in the K8s Secret
    remoteRef:
      key: production/myapp/database     # ← path in AWS Secrets Manager
      property: password                 # ← specific field within the JSON secret value
  - secretKey: DB_USERNAME
    remoteRef:
      key: production/myapp/database
      property: username
```

```bash
# Install External Secrets Operator
helm repo add external-secrets https://charts.external-secrets.io
helm repo update
helm install external-secrets \
  external-secrets/external-secrets \
  --namespace external-secrets-system \
  --create-namespace

kubectl apply -f external-secrets.yaml

# Watch the ExternalSecret sync status
kubectl get externalsecret database-credentials -n production

# The status should show:
# Ready    True    SecretSynced    Secret was synced

# Verify the K8s Secret was created (values are base64 encoded in the Secret)
kubectl get secret database-credentials -n production
kubectl describe secret database-credentials -n production
# Note: never use `kubectl get secret ... -o yaml` in production — it exposes the values in your terminal history

# Test encryption at rest (if configured via EncryptionConfiguration):
# The raw etcd data should be prefixed with "k8s:enc:aescbc:v1:" not plaintext
# etcdctl get /registry/secrets/production/database-credentials | hexdump -C | head
```

---

## 📂 Navigation

**In this folder:**
| File | |
|---|---|
| [📖 Theory.md](./Theory.md) | Full explanation |
| [⚡ Cheatsheet.md](./Cheatsheet.md) | Quick reference |
| [🎯 Interview_QA.md](./Interview_QA.md) | Interview prep |
| 💻 **Code_Example.md** | ← you are here |

⬅️ **Prev:** [Monitoring and Logging](../22_Monitoring_and_Logging/Code_Example.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Service Mesh](../24_Service_Mesh/Code_Example.md)
🏠 **[Home](../../README.md)**
