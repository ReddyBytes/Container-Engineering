# GitOps and CI/CD — Code Examples

All examples are production-quality with detailed comments explaining every decision.

---

## 1. ArgoCD Application: Deploying from Git

```yaml
# argocd-application.yaml
# An ArgoCD Application links a Git repository path to a K8s cluster namespace.
# ArgoCD polls this repo and applies any changes automatically.
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: payments-service                   # name of the ArgoCD Application object
  namespace: argocd                        # ArgoCD always lives in the argocd namespace
  # finalizer ensures ArgoCD cleans up K8s resources when this Application is deleted
  finalizers:
  - resources-finalizer.argocd.argoproj.io
spec:
  project: default                         # ArgoCD project (grouping + access control)
  source:
    repoURL: https://github.com/myorg/gitops-manifests   # Git repo with K8s YAML
    targetRevision: main                   # branch, tag, or commit SHA to track
    path: apps/payments/production         # subdirectory within the repo
  destination:
    server: https://kubernetes.default.svc # the cluster ArgoCD is running in
    namespace: production                  # namespace to deploy into
  syncPolicy:
    automated:
      prune: true                          # delete K8s resources removed from Git
      selfHeal: true                       # revert manual kubectl changes (drift correction)
      allowEmpty: false                    # don't prune everything if Git path becomes empty
    syncOptions:
    - CreateNamespace=true                 # create the namespace if it doesn't exist
    - PrunePropagationPolicy=foreground    # wait for child resources to delete before parents
    retry:
      limit: 5                             # retry failed syncs up to 5 times
      backoff:
        duration: 5s
        factor: 2                          # exponential backoff: 5s, 10s, 20s, ...
        maxDuration: 3m
```

```bash
# Apply the Application object (ArgoCD picks it up immediately)
kubectl apply -f argocd-application.yaml

# Watch sync status
argocd app get payments-service

# Manually trigger a sync (e.g., after pushing to Git)
argocd app sync payments-service

# List all applications and their sync/health status
argocd app list

# View the diff between Git state and live cluster state
argocd app diff payments-service

# Roll back to a previous Git commit
argocd app history payments-service       # list past syncs with revision SHAs
argocd app rollback payments-service 3   # roll back to sync #3
```

---

## 2. GitHub Actions Pipeline: Build, Push, Update Manifest

```yaml
# .github/workflows/deploy.yml
# This CI pipeline builds a Docker image, pushes it to ECR,
# then updates the image tag in the GitOps manifests repo.
# ArgoCD detects the manifest change and deploys automatically.
name: Build and Deploy

on:
  push:
    branches: [main]                       # only run on pushes to main

env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: my-payments-service
  GITOPS_REPO: myorg/gitops-manifests      # separate repo holding K8s manifests

jobs:
  build-push-deploy:
    runs-on: ubuntu-latest
    steps:

    - name: Checkout source code
      uses: actions/checkout@v4

    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ${{ env.AWS_REGION }}

    - name: Login to Amazon ECR
      id: login-ecr
      uses: aws-actions/amazon-ecr-login@v2

    - name: Build and push Docker image
      id: build
      env:
        ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        IMAGE_TAG: ${{ github.sha }}       # use commit SHA as image tag — unique and traceable
      run: |
        docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
        # Also tag as latest for convenience (optional — GitOps uses the SHA tag)
        docker tag $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG \
          $ECR_REGISTRY/$ECR_REPOSITORY:latest
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest
        echo "image=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" >> $GITHUB_OUTPUT

    - name: Update image tag in GitOps manifests repo
      env:
        GITHUB_TOKEN: ${{ secrets.GITOPS_DEPLOY_KEY }}  # PAT with write access to manifests repo
        IMAGE: ${{ steps.build.outputs.image }}
      run: |
        git config --global user.email "ci@myorg.com"
        git config --global user.name "CI Bot"
        git clone https://x-access-token:${GITHUB_TOKEN}@github.com/${GITOPS_REPO}.git gitops
        cd gitops
        # Update the image tag in the deployment manifest
        # sed matches the exact image line and replaces the tag
        sed -i "s|image: .*payments-service:.*|image: ${IMAGE}|g" \
          apps/payments/production/deployment.yaml
        git add apps/payments/production/deployment.yaml
        git commit -m "ci: update payments-service to ${GITHUB_SHA:0:8}

        Deployed by GitHub Actions run ${{ github.run_id }}
        Source commit: ${{ github.sha }}"
        git push
```

---

## 3. ArgoCD ApplicationSet: Multi-Environment from One Template

```yaml
# applicationset.yaml
# ApplicationSet generates one ArgoCD Application per environment automatically.
# Adding a new environment is just adding an entry to the list — no copy-paste.
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: payments-service-environments
  namespace: argocd
spec:
  generators:
  - list:
      elements:
      - env: dev
        cluster: https://kubernetes.default.svc  # same cluster, different namespace
        namespace: dev
        replicas: "1"                            # template variables can be any string
        syncPolicy: manual                       # dev: manual sync to avoid surprise deploys
      - env: staging
        cluster: https://kubernetes.default.svc
        namespace: staging
        replicas: "2"
        syncPolicy: automated
      - env: production
        cluster: https://prod-cluster.example.com  # separate cluster for production
        namespace: production
        replicas: "5"
        syncPolicy: automated
  template:
    metadata:
      name: 'payments-{{env}}'                  # one Application per environment
    spec:
      project: default
      source:
        repoURL: https://github.com/myorg/gitops-manifests
        targetRevision: main
        path: 'apps/payments/{{env}}'           # separate directory per environment
        kustomize:
          commonLabels:
            environment: '{{env}}'              # inject environment label into all resources
      destination:
        server: '{{cluster}}'
        namespace: '{{namespace}}'
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

---

## 4. Sealed Secrets: Safe Secrets in Git

```bash
# Install kubeseal CLI (macOS)
brew install kubeseal

# Install the Sealed Secrets controller in the cluster
helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
helm install sealed-secrets sealed-secrets/sealed-secrets \
  --namespace kube-system \
  --set fullnameOverride=sealed-secrets-controller

# --- Create a regular secret (DO NOT commit this to Git) ---
kubectl create secret generic db-credentials \
  --namespace production \
  --from-literal=username=payments_user \
  --from-literal=password='s3cr3t!P@ssword' \
  --dry-run=client -o yaml > /tmp/db-secret.yaml

# Encrypt the secret using the cluster's public key
# The output is safe to commit — only the cluster can decrypt it
kubeseal \
  --controller-name=sealed-secrets-controller \
  --controller-namespace=kube-system \
  --format yaml \
  < /tmp/db-secret.yaml > sealed-db-secret.yaml

# Commit sealed-db-secret.yaml to Git — the raw secret is never in Git
git add sealed-db-secret.yaml
git commit -m "add sealed db-credentials secret for production"

# The Sealed Secrets controller decrypts it into a regular K8s Secret automatically
kubectl apply -f sealed-db-secret.yaml
kubectl get secret db-credentials -n production  # now exists as a regular Secret
```

```yaml
# external-secret.yaml
# Alternative: External Secrets Operator reads from AWS Secrets Manager.
# The ExternalSecret object (safe to commit) references the secret by name —
# the actual value never touches Git.
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: db-credentials
  namespace: production
spec:
  refreshInterval: 1h                      # re-sync from AWS Secrets Manager every hour
  secretStoreRef:
    name: aws-secrets-manager              # references a SecretStore/ClusterSecretStore
    kind: ClusterSecretStore
  target:
    name: db-credentials                   # name of the K8s Secret to create
    creationPolicy: Owner                  # ESO owns the Secret lifecycle
  data:
  - secretKey: username                    # key name in the K8s Secret
    remoteRef:
      key: production/payments/db          # path in AWS Secrets Manager
      property: username                   # JSON field within the secret value
  - secretKey: password
    remoteRef:
      key: production/payments/db
      property: password
```

---

## 5. Flux: ImageAutomation for Fully Automated GitOps

```yaml
# flux-gitrepository.yaml
# Flux watches a Git repository for changes to K8s manifests
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata:
  name: gitops-manifests
  namespace: flux-system
spec:
  interval: 1m                             # poll Git every minute
  url: https://github.com/myorg/gitops-manifests
  secretRef:
    name: github-credentials              # secret containing the GitHub deploy key
  ref:
    branch: main
---
# flux-kustomization.yaml
# Flux reconciles the manifests from the GitRepository above
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: payments-production
  namespace: flux-system
spec:
  interval: 5m                             # reconcile every 5 minutes even without Git changes
  path: ./apps/payments/production         # path within the GitRepository
  prune: true                              # delete resources removed from Git
  sourceRef:
    kind: GitRepository
    name: gitops-manifests
  healthChecks:                            # wait for these to be healthy before marking success
  - apiVersion: apps/v1
    kind: Deployment
    name: payments-service
    namespace: production
  timeout: 2m                              # fail health check if not healthy within 2 minutes
---
# flux-imagerepository.yaml
# Flux watches an OCI registry for new image tags
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImageRepository
metadata:
  name: payments-service
  namespace: flux-system
spec:
  image: 123456789.dkr.ecr.us-east-1.amazonaws.com/payments-service
  interval: 1m                             # scan registry every minute for new tags
  secretRef:
    name: ecr-credentials
---
# flux-imagepolicy.yaml
# Select which image tags Flux should consider "latest"
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImagePolicy
metadata:
  name: payments-service
  namespace: flux-system
spec:
  imageRepositoryRef:
    name: payments-service
  policy:
    semver:
      range: '>=1.0.0 <2.0.0'             # only accept 1.x.x tags, never auto-upgrade to 2.x
---
# flux-imageupdateautomation.yaml
# When a new image tag matches the policy, Flux commits the tag update to Git
apiVersion: image.toolkit.fluxcd.io/v1beta1
kind: ImageUpdateAutomation
metadata:
  name: gitops-manifests
  namespace: flux-system
spec:
  interval: 5m
  sourceRef:
    kind: GitRepository
    name: gitops-manifests
  git:
    checkout:
      ref:
        branch: main
    commit:
      author:
        email: flux@myorg.com
        name: Flux Automation
      messageTemplate: 'ci: update {{range .Updated.Images}}{{println .}}{{end}}'
    push:
      branch: main
  update:
    strategy: Setters                      # use marker comments in manifests (see below)
```

```yaml
# deployment.yaml (in the manifests repo)
# The # {"$imagepolicy": ...} comment is a Flux marker —
# Flux replaces the image tag here when a new version is published
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
      - name: payments-service
        image: 123456789.dkr.ecr.us-east-1.amazonaws.com/payments-service:1.2.3 # {"$imagepolicy": "flux-system:payments-service"}
```

```bash
# Bootstrap Flux into a cluster (one-time setup)
flux bootstrap github \
  --owner=myorg \
  --repository=gitops-manifests \
  --branch=main \
  --path=./clusters/production \
  --personal                               # use personal access token

# Check Flux component health
flux check

# Watch image scanning + reconciliation
flux get images repository -A
flux get images policy -A
flux get kustomizations -A
```

---

## 📂 Navigation

**In this folder:**
| File | |
|---|---|
| [Theory.md](./Theory.md) | Full explanation |
| [Cheatsheet.md](./Cheatsheet.md) | Quick reference |
| [Interview_QA.md](./Interview_QA.md) | Interview prep |
| **Code_Example.md** | you are here |

⬅️ **Prev:** [Service Mesh](../24_Service_Mesh/Code_Example.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Helm Charts](../26_Helm_Charts/Code_Example.md)
🏠 **[Home](../../README.md)**
