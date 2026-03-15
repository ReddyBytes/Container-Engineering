# Module 26 — Helm Charts Code Example

## Building a Complete Helm Chart From Scratch

This example creates a full Helm chart for a web application, demonstrates environment-specific value overrides, and shows the complete deploy/upgrade/rollback workflow.

---

## Chart Directory Structure

```
mywebapp/
├── Chart.yaml
├── values.yaml
├── values-staging.yaml
├── values-production.yaml
├── templates/
│   ├── _helpers.tpl
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── configmap.yaml
│   ├── hpa.yaml
│   └── NOTES.txt
└── helmfile.yaml
```

---

## Chart.yaml

```yaml
# Chart.yaml — chart metadata
apiVersion: v2
name: mywebapp
description: A production-ready web application Helm chart
type: application

# Chart version — bump when templates/structure changes
version: 1.0.0

# App version — the Docker image version being packaged
appVersion: "2.4.1"

# Maintainers (optional but good practice)
maintainers:
- name: Platform Team
  email: platform@myorg.com

# Keywords for helm search
keywords:
- web
- api
- nodejs
```

---

## values.yaml (Defaults)

```yaml
# values.yaml — default configuration (safe for all environments)

# Number of pod replicas
replicaCount: 2

image:
  repository: myorg/mywebapp   # Docker image name
  tag: ""                       # defaults to Chart.appVersion if empty
  pullPolicy: IfNotPresent      # Only pull if not already on node

# Service configuration
service:
  type: ClusterIP               # ClusterIP | NodePort | LoadBalancer
  port: 80                      # Service port (external)
  targetPort: 3000              # Container port (app listens here)
  annotations: {}

# Ingress (disabled by default)
ingress:
  enabled: false
  className: nginx
  host: ""
  annotations: {}
  tls:
    enabled: false
    secretName: ""

# Application configuration (passed as ConfigMap)
config:
  logLevel: info
  nodeEnv: development
  maxConnections: "100"

# Secret reference (pre-existing K8s Secret, not created by Helm)
existingSecret: ""              # name of Secret containing DB_PASSWORD

# Resource requests and limits
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 256Mi

# Horizontal Pod Autoscaler
autoscaling:
  enabled: false
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70

# Health check probes
probes:
  liveness:
    path: /healthz
    initialDelaySeconds: 15
    periodSeconds: 20
  readiness:
    path: /ready
    initialDelaySeconds: 5
    periodSeconds: 10

# Node selector, tolerations, affinity (empty by default)
nodeSelector: {}
tolerations: []
affinity: {}

# Pod security context
podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 2000

# Container security context
securityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop:
    - ALL
```

---

## values-staging.yaml

```yaml
# values-staging.yaml — staging environment overrides
# Apply with: helm upgrade myapp . -f values.yaml -f values-staging.yaml

replicaCount: 1              # save resources in staging

image:
  tag: "2.4.1-rc1"          # release candidate tag

ingress:
  enabled: true
  host: myapp-staging.internal.example.com
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
  tls:
    enabled: false           # no TLS in staging

config:
  logLevel: debug            # verbose logging for testing
  nodeEnv: staging
  maxConnections: "50"

resources:
  requests:
    cpu: 50m                 # lower requests in staging
    memory: 64Mi
  limits:
    cpu: 200m
    memory: 128Mi

autoscaling:
  enabled: false             # no autoscaling in staging
```

---

## values-production.yaml

```yaml
# values-production.yaml — production environment overrides
# Apply with: helm upgrade myapp . -f values.yaml -f values-production.yaml

replicaCount: 4              # more replicas for production load

image:
  tag: "2.4.1"               # stable release tag
  pullPolicy: Always         # always pull in production

ingress:
  enabled: true
  host: myapp.example.com
  annotations:
    nginx.ingress.kubernetes.io/rate-limit: "100"
    cert-manager.io/cluster-issuer: letsencrypt-prod
  tls:
    enabled: true
    secretName: myapp-tls

config:
  logLevel: warn             # only warnings and errors in production
  nodeEnv: production
  maxConnections: "500"

existingSecret: myapp-production-secrets  # pre-created secret

resources:
  requests:
    cpu: 250m
    memory: 256Mi
  limits:
    cpu: 1000m
    memory: 512Mi

autoscaling:
  enabled: true
  minReplicas: 4
  maxReplicas: 20
  targetCPUUtilizationPercentage: 65

affinity:
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
    - labelSelector:
        matchLabels:
          app.kubernetes.io/name: mywebapp
      topologyKey: kubernetes.io/hostname  # spread across nodes
```

---

## templates/_helpers.tpl

```yaml
{{/*
Generate the full name for the release.
Combines release name + chart name, truncated to 63 chars.
*/}}
{{- define "mywebapp.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{/*
Common labels added to all resources.
These enable kubectl selectors and Helm tracking.
*/}}
{{- define "mywebapp.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | quote }}
{{ include "mywebapp.selectorLabels" . }}
app.kubernetes.io/version: {{ .Values.image.tag | default .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels — used by Deployment selector and Service selector.
Must be stable (never change after initial deploy).
*/}}
{{- define "mywebapp.selectorLabels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Image tag — use override value or fall back to Chart appVersion.
*/}}
{{- define "mywebapp.imageTag" -}}
{{- .Values.image.tag | default .Chart.AppVersion }}
{{- end }}
```

---

## templates/deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "mywebapp.fullname" . }}
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "mywebapp.labels" . | nindent 4 }}
spec:
  # If HPA is enabled, Deployment should not set replicas
  # (HPA will control it). If HPA is disabled, use values.
  {{- if not .Values.autoscaling.enabled }}
  replicas: {{ .Values.replicaCount }}
  {{- end }}
  selector:
    matchLabels:
      {{- include "mywebapp.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "mywebapp.selectorLabels" . | nindent 8 }}
      annotations:
        # Force pod restart when ConfigMap changes
        checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
    spec:
      {{- with .Values.podSecurityContext }}
      securityContext:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      containers:
      - name: {{ .Chart.Name }}
        image: "{{ .Values.image.repository }}:{{ include "mywebapp.imageTag" . }}"
        imagePullPolicy: {{ .Values.image.pullPolicy }}
        ports:
        - name: http
          containerPort: {{ .Values.service.targetPort }}
          protocol: TCP
        # Security context from values
        {{- with .Values.securityContext }}
        securityContext:
          {{- toYaml . | nindent 10 }}
        {{- end }}
        # Environment variables from ConfigMap
        envFrom:
        - configMapRef:
            name: {{ include "mywebapp.fullname" . }}-config
        # Secret environment (only if existingSecret is set)
        {{- if .Values.existingSecret }}
        env:
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: {{ .Values.existingSecret }}
              key: db-password
        {{- end }}
        # Liveness probe — is the container healthy?
        livenessProbe:
          httpGet:
            path: {{ .Values.probes.liveness.path }}
            port: http
          initialDelaySeconds: {{ .Values.probes.liveness.initialDelaySeconds }}
          periodSeconds: {{ .Values.probes.liveness.periodSeconds }}
        # Readiness probe — is the container ready for traffic?
        readinessProbe:
          httpGet:
            path: {{ .Values.probes.readiness.path }}
            port: http
          initialDelaySeconds: {{ .Values.probes.readiness.initialDelaySeconds }}
          periodSeconds: {{ .Values.probes.readiness.periodSeconds }}
        # Resource requests and limits from values
        resources:
          {{- toYaml .Values.resources | nindent 10 }}
        # Writable temp directory (needed with readOnlyRootFilesystem: true)
        volumeMounts:
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: tmp
        emptyDir: {}
      {{- with .Values.nodeSelector }}
      nodeSelector:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.affinity }}
      affinity:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.tolerations }}
      tolerations:
        {{- toYaml . | nindent 8 }}
      {{- end }}
```

---

## templates/service.yaml

```yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ include "mywebapp.fullname" . }}
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "mywebapp.labels" . | nindent 4 }}
  {{- with .Values.service.annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
spec:
  type: {{ .Values.service.type }}
  ports:
  - port: {{ .Values.service.port }}
    targetPort: http               # named port from deployment
    protocol: TCP
    name: http
  selector:
    {{- include "mywebapp.selectorLabels" . | nindent 4 }}
```

---

## templates/configmap.yaml

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "mywebapp.fullname" . }}-config
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "mywebapp.labels" . | nindent 4 }}
data:
  LOG_LEVEL: {{ .Values.config.logLevel | quote }}
  NODE_ENV: {{ .Values.config.nodeEnv | quote }}
  MAX_CONNECTIONS: {{ .Values.config.maxConnections | quote }}
```

---

## templates/ingress.yaml

```yaml
{{- if .Values.ingress.enabled }}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ include "mywebapp.fullname" . }}
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "mywebapp.labels" . | nindent 4 }}
  {{- with .Values.ingress.annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
spec:
  {{- if .Values.ingress.className }}
  ingressClassName: {{ .Values.ingress.className }}
  {{- end }}
  {{- if .Values.ingress.tls.enabled }}
  tls:
  - hosts:
    - {{ .Values.ingress.host }}
    secretName: {{ .Values.ingress.tls.secretName }}
  {{- end }}
  rules:
  - host: {{ .Values.ingress.host }}
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: {{ include "mywebapp.fullname" . }}
            port:
              name: http
{{- end }}
```

---

## templates/hpa.yaml

```yaml
{{- if .Values.autoscaling.enabled }}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ include "mywebapp.fullname" . }}
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "mywebapp.labels" . | nindent 4 }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ include "mywebapp.fullname" . }}
  minReplicas: {{ .Values.autoscaling.minReplicas }}
  maxReplicas: {{ .Values.autoscaling.maxReplicas }}
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: {{ .Values.autoscaling.targetCPUUtilizationPercentage }}
{{- end }}
```

---

## Deploy Commands: Full Workflow

```bash
# ─── First time: validate before installing ───

# Lint the chart
helm lint ./mywebapp

# Render templates (inspect output before applying)
helm template myapp ./mywebapp -f mywebapp/values.yaml -f mywebapp/values-production.yaml

# Dry run (validate against cluster API)
helm install myapp ./mywebapp \
  -f mywebapp/values.yaml \
  -f mywebapp/values-production.yaml \
  --namespace production \
  --create-namespace \
  --dry-run

# ─── Install ───
helm install myapp ./mywebapp \
  -f mywebapp/values.yaml \
  -f mywebapp/values-production.yaml \
  --namespace production \
  --create-namespace

# ─── Verify install ───
helm status myapp -n production
helm get values myapp -n production
kubectl get pods -n production -l app.kubernetes.io/name=mywebapp

# ─── Upgrade (e.g., new image tag) ───
# Edit values-production.yaml: change image.tag to "2.5.0"
helm upgrade myapp ./mywebapp \
  -f mywebapp/values.yaml \
  -f mywebapp/values-production.yaml \
  --namespace production \
  --atomic        # auto-rollback if pods don't become Ready
  --wait          # wait for all resources to be ready
  --timeout 5m

# ─── View history ───
helm history myapp -n production
# REVISION  UPDATED                  STATUS     CHART           APP VERSION
# 1         2024-01-10 10:00:00      superseded mywebapp-1.0.0  2.4.1
# 2         2024-01-15 14:30:00      deployed   mywebapp-1.0.0  2.5.0

# ─── Rollback ───
helm rollback myapp 1 -n production  # back to revision 1

# ─── Uninstall ───
helm uninstall myapp -n production

# ─── Staging deployment ───
helm upgrade --install myapp-staging ./mywebapp \
  -f mywebapp/values.yaml \
  -f mywebapp/values-staging.yaml \
  --namespace staging \
  --create-namespace
```

---

## helmfile.yaml — Multi-Chart Management

```yaml
# helmfile.yaml — deploy the full environment stack

repositories:
- name: bitnami
  url: https://charts.bitnami.com/bitnami
- name: prometheus-community
  url: https://prometheus-community.github.io/helm-charts

# Common labels applied to all releases
commonLabels:
  managed-by: helmfile
  environment: production

releases:
# ─── Infrastructure ───
- name: postgres
  namespace: databases
  chart: bitnami/postgresql
  version: "14.0.0"
  values:
  - values/postgres-production.yaml

- name: redis
  namespace: databases
  chart: bitnami/redis
  version: "18.0.0"
  values:
  - values/redis-production.yaml

# ─── Monitoring ───
- name: kube-prometheus-stack
  namespace: monitoring
  chart: prometheus-community/kube-prometheus-stack
  version: "55.0.0"
  values:
  - values/monitoring-production.yaml

# ─── Application ───
- name: myapp
  namespace: production
  chart: ./mywebapp
  values:
  - mywebapp/values.yaml
  - mywebapp/values-production.yaml
  # Inject image tag from CI environment variable
  set:
  - name: image.tag
    value: {{ env "IMAGE_TAG" | default "2.4.1" }}
  # myapp depends on infrastructure being ready
  needs:
  - databases/postgres
  - databases/redis
```

```bash
# Apply everything in dependency order
helmfile sync

# Show what would change
helmfile diff

# Apply only specific releases
helmfile sync --selector name=myapp

# Destroy everything (careful!)
helmfile destroy
```

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Helm Charts Theory](./Theory.md) |
| Cheatsheet | [Helm Charts Cheatsheet](./Cheatsheet.md) |
| Interview Q&A | [Helm Charts Interview Q&A](./Interview_QA.md) |
| Next Module | [27 — Advanced Scheduling](../27_Advanced_Scheduling/Theory.md) |
