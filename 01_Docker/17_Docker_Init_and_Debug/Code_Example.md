# Module 17 — docker init and docker debug: Code Examples

## Example 1: docker init Output for a Python Project

This shows the exact files that `docker init` generates for a Python project running FastAPI with uvicorn.

**Prompt sequence:**
```
$ docker init

? What application platform does your project use? Python
? What version of Python do you want to use? 3.12.3
? What port does your server listen on? 8000
? What is the command to run your app? uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Generated `Dockerfile`:**
```dockerfile
# syntax=docker/dockerfile:1

# Comments are provided throughout this file to help you get started.
# If you need more help, visit the Dockerfile reference guide at
# https://docs.docker.com/go/dockerfile-reference/

# Want to help us make this template better? Share your feedback here:
# https://forms.gle/sSLguTkxkjdeuAh2A

ARG PYTHON_VERSION=3.12.3
FROM python:${PYTHON_VERSION}-slim as base

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Create a non-privileged user that the app will run under.
# See https://docs.docker.com/go/dockerfile-user-best-practices/
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

# Download dependencies as a separate step to take advantage of Docker's caching.
# Leverage a cache mount to /root/.cache/pip to speed up subsequent builds.
# Leverage a bind mount to requirements.txt so we don't have to COPY it into
# the container.
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python -m pip install -r requirements.txt

# Switch to the non-privileged user to run the application.
USER appuser

# Copy the source code into the container.
COPY . .

# Expose the port that the application listens on.
EXPOSE 8000

# Run the application.
CMD uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Generated `.dockerignore`:**
```
# Include any files or directories that you don't want to be copied to your
# container here (e.g., local build artifacts, temporary files, etc.).
#
# For more help, visit the .dockerignore file reference guide at
# https://docs.docker.com/go/build-context-dockerignore/

**/.DS_Store
**/__pycache__
**/*.pyc
**/*.pyo
**/*.pyd
**/.Python
**/.git
**/.gitignore
**/.gitattributes
**/.hg
**/.svn
**/.tox
**/.venv
**/venv
**/.env
**/.cache
**/*.egg-info
**/dist
**/build
**/htmlcov
**/.pytest_cache
**/node_modules
Dockerfile
.dockerignore
compose.yaml
```

**Generated `compose.yaml`:**
```yaml
# Comments are provided throughout this file to help you get started.
# If you need more help, visit the Docker Compose reference guide at
# https://docs.docker.com/go/compose-spec-reference/

# Here the instructions define your application as a service called "server".
# This service is built from the Dockerfile in the current directory.
# You can add other services your application may depend on here, such as a
# database or a cache. For examples, see the Awesome Compose repository:
# https://github.com/docker/awesome-compose

services:
  server:
    build:
      context: .
    ports:
      - 8000:8000

# The commented out section below is an example of how to define a PostgreSQL
# database that your application can use. `depends_on` tells Docker Compose to
# start the database before your application. The `db-data` volume persists the
# database data between container restarts. The `db-password` secret is used
# to set the database password. You must create `db/password.txt` and add
# a password of your choosing to it before running `docker compose up`.
#     depends_on:
#       db:
#         condition: service_healthy
#   db:
#     image: postgres
#     restart: always
#     user: postgres
#     secrets:
#       - db-password
#     volumes:
#       - db-data:/var/lib/postgresql/data
#     environment:
#       - POSTGRES_DB=example
#       - POSTGRES_PASSWORD_FILE=/run/secrets/db-password
#     expose:
#       - 5432
#     healthcheck:
#       test: [ "CMD", "pg_isready" ]
#       interval: 10s
#       timeout: 5s
#       retries: 5
# volumes:
#   db-data:
# secrets:
#   db-password:
#     file: db/password.txt
```

Start the project immediately:
```bash
docker compose up --build
```

---

## Example 2: docker debug on a Distroless Container (Step by Step)

This example walks through debugging a crashed distroless Go application.

**Setup: the distroless app**

```dockerfile
# syntax=docker/dockerfile:1
FROM golang:1.22-alpine AS build
WORKDIR /app
COPY . .
RUN go build -o /server ./cmd/server

# Final image: distroless — no shell, no tools, just the binary
FROM gcr.io/distroless/static:nonroot
COPY --from=build /server /server
EXPOSE 8080
ENTRYPOINT ["/server"]
```

```bash
# Build and start the container
docker build -t myapp:debug-demo .
docker run -d --name myapp-demo -p 8080:8080 myapp:debug-demo
```

**Step 1: Confirm that exec fails**

```bash
$ docker exec -it myapp-demo sh
OCI runtime exec failed: exec failed: unable to start container process:
exec: "sh": executable file not found in $PATH: unknown

$ docker exec -it myapp-demo bash
OCI runtime exec failed: exec failed: unable to start container process:
exec: "bash": executable file not found in $PATH: unknown
```

No shell. No tools. Standard debugging approach is completely blocked.

**Step 2: Use docker debug (default busybox toolbox)**

```bash
$ docker debug myapp-demo

# You immediately get a shell
# The shell is from the busybox debug image, not your container
root@myapp-demo:/#
```

**Step 3: Inspect the running process**

```bash
root@myapp-demo:/# ps aux
PID   USER     TIME  COMMAND
    1 nonroot   0:00 /server        # ← your Go binary running as PID 1
   12 root      0:00 /bin/sh        # ← the debug shell (this is us)
```

**Step 4: Browse the container's filesystem**

```bash
root@myapp-demo:/# ls /proc/1/root/
server  etc  tmp  usr  var

root@myapp-demo:/# ls /proc/1/root/etc/
group  passwd  ssl

# Is there a config file?
root@myapp-demo:/# ls /proc/1/root/etc/myapp/ 2>&1
ls: /proc/1/root/etc/myapp/: No such file or directory
```

**Step 5: Check network**

```bash
root@myapp-demo:/# ss -tulpn
Netid  State   Recv-Q  Send-Q  Local Address:Port
tcp    LISTEN  0       128     0.0.0.0:8080

# Make a request to the app from inside its network namespace
root@myapp-demo:/# wget -qO- http://localhost:8080/health
{"status":"ok","version":"1.2.3"}
```

**Step 6: Check environment variables and config**

```bash
# See what environment variables PID 1 was started with
root@myapp-demo:/# cat /proc/1/environ | tr '\0' '\n'
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin
HOME=/home/nonroot
DB_URL=postgres://user:password@db:5432/myapp
LOG_LEVEL=info
```

**Step 7: Use netshoot for deeper network debugging**

```bash
# Exit the default shell
root@myapp-demo:/# exit

# Re-attach with netshoot for advanced network tools
$ docker debug --image nicolaka/netshoot myapp-demo

myapp-demo# tcpdump -i eth0 port 8080
# Shows all HTTP traffic hitting the container in real time

myapp-demo# dig db.internal
# Check if DNS resolves for the database hostname

myapp-demo# curl -v http://db:5432
# Test TCP connectivity to the database

myapp-demo# netstat -tulpn
# Full network connection listing
```

**Cleanup:**
```bash
# Exit debug shell
myapp-demo# exit

# The container is completely unchanged
docker ps
# myapp-demo is still running, exactly as before
```

---

## Example 3: Enabling containerd Image Store and Working with Multi-Platform Images

**Step 1: Enable the containerd image store (Docker Desktop pre-4.34)**

Via Docker Desktop GUI:
1. Click the gear icon (Settings)
2. Go to General
3. Check "Use containerd for pulling and storing images"
4. Click "Apply & Restart"

To verify it's enabled:
```bash
docker info | grep -i "storage driver"
# Output: Storage Driver: overlayfs  (containerd store)
# vs old:  Storage Driver: overlay2  (old store)
```

**Step 2: Pull multi-platform images locally**

```bash
# With old image store: this only pulled linux/amd64 on an amd64 machine
# With containerd store: you can pull any platform explicitly

# Pull the arm64 variant on an amd64 machine
docker pull --platform linux/arm64 nginx:1.25

# Pull the amd64 variant
docker pull --platform linux/amd64 nginx:1.25

# List images — now both are stored locally
docker image ls
# REPOSITORY   TAG     IMAGE ID       CREATED       SIZE     PLATFORM
# nginx        1.25    abc123...      2 weeks ago   43MB     linux/arm64
# nginx        1.25    def456...      2 weeks ago   41MB     linux/amd64
```

**Step 3: Inspect a multi-platform manifest**

```bash
# Inspect manifest list without pulling
docker buildx imagetools inspect nginx:1.25

# Output shows all available platforms:
# Name:      docker.io/library/nginx:1.25
# MediaType: application/vnd.oci.image.index.v1+json
#
# Manifests:
#   Name:      docker.io/library/nginx:1.25@sha256:aaa...
#   Platform:  linux/amd64
#
#   Name:      docker.io/library/nginx:1.25@sha256:bbb...
#   Platform:  linux/arm64
#
#   Name:      docker.io/library/nginx:1.25@sha256:ccc...
#   Platform:  linux/arm64/v8
```

**Step 4: Build multi-platform and load locally (containerd store only)**

With the old store, `docker buildx build --platform linux/amd64,linux/arm64` required `--push` because the local store couldn't hold multi-platform results.

With the containerd store, `--load` works for multi-platform:

```bash
# Build multi-platform and store locally
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --load \
  -t myapp:latest .

# Verify both platforms are stored
docker image ls --format "table {{.Repository}}\t{{.Tag}}\t{{.Platform}}"
# REPOSITORY   TAG       PLATFORM
# myapp        latest    linux/amd64
# myapp        latest    linux/arm64

# Run the arm64 variant on an amd64 machine (via emulation)
docker run --platform linux/arm64 --rm myapp:latest uname -m
# aarch64
```

**Step 5: Verify OCI compliance**

```bash
# Export image in OCI format (works with containerd store)
docker save myapp:latest | tar -x -C ./image-export/

# The structure is OCI-compliant:
ls ./image-export/
# blobs/
# index.json       ← OCI image index
# oci-layout       ← OCI layout marker

cat ./image-export/oci-layout
# {"imageLayoutVersion":"1.0.0"}
```

---

## 📂 Navigation

| | |
|---|---|
| **Previous** | [16_BuildKit_and_Docker_Scout](../16_BuildKit_and_Docker_Scout/Code_Example.md) |
| **Next** | *(End of Docker Module)* |
| **Theory** | [Theory.md](./Theory.md) |
| **Cheatsheet** | [Cheatsheet.md](./Cheatsheet.md) |
| **Interview Q&A** | [Interview_QA.md](./Interview_QA.md) |
| **Module Index** | [01_Docker README](../README.md) |
