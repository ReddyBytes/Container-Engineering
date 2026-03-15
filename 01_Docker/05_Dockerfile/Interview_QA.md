# Dockerfile — Interview Q&A

## Beginner

**Q1: What is the difference between CMD and ENTRYPOINT?**

Both define what runs when a container starts, but they behave differently when you pass arguments to `docker run`:

- **`CMD`** sets the default command. If you pass arguments to `docker run`, they completely replace CMD.
- **`ENTRYPOINT`** sets a fixed executable. Arguments passed to `docker run` are *appended* to ENTRYPOINT, not replacing it.

```dockerfile
# With only CMD:
CMD ["python", "app.py"]
```
```bash
docker run myapp               # runs: python app.py
docker run myapp python other.py  # overrides: python other.py
```

```dockerfile
# With ENTRYPOINT + CMD:
ENTRYPOINT ["python"]
CMD ["app.py"]
```
```bash
docker run myapp               # runs: python app.py
docker run myapp other.py      # runs: python other.py (CMD replaced, ENTRYPOINT fixed)
docker run --entrypoint ls myapp  # override entrypoint: ls
```

The common pattern: `ENTRYPOINT` for the executable, `CMD` for default arguments. Use `ENTRYPOINT` when you want the container to always behave like a specific tool.

---

**Q2: What is .dockerignore and why is it important?**

`.dockerignore` is a file in the same directory as your Dockerfile that lists patterns of files/directories to exclude from the build context. It works like `.gitignore`.

It's important for two reasons:

1. **Performance:** Docker sends the entire build context to the daemon before building. If you have a `node_modules` folder with 100,000 files, all of them are sent over the socket even if you never `COPY` them. A `.dockerignore` prevents that.

2. **Security:** Without `.dockerignore`, a `COPY . .` instruction could accidentally copy `.env` files, private keys, certificates, or other secrets into the image. Anyone who pulls the image (or runs `docker run` on it) could extract those secrets. Always exclude secrets from the build context.

Common entries: `.git`, `node_modules`, `.env`, `*.pem`, `__pycache__`, `.vscode`.

---

**Q3: What is the difference between COPY and ADD?**

Both copy files from the build context into the image. The difference is that `ADD` has extra behavior:
- It can accept URLs as source (fetching a remote file at build time)
- It auto-extracts compressed tar archives (`.tar.gz`, `.tar.bz2`, etc.) into the destination

**Use `COPY` almost always.** The extra behaviors of `ADD` are surprising and can cause unintended results. The one legitimate use of `ADD` is for adding and extracting a local tar archive. For fetching remote files, use `RUN curl` or `RUN wget` instead — this makes the fetch explicit in the layer and allows you to verify checksums.

---

**Q4: What does EXPOSE do?**

`EXPOSE` documents that the containerized application listens on a particular port. That's all it does — it's documentation, not an actual firewall rule or port binding.

```dockerfile
EXPOSE 8080   # documents: this app listens on 8080
```

This doesn't make port 8080 accessible from your host. To actually publish the port, you use `-p` at runtime:
```bash
docker run -p 8080:8080 myapp   # now accessible at localhost:8080
docker run -P myapp              # publishes all EXPOSE'd ports to random host ports
```

`EXPOSE` is useful for tooling (it shows up in `docker inspect`, and `docker run -P` uses it), and as documentation for anyone reading the Dockerfile.

---

## Intermediate

**Q5: Why should you always use exec form `["cmd", "arg"]` instead of shell form `cmd arg` for ENTRYPOINT?**

When you use shell form, Docker runs your command inside `/bin/sh -c`. This means `/bin/sh` is PID 1 in the container, not your application.

The problem: Linux signals (like SIGTERM from `docker stop`) are sent to PID 1. Shells (`/bin/sh`) don't typically forward signals to their child processes. So SIGTERM sent to the shell never reaches your app. Docker waits 10 seconds (the default stop timeout), then sends SIGKILL, forcibly killing your app without a chance to gracefully shut down.

With exec form, your process is PID 1 and receives signals directly:

```dockerfile
# BAD — shell is PID 1, signals not forwarded
ENTRYPOINT python app.py

# GOOD — python is PID 1, receives SIGTERM directly
ENTRYPOINT ["python", "app.py"]
```

If you use an entrypoint shell script, end it with `exec "$@"` to replace the shell with the final command:
```bash
#!/bin/sh
# do initialization...
exec "$@"   # replace this shell with the CMD process — it becomes PID 1
```

---

**Q6: What is the difference between ARG and ENV?**

| | `ARG` | `ENV` |
|---|---|---|
| Available during build | Yes | Yes |
| Available at runtime (container) | No | Yes |
| Visible in `docker inspect` | No | Yes |
| Can be overridden | `--build-arg` flag | `-e` flag at `docker run` |
| Use for secrets? | Caution: visible in `docker history` | No: visible in `docker inspect` |

`ARG` values are visible in `docker history` (as build layer metadata), so they're not truly secret during the build. For secrets needed during build (e.g., private npm registry token), use BuildKit's `--mount=type=secret` instead.

`ENV` values are embedded in the image metadata and visible to anyone who can run `docker inspect myimage`. Never use `ENV` for passwords or API keys.

---

**Q7: Explain layer caching in the context of Dockerfile instruction order. Give a concrete example of good vs bad ordering.**

Each Dockerfile instruction produces a layer. Docker caches layers by instruction + content hash of any files copied. A cache hit requires the instruction to be identical AND all layers above it to also be cache hits. The moment any layer is a miss, all subsequent layers are rebuilt.

**Bad ordering (slow builds):**

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY . .                   # every code change busts cache here...
RUN npm ci                 # ...so npm ci runs on EVERY build, even if package.json unchanged
CMD ["node", "src/index.js"]
```

**Good ordering (fast builds):**

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json ./   # copy only what npm needs
RUN npm ci                               # cached until package files change
COPY . .                                 # source changes only rebuild this layer
CMD ["node", "src/index.js"]
```

Result: With the good ordering, `npm ci` (which might take 30-60 seconds) only runs when `package.json` or `package-lock.json` changes. For the typical 50+ commits per day where only source files change, the build is nearly instant for the npm install step.

---

## Advanced

**Q8: What are multi-stage builds and why are they important for production images?**

A multi-stage build uses multiple `FROM` statements in one Dockerfile, each starting a new build stage. Files can be copied between stages with `COPY --from=stage_name`. Only the final stage's contents end up in the shipped image.

This solves a critical problem: build tools (compilers, test runners, dev dependencies) are huge and unnecessary in production images. Before multi-stage builds, you'd either ship a massive image with all build tools, or maintain two separate Dockerfiles.

```dockerfile
# Stage 1: Build
FROM golang:1.22 AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o server .

# Stage 2: Production image
# 'distroless' contains no shell, no package manager — minimal attack surface
FROM gcr.io/distroless/static-debian11
COPY --from=builder /app/server /server
ENTRYPOINT ["/server"]
```

The Go compiler (hundreds of MB) never ends up in the production image. The final image might be 10 MB.

Benefits:
- Dramatically smaller production images (smaller = faster pull, less attack surface)
- No build secrets in the final image (npm tokens, etc. only in builder stage)
- Single Dockerfile, one build command — no separate dev/prod Dockerfiles

---

**Q9: How would you handle a secret (like a private npm token) needed during `docker build` without leaking it into the image?**

Never use `ENV` or `ARG` for secrets — they're visible in image metadata and `docker history`.

**Modern solution: BuildKit secrets mount**

```dockerfile
# syntax=docker/dockerfile:1
FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json ./

# Mount the secret at build time — it's NEVER written to any layer
RUN --mount=type=secret,id=npm_token \
    NPM_TOKEN=$(cat /run/secrets/npm_token) \
    npm config set //registry.npmjs.org/:_authToken=$NPM_TOKEN && \
    npm ci && \
    npm config delete //registry.npmjs.org/:_authToken

COPY . .
CMD ["node", "src/index.js"]
```

```bash
# Pass secret at build time — it's NEVER stored in the image
docker buildx build \
  --secret id=npm_token,src=$HOME/.npmrc \
  -t myapp:1.0 .
```

The secret is mounted as a tmpfs file inside `/run/secrets/` during the RUN step and is never committed to any layer. Running `docker history`, `docker inspect`, or extracting the image filesystem will not reveal the secret.

---

**Q10: What is the ONBUILD instruction? When would you use it?**

`ONBUILD` registers a trigger instruction that fires when another image uses the current image as its base (`FROM your-image`). The trigger doesn't run when building the image that contains `ONBUILD` — only when a child image is built.

```dockerfile
# Base image Dockerfile (team base image)
FROM python:3.11-slim
WORKDIR /app
ONBUILD COPY requirements.txt .
ONBUILD RUN pip install -r requirements.txt
ONBUILD COPY . .
```

```dockerfile
# Child image — this ONBUILD triggers run here
FROM our-team-base:latest
CMD ["python", "app.py"]
```

When a developer builds with `FROM our-team-base:latest`, Docker automatically copies requirements.txt, installs dependencies, and copies source — without the developer writing those lines in their Dockerfile.

**When useful:** Shared base images where all consumers need the same build steps. Reduces boilerplate for teams with many similar applications.

**Caution:** ONBUILD can be surprising and opaque. Someone looking at a simple 2-line Dockerfile doesn't know what the base image's ONBUILD instructions do. Use sparingly and document clearly. Modern alternatives: shared Dockerfile templates or base images with explicit `FROM` + documented conventions.

---

**Q11: A security scanner found that your Docker image runs as root. How do you fix this and what risks does it mitigate?**

Fix: create a non-root user in the Dockerfile and `USER` to switch to it before the entrypoint:

```dockerfile
FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create a system user with no home directory, no login shell
RUN useradd --system --no-create-home --shell /usr/sbin/nologin appuser

# Copy files with ownership assigned to appuser
COPY --chown=appuser:appuser . .

# Switch to non-root user — all subsequent commands run as appuser
USER appuser

CMD ["python", "app.py"]
```

Risks mitigated:
1. **Container escape privilege escalation:** If an attacker exploits a vulnerability in the app and "escapes" the container (possible with kernel exploits or misconfigurations), they escape as the non-root user on the host — severely limiting what they can do.
2. **Filesystem access:** The non-root user can only read/write files it owns or has permissions for, limiting damage from a compromised process.
3. **Host process injection:** Root inside a container can interact with certain kernel subsystems. A non-root user cannot.
4. **Principle of least privilege:** Your web app doesn't need root. Give it exactly what it needs.

Additional hardening: combine with `--cap-drop=ALL` at runtime and a seccomp profile.

---

## 📂 Navigation

**In this folder:**
| File | |
|---|---|
| [📖 Theory.md](./Theory.md) | Full explanation |
| [⚡ Cheatsheet.md](./Cheatsheet.md) | Quick reference |
| 🎯 **Interview_QA.md** | ← you are here |
| [💻 Code_Example.md](./Code_Example.md) | Working code |

⬅️ **Prev:** [04 — Images and Layers](../04_Images_and_Layers/Interview_QA.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [06 — Container Lifecycle](../06_Containers_Lifecycle/Interview_QA.md)
🏠 **[Home](../../README.md)**
