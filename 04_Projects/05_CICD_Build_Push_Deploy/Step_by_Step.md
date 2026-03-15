# Step-by-Step: CI/CD — Build, Push, Deploy

---

## Step 1 — Set Up GitHub Secrets

Your workflow needs two secrets to function: a kubeconfig (so the runner can talk to your cluster) and your registry credentials (built into GitHub for GHCR).

**Export your kubeconfig:**

```bash
cat ~/.kube/config | base64
```

Copy the entire base64 output.

In your GitHub repository, go to: **Settings → Secrets and variables → Actions → New repository secret**

Add this secret:

| Secret Name | Value                                |
|-------------|--------------------------------------|
| `KUBECONFIG_B64` | The base64-encoded kubeconfig you just copied |

**GHCR authentication** uses the built-in `GITHUB_TOKEN` — no extra secret needed. GitHub Actions provides it automatically.

**Create the production environment with manual approval:**

1. Go to: **Settings → Environments → New environment**
2. Name it `production`
3. Under "Protection rules", check "Required reviewers"
4. Add yourself as a required reviewer
5. Save

Now any job targeting the `production` environment will pause and wait for your approval before running.

---

## Step 2 — Write the Test File

Create `app/test_main.py` — see Code_Example.md for the full file.

The tests use FastAPI's `TestClient` to make HTTP requests to the app in-process (no server needed). The CI pipeline runs these tests in a Docker container.

Verify they pass locally:

```bash
pip install pytest httpx
pytest app/test_main.py -v
```

**Expected:**
```
PASSED app/test_main.py::test_health_check
PASSED app/test_main.py::test_root
PASSED app/test_main.py::test_create_item
PASSED app/test_main.py::test_list_items
```

---

## Step 3 — Create the Workflow Directory

```bash
mkdir -p .github/workflows
```

Create `.github/workflows/deploy.yaml` — see Code_Example.md for the full file.

Walk through the four jobs:

**Job 1: `test`**
- Checks out your code
- Runs `docker build --target builder` to get the build stage
- Runs `docker run pytest` against the app inside that image
- If pytest fails → pipeline stops here, nothing gets deployed

**Job 2: `build-push`** (runs only if `test` passed)
- Uses `docker/build-push-action` with `platforms: linux/amd64,linux/arm64`
- Tags the image with the git SHA: `ghcr.io/USERNAME/myapi:abc1234`
- Also tags with `latest`
- Pushes to GHCR

**Job 3: `deploy-staging`** (runs only if `build-push` passed)
- Decodes the `KUBECONFIG_B64` secret to `~/.kube/config`
- Runs `kubectl set image deployment/myapi myapi=ghcr.io/USERNAME/myapi:SHA`
- Waits for the rollout: `kubectl rollout status deployment/myapi --timeout=3m`
- If rollout doesn't complete in 3 minutes → pipeline fails

**Job 4: `deploy-prod`** (runs only after manual approval)
- Same as staging but targets the production namespace/cluster
- The `environment: production` declaration triggers the approval gate

---

## Step 4 — Trigger the Pipeline

Commit and push everything:

```bash
git add .
git commit -m "feat: add CI/CD pipeline"
git push origin main
```

Go to your GitHub repo → **Actions** tab. You'll see the workflow run appear.

Watch the stages progress:

- `test` runs first (~2 minutes for a Docker build + pytest)
- `build-push` starts after test passes (~3-4 minutes for multi-platform build)
- `deploy-staging` starts after build-push (~30 seconds)
- `deploy-prod` is waiting for approval

**Expected output in the `build-push` job:**
```
#12 pushing ghcr.io/USERNAME/myapi:abc1234
#12 pushing layers
#12 ...
#12 DONE 45.2s
```

---

## Step 5 — Verify the Deployment Updated

After `deploy-staging` completes, check your cluster:

```bash
kubectl describe deployment myapi | grep Image
```

**Expected:**
```
Image: ghcr.io/YOUR_USERNAME/myapi:abc1234def5
```

The SHA in the image tag should match the commit SHA from the push that triggered the pipeline.

Verify the pods are running the new image:

```bash
kubectl get pods -l app=myapi -o jsonpath='{.items[*].spec.containers[0].image}'
```

**Expected:**
```
ghcr.io/YOUR_USERNAME/myapi:abc1234def5 ghcr.io/YOUR_USERNAME/myapi:abc1234def5 ghcr.io/YOUR_USERNAME/myapi:abc1234def5
```

---

## Step 6 — Approve the Production Deploy

Back in the GitHub Actions UI, click on the `deploy-prod` job. You'll see:

```
This workflow run is waiting for a required review from:
 - YOUR_USERNAME
[Review deployments] button
```

Click "Review deployments", select the `production` environment, optionally add a comment, and click "Approve and deploy."

The job runs immediately after approval.

---

## Step 7 — What Happens When a Test Fails

Break a test intentionally to see the pipeline stop early:

Edit `app/main.py` — change the `/health` endpoint to return `{"status": "broken"}`.

Commit and push:

```bash
git add .
git commit -m "chore: break a test deliberately"
git push origin main
```

Watch the pipeline:

- `test` job fails (pytest detects the wrong response)
- `build-push`, `deploy-staging`, `deploy-prod` are all **skipped**
- Your cluster is untouched

**Expected output in test job:**
```
FAILED app/test_main.py::test_health_check - AssertionError: assert 'broken' == 'ok'
```

Fix the code, push again. The pipeline recovers automatically.

---

## 📂 Navigation

| | |
|---|---|
| Guide | [Project_Guide.md](./Project_Guide.md) |
| Code | [Code_Example.md](./Code_Example.md) |
| All Projects | [04_Projects/](../) |
