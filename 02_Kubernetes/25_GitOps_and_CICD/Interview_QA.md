# Module 25 — GitOps and CI/CD Interview Q&A

---

## Q1: What is GitOps and how does it differ from traditional CI/CD?

**Answer:**

GitOps is an operational model where the desired state of a Kubernetes cluster is stored in a Git repository, and an automated agent continuously reconciles the actual cluster state with what Git says it should be.

Key differences from traditional CI/CD:

| | Traditional CI/CD (push) | GitOps (pull) |
|---|---|---|
| Who applies changes | CI pipeline (external) | Agent inside cluster |
| Credentials | Pipeline holds kubeconfig | Cluster credentials stay in cluster |
| Drift detection | Only on next deployment | Continuous |
| Audit trail | Pipeline logs | Git commit history |
| Rollback | Re-run old pipeline | `git revert` |
| Source of truth | What's running in cluster | Git |

GitOps enforces that every cluster change goes through Git — including emergency hotfixes. This creates a complete, reviewable audit trail.

---

## Q2: What is drift detection and why is it important?

**Answer:**

Drift is when the actual cluster state diverges from the desired state in Git. This can happen when:
- Someone runs `kubectl edit` or `kubectl patch` manually
- A controller modifies a resource
- An emergency fix is applied directly without a Git commit

ArgoCD/Flux continuously compare the cluster state against Git. When they differ, the app is marked `OutOfSync`. With `selfHeal: true`, the agent automatically reverts the manual change.

Why it matters: without drift detection, the cluster gradually accumulates undocumented manual changes. When something breaks, nobody knows what the "correct" state should be. With GitOps, Git is always the truth — any deviation is immediately visible and correctable.

---

## Q3: What is the difference between ArgoCD and Flux?

**Answer:**

Both are GitOps operators that watch Git repositories and sync manifests to Kubernetes clusters. Main differences:

| | ArgoCD | Flux |
|---|---|---|
| Interface | Rich web UI | CLI-focused (basic UI via Weave GitOps) |
| Architecture | Monolithic (all-in-one) | Modular (separate controllers) |
| Helm support | Via App source | Dedicated HelmRelease CRD |
| Image automation | External tool needed | Built-in ImageAutomation controller |
| Multi-cluster | ApplicationSet | Built-in |
| CNCF status | Graduated | Graduated |
| Learning curve | Gentler (UI helps) | Steeper (more composable) |

ArgoCD tends to be chosen by teams wanting a good UI and simpler setup. Flux is preferred by teams wanting a more Kubernetes-native, composable approach.

---

## Q4: Why is push-based CI/CD considered less secure than pull-based GitOps?

**Answer:**

In push-based CI/CD, the pipeline (GitHub Actions, Jenkins, etc.) has Kubernetes credentials (`kubeconfig`) to run `kubectl apply`. These credentials:
- Exist outside the cluster
- Must be stored as CI/CD secrets
- Are accessible to anyone who can run the CI pipeline
- Could be stolen if the CI/CD platform is compromised
- Often have broad permissions to deploy anywhere

In pull-based GitOps (ArgoCD/Flux), the agent runs *inside* the cluster. The cluster talks out to Git (read-only), but nothing external has write access to the cluster. The cluster credentials never leave the cluster. The CI pipeline only needs write access to a Git repository — not to Kubernetes.

This significantly reduces the blast radius if CI/CD credentials are compromised.

---

## Q5: How do you handle Kubernetes Secrets in a GitOps workflow?

**Answer:**

You cannot commit plaintext secrets to Git. Three main approaches:

**1. Sealed Secrets**: encrypt the Secret with the cluster's public key. The encrypted `SealedSecret` YAML is safe to store in Git. The controller in the cluster decrypts it. Downside: if you need to rotate the sealing key or recover the cluster, the process is complex.

**2. External Secrets Operator**: store secret values in an external system (AWS Secrets Manager, GCP Secret Manager, HashiCorp Vault). Commit only a `ExternalSecret` resource to Git, which describes where to find the secret. The operator syncs the actual value into a K8s Secret. Secret values never touch Git.

**3. SOPS + Age/GPG**: encrypt secret YAML files with SOPS (Mozilla) before committing. Flux has native SOPS decryption support. Requires managing encryption keys.

External Secrets Operator is the most operationally clean for production: secrets are in a managed secret store with access controls, rotation, and audit logging.

---

## Q6: What is an ArgoCD ApplicationSet and when would you use it?

**Answer:**

ApplicationSet is an ArgoCD CRD that generates multiple `Application` objects from a template and a set of parameters (a generator).

Use cases:
- **Multi-environment**: generate one Application per environment (dev, staging, prod) from the same template, pointing to different paths in Git
- **Multi-cluster**: deploy the same app to 50 clusters automatically
- **Per-team apps**: generate one Application per team directory in a monorepo
- **PR environments**: create a temporary Application for every open pull request (with a Git generator)

Without ApplicationSet, managing 20 environments means 20 Application objects written by hand. With ApplicationSet, you write the template once and list the environments. Adding a new environment is one line in the generator list.

---

## Q7: Explain the typical GitOps pipeline from code commit to production.

**Answer:**

1. **Developer** opens a PR with application code changes
2. **CI pipeline** (GitHub Actions) runs: unit tests, build Docker image, security scan
3. On PR merge to `main`, CI **builds and pushes** the Docker image with the commit SHA as tag: `myapp:abc1234`
4. CI (or a separate automation) **updates the image tag** in the GitOps manifests repository: changes `image: myapp:old123` to `image: myapp:abc1234`
5. The image tag update goes through a **PR in the manifests repo** (optional, for production gates) or auto-commits directly
6. **ArgoCD** detects the change in the manifests repo (polling every 3 minutes, or via webhook)
7. ArgoCD **syncs** the change — applies the updated Deployment to the cluster
8. Kubernetes **performs a rolling update** — new pods come up, old pods terminate
9. ArgoCD **monitors health** — if the rollout fails (pods not Ready), it marks the app as Degraded and alerts

The key separation: the application repo and the manifests repo are separate. The CI pipeline never touches the cluster directly.

---

## Q8: What does `selfHeal: true` do in ArgoCD, and when would you disable it?

**Answer:**

With `selfHeal: true`, ArgoCD automatically reverts any manual changes made directly to the cluster. If someone runs `kubectl scale deployment myapp --replicas=10` while Git says `replicas: 3`, ArgoCD will revert it back to 3 within minutes.

This enforces the GitOps contract: Git is the only way to make changes.

When to disable it:
- **During incident response**: if you need to make quick cluster changes and don't have time to go through Git, temporarily disabling selfHeal lets you patch things live
- **HPA-managed replicas**: if HPA is scaling your deployment, selfHeal might fight HPA by reverting replica counts. Use ArgoCD's `ignoreDifferences` to exclude the replicas field.
- **Learning environments**: teams learning GitOps might want to make manual experiments

Production recommendation: enable selfHeal, but have a documented process for emergency situations.

---

## Q9: What is Kustomize and how does it integrate with ArgoCD?

**Answer:**

Kustomize is a Kubernetes-native configuration customization tool. It lets you have a `base` configuration (the common deployment, service, etc.) and `overlays` for each environment that patch the base.

```
base/
  deployment.yaml    (replicas: 1)
  service.yaml
overlays/
  production/
    kustomization.yaml
    patch-replicas.yaml  (replicas: 10, image: myapp:1.4.2)
```

ArgoCD natively supports Kustomize — point an Application at the overlay path, and ArgoCD runs `kustomize build` before applying. No Helm required.

This pattern works well for GitOps: the base manifests are shared, environment-specific changes are small patches, and the full rendered manifests are never stored in Git (they're generated at sync time).

---

## Q10: How do you roll back with GitOps if a bad deployment goes out?

**Answer:**

In GitOps, rollback is a Git operation:

**Option 1: Git revert**
```bash
git revert <bad-commit-sha>
git push origin main
# ArgoCD detects the revert commit and syncs → rolls back
```

**Option 2: ArgoCD rollback**
```bash
# Roll back to a previous revision in ArgoCD's history
argocd app rollback myapp <revision-number>
argocd app history myapp  # see revision numbers
```

Note: `argocd app rollback` applies the previous manifest version from ArgoCD's history, but if `selfHeal: true` is enabled, ArgoCD will re-sync to Git state shortly after. For the rollback to stick, you need to also update Git.

Best practice: the `git revert` approach is preferred — it creates a new commit that undoes the bad change, maintaining a clean audit trail.

---

## Q11: What is the difference between a "push-based" and "pull-based" image update in GitOps?

**Answer:**

**Push-based image update**: the CI pipeline, after building and pushing the image, commits the updated image tag to the GitOps manifests repo. CI "pushes" the change into Git. This is the most common pattern.

**Pull-based image update (Flux ImageAutomation)**: Flux's Image Automation controller watches the container registry. When it detects a new image tag matching a policy (e.g., `semver: '>=1.0.0'`), it automatically commits the updated image tag to the GitOps repo. No CI involvement needed for the manifest update.

Flux's approach is more automated but requires:
- `ImageRepository` CRD: define what registry to watch
- `ImagePolicy` CRD: define what tag pattern to follow
- `ImageUpdateAutomation` CRD: define how to commit the update

This enables true end-to-end automation: push an image → Flux detects it → Flux updates Git → Flux syncs the cluster. The developer never manually updates image tags.

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [GitOps and CI/CD Theory](./Theory.md) |
| Cheatsheet | [GitOps and CI/CD Cheatsheet](./Cheatsheet.md) |
| Next Module | [26 — Helm Charts](../26_Helm_Charts/Theory.md) |
