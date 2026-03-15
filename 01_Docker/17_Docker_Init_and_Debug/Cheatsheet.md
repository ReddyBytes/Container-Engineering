# Module 17 — docker init and docker debug: Cheatsheet

## docker init

```bash
# Run the interactive wizard in your project directory
docker init

# What it generates:
# - Dockerfile       (multi-stage, non-root user, cache mounts, healthcheck)
# - .dockerignore    (language-appropriate ignores)
# - compose.yaml     (working Compose configuration)
```

### Supported Runtimes

| Runtime | Signature File(s) |
|---------|------------------|
| Python | `requirements.txt`, `pyproject.toml`, `Pipfile` |
| Node.js | `package.json` |
| Go | `go.mod` |
| Rust | `Cargo.toml` |
| ASP.NET | `*.csproj`, `*.sln` |
| PHP | `composer.json` |
| Java | `pom.xml` (Maven), `build.gradle` (Gradle) |

### What docker init Includes (Automatically)

- `# syntax=docker/dockerfile:1` parser directive
- Separate dependency installation stage (layer cache optimization)
- BuildKit cache mounts for package managers
- Non-root user creation and switch
- `ARG` for parameterized image version
- `.dockerignore` with language-appropriate entries
- `compose.yaml` with working service definition

### When to Use / Not Use

| Use | Don't Use |
|-----|-----------|
| New projects | Monorepo with complex structure |
| Learning best practices | Custom base images needed |
| Simple services | Specialized build requirements (GPU, native extensions) |
| Quick containerization | Multiple interconnected services with shared configs |

---

## docker debug

```bash
# Debug a running container (even distroless/scratch — no shell required)
docker debug CONTAINER_NAME_OR_ID

# Use a specific debug image (recommended: netshoot for networking)
docker debug --image nicolaka/netshoot CONTAINER

# Use full Ubuntu with apt
docker debug --image ubuntu:22.04 CONTAINER
```

### Common Commands Inside docker debug Shell

```bash
# Show running processes
ps aux

# Browse the container's filesystem (via /proc/1/root)
ls -la /proc/1/root/

# Check listening ports and connections
ss -tulpn
netstat -tulpn     # if available

# Make HTTP requests (from inside the container's network namespace)
curl -v http://localhost:8080/health

# DNS resolution
dig api.example.com
nslookup api.example.com

# Read environment variables of PID 1
cat /proc/1/environ | tr '\0' '\n'

# List open files
ls -la /proc/1/fd/

# Tail a log file
tail -f /proc/1/root/var/log/app.log

# Network traffic capture (with netshoot)
tcpdump -i eth0 port 8080
```

### docker debug vs kubectl debug

| | `docker debug` | `kubectl debug` |
|---|---|---|
| Platform | Docker | Kubernetes |
| Mechanism | Joins container namespaces | Adds ephemeral container to pod |
| Modifies target | No | Adds ephemeral container |
| Custom image | `--image` flag | `--image` flag |

---

## containerd Image Store

### Enable in Docker Desktop (pre-4.34)

Settings → General → "Use containerd for pulling and storing images" → Apply & Restart

(Default since Docker Desktop 4.34)

### Commands After Enabling

```bash
# Pull a specific architecture locally (multi-platform aware)
docker pull --platform linux/arm64 nginx:latest
docker pull --platform linux/amd64 nginx:latest

# Inspect multi-platform manifest locally
docker buildx imagetools inspect nginx:latest

# List images with platform info
docker image ls --format "table {{.Repository}}\t{{.Tag}}\t{{.Platform}}"

# Store multi-platform build result locally (not possible with old store)
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --load \
  -t myapp:latest .
```

### containerd Image Store vs Old Store

| | Old Docker Store | containerd Store |
|---|---|---|
| Multi-platform local storage | No (pulls one arch) | Yes (stores manifest list) |
| OCI compliance | Partial | Full |
| Kubernetes compatible format | No | Yes |
| Default since | — | Docker Desktop 4.34 |

---

## Docker Extensions

```bash
# List installed extensions
docker extension ls

# Install an extension
docker extension install PUBLISHER/EXTENSION:TAG

# Common extensions:
docker extension install portainer/portainer-docker-extension:latest
docker extension install docker/disk-usage-extension

# Update an extension
docker extension update PUBLISHER/EXTENSION

# Remove an extension
docker extension rm PUBLISHER/EXTENSION
```

### Notable Extensions

| Extension | Use Case |
|-----------|---------|
| Portainer | Full container management GUI |
| Disk Usage | Visualize Docker's disk consumption |
| Logs Explorer | Search logs across containers |
| Snyk | Security scanning in Desktop |
| Grafana k6 | Load testing |

---

## Quality Checklist: docker init Output vs Stack Overflow Dockerfile

| Practice | Stack Overflow (typical) | docker init Output |
|----------|--------------------------|-------------------|
| `# syntax=docker/dockerfile:1` | Never | Always |
| Non-root user | Rarely | Always |
| Cache mounts | Never | Always |
| Parameterized base image version | Rarely | Always |
| `.dockerignore` | Often missing | Generated |
| Multi-stage build | Sometimes | Always (for supported runtimes) |
| `HEALTHCHECK` | Rarely | Included |
| Comments explaining choices | Never | Included |

---

## 📂 Navigation

| | |
|---|---|
| **Previous** | [16_BuildKit_and_Docker_Scout](../16_BuildKit_and_Docker_Scout/Cheatsheet.md) |
| **Next** | *(End of Docker Module)* |
| **Theory** | [Theory.md](./Theory.md) |
| **Interview Q&A** | [Interview_QA.md](./Interview_QA.md) |
| **Code Examples** | [Code_Example.md](./Code_Example.md) |
| **Module Index** | [01_Docker README](../README.md) |
