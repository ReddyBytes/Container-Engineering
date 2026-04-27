# solution.py — CI/CD Build, Push, Deploy
#
# Full working FastAPI app used in the CI/CD pipeline project.
# Tests in app/test_main.py are run against this code inside Docker
# as the first step of the GitHub Actions pipeline.
#
# NOTE: This file also encodes the full deploy.yaml workflow as a docstring
# at the bottom, so you have everything in one place for reference.

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

app = FastAPI()

# In-memory item store — no database dependency keeps CI setup simple.
_items: List[Dict[str, Any]] = []
_next_id = 1


class ItemCreate(BaseModel):
    name: str
    price: float


class Item(BaseModel):
    id: int
    name: str
    price: float


@app.get("/health")
def health():
    """Readiness probe. The test job calls this to verify the app boots."""
    return {"status": "ok"}


@app.get("/")
def root():
    return {"message": "CI/CD Demo API"}


@app.get("/items")
def list_items():
    return {"items": list(_items)}  # ← return a copy so callers can't mutate the store


@app.post("/items", status_code=201)
def create_item(item: ItemCreate):
    """Create a new item with an auto-incremented id."""
    global _next_id
    new_item = {
        "id": _next_id,
        "name": item.name,
        "price": item.price,
    }
    _items.append(new_item)
    _next_id += 1  # ← move the counter forward for the next call
    return new_item


@app.get("/items/{item_id}")
def get_item(item_id: int):
    """Fetch a single item. The test suite verifies 404 for missing ids."""
    for item in _items:
        if item["id"] == item_id:
            return item
    raise HTTPException(status_code=404, detail="Item not found")


# =============================================================================
# REFERENCE: Full .github/workflows/deploy.yaml
# =============================================================================
#
# name: Build and Deploy
#
# on:
#   push:
#     branches: [main]
#
# env:
#   REGISTRY: ghcr.io
#   IMAGE_NAME: ${{ github.repository_owner }}/myapi
#
# jobs:
#
#   test:
#     name: Test
#     runs-on: ubuntu-latest
#     steps:
#       - uses: actions/checkout@v4
#       - name: Build test image
#         run: docker build --target builder -t myapi-test .
#       - name: Run tests
#         run: |
#           docker run --rm myapi-test \
#             python -m pytest app/test_main.py -v --tb=short
#
#   build-push:
#     name: Build and Push
#     runs-on: ubuntu-latest
#     needs: test
#     permissions:
#       contents: read
#       packages: write
#     outputs:
#       sha_tag: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:sha-${{ github.sha }}
#     steps:
#       - uses: actions/checkout@v4
#       - uses: docker/setup-buildx-action@v3
#       - uses: docker/login-action@v3
#         with:
#           registry: ${{ env.REGISTRY }}
#           username: ${{ github.actor }}
#           password: ${{ secrets.GITHUB_TOKEN }}   # ← built-in, no secret to create
#       - name: Extract metadata
#         id: meta
#         uses: docker/metadata-action@v5
#         with:
#           images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
#           tags: |
#             type=sha,format=long          # ghcr.io/USER/myapi:sha-<40-char-SHA>
#             type=raw,value=latest,enable=${{ github.ref == 'refs/heads/main' }}
#       - uses: docker/build-push-action@v5
#         with:
#           context: .
#           platforms: linux/amd64,linux/arm64   # ← multi-arch in one push
#           push: true
#           tags: ${{ steps.meta.outputs.tags }}
#           cache-from: type=gha                  # ← reuse layer cache across runs
#           cache-to: type=gha,mode=max
#
#   deploy-staging:
#     name: Deploy to Staging
#     runs-on: ubuntu-latest
#     needs: build-push
#     steps:
#       - uses: actions/checkout@v4
#       - name: Configure kubectl
#         run: |
#           mkdir -p ~/.kube
#           echo "${{ secrets.KUBECONFIG_B64 }}" | base64 -d > ~/.kube/config
#           chmod 600 ~/.kube/config   # ← prevent "insecure permissions" warning
#       - uses: azure/setup-kubectl@v3
#         with:
#           version: 'v1.28.0'
#       - name: Update image
#         run: |
#           SHA_TAG="${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:sha-${{ github.sha }}"
#           kubectl set image deployment/myapi myapi="$SHA_TAG" -n staging
#       - name: Wait for rollout
#         run: kubectl rollout status deployment/myapi -n staging --timeout=3m
#
#   deploy-prod:
#     name: Deploy to Production
#     runs-on: ubuntu-latest
#     needs: deploy-staging
#     environment:
#       name: production                   # ← triggers the approval gate
#       url: https://app.yourcompany.com
#     steps:
#       - uses: actions/checkout@v4
#       - name: Configure kubectl
#         run: |
#           mkdir -p ~/.kube
#           echo "${{ secrets.KUBECONFIG_B64 }}" | base64 -d > ~/.kube/config
#           chmod 600 ~/.kube/config
#       - uses: azure/setup-kubectl@v3
#         with:
#           version: 'v1.28.0'
#       - name: Update image
#         run: |
#           SHA_TAG="${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:sha-${{ github.sha }}"
#           kubectl set image deployment/myapi myapi="$SHA_TAG" -n production
#       - name: Wait for rollout
#         run: kubectl rollout status deployment/myapi -n production --timeout=5m
