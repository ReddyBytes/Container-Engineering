# Multi-Stage Builds — Interview Q&A

---

## Beginner

**Q1: What problem do multi-stage builds solve?**

Without multi-stage builds, your production image contains everything needed to build the application — compilers, build tools, test frameworks, dev dependencies — none of which should be in production. This wastes space (images can be 1 GB+ unnecessarily), increases security risk (more packages = more CVEs), and slows down deployments.

Multi-stage builds let you compile your app in one stage and copy only the built artifact into a clean, minimal final stage. You hand out the cake, not the kitchen.

---

**Q2: What is the FROM ... AS syntax used for?**

The `AS` keyword names a build stage so other stages can reference it:

```dockerfile
FROM golang:1.22 AS builder   # name this stage "builder"
RUN go build -o server .

FROM alpine:3.19               # new stage, clean filesystem
COPY --from=builder /app/server .   # reference "builder" by name
```

Without the name, you'd have to reference stages by their 0-based index, which is fragile.

---

**Q3: What does COPY --from=builder do?**

It copies files from a previously named build stage into the current stage, instead of from the local host filesystem. This is how you transfer build artifacts between stages — you pull only what you need, leaving everything else behind.

---

**Q4: In a multi-stage build, which stage becomes the final image?**

The last `FROM` statement's stage becomes the final image. All previous stages are intermediate — they exist only during the build and are discarded afterward. You can also explicitly choose which stage becomes the final image using `docker build --target stagename`.

---

**Q5: What is the `scratch` image?**

`scratch` is Docker's reserved empty image — it has literally nothing: no OS, no shell, no utilities. It's the smallest possible base. Go binaries compiled with `CGO_ENABLED=0` are fully self-contained and can run from `scratch`. The resulting image is only as large as the binary itself (~5–15 MB). It's also highly secure: nothing to exploit, no shell for attackers to use.

---

## Intermediate

**Q6: Why do you copy go.mod before the source code in Go multi-stage builds?**

Docker's layer cache works sequentially. If you copy all source code first, any change to any file invalidates the cache for all subsequent layers — including the slow `go mod download` step. By copying only `go.mod` and `go.sum` first, the dependency download is cached and only re-runs when your dependencies actually change. This can save 1–2 minutes per build.

```dockerfile
COPY go.mod go.sum ./      # only changes when deps change
RUN go mod download         # stays cached
COPY . .                    # invalidates only build step on source change
RUN go build -o server .
```

---

**Q7: How would you set up a multi-stage build that runs tests in CI?**

Add an explicit test stage and use `--target` to build to it in CI:

```dockerfile
FROM golang:1.22 AS builder
WORKDIR /app
COPY . .
RUN go build -o server .

FROM golang:1.22 AS tester
WORKDIR /app
COPY . .
RUN go test ./...

FROM alpine:3.19 AS production
COPY --from=builder /app/server .
```

In CI:
```bash
# Fail fast if tests fail
docker build --target tester -t my-app:test .

# Only build production image if tests pass
docker build --target production -t my-app:prod .
```

---

**Q8: How do parallel stages work in multi-stage builds?**

With BuildKit enabled, Docker analyzes the dependency graph of stages. Stages that don't depend on each other build in parallel. If you have a frontend stage and a backend stage with no relationship, they compile simultaneously — reducing total build time significantly.

```dockerfile
FROM node:20 AS frontend    # runs in parallel
RUN npm run build

FROM python:3.12 AS backend  # runs in parallel
RUN pip install -r requirements.txt

FROM nginx:alpine            # waits for both stages
COPY --from=frontend /app/dist /html
COPY --from=backend /app /backend
```

---

**Q9: What's the typical size difference between a Node.js app with and without multi-stage?**

A Node.js frontend app built from `node:20` can be 600–800 MB because it includes Node.js runtime, npm, and all dev dependencies (TypeScript, webpack, Jest, etc.). Using multi-stage to build the static files and then serving them from `nginx:1.25-alpine` results in a 20–30 MB image — a 95%+ reduction. nginx serves the static files, and Node.js is no longer needed at runtime.

---

**Q10: Can you copy from an external image in a multi-stage build?**

Yes. `COPY --from=` accepts any image reference, not just named stages:

```dockerfile
# Copy CA certificates from Alpine without inheriting Alpine
COPY --from=alpine:3.19 /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

# Copy a tool binary from its official image
COPY --from=grpc/grpc-gateway:latest /bin/protoc-gen-grpc-gateway /usr/local/bin/
```

This is useful when your `scratch`-based image needs one specific file (like CA certs for HTTPS calls) but you don't want to base your image on Alpine.

---

## Advanced

**Q11: How do multi-stage builds affect the Docker build cache in CI?**

Each stage has its own cache. In CI, to preserve cache across runs, you use `--cache-from` with a registry:

```bash
# Pull previous cache
docker pull myregistry/my-app:buildcache || true

# Build using cached layers
docker build \
  --cache-from myregistry/my-app:buildcache \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  -t myregistry/my-app:latest .

# Push updated cache
docker push myregistry/my-app:buildcache
```

With GitHub Actions, `docker/build-push-action` handles this automatically via `cache-from: type=gha` and `cache-to: type=gha`.

---

**Q12: What are the security advantages of multi-stage builds beyond just image size?**

1. **Smaller attack surface**: Fewer packages = fewer CVE exposures. A 5 MB binary-only image has near-zero OS vulnerabilities vs. a full golang:1.22 image with hundreds of packages.
2. **No secrets in final image**: Build secrets (npm auth tokens, git credentials) stay in the builder stage and are never present in the final image.
3. **No shell in scratch images**: Attackers who gain code execution can't pop a shell if there isn't one.
4. **Supply chain reduction**: Fewer packages means fewer third-party dependencies to audit.
5. **Smaller scanning scope**: Vulnerability scanners run in seconds on a 10 MB image; minutes on a 1 GB image.

---

**Q13: How does the Python multi-stage pattern differ from Go's?**

Go compiles to a static binary that needs no runtime. Python is interpreted — the Python interpreter must be present at runtime. So you can't use `scratch`. Instead, the multi-stage approach:

1. **Builder stage**: Use `python:3.12` (full) to install packages
2. **Runtime stage**: Use `python:3.12-slim` (minimal, no dev tools, no build headers)

The `--prefix=/install` trick installs packages to a custom directory, which you then copy wholesale:

```dockerfile
FROM python:3.12 AS builder
RUN pip install --prefix=/install -r requirements.txt

FROM python:3.12-slim
COPY --from=builder /install /usr/local
COPY app.py .
CMD ["python", "app.py"]
```

This avoids copying `pip` itself or its metadata into the final image.

---

## 📂 Navigation

| | Link |
|---|---|
| Previous | [10 · Docker Registry](../10_Docker_Registry/Interview_QA.md) |
| Theory | [Multi-Stage Theory](./Theory.md) |
| Cheatsheet | [Multi-Stage Cheatsheet](./Cheatsheet.md) |
| Code Examples | [Multi-Stage Code Examples](./Code_Example.md) |
| Next | [12 · Docker Security](../12_Docker_Security/Interview_QA.md) |
