# 05 — Recap: CI/CD Build, Push, Deploy

---

## ## What You Built

You built a complete automated deployment pipeline: every push to `main` tests
your code, builds a multi-platform Docker image tagged with the commit SHA,
pushes it to GHCR, deploys it to staging, and waits for a human to approve
the production deployment.

You never touched the cluster manually after setup. The pipeline is the
deployment record, the test report, and the audit trail — all in one.

---

## ## Key Concepts Reinforced

### Why SHA tags, not `latest`

The `latest` tag is mutable — it means "whatever was pushed most recently."
If you deploy `latest` and a new build happens mid-rollout, different pods
may pull different versions of the image. The SHA tag is immutable and
traceable: given any running deployment, you can identify the exact commit
it came from.

### How `needs:` enforces order

Without `needs:`, all jobs run in parallel. The `needs: test` on the
`build-push` job means: "only start this job if `test` completed successfully."
The entire chain — test → build → staging → prod — is a directed acyclic graph
of dependencies. Failure at any node stops all downstream nodes.

### How the approval gate works

The `environment: production` declaration on `deploy-prod` is what triggers
the pause. GitHub checks the environment's protection rules. If any required
reviewer has not approved, the job is blocked. After approval, the job runs
with exactly the same SHA it would have run with immediately — no new code
can slip in between approval and execution.

### Why multi-platform matters

Most CI runners are `amd64`. Your laptop might be `arm64` (Apple Silicon).
Production nodes could be either. Building for both architectures in the same
pipeline means the image works everywhere without rebuilding. The cost: the
build job takes 2-3x longer. Worth it.

---

## ## Step Summary

| Step | What you did                               | Key mechanism                  |
|------|--------------------------------------------|--------------------------------|
| 1    | Created GitHub Secret (kubeconfig)         | `KUBECONFIG_B64` secret        |
| 2    | Wrote pytest test suite                    | `TestClient`, 5 tests          |
| 3    | Wrote the workflow file                    | 4-job pipeline, `needs:` chain |
| 4    | Pushed and watched the pipeline run        | GitHub Actions UI              |
| 5    | Verified staging deployment updated        | `kubectl describe`             |
| 6    | Approved and watched production deploy     | GitHub Environments gate       |
| 7    | Broke a test to verify safety gates        | Pipeline stopped at test job   |

---

## ## Extend It

1. **Add Slack notifications** — use the `slackapi/slack-github-action` to post
   a message to a channel when a deployment succeeds or fails.

2. **Add semver tagging** — instead of (or in addition to) SHA tags, use
   `type=semver,pattern={{version}}` in `docker/metadata-action` so you get
   versioned tags like `1.2.3` when you push a git tag.

3. **Add a rollback job** — add a fifth job `rollback` with
   `if: failure()` that runs `kubectl rollout undo deployment/myapi` if
   the rollout fails.

4. **Add image scanning** — insert a step between `build-push` and
   `deploy-staging` that runs `docker/scout-action` or `aquasec/trivy-action`
   to scan the image for CVEs. Fail the pipeline if critical vulnerabilities
   are found.

5. **Replace `kubectl set image` with manifest files** — use the
   `scripts/update-image.sh` approach: sed the image tag into the YAML file,
   commit it back to a `deploy/` branch, and let ArgoCD (from project 06)
   pick up the change. This is the GitOps pattern.

---

⬅️ **Prev:** [04 — Full-Stack on K8s](../04_Full_Stack_on_K8s/01_MISSION.md) &nbsp;&nbsp; ➡️ **Next:** [06 — Production K8s Cluster](../06_Production_K8s_Cluster/01_MISSION.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
