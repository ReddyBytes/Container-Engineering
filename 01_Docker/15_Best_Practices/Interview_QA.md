# Docker Best Practices — Interview Q&A

## Beginner

**Q1: What makes a good Dockerfile?**

A good Dockerfile produces an image that is small, fast to build, reproducible, and secure. The main characteristics:

**Small image size:** Start from a minimal base (`alpine`, `slim`, or `distroless`). Only install what the application actually needs. Use multi-stage builds to leave build tools out of the final image.

**Optimized layer caching:** Order instructions from least-frequently-changed to most-frequently-changed. Copy dependency manifests first, install dependencies, then copy source code. This way a code change doesn't re-run a long `npm install`.

**Non-root user:** Create a dedicated non-root user and switch to it with `USER`. Running as root inside a container is a security risk if the container is ever compromised.

**Pinned versions:** Use specific version tags (`python:3.12.3-slim`) not floating tags (`python:latest`). Reproducible builds require knowing exactly what you're building from.

**Explicit metadata:** `EXPOSE` the port your app listens on. Set a meaningful `CMD`. Add `LABEL` metadata for maintainer and version information.

**Clean apt/yum operations:** Run `apt-get update` and `apt-get install` in a single `RUN` layer and delete caches in the same layer so they don't persist as wasted space in the image.

---

**Q2: Why should you use a `.dockerignore` file and what goes in it?**

`.dockerignore` tells Docker which files to exclude from the **build context** — the set of files sent to the Docker daemon when you run `docker build`. Without it, everything in the directory is sent, including files you never want in the image.

Problems without `.dockerignore`:
- `node_modules` (potentially gigabytes) is sent to the daemon on every build
- `.git` (commit history, all branches) inflates the build context
- `.env` files with credentials could be accidentally `COPY`'d into the image
- Build speed suffers — transferring a large context takes time even before the first instruction runs

What to always include in `.dockerignore`:

```
.git
.gitignore
node_modules
__pycache__
*.pyc
*.pyo
.env
*.pem
*.key
.DS_Store
dist/
build/
coverage/
.idea/
.vscode/
*.test.js
*.spec.py
README.md
docs/
```

The rule: if a file doesn't need to be in the image, it shouldn't be in the build context.

---

**Q3: What does "one process per container" mean and why is it recommended?**

Each container should run one main service — not a bundle of services duct-taped together. Not nginx + your API + a background job + a cron scheduler all in one container.

Why:
- **Independent scaling:** Need more API workers? Scale the API container. Scaling a bundle always scales everything together.
- **Failure isolation:** If the cron job crashes, it shouldn't take the web server with it.
- **Clean logs:** Logs from one container = one service. Easy to query, easy to alert on.
- **Simpler health checks:** You check one service's health, not an aggregate of four.
- **Independent updates:** Update the worker without touching the web tier.

The exception: init systems and sidecar processes that exist specifically to support the main process (log shippers, metrics exporters) are acceptable in some architectures. But they should be deliberate design choices, not convenience shortcuts.

---

**Q4: Where should a containerized application write its logs?**

To `stdout` and `stderr`. Never to files inside the container.

The container runtime captures these streams. `docker logs` works. Log aggregators (Datadog, CloudWatch, Loki, Splunk) collect them automatically. Kubernetes' `kubectl logs` works.

If you write to files:
- `docker logs` shows nothing — the file is inside the container
- Log aggregators see nothing — they watch stdout/stderr
- Files fill up the container's writable layer, eventually causing the container to fail

```dockerfile
# Python: disable buffering so logs appear immediately
ENV PYTHONUNBUFFERED=1

# Node.js logs to stdout by default
# For other apps, configure the logging output in the app's config
```

For applications that write to files by default (nginx, Apache, many Java frameworks), configure them to write to `/dev/stdout` and `/dev/stderr` instead, or symlink log files to those special devices.

---

**Q5: Why should you pin specific version tags for base images instead of using `latest`?**

`latest` is a moving target. Today's `python:latest` might be 3.11. Next month it's 3.12. The build that worked today might fail tomorrow because a new Python version changed behavior or removed a feature your code relied on.

Specific tags give you:
- **Reproducibility:** The same tag produces the same image weeks or months later
- **Predictability:** You know exactly what you're deploying
- **Auditability:** When something breaks, you can point to exactly which base image was used
- **Controlled upgrades:** You update the tag intentionally, review the changes, and test before deploying

Use `latest` only for throwaway local experiments — never in a Dockerfile that will be used in CI/CD or production.

For maximum reproducibility, pin by digest: `python:3.12.3-slim@sha256:abc123...` — a digest is cryptographically tied to the exact image content and cannot be changed.

---

## Intermediate

**Q6: What is image layer caching and how do you optimize for it?**

Every `RUN`, `COPY`, and `ADD` instruction in a Dockerfile creates a new layer. Docker caches these layers. When you rebuild, Docker reuses cached layers from the first changed instruction downward. If nothing changed, the entire build uses cache and completes in seconds.

The critical insight: Docker invalidates cache for a layer when the instruction itself changes, or when any file added in that layer changes. All layers below the invalidated one also get rebuilt.

**Bad order — code change triggers dependency reinstall:**
```dockerfile
COPY . .                   # any code change invalidates this layer
RUN npm ci                 # re-runs every time (even if package.json didn't change)
```

**Good order — code change does NOT affect dependencies:**
```dockerfile
COPY package.json package-lock.json ./   # only invalidated when these files change
RUN npm ci                               # uses cache unless package*.json changed
COPY . .                                 # code changes only affect this and below
```

Real-world impact: with a project that has 300 npm packages, bad layer order means 2-3 minutes per build. Good layer order means 5 seconds (cache hit). On a team doing 20 builds per day, that's hours per day in CI time.

The same pattern applies to Python (`requirements.txt` first), Java (`pom.xml` or `build.gradle` first), and Go (`go.mod` and `go.sum` first).

---

**Q7: What is a distroless image and when should you use one?**

A distroless image contains only the application runtime and its dependencies — no shell (`bash`/`sh`), no package manager (`apt`, `apk`), no standard Unix utilities (`ls`, `curl`, `cat`). Google maintains the most widely used distroless images at `gcr.io/distroless/`.

Examples:
```dockerfile
# Instead of python:3.12-slim (has bash, apt, many utils)
FROM gcr.io/distroless/python3-debian12

# Instead of eclipse-temurin:21-jre-alpine
FROM gcr.io/distroless/java21-debian12
```

Benefits:
- **Smallest possible attack surface:** No shell means an attacker who gets code execution inside the container can't easily run commands, download tools, or explore the filesystem
- **Fewer CVEs:** No shell, no libc tools, no package managers — far fewer packages to have vulnerabilities
- **Smaller image size:** Less software = smaller image

Trade-offs:
- **Debugging is harder:** No `docker exec container bash` — you can't get a shell. You need a separate debug sidecar or `--debug` variant of the image.
- **Only for production:** Keep a shell-enabled image for development and debugging; use distroless for the final production stage in multi-stage builds.

```dockerfile
# Multi-stage: build in a full image, run in distroless
FROM python:3.12 AS builder
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

FROM gcr.io/distroless/python3-debian12
COPY --from=builder /install /usr/local
COPY src/ /app/
CMD ["/app/main.py"]
```

---

**Q8: Why should containers run as a non-root user?**

By default, processes inside a Docker container run as root (UID 0). If the container process is compromised — via a bug in the app, a dependency, or the base image — an attacker has root inside the container.

While containers are isolated, root inside a container can:
- Read any mounted volume (potentially exposing host data)
- Exploit container escape vulnerabilities (which exist; the kernel is shared)
- Modify the container filesystem in ways that might persist via volumes
- Access sensitive information in environment variables or files

Adding a non-root user is two lines:
```dockerfile
RUN groupadd --gid 1001 app && \
    useradd --uid 1001 --gid app --no-create-home app

COPY --chown=app:app . .
USER app
```

With a non-root user, an attacker who gains code execution in your container has constrained privileges — they cannot write to system paths, bind privileged ports, or easily escalate.

In Kubernetes, you can enforce this at the cluster level with a `SecurityContext` or via Pod Security Standards. Many security scanners flag containers running as root as a critical issue.

---

**Q9: What is multi-stage build and how does it reduce the attack surface?**

A multi-stage build uses multiple `FROM` instructions in a single Dockerfile. Each `FROM` starts a new build stage. You copy only specific artifacts from one stage to the next.

```dockerfile
# Stage 1: Build (has compiler, build tools, source code)
FROM golang:1.22 AS builder
WORKDIR /app
COPY . .
RUN go build -o /app/myservice ./cmd/server

# Stage 2: Runtime (has only the binary)
FROM gcr.io/distroless/static-debian12
COPY --from=builder /app/myservice /myservice
ENTRYPOINT ["/myservice"]
```

The final image contains only the compiled binary. The Go compiler, source code, git history, test files, and build dependencies never appear in the image that gets pushed to the registry and deployed.

Attack surface reduction:
- No compiler means an attacker can't compile new exploits inside the container
- No source code means intellectual property isn't exposed in the image
- No build tools (`make`, `gcc`, `git`) means fewer utilities available to an attacker
- Smaller image means fewer packages, fewer CVEs

For a typical Go service: build stage might be 1.2 GB; final distroless stage is 5-15 MB. That's 100x+ size reduction with the attack surface to match.

---

## Advanced

**Q10: How do you reduce the CVE count in a Docker image systematically?**

A systematic CVE reduction process:

**1. Start with a minimal base.** `alpine` (5 MB) has 10-20 packages. `debian:slim` has 100+. `distroless` has even fewer. Fewer packages = fewer CVEs to start.

**2. Use multi-stage builds.** Build tools (gcc, rustc, pip, npm) stay in the build stage. The production image has only the runtime.

**3. Scan in CI and enforce a gate.** Run `trivy image --exit-code 1 --severity CRITICAL myimage` in CI. A build that introduces a CRITICAL CVE fails. This prevents regressions.

**4. Automate base image updates.** Use Dependabot or Renovate to open PRs when new base image versions are available. Many CVEs are fixed by simply updating `FROM python:3.12.3-slim` to `3.12.4-slim`.

**5. Audit with `docker scout`.** `docker scout cves --only-fixed myimage` shows CVEs that have fixes available in newer versions. These are your immediate wins.

**6. Pin and update dependencies.** Pinned app dependencies (in `requirements.txt`, `package-lock.json`) are reproducible; automated tools bump them with CVE context in the PR.

**7. Remove unnecessary files in build stage.** Delete test files, documentation, and build artifacts before copying to the production stage.

**8. Use BuildKit secret mounts for credentials.** `--mount=type=secret` passes build-time secrets without baking them into any layer.

---

**Q11: What are Docker Content Trust and image signing, and why do they matter?**

Docker Content Trust (DCT) is a mechanism for verifying the authenticity and integrity of container images. It uses **The Update Framework (TUF)** and **Notary** to sign and verify image content.

When DCT is enabled (`DOCKER_CONTENT_TRUST=1`), Docker:
- Signs images when pushing: `docker push` signs the image manifest with a private key
- Verifies images when pulling: `docker pull` refuses images that aren't signed or whose signature doesn't verify

```bash
# Enable DCT for all docker commands
export DOCKER_CONTENT_TRUST=1

# Push signs the image automatically (requires Notary keys)
docker push myorg/myimage:1.2.3

# Pull verifies signature (fails if unsigned or signature invalid)
docker pull myorg/myimage:1.2.3
```

Why it matters:
- **Supply chain security:** Prevents pulling tampered images — an attacker who compromises your registry cannot substitute a malicious image because it won't have a valid signature
- **Tag integrity:** Verifies the image tagged as `v1.2.3` is actually what your team built and signed, not a different image that was pushed under that tag
- **Regulatory compliance:** Some security frameworks (PCI-DSS, FedRAMP) require cryptographic verification of deployed artifacts

Modern alternatives and extensions:
- **Sigstore/Cosign:** A more modern approach to container image signing, keyless signing via OIDC, increasingly used in supply chain security
- **In-toto:** An attestation framework that signs the entire supply chain, not just the final image
- **OCI signatures:** Sigstore stores signatures as OCI artifacts alongside the image in the registry

---

**Q12: How do you audit container security in a CI/CD pipeline?**

A comprehensive security audit pipeline has multiple layers:

**Layer 1: Static Dockerfile analysis (before build)**
```yaml
# In CI (GitHub Actions example)
- name: Lint Dockerfile
  uses: hadolint/hadolint-action@v3
  with:
    dockerfile: Dockerfile
    failure-threshold: warning
```
Hadolint catches common mistakes: `apt-get update` without `install`, `ADD` instead of `COPY`, running as root, etc.

**Layer 2: Image scanning (after build)**
```bash
# Trivy: comprehensive vulnerability scanner
trivy image --exit-code 1 --severity CRITICAL,HIGH myimage:$SHA

# Docker Scout (built into Docker CLI)
docker scout cves --exit-code --only-severity critical myimage:$SHA
```

**Layer 3: Secret scanning (before build)**
```bash
# Detect accidentally committed secrets
trufflesecurity/trufflehog filesystem --directory .
# or: gitleaks detect --source .
```

**Layer 4: Software Bill of Materials (SBOM) generation**
```bash
# Generate SBOM for compliance and auditing
docker sbom myimage:$SHA > sbom.json
syft myimage:$SHA -o spdx-json > sbom.spdx.json
```

**Layer 5: Image signing (after scan passes)**
```bash
# Sign with Cosign (Sigstore)
cosign sign --key cosign.key myimage:$SHA
```

**Layer 6: Runtime security policies**
Define allowed images and required policies in OPA/Gatekeeper or Kyverno (for Kubernetes), rejecting deployments that don't meet security requirements.

The principle: shift security left — catch problems at build time, not at runtime. A CVE detected in CI costs minutes to fix; one detected in production costs hours and potentially causes an incident.

---

**Q13: What is OCI compliance and why does it matter for container portability?**

OCI stands for the **Open Container Initiative** — a Linux Foundation project that defines open standards for container formats and runtimes. The key specifications:

- **OCI Image Specification:** Defines the format of a container image (manifest, layers, configuration). Any OCI-compliant image can be run by any OCI-compliant runtime.
- **OCI Runtime Specification:** Defines how a container runtime creates and runs containers (the low-level lifecycle: creating a bundle, starting/stopping a container). `runc` is the reference implementation.
- **OCI Distribution Specification:** Defines the API for distributing (pushing/pulling) container images between registries.

**Why it matters:**

Before OCI (circa 2015), Docker had a proprietary format. The ecosystem was locked to Docker's implementation. OCI created interoperability:

- A Docker-built image runs on containerd, podman, CRI-O, or any OCI runtime
- Kubernetes (via CRI) works with any OCI-compliant runtime — switching from Docker to containerd requires no image rebuilds
- Images pushed to Docker Hub can be pulled by any OCI-compliant tool
- Alternative builders like Buildah, Kaniko, and ko produce OCI images that work everywhere

**Practical implications:**
```bash
# Build with Docker — produces OCI-compliant image
docker build -t myimage .

# Run with Podman (not Docker) — works because OCI-compliant
podman run myimage

# Push to any OCI-compliant registry (ECR, GCR, ACR, Quay)
docker push myregistry.example.com/myimage:1.0.0

# Pull with containerd (Kubernetes runtime)
# Works: same OCI format
```

OCI compliance is the reason you can build with Docker in CI, push to Amazon ECR, and run on a Kubernetes cluster using containerd — all different tools, all speaking the same standard.

---

## 📂 Navigation

**In this folder:**
| File | |
|---|---|
| [📖 Theory.md](./Theory.md) | Full explanation |
| [⚡ Cheatsheet.md](./Cheatsheet.md) | Quick reference |
| 🎯 **Interview_QA.md** | ← you are here |

⬅️ **Prev:** [Docker in CI/CD](../14_Docker_in_CICD/Interview_QA.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [BuildKit and Docker Scout](../16_BuildKit_and_Docker_Scout/Theory.md)
🏠 **[Home](../../README.md)**
