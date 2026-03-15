# Module 23 — Kubernetes Security Interview Q&A

---

## Q1: What replaced Pod Security Policies (PSP) in Kubernetes, and why were PSPs removed?

**Answer:**

PSPs were replaced by **Pod Security Standards (PSS)** enforced by the built-in `PodSecurity` admission controller (stable in K8s 1.25, which also removed PSPs).

PSPs were removed because they were:
- Confusing to configure correctly (enabling a PSP didn't automatically apply it — you also needed RBAC bindings)
- Easy to misconfigure with subtle security gaps
- Not consistent across clusters
- The activation mechanism (you had to create a PSP and bind it via RBAC) was non-intuitive

PSS is simpler: apply a label to a namespace specifying the enforcement level (`privileged`, `baseline`, `restricted`). The admission controller automatically validates pods against that level. No RBAC required.

---

## Q2: What does `readOnlyRootFilesystem: true` protect against?

**Answer:**

It makes the container's root filesystem read-only. Even if an attacker achieves code execution inside the container, they cannot:
- Write malware or backdoors to the filesystem
- Modify configuration files
- Create new executable files
- Write to `/tmp` (unless a separate tmpfs volume is mounted there explicitly)

This significantly limits what an attacker can do after initial compromise. Combined with `allowPrivilegeEscalation: false` and dropped capabilities, the container becomes much harder to exploit as a pivot point.

Note: applications that need to write to disk should use mounted volumes (emptyDir for scratch space, PVCs for persistent data), not the container filesystem.

---

## Q3: What is the difference between a validating and mutating admission controller?

**Answer:**

Both intercept requests to the Kubernetes API server before resources are persisted to etcd.

**Mutating admission controllers** run first and can modify the incoming object. Examples:
- Inject a sidecar container (Istio, Linkerd)
- Add default labels/annotations
- Set default resource limits if not specified
- Add imagePullSecrets

**Validating admission controllers** run after mutating controllers and can only approve or reject the request. Examples:
- Reject pods without resource limits
- Reject images with `:latest` tag
- Reject pods that would run as root

Both types can be implemented as **webhooks** (external HTTP servers) or built-in to the API server. Kyverno and OPA/Gatekeeper work via webhooks.

---

## Q4: What are Linux capabilities in the context of container security?

**Answer:**

Linux traditionally had two privilege levels: root (UID 0, can do anything) and non-root. Linux capabilities split root's powers into ~40 individual capabilities that can be granted or removed independently.

Examples:
- `CAP_NET_BIND_SERVICE` — bind to ports < 1024
- `CAP_NET_ADMIN` — configure network interfaces, routes
- `CAP_SYS_PTRACE` — trace other processes (debugging, but also attacker tool)
- `CAP_SYS_ADMIN` — a very broad capability that enables many dangerous operations
- `CAP_CHOWN` — change file ownership

In Kubernetes:
```yaml
capabilities:
  drop:
  - ALL              # remove all default capabilities
  add:
  - NET_BIND_SERVICE # add back only what's needed
```

Dropping ALL capabilities means even a process running as root inside the container has very limited power. Combined with `runAsNonRoot: true`, this is a strong defense.

---

## Q5: What is OPA/Gatekeeper and how does Kyverno differ?

**Answer:**

Both are policy engines for Kubernetes that enforce organizational policies as code.

**OPA/Gatekeeper:**
- Open Policy Agent is a general-purpose policy engine
- Policies written in **Rego** (a declarative query language)
- Powerful but steep learning curve — Rego is not YAML
- `ConstraintTemplate` defines the policy structure; `Constraint` applies it
- Works as a validating webhook

**Kyverno:**
- Kubernetes-native policy engine
- Policies written in **YAML** (same format as all K8s manifests)
- Lower barrier to entry for K8s teams
- Can validate (reject), mutate (modify), and generate (create resources)
- Example: auto-create a NetworkPolicy when a namespace is created

For teams already fluent in Rego or with complex policy logic, OPA/Gatekeeper is more powerful. For Kubernetes-focused teams wanting simple, readable policies, Kyverno is often preferred.

---

## Q6: Why are Kubernetes Secrets not truly secret by default, and how do you fix it?

**Answer:**

By default, Kubernetes Secrets are stored in etcd base64-encoded — **not encrypted**. Base64 is an encoding, not encryption. Anyone with etcd read access can decode all secrets trivially.

Additionally, Secrets are transmitted unencrypted between etcd and the API server unless TLS is configured (which it should be, but misconfigured clusters exist).

How to fix:
1. **Encryption at rest**: configure `EncryptionConfiguration` on the API server to encrypt Secrets in etcd with AES-CBC or use a KMS provider
2. **KMS integration**: use AWS KMS, GCP KMS, or Azure Key Vault as the encryption key provider so keys are managed externally
3. **External secret stores**: use External Secrets Operator to sync secrets from AWS Secrets Manager, HashiCorp Vault, etc. — the secret value never lives in etcd
4. **Restrict etcd access**: only the API server should access etcd; protect with mTLS and firewall rules

---

## Q7: What is Falco and what does runtime security mean?

**Answer:**

Most Kubernetes security controls are preventive — they stop bad things from being deployed. **Runtime security** is about detecting malicious activity after a container is running.

**Falco** (CNCF project) monitors Linux system calls using eBPF or a kernel module. It watches every process inside containers and alerts when behavior matches suspicious patterns:

- A shell is spawned inside a container (`kubectl exec` or RCE)
- A process reads `/etc/shadow` or Kubernetes service account tokens
- A process writes to a binary directory (`/usr/bin`, `/bin`)
- A container connects to an unexpected IP address
- A process runs a package manager (`apt`, `yum`)

Why this matters: even if an attacker gets code execution in a container, Falco will alert within seconds. Combined with automated response (kill the pod, isolate the node), this can contain breaches before significant damage occurs.

---

## Q8: What is seccomp and how does it differ from capabilities?

**Answer:**

Both limit what container processes can do, but at different levels:

**Capabilities**: Linux permission model — coarse-grained, ~40 specific operations that can be individually granted/removed.

**Seccomp (Secure Computing mode)**: system call filtering — a list of which Linux system calls a process is allowed to make. A process trying to call a blocked syscall receives EPERM or is killed.

The `RuntimeDefault` seccomp profile (enabled by setting `seccompProfile.type: RuntimeDefault`) uses the container runtime's default filter, which blocks ~100 potentially dangerous syscalls while allowing the 300+ that normal applications need.

Why use both: capabilities block specific operations (bind to port 80), while seccomp blocks specific syscalls (ptrace, reboot, load kernel module). They complement each other.

---

## Q9: How do you audit what images are running in your cluster and check for vulnerabilities?

**Answer:**

```bash
# List all unique images running in the cluster
kubectl get pods -A -o jsonpath='{range .items[*]}{.spec.containers[*].image}{"\n"}{end}' | sort -u

# Scan with Trivy (after collecting image list)
trivy image myapp:1.4.2 --severity HIGH,CRITICAL

# Continuous scanning: use tools like:
# - Trivy Operator (runs as K8s operator, scans images in cluster)
# - Snyk
# - AWS ECR scanning, GCR scanning (cloud-native)
```

For continuous scanning, **Trivy Operator** runs in the cluster and creates `VulnerabilityReport` CRDs for every running workload's images, queryable via kubectl.

---

## Q10: A developer wants to run a container as root because the app requires it. What do you say?

**Answer:**

Challenge the assumption first. Most applications that "need root" actually need one of:
- A specific capability (e.g., `NET_BIND_SERVICE` for port < 1024 — or just configure the app to use port 8080)
- Write access to a specific directory (use a mounted volume with correct `fsGroup`)
- File ownership (set correct ownership in the Dockerfile)

If root is genuinely required (some legacy apps), mitigate:
1. Enable `allowPrivilegeEscalation: false` — root inside the container can't become root on the host
2. Drop all capabilities and add back only what's needed
3. Enable seccomp profile
4. Consider user namespaces (K8s 1.25+ alpha) — root inside maps to non-root on host
5. Put the pod in an isolated namespace with strict NetworkPolicies
6. Use Falco to monitor it aggressively

Document why root is needed and set a target to refactor the app to be rootless.

---

## Q11: What is the difference between `audit`, `warn`, and `enforce` modes in Pod Security Standards?

**Answer:**

All three check pods against the configured security level (baseline or restricted), but they differ in what happens when a violation is found:

- **enforce**: the pod is **rejected**. The API server returns an error and the pod is not created. Use in production once you've confirmed no violations.
- **warn**: the pod is **allowed** but `kubectl` shows a warning message. Good during migration — you see what would be rejected without breaking anything.
- **audit**: the pod is **allowed** but the violation is **logged in the API server audit log**. Useful for discovering violations without any user-visible impact.

Best practice for adopting PSS:
1. Start with `warn` and `audit` — observe violations
2. Fix violations in your workloads
3. Switch to `enforce` once clean

You can set all three simultaneously on the same namespace, each at potentially different levels.

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Security Theory](./Theory.md) |
| Cheatsheet | [Security Cheatsheet](./Cheatsheet.md) |
| Next Module | [24 — Service Mesh](../24_Service_Mesh/Theory.md) |
