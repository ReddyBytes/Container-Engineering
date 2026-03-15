# Module 25 — GitOps and CI/CD Cheatsheet

## Core GitOps Principles

| Principle | Meaning |
|---|---|
| Declarative | Desired state described in files (YAML) |
| Versioned | All state stored in Git |
| Pulled | Agent in cluster pulls from Git (not CI pushing) |
| Reconciled | Continuous comparison + correction of drift |

---

## ArgoCD Installation

```bash
# Install ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f \
  https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for pods
kubectl wait --for=condition=Ready pods --all -n argocd --timeout=300s

# Get initial admin password
kubectl get secret argocd-initial-admin-secret -n argocd \
  -o jsonpath="{.data.password}" | base64 -d

# Access UI
kubectl port-forward svc/argocd-server 8080:443 -n argocd

# Install argocd CLI
brew install argocd  # macOS
# or: curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64

# Login
argocd login localhost:8080
```

---

## ArgoCD Application YAML

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapp-production
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/myorg/gitops-repo
    targetRevision: main
    path: environments/production/myapp
  destination:
    server: https://kubernetes.default.svc
    namespace: production
  syncPolicy:
    automated:
      prune: true        # delete resources removed from Git
      selfHeal: true     # fix manual cluster changes
    syncOptions:
    - CreateNamespace=true
```

---

## ArgoCD CLI Commands

```bash
# List apps
argocd app list

# Get app status
argocd app get myapp-production

# Sync an app (apply Git state to cluster)
argocd app sync myapp-production

# Sync with prune (delete removed resources)
argocd app sync myapp-production --prune

# Rollback to previous revision
argocd app rollback myapp-production <revision>

# Get app history
argocd app history myapp-production

# Diff: what would change on sync?
argocd app diff myapp-production

# Create app via CLI
argocd app create myapp \
  --repo https://github.com/myorg/gitops-repo \
  --path environments/production/myapp \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace production \
  --sync-policy automated

# Delete app (--cascade deletes K8s resources too)
argocd app delete myapp --cascade
```

---

## ArgoCD ApplicationSet

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: myapp-envs
  namespace: argocd
spec:
  generators:
  - list:
      elements:
      - env: dev
        namespace: development
      - env: staging
        namespace: staging
      - env: prod
        namespace: production
  template:
    metadata:
      name: 'myapp-{{env}}'
    spec:
      project: default
      source:
        repoURL: https://github.com/myorg/gitops
        targetRevision: main
        path: 'environments/{{env}}'
      destination:
        server: https://kubernetes.default.svc
        namespace: '{{namespace}}'
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

---

## Flux Installation

```bash
# Install Flux CLI
brew install fluxcd/tap/flux  # macOS

# Pre-check
flux check --pre

# Bootstrap with GitHub
flux bootstrap github \
  --owner=myorg \
  --repository=gitops-repo \
  --branch=main \
  --path=./clusters/production \
  --personal

# Get Flux components
kubectl get all -n flux-system

# List Flux sources
flux get sources git

# Force sync
flux reconcile kustomization flux-system --with-source

# Check status
flux get kustomizations
```

---

## Sealed Secrets

```bash
# Install Sealed Secrets controller
helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
helm install sealed-secrets sealed-secrets/sealed-secrets \
  -n kube-system

# Install kubeseal CLI
brew install kubeseal  # macOS

# Seal a secret
kubectl create secret generic db-password \
  --from-literal=password=mysecret \
  --dry-run=client -o yaml | \
  kubeseal -o yaml > sealed-db-password.yaml

# Commit sealed-db-password.yaml to Git (safe!)

# View the sealing key (backup this!)
kubectl get secret -n kube-system \
  -l sealedsecrets.bitnami.com/sealed-secrets-key
```

---

## External Secrets Operator

```yaml
# Install
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  -n external-secrets --create-namespace

# SecretStore (AWS Secrets Manager)
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-backend
  namespace: production
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        serviceAccount:
          name: external-secrets-sa

---
# ExternalSecret
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: db-credentials
  namespace: production
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-backend
    kind: SecretStore
  target:
    name: db-secret
  data:
  - secretKey: password
    remoteRef:
      key: prod/db/password
```

---

## GitHub Actions: Build + Push + Update Manifests

```yaml
name: Build and Deploy
on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Build and push image
      run: |
        docker build -t myapp:${{ github.sha }} .
        docker push myapp:${{ github.sha }}

    - name: Update image tag in GitOps repo
      run: |
        git clone https://github.com/myorg/gitops-repo
        cd gitops-repo
        sed -i "s|image: myapp:.*|image: myapp:${{ github.sha }}|" \
          environments/production/deployment.yaml
        git config user.email "ci@myorg.com"
        git config user.name "CI Bot"
        git commit -am "Update myapp to ${{ github.sha }}"
        git push
```

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [GitOps and CI/CD Theory](./Theory.md) |
| Interview Q&A | [GitOps and CI/CD Interview Q&A](./Interview_QA.md) |
| Next Module | [26 — Helm Charts](../26_Helm_Charts/Theory.md) |
