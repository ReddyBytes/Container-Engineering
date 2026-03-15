# Docker Registry — Interview Q&A

---

## Beginner

**Q1: What is a Docker registry?**

A registry is a storage and distribution service for Docker images. When you run `docker pull nginx`, Docker connects to a registry (Docker Hub by default), downloads the image, and stores it locally. When you push your own image with `docker push`, you upload it to a registry so it can be pulled on other machines.

---

**Q2: What is the difference between Docker Hub, ECR, and GHCR?**

- **Docker Hub** — Docker's own public registry. Default for `docker pull`. Has official images, verified publisher images, and community images. Free tier has rate limits.
- **AWS ECR** — Private registry hosted on AWS. Access controlled by IAM. Best for teams already on AWS. Supports native image scanning.
- **GHCR** — GitHub Container Registry (ghcr.io). Best for teams whose code is on GitHub. Uses `GITHUB_TOKEN` for auth in Actions, making it seamless in CI.

---

**Q3: What does `docker login` do?**

It authenticates you to a registry. After running `docker login`, your credentials (or an access token) are saved to `~/.docker/config.json`. Docker uses these credentials automatically when pushing or pulling from that registry. Each registry requires a separate login.

---

**Q4: What does an image tag represent?**

A tag is a human-readable label pointing to a specific version of an image. For example, `nginx:1.25` means the nginx image at version 1.25. Tags are mutable — they can be moved to point to a different image layer. Only a digest (SHA256 hash) is truly immutable.

---

**Q5: Why is using `latest` in production a bad practice?**

`latest` is just a tag that has no auto-update behavior. Problems:
1. Non-deterministic: `latest` today may be different from `latest` tomorrow
2. No traceability: you can't tell what code is in "latest"
3. No rollback path: you don't know what the previous "latest" was
4. Cache confusion: Docker may use a stale locally cached `latest`

Always pin to a specific version tag in production.

---

## Intermediate

**Q6: Walk me through pushing an image to ECR from scratch.**

```bash
# 1. Create the ECR repository
aws ecr create-repository --repository-name my-app --region us-east-1

# 2. Authenticate Docker to your ECR account
aws ecr get-login-password --region us-east-1 \
  | docker login --username AWS --password-stdin \
    123456789012.dkr.ecr.us-east-1.amazonaws.com

# 3. Build the image
docker build -t my-app:1.0.0 .

# 4. Tag it with the full ECR path
docker tag my-app:1.0.0 \
  123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app:1.0.0

# 5. Push
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app:1.0.0
```

---

**Q7: What is the image naming convention for private registries?**

```
registry/namespace/repository:tag
```

When the registry is omitted, Docker Hub is assumed. For a private registry:
- `123456789.dkr.ecr.us-east-1.amazonaws.com/my-app:v1.0.0` — ECR
- `ghcr.io/my-org/my-app:v1.0.0` — GHCR
- `harbor.company.com/team/my-app:v1.0.0` — Harbor

The registry hostname must be included in both the tag and the push command.

---

**Q8: What is vulnerability scanning, and which tools do it?**

Image vulnerability scanning analyzes the OS packages and language dependencies installed in an image against a database of known CVEs (Common Vulnerabilities and Exposures). It reports vulnerabilities by severity: CRITICAL, HIGH, MEDIUM, LOW.

Tools:
- **Docker Scout** — Built into Docker CLI. `docker scout quickview myimage`
- **Trivy** — Open source from Aqua Security. Scans images, Dockerfiles, K8s manifests. Most widely used in CI.
- **ECR Scanning** — Native AWS scanning, can be triggered on push
- **Snyk** — Commercial scanner with IDE integrations

In CI, run `trivy image --exit-code 1 --severity CRITICAL myimage` to fail the pipeline if critical CVEs are found.

---

**Q9: What is the difference between a tag and a digest?**

A **tag** is a human-readable mutable label. The `latest` tag, for example, can be re-pushed to point to a completely different image. A **digest** is the SHA256 hash of the image manifest — it is immutable. Pulling by digest guarantees you get the exact same bits every time:

```bash
# Pull by tag (mutable - could change)
docker pull my-app:v1.0.0

# Pull by digest (immutable - never changes)
docker pull my-app@sha256:a1b2c3d4...
```

In high-security environments, pin base images by digest in Dockerfiles.

---

**Q10: What is Harbor and why would you use it?**

Harbor is an open-source, self-hosted container registry. Reasons to use it:
- **Compliance/air-gap**: Images never leave your infrastructure
- **RBAC**: Fine-grained access control per project/team
- **Replication**: Mirror images between registries or data centers
- **Scanning**: Built-in Trivy integration
- **Content trust**: Image signing with Notary

Teams in regulated industries (healthcare, finance, government) often run Harbor on-premises rather than using a cloud-hosted registry.

---

## Advanced

**Q11: How do you implement an image tagging strategy for a CI/CD pipeline?**

A robust strategy uses multiple tags for the same image:

1. **Git SHA** (always): Immutable, traceable to exact commit
   ```
   ghcr.io/my-org/my-app:a3f9b2c
   ```

2. **Semver** (on release): Human-readable version
   ```
   ghcr.io/my-org/my-app:v1.2.3
   ghcr.io/my-org/my-app:v1.2    # floating minor
   ghcr.io/my-org/my-app:v1      # floating major
   ```

3. **Branch name** (for preview): Useful for staging environments
   ```
   ghcr.io/my-org/my-app:main
   ghcr.io/my-org/my-app:feature-payment
   ```

In GitHub Actions, this is done using `docker/metadata-action` which auto-generates these tags.

---

**Q12: How do ECR lifecycle policies work and why do they matter?**

ECR lifecycle policies automatically delete old images based on rules. Without them, ECR repositories grow indefinitely, increasing storage costs and making it hard to find current images.

Example policy that keeps only the 10 most recent images per tag prefix:

```json
{
  "rules": [{
    "rulePriority": 1,
    "description": "Keep last 10 images",
    "selection": {
      "tagStatus": "tagged",
      "tagPrefixList": ["v"],
      "countType": "imageCountMoreThan",
      "countNumber": 10
    },
    "action": { "type": "expire" }
  }]
}
```

In large teams running CI many times a day, this saves significant storage costs.

---

**Q13: How do you securely store Docker registry credentials in CI/CD?**

Never hard-code credentials. Use these approaches:

- **GitHub Actions + GHCR**: Use the built-in `GITHUB_TOKEN` secret — no additional credentials needed
- **GitHub Actions + ECR**: Use OIDC (OpenID Connect) to assume an IAM role directly from the workflow — no stored AWS keys
- **Any CI + Docker Hub**: Store as an encrypted repository secret, use an access token (not password), and scope the token to read-only or repository-specific

The OIDC approach is the gold standard: the CI runner gets a short-lived token dynamically — there are no static credentials to rotate or leak.

---

## 📂 Navigation

| | Link |
|---|---|
| Previous | [09 · Docker Compose](../09_Docker_Compose/Interview_QA.md) |
| Theory | [Registry Theory](./Theory.md) |
| Cheatsheet | [Registry Cheatsheet](./Cheatsheet.md) |
| Next | [11 · Multi-Stage Builds](../11_Multi_Stage_Builds/Interview_QA.md) |
