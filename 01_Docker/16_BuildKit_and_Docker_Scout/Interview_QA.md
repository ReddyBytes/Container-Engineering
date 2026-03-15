# Module 16 — BuildKit and Docker Scout: Interview Q&A

---

## Q1: What is BuildKit and what problems does it solve over the legacy Docker build engine?

**Answer:**

BuildKit is Docker's modern build engine, open-sourced as `moby/buildkit` and made the default in Docker 23+. It replaced the legacy builder which processed Dockerfile instructions sequentially.

BuildKit solves three major problems:

1. **Sequential execution**: The legacy builder ran every `FROM` stage one at a time. BuildKit analyzes the Dockerfile as a dependency graph and executes independent stages in parallel, dramatically reducing build times in multi-stage Dockerfiles.

2. **Cache pollution from build tools**: With the old engine, developers had to choose between caching package downloads (which bloated images) or deleting caches every build (which was slow). BuildKit's `--mount=type=cache` keeps package manager caches on the build host without ever writing them into image layers.

3. **Secrets in layers**: Before BuildKit, passing credentials into a build meant copying files that ended up permanently in image layers. BuildKit's `--mount=type=secret` makes secrets available during a `RUN` step only, never writing them to any layer.

---

## Q2: You need to pass an `.npmrc` file containing a private registry token into a Docker build. How do you do this safely with BuildKit?

**Answer:**

Use a BuildKit secret mount. Never use `COPY` for secrets because the file will be stored in the image layer permanently — even if you later `RUN rm` it, the layer still exists.

In the Dockerfile:
```dockerfile
# syntax=docker/dockerfile:1
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc \
    npm install
```

Build command:
```bash
docker buildx build --secret id=npmrc,src=.npmrc -t myapp .
```

The `.npmrc` file is passed as a secret. During the `RUN` step, it is available at `/root/.npmrc`. After the step completes, it is gone — not in any image layer, not in the build cache. Running `docker history myapp` will show no trace of it.

---

## Q3: What is the difference between `--cache-from` with `type=inline` vs `type=registry,mode=max`?

**Answer:**

- **Inline cache** embeds cache metadata directly inside the final image. It's simple to use but only caches the layers that end up in the final image. Intermediate stages that don't contribute files to the final image are not cached.

- **Registry cache with `mode=max`** stores cache data in a separate repository in the registry, independent of the image itself. With `mode=max`, every intermediate stage's layers are cached, not just the final image's layers. This is significantly more effective in multi-stage builds because earlier stages like "compile" or "test" get cache hits even if their output isn't directly in the final image.

In CI, `mode=max` registry cache is the recommended approach because it maximizes cache hit rate across builds.

---

## Q4: What does `# syntax=docker/dockerfile:1` do and when is it required?

**Answer:**

It is a **parser directive** — a special instruction that must be the first line of the Dockerfile (before any comments). It pins the Dockerfile syntax to a specific version of the BuildKit frontend parser.

It is required (or at minimum strongly recommended) when using:
- Cache mounts (`--mount=type=cache`)
- Secret mounts (`--mount=type=secret`)
- SSH mounts (`--mount=type=ssh`)
- Heredoc syntax (`RUN <<EOF`)
- Bind mounts in `RUN` (`--mount=type=bind`)

Without this directive, Docker uses the default parser which may not support these features or may interpret them differently across Docker versions. Pinning to `docker/dockerfile:1` ensures consistent behavior and access to the latest stable features in the 1.x specification.

---

## Q5: How do BuildKit cache mounts work, and how are they different from Docker layer caching?

**Answer:**

Docker **layer caching** works by storing the result of each Dockerfile instruction as a layer. If the instruction and its inputs haven't changed, Docker reuses the cached layer. The cache contents (including downloaded packages) become part of the image.

BuildKit **cache mounts** (`--mount=type=cache`) are directories that exist on the build host outside of any image layer. They persist between builds and are read/written during `RUN` steps, but their contents are never committed to an image layer.

Practical difference: with layer caching, if you `RUN pip install -r requirements.txt` and your `requirements.txt` changes, Docker re-runs the entire download. With a cache mount, pip's download cache is always present on disk — pip skips re-downloading packages it already has, even when `requirements.txt` changes.

The cache mount also means the pip cache directory is not in the image at all, keeping images small.

---

## Q6: What is Docker Scout and how does it differ from running a separate scanning tool like Trivy?

**Answer:**

Docker Scout is a vulnerability scanner and supply chain security tool built directly into the Docker CLI (introduced 2022, expanded significantly in 2024). It scans images for CVEs, generates SBOMs, compares image versions, and recommends better base images.

Key differences from Trivy:

| | Docker Scout | Trivy |
|---|---|---|
| Installation | Built into Docker CLI | Separate install required |
| Cost | Free tier with limits; paid for full features | Fully open-source, free |
| Integration | Deep Docker Hub integration, policies in Docker org | Integrates via CLI/API |
| Base image recommendations | Yes | No |
| Scope | Container images primarily | Images, filesystems, IaC, git repos |

Both tools use similar vulnerability databases. Trivy is typically preferred for open-source deployments and broader scanning scope (IaC, filesystem). Scout is convenient for teams already using Docker Hub because scanning is integrated into the push/pull workflow.

---

## Q7: What is an SBOM and why is it becoming a requirement?

**Answer:**

An SBOM (Software Bill of Materials) is a formal, machine-readable inventory of every software component in an artifact — every package, library, and transitive dependency with their versions, licenses, and source information.

Think of it as the ingredient list on food packaging, but for software. If a critical vulnerability is discovered in a library (like Log4Shell), an SBOM lets you immediately determine whether that library exists in any of your deployed images, without having to re-scan everything.

SBOMs are becoming mandatory because:
- US Executive Order 14028 (2021) requires SBOMs for software sold to the US federal government
- Enterprise procurement teams increasingly require SBOMs from vendors
- They enable faster response to zero-day vulnerabilities
- They support license compliance auditing

Common formats: **SPDX** (Linux Foundation standard) and **CycloneDX** (OWASP standard). Both are supported by Scout, Trivy, and Syft.

---

## Q8: A teammate's Dockerfile has this pattern. What is wrong with it?

```dockerfile
FROM node:20
COPY .npmrc /root/.npmrc
RUN npm install
RUN rm /root/.npmrc
```

**Answer:**

The secret is permanently embedded in the image. Docker layers are immutable snapshots — `COPY .npmrc` creates a layer containing the file. The subsequent `RUN rm /root/.npmrc` creates a new layer where the file is absent, but the original layer still exists in the image.

Anyone with access to the image can recover the `.npmrc` by running:
```bash
docker history myapp
docker export $(docker create myapp) | tar -x --to-stdout layer-id/root/.npmrc
```

Or by using tools like `dive` to inspect individual layers.

The fix is to use a BuildKit secret mount:
```dockerfile
# syntax=docker/dockerfile:1
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc \
    npm install
```
```bash
docker buildx build --secret id=npmrc,src=.npmrc -t myapp .
```

The secret is never written to any layer. It cannot be recovered from the image.

---

## Q9: How do you build a Docker image that runs on both Intel (amd64) and Apple Silicon / AWS Graviton (arm64)?

**Answer:**

Use `docker buildx build` with the `--platform` flag:

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --push \
  -t registry.example.com/myapp:latest .
```

This produces a **manifest list** (image index) in the registry. When users pull the image, Docker automatically selects the correct architecture variant.

Requirements:
1. A BuildKit builder with multi-platform support (QEMU emulation is set up automatically in Docker Desktop; in CI, use `docker/setup-qemu-action`)
2. `--push` flag, because the local Docker image store cannot hold multi-platform manifests
3. The Dockerfile should be architecture-agnostic, or use `ARG TARGETARCH` / `ARG TARGETPLATFORM` build args to differentiate per-platform compilation

For compiled languages like Go, using `--platform=$BUILDPLATFORM` for the build stage avoids slow QEMU emulation:
```dockerfile
FROM --platform=$BUILDPLATFORM golang:1.22 AS build
ARG TARGETARCH
RUN GOARCH=$TARGETARCH go build -o /server .
```

---

## Q10: What is the `sharing` option on BuildKit cache mounts and when do you need it?

**Answer:**

The `sharing` option controls concurrent access to a cache mount when multiple builds run in parallel on the same host. There are three values:

- **`shared`** (default): Multiple builds can read and write simultaneously. Fine for most caches.
- **`locked`**: Only one build accesses the cache at a time. Others wait. Required for apt, which uses lock files that corrupt if two processes write simultaneously.
- **`private`**: Each concurrent build gets its own copy of the cache. Use when the cache directory cannot be shared at all.

Example for apt (where you always want `locked`):
```dockerfile
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y curl
```

Without `sharing=locked` on apt caches, parallel CI builds on the same runner can corrupt the apt state, leading to unpredictable build failures.

---

## Q11: How does Docker Scout integrate into a CI pipeline to enforce security policies?

**Answer:**

Scout integrates at two levels:

**1. Ad-hoc scanning with exit codes:**
```bash
# Fails CI build if any critical CVE exists
docker scout cves --exit-code --only-severity critical myapp:latest
```
The `--exit-code` flag causes Scout to return a non-zero exit code if matching vulnerabilities are found, which causes CI pipeline steps to fail.

**2. Policy-based enforcement (Docker Scout in organizations):**
- Policies are configured in the Docker Scout dashboard at the org or repo level
- Policies define thresholds: "block on any Critical CVE", "warn on High CVEs"
- `docker scout policy IMAGE` evaluates the image against all configured policies
- Integrated with Docker Hub: images pushed to Hub are automatically scanned, and policy status is visible in the Hub UI

In a GitHub Actions workflow, a typical pattern is:
1. Build image
2. Push to registry
3. Run `docker scout cves --exit-code --only-severity critical` — fails the workflow if critical CVEs are found
4. Optionally post Scout results as a PR comment using the `docker/scout-action` GitHub Action

---

## 📂 Navigation

| | |
|---|---|
| **Previous** | [15_Best_Practices](../15_Best_Practices/Interview_QA.md) |
| **Next** | [17_Docker_Init_and_Debug](../17_Docker_Init_and_Debug/Interview_QA.md) |
| **Theory** | [Theory.md](./Theory.md) |
| **Cheatsheet** | [Cheatsheet.md](./Cheatsheet.md) |
| **Code Examples** | [Code_Example.md](./Code_Example.md) |
| **Module Index** | [01_Docker README](../README.md) |
