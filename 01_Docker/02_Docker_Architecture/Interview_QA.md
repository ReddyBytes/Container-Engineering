# Docker Architecture — Interview Q&A

## Beginner

**Q1: What is the Docker daemon (`dockerd`) and what does it do?**

`dockerd` is a long-running background service — the "brain" of Docker. It exposes the Docker REST API, which the `docker` CLI uses to send commands. When you run `docker build`, `docker run`, or `docker network create`, you're sending API requests to `dockerd`.

`dockerd` handles Docker-specific features: building images from Dockerfiles, managing Docker networks, managing named volumes, and handling image tagging and pushing. For the actual work of starting containers, it delegates to `containerd`.

---

**Q2: What is the relationship between the `docker` CLI and the Docker daemon?**

The `docker` CLI is a client — it contains no logic for running containers. It takes your commands, translates them into HTTP API calls (using the Docker REST API), and sends them to `dockerd` over a Unix socket at `/var/run/docker.sock`.

You can verify this by pointing the CLI at a remote Docker daemon:
```bash
docker -H tcp://remote-host:2376 run nginx
```
The CLI running on your laptop talks to a daemon on a different machine. The CLI is just the control plane; the daemon is where work happens.

---

**Q3: What is Docker Hub and when would you use a private registry instead?**

Docker Hub is the public registry operated by Docker Inc. It hosts official images (nginx, ubuntu, python, etc.) and community/user images. It's the default registry when you pull an image without specifying a hostname.

You use a private registry when:
- You're storing proprietary application images you don't want public
- You need images co-located in your cloud region for faster pulls (AWS ECR in us-east-1 for EC2s in us-east-1)
- You need access controls and audit logging beyond what Docker Hub offers
- You're in an air-gapped environment without internet access

Common private registries: AWS ECR, GCP Artifact Registry, GitHub Container Registry (ghcr.io), Harbor (self-hosted).

---

**Q4: What is `/var/run/docker.sock`?**

It's a Unix domain socket — a file-based inter-process communication mechanism. The Docker daemon listens on this socket for API requests. When you run `docker run nginx`, the CLI opens a connection to this socket and sends a JSON POST request.

It's a file, so standard Unix file permissions apply. By default, only root and members of the `docker` group can access it. This is why you need to run `sudo docker ...` if you're not in the docker group.

---

## Intermediate

**Q5: Explain the role of `containerd-shim`. Why does it exist?**

`containerd-shim` (or just "shim") is a small, per-container process that sits between `containerd` and the actual container process.

When a container is started:
1. containerd spawns a shim
2. The shim calls `runc` to create the container
3. `runc` starts the container process and exits
4. The shim remains running as the container's parent process

The shim's purposes:
- **Daemon independence:** If `containerd` (or `dockerd`) crashes or is upgraded, the shim keeps running, keeping the container alive. This allows zero-downtime daemon upgrades.
- **I/O relay:** The shim holds the container's stdin/stdout/stderr pipes, so `docker logs` and `docker attach` can reconnect at any time.
- **Exit reporting:** When the container process exits, the shim captures the exit code and reports it back to containerd.

Without the shim, restarting the Docker daemon would kill all running containers.

---

**Q6: How does OverlayFS enable Docker image layers?**

OverlayFS is a Union filesystem — it merges multiple directories (called layers) into a single unified filesystem view.

Docker uses OverlayFS like this:
- Each image layer is stored as a directory on the host (the **lowerdir** — read-only)
- When you start a container, Docker creates a new empty writable directory (the **upperdir**)
- OverlayFS presents the container with a **merged** view: all the read-only layers merged together, with the writable layer on top

When the container writes to a file that exists in a lower read-only layer, OverlayFS performs **copy-on-write**: it copies the file from the lower layer to the upper writable layer, then allows the write. The lower layer is never modified.

This means:
- 100 containers based on the same image share those read-only layers — only one copy on disk
- Each container has its own isolated writable layer — changes don't affect each other or the image
- Deleting a container removes only its writable layer; the image layers remain

---

**Q7: What happens in Docker architecture when Kubernetes runs containers?**

Kubernetes does not use `dockerd` at all (Docker was deprecated as the Kubernetes runtime in v1.20 and removed in v1.24). Instead, Kubernetes uses the **Container Runtime Interface (CRI)** — a standard gRPC API that any compatible runtime can implement.

The standard Kubernetes setup today:
- **kubelet** (the per-node Kubernetes agent) calls containerd via CRI
- containerd manages the container lifecycle, image pulling, and snapshots
- containerd calls runc (or another OCI runtime like gVisor's `runsc`) to start containers

So in a Kubernetes cluster, the stack is: `kubelet → containerd → runc → container`. Docker and `dockerd` are not involved. The `docker` CLI won't show Kubernetes-managed containers — you'd use `crictl` or `ctr` to inspect them at the containerd level.

---

**Q8: A developer needs to run Docker commands inside a CI container (Docker-in-Docker). What are the two approaches and their trade-offs?**

**Approach 1: Bind-mount the Docker socket**
```bash
docker run -v /var/run/docker.sock:/var/run/docker.sock my-ci-image
```
The CI container talks to the *host's* Docker daemon. Simple, fast, and images built are available on the host.

Trade-off: The CI container has full access to the host's Docker daemon — it can see/stop all containers on the host, including other CI jobs. It's a significant security risk in shared environments. A compromised build script could do anything.

**Approach 2: Docker-in-Docker (dind)**
Run a privileged `docker:dind` sidecar container. The CI container talks to that sidecar's Docker daemon instead of the host's.

```yaml
# In a CI environment like GitLab:
services:
  - docker:dind
variables:
  DOCKER_HOST: tcp://docker:2376
```

Trade-off: Requires `--privileged` on the dind container, which grants extensive kernel capabilities. Slower due to nested filesystems. Images built are isolated in the dind container and must be explicitly pushed to survive.

**Better modern approach:** Use rootless Docker or kaniko/buildkit for image builds that don't require a daemon socket at all.

---

## Advanced

**Q9: Explain rootless Docker. How does it work and what are its limitations?**

Rootless Docker allows `dockerd` to run as a non-root user. This dramatically improves security because:
- Even if a container escapes, it escapes to a non-root user on the host
- The Docker daemon itself doesn't have root privileges

How it works:
- Uses **user namespaces** to map the container's root user (UID 0) to an unprivileged sub-UID on the host (e.g., UID 100000)
- Uses **`slirp4netns`** or **`pasta`** instead of iptables/bridge networking (which require root)
- The daemon socket is in a user-specific location (`$XDG_RUNTIME_DIR/docker.sock`)

Limitations:
- Some features require kernel capabilities that non-root processes don't have (e.g., overlayfs without `fuse-overlayfs`, some network modes)
- Port binding below 1024 requires additional configuration (`net.ipv4.ip_unprivileged_port_start`)
- Performance can be slightly lower due to `fuse-overlayfs` vs kernel OverlayFS
- Requires kernel ≥ 5.11 for full feature support and newuidmap/newgidmap binaries

Setup:
```bash
dockerd-rootless-setuptool.sh install
export DOCKER_HOST=unix://$XDG_RUNTIME_DIR/docker.sock
```

---

**Q10: Walk through exactly what happens at the process level when `docker stop` is called.**

`docker stop <container>` sends a **SIGTERM** signal to PID 1 of the container. This is the graceful shutdown signal — it gives the application a chance to finish in-flight requests, close connections, and clean up.

After a grace period (default 10 seconds, configurable with `--time`), if the process hasn't exited, Docker sends **SIGKILL**, which immediately terminates the process without cleanup.

The sequence:
1. `docker stop` → CLI sends `POST /containers/<id>/stop` to dockerd
2. dockerd → containerd: send SIGTERM to container PID 1
3. containerd-shim delivers SIGTERM to the container process
4. Application catches SIGTERM, performs graceful shutdown (if written to do so)
5. If process exits within timeout → success
6. If process still running after timeout → containerd-shim sends SIGKILL → forced termination
7. containerd reports container as "stopped"
8. containerd-shim collects exit code, reports to containerd, then exits

Important: if your container's PID 1 is a shell script (`CMD /start.sh`), shells typically do NOT forward signals to child processes. This means SIGTERM to the shell won't reach your application. The fix is to use `exec` in your entrypoint script: `exec myapp` — this replaces the shell process with the app process, making your app PID 1.

---

**Q11: How does the Docker content trust / image signature verification work?**

Docker Content Trust (DCT) uses **Notary** — a framework for cryptographic signing and verification of content. When enabled (`DOCKER_CONTENT_TRUST=1`), Docker only pulls/runs images that have been cryptographically signed.

How it works:
1. When you push an image with DCT enabled, Docker generates a signing keypair
2. The image manifest is signed with your private key
3. The signature is stored in a Notary server (separate from the registry)
4. When pulling, Docker fetches the signature from Notary and verifies it against the publisher's public key
5. If signature doesn't match or doesn't exist, the pull is refused

Limitations of DCT:
- Uses its own Notary infrastructure, separate from registries
- Industry has largely moved toward **OCI cosign** (from Sigstore project) for image signing
- cosign signs and stores signatures as OCI artifacts directly in the registry — no separate server needed

```bash
# Enable Docker Content Trust
export DOCKER_CONTENT_TRUST=1
docker pull nginx   # will fail if not signed

# Modern approach: cosign
cosign sign --key cosign.key myregistry.example.com/myapp:v1
cosign verify --key cosign.pub myregistry.example.com/myapp:v1
```

---

## 📂 Navigation

**In this folder:**
| File | |
|---|---|
| [📖 Theory.md](./Theory.md) | Full explanation |
| [⚡ Cheatsheet.md](./Cheatsheet.md) | Quick reference |
| 🎯 **Interview_QA.md** | ← you are here |

⬅️ **Prev:** [01 — Virtualization and Containers](../01_Virtualization_and_Containers/Interview_QA.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [03 — Installation and Setup](../03_Installation_and_Setup/Interview_QA.md)
🏠 **[Home](../../README.md)**
