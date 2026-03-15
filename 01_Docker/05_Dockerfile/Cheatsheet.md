# Dockerfile — Cheatsheet

## Instruction Quick Reference

| Instruction | Purpose | Persists to runtime? | Creates layer? |
|---|---|---|---|
| `FROM` | Base image | — (defines base) | No (uses existing) |
| `RUN` | Execute build command | No | Yes |
| `COPY` | Copy files from context | Yes | Yes |
| `ADD` | Copy files / extract tar / fetch URL | Yes | Yes |
| `WORKDIR` | Set working directory | Yes | No |
| `ENV` | Set environment variable | Yes | No |
| `ARG` | Build-time variable | No | No |
| `CMD` | Default container command | Yes | No |
| `ENTRYPOINT` | Fixed container executable | Yes | No |
| `EXPOSE` | Document port (metadata only) | Yes (label) | No |
| `USER` | Set running user | Yes | No |
| `LABEL` | Attach key-value metadata | Yes | No |
| `VOLUME` | Declare mountpoint | Yes | No |
| `HEALTHCHECK` | Define health test | Yes | No |
| `ONBUILD` | Trigger for downstream builds | — | No |
| `STOPSIGNAL` | Signal sent to stop container | Yes | No |
| `SHELL` | Override default shell | No | No |

---

## All Instructions with Syntax

```dockerfile
# Comment
FROM image:tag
FROM image:tag AS stage_name          # multi-stage build stage

ARG BUILD_VAR=default_value           # before FROM: parameterize base image
FROM python:${PYTHON_VERSION}-slim    # use ARG in FROM

WORKDIR /path/to/dir                  # creates dir if needed, cd into it

# Install system packages (combine into one RUN to reduce layers)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        git && \
    rm -rf /var/lib/apt/lists/*

# Copy files
COPY src dest                         # copy from build context to image
COPY --chown=user:group src dest      # copy with ownership
COPY --from=stage_name /path /dest   # copy from another build stage

ADD src dest                          # like COPY + auto-extract tar + fetch URLs
ADD archive.tar.gz /opt/             # extracts tar into /opt/

ENV KEY=value                         # set env variable
ENV KEY1=val1 \                       # set multiple
    KEY2=val2

ARG BUILD_VAR                         # declare build arg (after FROM: stage-scoped)
ARG BUILD_VAR=default

LABEL key="value"                     # metadata
LABEL org.opencontainers.image.version="1.0.0"

EXPOSE 8080                           # document port (metadata only)
EXPOSE 8080/tcp
EXPOSE 53/udp

USER username                         # switch user
USER 1001                             # switch by UID
USER 1001:1001                        # switch by UID:GID

VOLUME ["/data"]                      # declare mountpoint
VOLUME /data /logs                    # multiple mountpoints

# CMD — default command, fully replaceable
CMD ["executable", "arg1", "arg2"]   # exec form (preferred)
CMD executable arg1 arg2              # shell form (runs in /bin/sh -c)
CMD ["arg1", "arg2"]                  # default args when ENTRYPOINT is set

# ENTRYPOINT — fixed executable, args are appended
ENTRYPOINT ["executable"]             # exec form (preferred)
ENTRYPOINT ["./docker-entrypoint.sh"] # common: entrypoint script

# HEALTHCHECK
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1
HEALTHCHECK NONE                      # disable inherited HEALTHCHECK

STOPSIGNAL SIGTERM                    # signal to stop container (default: SIGTERM)
SHELL ["/bin/bash", "-c"]            # override default shell for RUN instructions

# Multi-stage: copy from builder
FROM golang:1.22 AS builder
RUN go build -o /app .
FROM gcr.io/distroless/base
COPY --from=builder /app /app
ENTRYPOINT ["/app"]
```

---

## CMD vs ENTRYPOINT Decision Guide

| Scenario | Use |
|---|---|
| Container runs one specific program, no override needed | `ENTRYPOINT ["prog"]` |
| Container should behave like a CLI tool (`docker run mytool --help`) | `ENTRYPOINT ["mytool"]` + `CMD ["--help"]` |
| Container command should be fully replaceable by user | `CMD ["default", "command"]` |
| Initialization script needed before main process | `ENTRYPOINT ["./entrypoint.sh"]` + `CMD ["app"]` |
| Base image for other images | `CMD ["bash"]` (easily overridden) |

**Signal handling rule:** always use exec form `["cmd"]` for ENTRYPOINT/CMD so your process is PID 1 and receives SIGTERM directly.

---

## Layer Optimization Patterns

```dockerfile
# BAD: separate RUN for install and clean — clean is in a different layer
RUN apt-get update && apt-get install -y curl
RUN rm -rf /var/lib/apt/lists/*         # doesn't help! curl still in lower layer

# GOOD: install and clean in same RUN — deleted files never stored
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# BAD: copy all source before installing deps
COPY . .
RUN pip install -r requirements.txt    # rebuilds on every code change

# GOOD: copy deps manifest first
COPY requirements.txt .
RUN pip install -r requirements.txt    # cached until requirements.txt changes
COPY . .                               # code changes only affect this layer
```

---

## .dockerignore Essentials

```
# Version control
.git
.gitignore

# Dependencies (installed inside container, no need to copy)
node_modules
vendor/
__pycache__
*.pyc

# Secrets and config (NEVER include in images)
.env
.env.*
*.pem
*.key
secrets/

# Build artifacts
dist/
build/
target/
*.log

# Dev tooling
.vscode/
.idea/
*.swp
.DS_Store

# Docker files themselves
Dockerfile*
docker-compose*.yml
.dockerignore

# Tests (optional — remove if you run tests in multi-stage build)
tests/
test/
spec/
```

---

## Common Build Commands

```bash
# Basic build
docker build -t myapp:1.0 .

# Build with custom Dockerfile location
docker build -f path/to/Dockerfile -t myapp:1.0 .

# Build with custom context directory
docker build -t myapp:1.0 /path/to/context

# Build with build args
docker build --build-arg VERSION=1.2.3 --build-arg ENV=prod -t myapp:1.0 .

# Build without cache (force full rebuild)
docker build --no-cache -t myapp:1.0 .

# Build a specific stage (multi-stage)
docker build --target builder -t myapp-builder .

# Build with verbose output (see all steps, no progress spinner)
docker build --progress=plain -t myapp:1.0 .

# Multi-platform build (requires buildx)
docker buildx build --platform linux/amd64,linux/arm64 -t myapp:1.0 --push .
```

---

## 📂 Navigation

**In this folder:**
| File | |
|---|---|
| [📖 Theory.md](./Theory.md) | Full explanation |
| ⚡ **Cheatsheet.md** | ← you are here |
| [🎯 Interview_QA.md](./Interview_QA.md) | Interview prep |
| [💻 Code_Example.md](./Code_Example.md) | Working code |

⬅️ **Prev:** [04 — Images and Layers](../04_Images_and_Layers/Cheatsheet.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [06 — Container Lifecycle](../06_Containers_Lifecycle/Cheatsheet.md)
🏠 **[Home](../../README.md)**
