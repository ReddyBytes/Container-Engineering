# 05 — Guide: CI/CD Build, Push, Deploy

Work through each step in order. Try it yourself before opening hints.

---

## ## Step 1 — Set up GitHub Secrets

The pipeline needs two things: credentials to push to GHCR (already built in),
and a kubeconfig to deploy to your cluster.

<details>
<summary>💡 Hint</summary>

Export your kubeconfig as base64. Add it as a GitHub Actions Secret named
`KUBECONFIG_B64`. GHCR auth uses the automatic `GITHUB_TOKEN` — no extra secret
needed for the registry.

Also create a `production` environment with a required reviewer so the
deploy-prod job pauses for approval.

</details>

<details>
<summary>✅ Answer</summary>

Export your kubeconfig:

```bash
cat ~/.kube/config | base64
```

In GitHub: Settings → Secrets and variables → Actions → New repository secret

| Secret Name     | Value                                      |
|-----------------|--------------------------------------------|
| `KUBECONFIG_B64` | The base64 output from the command above  |

Create the production environment:

1. Settings → Environments → New environment
2. Name: `production`
3. Protection rules → Required reviewers → add yourself
4. Save

</details>

---

## ## Step 2 — Write the test suite

Create `app/test_main.py` with at least five tests covering: health check,
root endpoint, creating an item, listing items, and a 404 for a missing item.

<details>
<summary>💡 Hint</summary>

Use FastAPI's `TestClient`. It makes HTTP requests to the app in-process — no
server needs to be running. Tests run inside the Docker builder stage where
all dependencies are already installed.

</details>

<details>
<summary>✅ Answer</summary>

```python
# app/test_main.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()

def test_create_item():
    response = client.post("/items", json={"name": "laptop", "price": 999.99})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "laptop"
    assert "id" in data

def test_list_items():
    response = client.get("/items")
    assert response.status_code == 200
    assert "items" in response.json()

def test_get_nonexistent_item():
    response = client.get("/items/99999")
    assert response.status_code == 404
```

Verify locally before pushing:

```bash
pip install pytest httpx
pytest app/test_main.py -v
```

</details>

---

## ## Step 3 — Write the workflow file

Create `.github/workflows/deploy.yaml`. It must define four jobs: `test`,
`build-push`, `deploy-staging`, `deploy-prod`.

<details>
<summary>💡 Hint</summary>

Use `needs:` to chain jobs. Each job must explicitly depend on the previous one
or it will run in parallel. Use `docker/setup-buildx-action`, `docker/login-action`,
`docker/metadata-action`, and `docker/build-push-action` for the build job.
For deploy jobs, decode the kubeconfig secret with `base64 -d`, install kubectl
with `azure/setup-kubectl`, then use `kubectl set image` and `kubectl rollout status`.

</details>

<details>
<summary>✅ Answer</summary>

See `src/solution.py` for the full workflow content. Key structure:

```yaml
name: Build and Deploy

on:
  push:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository_owner }}/myapi

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build --target builder -t myapi-test .
      - run: docker run --rm myapi-test python -m pytest app/test_main.py -v --tb=short

  build-push:
    needs: test
    permissions:
      contents: read
      packages: write
    # ... buildx + login + metadata + build-push-action

  deploy-staging:
    needs: build-push
    # ... decode kubeconfig, install kubectl, set image, rollout status

  deploy-prod:
    needs: deploy-staging
    environment:
      name: production
    # ... same as staging but namespace: production
```

</details>

---

## ## Step 4 — Trigger the pipeline

Push everything to `main` and watch the pipeline run.

<details>
<summary>💡 Hint</summary>

Commit the workflow file, app code, Dockerfile, and test file. Push to main.
In the GitHub UI go to the Actions tab to watch the jobs progress in real time.

</details>

<details>
<summary>✅ Answer</summary>

```bash
git add .
git commit -m "feat: add CI/CD pipeline"
git push origin main
```

GitHub → Actions tab. Expected progression:

- `test` runs first (~2 minutes)
- `build-push` starts after test passes (~3-4 minutes for multi-platform)
- `deploy-staging` runs (~30 seconds)
- `deploy-prod` is paused, waiting for approval

</details>

---

## ## Step 5 — Verify the staging deployment

After `deploy-staging` completes, check your cluster to confirm the new image
tag was applied.

<details>
<summary>💡 Hint</summary>

Use `kubectl describe deployment myapi -n staging | grep Image` to see the
current image tag. The SHA in the tag should match the commit SHA from the push.

</details>

<details>
<summary>✅ Answer</summary>

```bash
kubectl describe deployment myapi -n staging | grep Image
```

Expected:

```
Image: ghcr.io/YOUR_USERNAME/myapi:sha-abc1234def5...
```

The SHA should match the output of `git rev-parse HEAD` locally.

Verify pods are running the new image:

```bash
kubectl get pods -l app=myapi -n staging \
  -o jsonpath='{.items[*].spec.containers[0].image}'
```

</details>

---

## ## Step 6 — Approve the production deployment

The `deploy-prod` job is paused. Find and approve it in the GitHub UI.

<details>
<summary>💡 Hint</summary>

In the Actions tab, click on the running workflow. Click the `deploy-prod` job.
You will see a "Review deployments" button. Click it, select the `production`
environment, optionally add a comment, and approve.

</details>

<details>
<summary>✅ Answer</summary>

In GitHub Actions UI:

1. Click the workflow run
2. Click `deploy-prod` (shows "Waiting for review")
3. Click "Review deployments"
4. Check `production`, add a comment if desired
5. Click "Approve and deploy"

The job runs immediately. Verify:

```bash
kubectl describe deployment myapi -n production | grep Image
```

The image tag should now match staging.

</details>

---

## ## Step 7 — Break a test and watch the pipeline stop

Intentionally break a test to confirm broken code never reaches the cluster.

<details>
<summary>💡 Hint</summary>

Change the `/health` endpoint in `app/main.py` to return `{"status": "broken"}`.
Push to main. Watch the `test` job fail and all subsequent jobs be skipped.

</details>

<details>
<summary>✅ Answer</summary>

Edit `app/main.py`:

```python
@app.get("/health")
def health():
    return {"status": "broken"}  # ← deliberate break
```

```bash
git add .
git commit -m "chore: break a test deliberately"
git push origin main
```

Expected in Actions:

- `test` job fails: `FAILED app/test_main.py::test_health_check`
- `build-push`, `deploy-staging`, `deploy-prod` all show "Skipped"
- Your cluster is completely untouched

Fix the code, push again. The pipeline recovers automatically.

</details>

---

⬅️ **Prev:** [04 — Full-Stack on K8s](../04_Full_Stack_on_K8s/01_MISSION.md) &nbsp;&nbsp; ➡️ **Next:** [06 — Production K8s Cluster](../06_Production_K8s_Cluster/01_MISSION.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
