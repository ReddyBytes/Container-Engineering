# Module 26 — Helm Charts Interview Q&A

---

## Q1: What is Helm and what problem does it solve in Kubernetes?

**Answer:**

Helm is the package manager for Kubernetes. It solves three problems:

1. **Multi-file complexity**: a real application needs 5–15+ Kubernetes manifests (Deployment, Service, ConfigMap, Secret, Ingress, HPA, etc.). Managing them individually with `kubectl apply` is error-prone.

2. **Environment configuration**: the same app needs different settings for dev/staging/prod (different replica counts, resource limits, image tags). Helm templates with values files handle this elegantly.

3. **Lifecycle management**: Helm tracks release history, enabling atomic upgrades and reliable rollbacks. `helm rollback` restores the previous known-good state, including all associated Kubernetes objects.

Without Helm, you either have raw YAML files for every environment (lots of copy-paste), Kustomize overlays (good but no lifecycle tracking), or custom scripting.

---

## Q2: What is the difference between a chart version and an app version in Chart.yaml?

**Answer:**

- **`version`** (chart version): the version of the Helm chart itself — its templates, structure, and helpers. Change this when you modify the chart templates, add new configurable values, or change chart behavior. Follows semver.

- **`appVersion`** (application version): the version of the application being packaged. This is informational — it appears in `helm list` output and is typically used as the default image tag in values.yaml. Changing the application's Docker image does not require changing the chart version.

Example: you might release chart version `1.5.0` of your `myapp` chart to package application version `3.0.1`. When you upgrade to application `3.0.2`, you'd update `appVersion: "3.0.2"` and might bump chart version to `1.5.1` (patch) if you only changed the default image tag.

---

## Q3: What is a Helm release and how does Helm track state?

**Answer:**

A **release** is a deployed instance of a Helm chart. The same chart can be installed multiple times under different release names — each is an independent release.

Helm stores release state as Kubernetes Secrets in the same namespace as the release:
```
secret: sh.helm.release.v1.myapp.v1  (revision 1)
secret: sh.helm.release.v1.myapp.v2  (revision 2, after upgrade)
```

Each Secret contains the full chart metadata, values used, and rendered manifests for that revision — base64 encoded and gzip compressed. This is how Helm can:
- Show history (`helm history`)
- Diff between revisions
- Rollback to any previous revision (it has the exact manifests from that revision)

---

## Q4: Explain the difference between `helm upgrade` and `helm upgrade --install`.

**Answer:**

- **`helm upgrade myapp ./chart`**: upgrades an existing release. Fails with an error if the release doesn't exist.

- **`helm upgrade --install myapp ./chart`**: upgrades if the release exists, installs if it doesn't. This is **idempotent** — you can run it safely whether the release exists or not.

`helm upgrade --install` is the recommended pattern for CI/CD pipelines and GitOps workflows where you don't want to branch logic on whether the release already exists. The pipeline just runs `helm upgrade --install` every time.

---

## Q5: What are Helm hooks and give an example use case?

**Answer:**

Helm hooks are Kubernetes Jobs, Pods, or ConfigMaps that run at specific points in the Helm lifecycle (before/after install, upgrade, rollback, delete). They are annotated with `helm.sh/hook`.

Example use cases:

1. **Database migrations** (`pre-upgrade` hook): run `python manage.py migrate` before the application upgrade so the new app version starts with a migrated database. If the migration fails, the upgrade fails before applying new manifests.

2. **Test after install** (`test` hook): a Job that sends HTTP requests to verify the app is responding correctly after install. Run with `helm test myapp`.

3. **Backup before delete** (`pre-delete` hook): dump the database before `helm uninstall` permanently removes the stateful resources.

4. **Certificate generation** (`pre-install` hook): generate TLS certificates and store as Secrets before the first install.

Key hook annotations:
- `helm.sh/hook`: lifecycle event
- `helm.sh/hook-weight`: ordering (lower number runs first)
- `helm.sh/hook-delete-policy`: when to clean up the hook resource

---

## Q6: How do you pass sensitive values (passwords, API keys) to Helm without storing them in values.yaml?

**Answer:**

**Never store sensitive values in values.yaml** (which is committed to Git).

Options:

1. **`--set` at runtime** (for CI/CD):
   ```bash
   helm upgrade myapp ./chart \
     --set db.password="${DB_PASSWORD}"  # from environment variable
   ```

2. **Separate values file not committed to Git**:
   ```bash
   helm upgrade myapp ./chart \
     -f values.yaml \
     -f secrets.yaml   # gitignored file with sensitive values
   ```

3. **Kubernetes Secrets as pre-existing resources**: don't put the secret in Helm at all. Create the Secret separately (via Sealed Secrets, External Secrets, or Vault). Reference it by name in the chart's templates:
   ```yaml
   env:
   - name: DB_PASSWORD
     valueFrom:
       secretKeyRef:
         name: {{ .Values.db.existingSecret }}
         key: password
   ```

4. **Helm Secrets plugin**: integrates SOPS encryption into Helm — encrypts values files that can be safely committed to Git.

Option 3 is the cleanest for production GitOps.

---

## Q7: What is the `nindent` function and why is it needed in templates?

**Answer:**

`nindent N` adds `N` spaces of indentation to each line of the input, plus a newline at the beginning. It is critical because YAML is indentation-sensitive.

Example problem without proper indentation:
```yaml
# values.yaml
resources:
  limits:
    cpu: 500m
    memory: 256Mi

# template (broken)
resources:
{{ toYaml .Values.resources }}
```

The output would not be indented correctly. With `nindent`:
```yaml
resources:
{{- toYaml .Values.resources | nindent 10 }}
```

Produces correctly indented YAML. The `{{-` (with hyphen) also trims the preceding whitespace/newline.

Common usage:
- `| nindent 4` for top-level YAML keys
- `| nindent 6` for items under a list
- `| nindent 8` for deeper nesting

Getting indentation wrong produces invalid YAML — a very common beginner mistake with Helm templates.

---

## Q8: What is Helmfile and when would you use it?

**Answer:**

Helmfile is a declarative spec for multiple Helm releases. It solves the problem of managing many charts across namespaces with different values files.

Without Helmfile, deploying a full environment might require:
```bash
helm upgrade --install postgres bitnami/postgresql -f postgres-prod.yaml -n databases
helm upgrade --install redis bitnami/redis -f redis-prod.yaml -n databases
helm upgrade --install myapp ./charts/myapp -f myapp-prod.yaml -n production
# ... 10 more commands
```

With Helmfile, it's one file and one command:
```bash
helmfile sync
```

Use Helmfile when:
- You manage multiple charts per environment
- You want to see a diff before applying (`helmfile diff`)
- You want environment-specific releases in a single file
- You want to template values using environment variables

---

## Q9: What is `helm lint` and when should you run it?

**Answer:**

`helm lint ./mychart` validates a chart for common errors:
- Malformed YAML in templates
- Missing required fields in Chart.yaml
- Template syntax errors
- Best practice violations

It's a fast, zero-cluster check that should run in CI before every chart publish or deploy:

```bash
# Basic lint
helm lint ./mychart

# Lint with specific values (more realistic — catches conditional errors)
helm lint ./mychart -f values-production.yaml

# Return non-zero exit code on any issue (for CI)
helm lint ./mychart --strict
```

Combined with `helm template ./mychart | kubectl apply --dry-run=client -f -`, you get a comprehensive pre-deploy validation that catches most errors before they reach the cluster.

---

## Q10: Explain chart dependencies (subcharts) in Helm.

**Answer:**

Chart dependencies are other Helm charts that your chart depends on. Declared in `Chart.yaml`:

```yaml
dependencies:
- name: postgresql
  version: "14.x.x"
  repository: https://charts.bitnami.com/bitnami
  condition: postgresql.enabled    # only install if .Values.postgresql.enabled=true
```

```bash
helm dependency update   # downloads charts to charts/ directory
```

When you `helm install`, Helm installs your chart AND all dependencies. Values for subcharts are scoped under their chart name:
```yaml
# values.yaml — configure the postgresql subchart
postgresql:
  enabled: true
  auth:
    postgresPassword: "secret"
  primary:
    persistence:
      size: 10Gi
```

Use cases: an application chart that bundles PostgreSQL, Redis, or other infrastructure components so users can install everything with one `helm install` command.

---

## Q11: How do you use Helm in a GitOps workflow with ArgoCD?

**Answer:**

ArgoCD has native Helm support — you point an Application at a Helm chart (in a Helm registry or as a directory in Git), and ArgoCD renders it and syncs.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
spec:
  source:
    repoURL: https://charts.bitnami.com/bitnami
    chart: postgresql
    targetRevision: "14.0.0"
    helm:
      releaseName: postgres
      values: |
        auth:
          postgresPassword: ""
        primary:
          persistence:
            size: 50Gi
```

Or point at a chart in a Git repo:
```yaml
source:
  repoURL: https://github.com/myorg/charts
  path: charts/myapp
  targetRevision: main
  helm:
    valueFiles:
    - environments/production/values.yaml
```

ArgoCD runs `helm template` under the hood — it renders the chart and applies the manifests via kubectl. The actual Helm release tracking (Helm Secrets) lives in ArgoCD's namespace, not the target namespace.

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Helm Charts Theory](./Theory.md) |
| Cheatsheet | [Helm Charts Cheatsheet](./Cheatsheet.md) |
| Code Example | [Helm Charts Code Example](./Code_Example.md) |
| Next Module | [27 — Advanced Scheduling](../27_Advanced_Scheduling/Theory.md) |
