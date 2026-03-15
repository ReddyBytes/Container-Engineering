# Code Examples: CI/CD — Build, Push, Deploy

---

## .github/workflows/deploy.yaml

```yaml
# .github/workflows/deploy.yaml
# Full CI/CD pipeline: test → build → push → deploy staging → deploy prod
#
# Triggers on every push to main.
# Production deploy requires manual approval (GitHub Environment).

name: Build and Deploy

on:
  push:
    branches:
      - main

# Environment variables available to all jobs
env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository_owner }}/myapi

jobs:

  # ---------------------------------------------------------------------------
  # Job 1: Run tests inside Docker
  # ---------------------------------------------------------------------------
  test:
    name: Test
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      # Build the builder stage only — faster than a full multi-stage build
      - name: Build test image
        run: |
          docker build --target builder -t myapi-test .

      # Run pytest inside the builder image.
      # The builder stage has all dependencies installed.
      - name: Run tests
        run: |
          docker run --rm myapi-test \
            python -m pytest app/test_main.py -v --tb=short

  # ---------------------------------------------------------------------------
  # Job 2: Build multi-platform image and push to GHCR
  # ---------------------------------------------------------------------------
  build-push:
    name: Build and Push
    runs-on: ubuntu-latest
    needs: test    # Only runs if 'test' job succeeded

    # Write permission on packages is required to push to GHCR
    permissions:
      contents: read
      packages: write

    outputs:
      # Export the full image reference so deploy jobs can use the exact tag
      image: ${{ steps.meta.outputs.tags }}
      sha_tag: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      # Set up Docker Buildx for multi-platform builds
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      # Log in to GHCR using the built-in GitHub token
      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      # Generate image tags and labels
      # - SHA tag:    ghcr.io/USER/myapi:abc1234def5  (immutable, specific)
      # - latest tag: ghcr.io/USER/myapi:latest       (mutable, convenient)
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=sha,format=long
            type=raw,value=latest,enable=${{ github.ref == 'refs/heads/main' }}

      # Build for both amd64 (cloud servers) and arm64 (M1/M2 Macs, AWS Graviton)
      - name: Build and push image
        uses: docker/build-push-action@v5
        with:
          context: .
          platforms: linux/amd64,linux/arm64
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          # Cache layers using GitHub Actions cache for faster subsequent builds
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # ---------------------------------------------------------------------------
  # Job 3: Deploy to staging
  # ---------------------------------------------------------------------------
  deploy-staging:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    needs: build-push

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      # Decode the base64 kubeconfig secret and write it to the standard location
      - name: Configure kubectl
        run: |
          mkdir -p ~/.kube
          echo "${{ secrets.KUBECONFIG_B64 }}" | base64 -d > ~/.kube/config
          chmod 600 ~/.kube/config

      # Install kubectl on the runner
      - name: Install kubectl
        uses: azure/setup-kubectl@v3
        with:
          version: 'v1.28.0'

      # Update the deployment image to the exact SHA-tagged version
      - name: Update deployment image
        run: |
          SHA_TAG="${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:sha-${{ github.sha }}"
          echo "Deploying image: $SHA_TAG"
          kubectl set image deployment/myapi myapi="$SHA_TAG" \
            -n staging

      # Wait for the rollout to complete. Fail if it takes more than 3 minutes.
      # This catches: image pull errors, crashloopbackoff, failing health probes.
      - name: Verify rollout
        run: |
          kubectl rollout status deployment/myapi \
            -n staging \
            --timeout=3m

      - name: Print deployed image
        run: |
          kubectl describe deployment myapi -n staging | grep Image

  # ---------------------------------------------------------------------------
  # Job 4: Deploy to production (requires manual approval)
  # ---------------------------------------------------------------------------
  deploy-prod:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: deploy-staging

    # The 'production' environment has required reviewers configured.
    # This job pauses until an authorized person approves it in the GitHub UI.
    environment:
      name: production
      url: https://app.yourcompany.com

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Configure kubectl
        run: |
          mkdir -p ~/.kube
          echo "${{ secrets.KUBECONFIG_B64 }}" | base64 -d > ~/.kube/config
          chmod 600 ~/.kube/config

      - name: Install kubectl
        uses: azure/setup-kubectl@v3
        with:
          version: 'v1.28.0'

      - name: Update deployment image
        run: |
          SHA_TAG="${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:sha-${{ github.sha }}"
          echo "Deploying image: $SHA_TAG"
          kubectl set image deployment/myapi myapi="$SHA_TAG" \
            -n production

      - name: Verify rollout
        run: |
          kubectl rollout status deployment/myapi \
            -n production \
            --timeout=5m

      - name: Print deployed image
        run: |
          kubectl describe deployment myapi -n production | grep Image
```

---

## app/test_main.py

```python
# app/test_main.py
# Pytest test suite for the FastAPI app.
# These run in the CI pipeline before any image is built.

import pytest
from fastapi.testclient import TestClient
from app.main import app

# TestClient makes HTTP requests to the app without starting a server.
client = TestClient(app)


def test_health_check():
    """Health endpoint must return 200 and status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_root():
    """Root endpoint returns a welcome message."""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_create_item():
    """POST /items creates an item and returns it with an ID."""
    response = client.post("/items", json={"name": "laptop", "price": 999.99})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "laptop"
    assert data["price"] == 999.99
    assert "id" in data


def test_list_items():
    """GET /items returns a list."""
    response = client.get("/items")
    assert response.status_code == 200
    assert "items" in response.json()


def test_get_nonexistent_item():
    """GET /items/99999 returns 404."""
    response = client.get("/items/99999")
    assert response.status_code == 404
```

---

## k8s/deployment.yaml

```yaml
# k8s/deployment.yaml
# The CI pipeline updates the 'image' field using:
#   kubectl set image deployment/myapi myapi=NEW_IMAGE_TAG
#
# The image tag shown here is a placeholder.

apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapi
  namespace: staging    # Change to 'production' for the prod deployment
  labels:
    app: myapi
spec:
  replicas: 2
  selector:
    matchLabels:
      app: myapi
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: myapi
    spec:
      containers:
        - name: myapi
          # This gets overwritten by kubectl set image in CI
          image: ghcr.io/YOUR_USERNAME/myapi:latest
          imagePullPolicy: Always
          ports:
            - containerPort: 8000
          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "500m"
              memory: "256Mi"
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 20
            periodSeconds: 20
```

---

## scripts/update-image.sh

```bash
#!/usr/bin/env bash
# scripts/update-image.sh
# Alternative to kubectl set image:
# Updates the image tag in the deployment YAML file in-place,
# then applies it. Useful if you want changes tracked in git.
#
# Usage: ./scripts/update-image.sh ghcr.io/USERNAME/myapi:sha-abc1234 k8s/deployment.yaml

set -euo pipefail

IMAGE_TAG="${1:?Usage: $0 IMAGE_TAG DEPLOYMENT_FILE}"
DEPLOYMENT_FILE="${2:?Usage: $0 IMAGE_TAG DEPLOYMENT_FILE}"

echo "Updating image to: $IMAGE_TAG"
echo "In file: $DEPLOYMENT_FILE"

# Use sed to replace the image line.
# Matches lines like: "image: ghcr.io/USERNAME/myapi:ANYTHING"
sed -i.bak \
  "s|image: ghcr.io/[^/]*/myapi:.*|image: ${IMAGE_TAG}|g" \
  "$DEPLOYMENT_FILE"

rm -f "${DEPLOYMENT_FILE}.bak"

echo "Applying updated manifest..."
kubectl apply -f "$DEPLOYMENT_FILE"

echo "Waiting for rollout..."
kubectl rollout status deployment/myapi --timeout=3m

echo "Done. Deployed: $IMAGE_TAG"
```

---

## 📂 Navigation

| | |
|---|---|
| Guide | [Project_Guide.md](./Project_Guide.md) |
| Steps | [Step_by_Step.md](./Step_by_Step.md) |
| All Projects | [04_Projects/](../) |
