# Module 26 — Helm Charts Cheatsheet

## Repository Management

```bash
# Add popular repositories
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add stable https://charts.helm.sh/stable

helm repo update             # refresh all repos
helm repo list               # show configured repos
helm repo remove bitnami     # remove a repo

# Search
helm search repo bitnami/postgresql
helm search repo nginx --versions   # list all versions
helm search hub grafana             # search Artifact Hub (all public charts)
```

---

## Install / Upgrade / Rollback

```bash
# Install
helm install <name> <chart>
helm install myapp ./mychart
helm install myapp bitnami/nginx
helm install myapp bitnami/nginx -n production --create-namespace
helm install myapp bitnami/nginx -f values.yaml
helm install myapp bitnami/nginx --set replicaCount=3
helm install myapp bitnami/nginx --version 15.0.0     # pin chart version

# Dry run (validate without applying)
helm install myapp bitnami/nginx --dry-run

# Template (render to stdout, no install)
helm template myapp bitnami/nginx -f values.yaml

# Upgrade
helm upgrade myapp bitnami/nginx -f values.yaml
helm upgrade myapp bitnami/nginx --set image.tag=1.5
helm upgrade --install myapp bitnami/nginx   # idempotent (install if missing)
helm upgrade myapp bitnami/nginx --atomic    # rollback automatically on failure
helm upgrade myapp bitnami/nginx --wait      # wait for pods to be Ready

# Rollback
helm rollback myapp          # to previous revision
helm rollback myapp 2        # to specific revision

# History
helm history myapp           # show all revisions
helm history myapp -n production

# Status
helm status myapp
helm status myapp -n production
```

---

## Inspection Commands

```bash
# List releases
helm list
helm list -A                              # all namespaces
helm list --deployed                      # only deployed
helm list --failed                        # only failed

# Values
helm get values myapp                     # user-supplied only
helm get values myapp --all               # all (including defaults)

# Rendered manifests
helm get manifest myapp

# Chart info
helm show chart bitnami/postgresql
helm show values bitnami/postgresql       # all configurable values
helm show readme bitnami/postgresql
helm show all bitnami/postgresql

# Uninstall
helm uninstall myapp
helm uninstall myapp -n production
helm uninstall myapp --keep-history       # keep history for rollback
```

---

## Create and Develop a Chart

```bash
# Scaffold a new chart
helm create mychart

# Lint (check for errors)
helm lint ./mychart
helm lint ./mychart -f values-production.yaml

# Package chart into .tgz
helm package ./mychart

# Push to OCI registry (Helm 3.8+)
helm push mychart-1.0.0.tgz oci://registry.example.com/charts

# Dependencies
helm dependency update ./mychart          # download charts/ dependencies
helm dependency list ./mychart            # show dependencies
```

---

## values.yaml Patterns

```yaml
# Scalar values
replicaCount: 3
nameOverride: ""

# Nested object
image:
  repository: myapp
  tag: "1.4.2"
  pullPolicy: IfNotPresent

# Conditional feature
ingress:
  enabled: true
  className: nginx
  host: app.example.com
  tls:
    enabled: true
    secretName: app-tls

# List
extraEnv:
- name: LOG_LEVEL
  value: info
- name: PORT
  value: "8080"

# Resource limits
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 256Mi
```

---

## Template Syntax Quick Reference

```yaml
# Access values
{{ .Values.replicaCount }}
{{ .Values.image.repository }}

# Chart and release metadata
{{ .Chart.Name }}
{{ .Chart.Version }}
{{ .Release.Name }}
{{ .Release.Namespace }}

# Conditional
{{- if .Values.ingress.enabled }}
  # ingress yaml
{{- end }}

# Default value
{{ .Values.image.tag | default "latest" }}

# Quote strings
{{ .Values.config.value | quote }}

# Indent (critical for nested YAML)
{{- toYaml .Values.resources | nindent 10 }}

# Include a named template
{{ include "mychart.fullname" . }}
{{ include "mychart.labels" . | nindent 4 }}

# Loop
{{- range .Values.extraEnv }}
- name: {{ .name }}
  value: {{ .value | quote }}
{{- end }}
```

---

## Common Helm Hooks

```yaml
annotations:
  "helm.sh/hook": pre-install          # before first install
  "helm.sh/hook": post-install         # after first install
  "helm.sh/hook": pre-upgrade          # before every upgrade
  "helm.sh/hook": post-upgrade         # after every upgrade
  "helm.sh/hook": pre-delete           # before uninstall
  "helm.sh/hook": test                 # run with 'helm test'
  "helm.sh/hook-weight": "-5"          # order (lower runs first)
  "helm.sh/hook-delete-policy": hook-succeeded  # cleanup after success
```

---

## Helmfile

```yaml
# helmfile.yaml
repositories:
- name: bitnami
  url: https://charts.bitnami.com/bitnami

releases:
- name: myapp
  namespace: production
  chart: ./charts/myapp
  values:
  - values/production.yaml
  set:
  - name: image.tag
    value: "{{ env \"IMAGE_TAG\" }}"
```

```bash
helmfile sync             # apply all
helmfile diff             # show planned changes
helmfile template         # render all
helmfile apply            # diff then sync
```

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Helm Charts Theory](./Theory.md) |
| Interview Q&A | [Helm Charts Interview Q&A](./Interview_QA.md) |
| Code Example | [Helm Charts Code Example](./Code_Example.md) |
| Next Module | [27 — Advanced Scheduling](../27_Advanced_Scheduling/Theory.md) |
