# Docker Practice Questions — 100 Questions from Basics to Mastery

> Test yourself across the full Docker curriculum. Answers hidden until clicked.

---

## How to Use This File

1. **Read the question** — attempt your answer before opening the hint
2. **Use the framework** — run through the 5-step thinking process first
3. **Check your answer** — click "Show Answer" only after you've tried

---

## How to Think: 5-Step Framework

1. **Restate** — what is this question actually asking?
2. **Identify the concept** — which Docker concept is being tested?
3. **Recall the rule** — what is the exact behaviour or rule?
4. **Apply to the case** — trace through the scenario step by step
5. **Sanity check** — does the result make sense? What edge cases exist?

---

## Progress Tracker

- [ ] **Tier 1 — Basics** (Q1–Q33): Fundamentals and core commands
- [ ] **Tier 2 — Intermediate** (Q34–Q66): Advanced features and real patterns
- [ ] **Tier 3 — Advanced** (Q67–Q75): Deep internals and edge cases
- [ ] **Tier 4 — Interview / Scenario** (Q76–Q90): Explain-it, compare-it, real-world problems
- [ ] **Tier 5 — Critical Thinking** (Q91–Q100): Predict output, debug, design decisions

---

## Question Type Legend

| Tag | Meaning |
|---|---|
| `[Normal]` | Recall + apply |
| `[Thinking]` | Requires reasoning about internals |
| `[Logical]` | Predict output or trace execution |
| `[Critical]` | Tricky gotcha or edge case |
| `[Interview]` | Explain or compare in interview style |
| `[Debug]` | Find and fix the broken code/config |
| `[Design]` | Architecture or approach decision |

---

## 🟢 Tier 1 — Basics

---

### Q1 · [Normal] · `containers-vs-vms`

> **What is the difference between a container and a virtual machine? What makes containers lightweight?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A VM virtualizes hardware and runs a full OS (kernel + userspace) on top of a hypervisor. A container virtualizes the OS userspace only — it shares the host kernel and runs as isolated processes.

**How to think through this:**
1. A VM needs a hypervisor (VMware, KVM, Hyper-V) to emulate hardware. Each VM boots its own kernel — that's why they take seconds to minutes to start and consume gigabytes of RAM.
2. A container uses Linux kernel features (namespaces for isolation, cgroups for resource limits) to carve out an isolated process environment. No second kernel, no hardware emulation.
3. Because containers share the host kernel and only bundle the application + its userspace dependencies, they start in milliseconds and are measured in megabytes.

**Key takeaway:** Containers are lightweight because they share the host OS kernel — they are isolated processes, not isolated machines.

</details>

📖 **Theory:** [containers-vs-vms](./01_Virtualization_and_Containers/Theory.md#mistake-1-treating-containers-like-vms)


---

### Q2 · [Normal] · `docker-architecture`

> **Describe Docker's architecture: daemon, client, registry. What is the Docker socket?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Docker uses a client-server architecture. The Docker client sends commands to the Docker daemon, which does the actual work. Images are stored and retrieved from a registry.

**How to think through this:**
1. **Docker client** (`docker` CLI): The tool you type commands into. It translates your commands into REST API calls.
2. **Docker daemon** (`dockerd`): A long-running background process that manages images, containers, networks, and volumes. It listens for API requests.
3. **Docker registry**: A storage and distribution system for Docker images. Docker Hub is the default public registry.
4. **Docker socket** (`/var/run/docker.sock`): A Unix domain socket that the daemon listens on locally. When the CLI runs on the same machine as the daemon, it communicates over this socket. Mounting this socket into a container gives that container control over the host's Docker daemon — a significant security concern.

**Key takeaway:** The Docker socket is the IPC channel between the CLI and daemon — whoever has access to it has root-equivalent power over Docker.

</details>

📖 **Theory:** [docker-architecture](./02_Docker_Architecture/Theory.md#docker-architecture)


---

### Q3 · [Normal] · `docker-daemon`

> **What is the Docker daemon (dockerd)? What does it manage? How does the Docker CLI communicate with it?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
`dockerd` is the persistent background process that is the engine of Docker. The CLI communicates with it via a REST API over a Unix socket (or TCP in remote setups).

**How to think through this:**
1. `dockerd` manages the full lifecycle of: images (pull, build, delete), containers (create, run, stop, remove), networks (create, connect), and volumes (create, mount).
2. It also communicates with container runtimes — by default, it delegates low-level container execution to `containerd`, which in turn uses `runc`.
3. The CLI (`docker run ...`) serializes your command into an HTTP request and sends it to the daemon's REST API endpoint, typically at `unix:///var/run/docker.sock`. The daemon executes the request and returns a response.
4. You can configure `dockerd` to also listen on a TCP socket (`tcp://0.0.0.0:2376`) for remote management, secured with TLS.

**Key takeaway:** `dockerd` is the brains — the CLI is just a thin HTTP client that translates your commands into API calls.

</details>

📖 **Theory:** [docker-daemon](./02_Docker_Architecture/Theory.md#2-docker-daemon-dockerd)


---

### Q4 · [Normal] · `docker-install`

> **What does `docker info` show? What is the difference between Docker CE and Docker EE?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
`docker info` prints a full system-level summary of the Docker installation and its current state. Docker CE is the free community edition; Docker EE (now Docker Business) is the paid enterprise product with added support and security features.

**How to think through this:**
1. `docker info` shows: daemon version, number of running/stopped/paused containers, number of images, storage driver, logging driver, kernel version, OS, total memory, CPU count, Docker root directory, and registry configuration.
2. **Docker CE (Community Edition):** Free, open source, supported by the community. Suitable for developers and smaller deployments.
3. **Docker EE / Docker Business:** Paid product with enterprise SLAs, certified infrastructure support, role-based access control, image signing, and vulnerability scanning via Docker Scout.
4. The underlying engine is largely the same — EE adds management tooling (formerly Universal Control Plane + Docker Trusted Registry) and commercial support.

**Key takeaway:** `docker info` is your first diagnostic command — it tells you everything about the daemon's state and configuration at a glance.

</details>

📖 **Theory:** [docker-install](./03_Installation_and_Setup/Theory.md#installation-macos-docker-desktop)


---

### Q5 · [Thinking] · `docker-hello-world`

> **What happens when you run `docker run hello-world`? Trace each step.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Docker checks for the image locally, pulls it from Docker Hub if absent, creates a container, runs it, and the container prints a message then exits.

**How to think through this:**
1. **CLI → daemon:** `docker run hello-world` sends a "create and run container" request to `dockerd`.
2. **Image check:** The daemon looks in its local image cache for `hello-world:latest`. It is not there on a fresh install.
3. **Pull:** The daemon contacts Docker Hub (registry), authenticates (anonymous for public images), and pulls the image layers. You see `Unable to find image 'hello-world:latest' locally` followed by pull progress.
4. **Container creation:** The daemon calls `containerd` to create a new container from the image layers.
5. **Execution:** `runc` (or the configured OCI runtime) starts the container process. The `hello-world` binary writes its message to stdout.
6. **Exit:** The process exits with code 0. The container enters the `stopped` state. The output is streamed back to your terminal.

**Key takeaway:** `docker run` is six steps under the hood — check cache, pull, create, start, execute, exit — and the entire stack from CLI to OCI runtime is involved.

</details>

📖 **Theory:** [docker-hello-world](./03_Installation_and_Setup/Theory.md#your-first-container-docker-run-hello-world-explained)


---

### Q6 · [Normal] · `images-layers`

> **What is a Docker image? What are layers? How are layers shared between images?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A Docker image is a read-only, ordered stack of filesystem layers. Each layer represents a set of file changes. Layers with the same content hash are stored once and shared across all images that reference them.

**How to think through this:**
1. Think of an image like a stack of transparent acetate sheets. Each sheet adds or modifies files. The final view is the union of all sheets from bottom to top.
2. Each Dockerfile instruction that modifies the filesystem (`RUN`, `COPY`, `ADD`) creates a new layer. `FROM`, `ENV`, `EXPOSE`, `CMD` create metadata layers with no filesystem delta.
3. Layers are content-addressed by SHA256 hash. If two images both start `FROM ubuntu:22.04`, they share the exact same set of Ubuntu base layers on disk — not copies.
4. The storage driver (overlay2 by default) presents this stack as a single merged filesystem to the running container using a union mount.
5. When a container runs, a thin writable layer is added on top of the read-only image layers. This is why you can run many containers from one image without duplicating data.

**Key takeaway:** Layer sharing is what makes Docker storage efficient — common base layers are stored once and reused by every image that builds on them.

</details>

📖 **Theory:** [images-layers](./04_Images_and_Layers/Theory.md#images-and-layers)


---

### Q7 · [Normal] · `image-commands`

> **What do `docker images`, `docker pull`, `docker rmi`, and `docker image prune` do?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
These are the four core image management commands: list, fetch, delete, and clean up dangling images.

**How to think through this:**
1. `docker images` (alias: `docker image ls`): Lists all images in the local cache. Shows repository, tag, image ID, creation date, and size.
2. `docker pull <image>`: Downloads an image (and its layers) from a registry to the local cache. Does not create a container.
3. `docker rmi <image>` (alias: `docker image rm`): Removes an image from the local cache. Fails if a container (running or stopped) is using it. Use `-f` to force.
4. `docker image prune`: Removes all **dangling** images — images with no tag and no container referencing them, typically leftover intermediate build layers. Add `-a` to remove all unused images (tagged but not used by any container).

**Key takeaway:** `prune` is your disk-reclaim tool — `prune` alone removes dangling layers, `prune -a` is the nuclear option that removes everything not actively used.

</details>

📖 **Theory:** [image-commands](./04_Images_and_Layers/Theory.md#essential-image-commands)


---

### Q8 · [Thinking] · `layer-caching`

> **How does Docker's layer cache work? What invalidates the cache during a build?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Docker caches each build layer by the instruction text and its inputs. A cache miss on any layer forces all subsequent layers to rebuild.

**How to think through this:**
1. During a build, Docker processes each Dockerfile instruction in order. For each instruction it computes a cache key based on: the instruction text, the parent layer's hash, and (for `COPY`/`ADD`) the checksum of the source files.
2. If a matching cached layer exists, Docker reuses it and moves on. This is a cache hit.
3. Cache invalidation triggers:
   - Changing the text of a `RUN` instruction.
   - Changing any file referenced by `COPY` or `ADD`.
   - Changing a base image (`FROM`) — if `docker pull` fetches a newer version.
   - Any instruction after an already-invalidated instruction (cache is sequential — once broken, it stays broken for all downstream layers).
4. The classic mistake: putting `COPY . .` before `RUN pip install`. Every code change invalidates the pip install layer. Fix: copy only `requirements.txt` first, run `pip install`, then copy the rest of the code.

**Key takeaway:** Order your Dockerfile instructions from least-frequently-changed to most-frequently-changed to maximize cache reuse.

</details>

📖 **Theory:** [layer-caching](./04_Images_and_Layers/Theory.md#layer-caching-dockers-superpower-and-gotcha)


---

### Q9 · [Normal] · `dockerfile-basics`

> **What is a Dockerfile? Write a minimal Dockerfile for a Python Flask app.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A Dockerfile is a plain-text script of instructions that tells Docker how to build an image layer by layer.

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "app.py"]
```

**How to think through this:**
1. `FROM python:3.12-slim` — start from a minimal official Python image (slim variant avoids unnecessary system packages).
2. `WORKDIR /app` — set the working directory so all subsequent paths are relative to `/app`.
3. Copy `requirements.txt` first and install dependencies before copying the full source — this lets Docker cache the pip install layer unless requirements change.
4. `COPY . .` — copy the application code after dependencies are installed.
5. `EXPOSE 5000` — documents the port (does not actually publish it; that happens at `docker run -p`).
6. `CMD` — the default command run when the container starts.

**Key takeaway:** A Dockerfile is a recipe — each instruction adds a layer, and good ordering maximizes cache efficiency.

</details>

📖 **Theory:** [dockerfile-basics](./05_Dockerfile/Theory.md#dockerfile)


---

### Q10 · [Normal] · `dockerfile-instructions`

> **Explain these Dockerfile instructions: FROM, RUN, COPY, ADD, WORKDIR, EXPOSE, ENV, CMD, ENTRYPOINT.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Each instruction serves a distinct role — some modify the filesystem (create layers), others set metadata or define container behavior.

**How to think through this:**
1. **FROM** — sets the base image. Every Dockerfile must start with this. `FROM scratch` means an empty filesystem.
2. **RUN** — executes a shell command during the build and commits the result as a new layer. Used to install packages, compile code, etc.
3. **COPY** — copies files/directories from the build context (your local machine) into the image. Preferred over ADD for simple file copying.
4. **ADD** — like COPY, but also supports URL sources and auto-extracts tar archives. Use sparingly — COPY is more explicit.
5. **WORKDIR** — sets the current directory for subsequent RUN, COPY, CMD, and ENTRYPOINT instructions. Creates the directory if it does not exist.
6. **EXPOSE** — documents which port the container listens on. Informational only — does not publish the port.
7. **ENV** — sets an environment variable that persists both at build time and in the running container.
8. **CMD** — default command run when the container starts. Can be overridden at `docker run`. Only the last CMD takes effect.
9. **ENTRYPOINT** — defines the executable that always runs. CMD becomes the default arguments to ENTRYPOINT. Harder to override (requires `--entrypoint` flag).

**Key takeaway:** ENTRYPOINT is the "what to run" and CMD is the "with what default arguments" — together they give you a flexible, overridable container command.

</details>

📖 **Theory:** [dockerfile-instructions](./05_Dockerfile/Theory.md#dockerfile)


---

### Q11 · [Critical] · `dockerfile-best-practices`

> **What are 5 Dockerfile best practices for production images? (Size, caching, security)**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
The five most impactful practices are: use minimal base images, order instructions for cache efficiency, use multi-stage builds, avoid running as root, and minimize layer count.

**How to think through this:**
1. **Use minimal base images:** Start from `alpine`, `slim`, or `distroless` variants. A `python:3.12-slim` is ~50MB vs ~1GB for the full image. Less surface area = fewer vulnerabilities.
2. **Order for cache efficiency:** Put instructions that change rarely (dependency installs) before instructions that change often (copying source code). A changed early layer busts all caches below it.
3. **Multi-stage builds:** Use one stage to compile/build and a second minimal stage to run. The final image contains no build tools, compilers, or intermediate artifacts.
4. **Do not run as root:** Add a `RUN useradd -r appuser && chown appuser /app` and `USER appuser` before CMD. A container breakout as root is far more dangerous.
5. **Minimize layer count and clean up in the same RUN:** Chain commands with `&&` and clean up in the same layer: `RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*`. Cleanup in a separate RUN does not reduce size because the previous layer already captured the files.

**Key takeaway:** Production Dockerfiles are not just about making it work — they are about making images small, secure, and cache-friendly.

</details>

📖 **Theory:** [dockerfile-best-practices](./05_Dockerfile/Theory.md#dockerfile)


---

### Q12 · [Normal] · `container-lifecycle`

> **What are the container states: created, running, paused, stopped, removed? What transitions exist between them?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A container moves through five states from creation to deletion. Each state corresponds to what the container process is doing (or not doing).

**How to think through this:**
1. **created:** Container exists (filesystem, network, metadata set up) but the main process has not started. Reached by `docker create`.
2. **running:** The main process is actively executing. Reached by `docker start` or `docker run`.
3. **paused:** The process is frozen using SIGSTOP (cgroup freezer). CPU is not consumed but memory is held. Reached by `docker pause`. Resume with `docker unpause`.
4. **stopped (exited):** The main process has terminated (either normally or via `docker stop`, which sends SIGTERM then SIGKILL). Container filesystem still exists.
5. **removed:** Container is deleted with `docker rm`. Filesystem is gone. Non-recoverable.

Transitions:
- `created` → `running`: `docker start`
- `running` → `paused`: `docker pause`
- `paused` → `running`: `docker unpause`
- `running` → `stopped`: process exits, or `docker stop`
- `stopped` → `running`: `docker start`
- `stopped/created` → `removed`: `docker rm`

**Key takeaway:** Stopped containers still consume disk space — `docker rm` is the only way to fully release their resources.

</details>

📖 **Theory:** [container-lifecycle](./06_Containers_Lifecycle/Theory.md#container-lifecycle)


---

### Q13 · [Normal] · `container-commands`

> **What do `docker run`, `docker start`, `docker stop`, `docker rm`, `docker ps -a` do?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
These five commands cover the essential container control loop: create+run, restart, stop, delete, and list.

**How to think through this:**
1. `docker run <image>`: Pulls the image (if needed), creates a new container, and starts it. Combines `docker create` + `docker start`. Common flags: `-d` (detach), `-p` (publish port), `-v` (mount volume), `--name` (name the container), `--rm` (auto-remove on exit).
2. `docker start <container>`: Starts an existing stopped container. Does not create a new one.
3. `docker stop <container>`: Sends SIGTERM to the main process, waits 10 seconds (configurable with `--time`), then sends SIGKILL. Graceful shutdown first.
4. `docker rm <container>`: Deletes a stopped container and its writable layer. Use `-f` to force-remove a running container (sends SIGKILL first).
5. `docker ps -a`: Lists all containers (running and stopped). Without `-a`, shows only running containers. Shows container ID, image, command, created time, status, ports, and name.

**Key takeaway:** `docker run` is create+start in one shot — `docker start` is for bringing back a stopped container without recreating it.

</details>

📖 **Theory:** [container-commands](./06_Containers_Lifecycle/Theory.md#container-lifecycle)


---

### Q14 · [Thinking] · `container-exec`

> **What does `docker exec -it container_name bash` do? When would you use `docker attach` instead?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
`docker exec` spawns a new process inside a running container. `docker attach` connects your terminal to the container's existing PID 1 process.

**How to think through this:**
1. `docker exec -it container_name bash`:
   - `-i` (interactive): keeps stdin open.
   - `-t` (tty): allocates a pseudo-terminal so you get a proper shell prompt.
   - `bash`: the command to run as a new process inside the container's namespaces.
   - This is the standard way to "shell into" a running container for debugging. Exiting this shell does not affect the container.
2. `docker attach container_name`:
   - Connects your terminal to the container's PID 1 (the main process). You see exactly what PID 1 is outputting to stdout/stderr.
   - Use this when you want to interact directly with the main process (e.g., a running Python REPL or interactive program).
   - Danger: pressing `Ctrl+C` sends SIGINT to PID 1, which may stop the container. The safe detach sequence is `Ctrl+P, Ctrl+Q`.
3. Use `exec` for debugging/inspection. Use `attach` when you genuinely need to interact with the main process.

**Key takeaway:** Use `exec` for debugging (safe, new process) — use `attach` only when you need to interact with PID 1, and know the detach shortcut.

</details>

📖 **Theory:** [container-exec](./06_Containers_Lifecycle/Theory.md#container-lifecycle)


---

### Q15 · [Normal] · `volumes-basics`

> **What are Docker volumes? How do you create and mount a volume? Where is data stored on the host?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Docker volumes are Docker-managed persistent storage units that exist independently of any container. Data survives container deletion.

**How to think through this:**
1. Without a volume, all writes inside a container go to its writable layer, which is deleted with `docker rm`. Volumes solve the persistence problem.
2. Create a volume: `docker volume create mydata`
3. Mount at run time: `docker run -v mydata:/app/data myimage` — the volume `mydata` is mounted at `/app/data` inside the container.
4. Inspect where it lives on the host: `docker volume inspect mydata` — look at the `Mountpoint` field. On Linux with the default local driver: `/var/lib/docker/volumes/mydata/_data`.
5. On Docker Desktop (Mac/Windows), the Docker VM is an intermediary — volumes live inside the VM's filesystem, not directly on your Mac disk.
6. List volumes: `docker volume ls`. Remove: `docker volume rm mydata`. Remove all unused: `docker volume prune`.

**Key takeaway:** Volumes are the right way to persist data — they are managed by Docker, portable, and survive container lifecycle.

</details>

📖 **Theory:** [volumes-basics](./07_Volumes_and_Bind_Mounts/Theory.md#volumes-and-bind-mounts)


---

### Q16 · [Normal] · `bind-mounts`

> **What is a bind mount? How does `docker run -v /host/path:/container/path` differ from a named volume?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A bind mount maps a specific path on the host filesystem directly into the container. Unlike a named volume, Docker does not manage it — you control the path.

**How to think through this:**
1. `docker run -v /host/path:/container/path`: whatever is at `/host/path` on the host appears at `/container/path` in the container. Changes are immediately visible in both directions.
2. Named volume (`-v myvolume:/container/path`): Docker manages the storage location. You reference it by name, not by path. Docker initializes the volume with the image's content at that path if the volume is empty.
3. Key differences:
   - **Control:** Bind mount = you pick the host path. Named volume = Docker picks the path.
   - **Portability:** Named volumes are portable across hosts (Docker manages them). Bind mounts depend on the host directory structure existing.
   - **Initialization:** Named volumes get seeded with image data on first use. Bind mounts use whatever is at the host path (potentially empty).
4. Use bind mounts for development (live code reload, config files). Use named volumes for production data (databases, uploads).

**Key takeaway:** Bind mounts give you direct host access (great for dev); named volumes give you Docker-managed, portable persistence (great for prod).

</details>

📖 **Theory:** [bind-mounts](./07_Volumes_and_Bind_Mounts/Theory.md#volumes-and-bind-mounts)


---

### Q17 · [Thinking] · `volume-vs-bind`

> **When would you use a named volume vs a bind mount? What is a tmpfs mount?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Use named volumes for persistent production data, bind mounts for development workflows, and tmpfs mounts for sensitive in-memory data that must not touch disk.

**How to think through this:**
1. **Named volume — use when:**
   - You need persistent data that survives container restarts (databases, file uploads).
   - You want Docker to manage backup, restore, and migration via `docker volume` commands.
   - You are running in CI/CD or production where host paths are not predictable.
2. **Bind mount — use when:**
   - Developing locally and you want live code changes reflected inside the container without rebuilding.
   - You need to inject a specific config file from a known host location.
   - You want to share files between the host and container for inspection.
3. **tmpfs mount** (`--mount type=tmpfs,target=/tmp`):
   - Mounts a temporary in-memory filesystem inside the container.
   - Data exists only in RAM — it is never written to host disk.
   - Use for secrets, session data, or any sensitive scratch space that must not persist.
   - Wiped when the container stops.

**Key takeaway:** tmpfs is your in-memory scratchpad — fast, secure, and ephemeral by design.

</details>

📖 **Theory:** [volume-vs-bind](./07_Volumes_and_Bind_Mounts/Theory.md#volumes-and-bind-mounts)


---

### Q18 · [Normal] · `docker-networking`

> **What is a Docker network? What network does a container use by default?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A Docker network is a virtual network that allows containers to communicate with each other and with the outside world. By default, containers are connected to the `bridge` network.

**How to think through this:**
1. When Docker is installed, it creates three default networks: `bridge`, `host`, and `none`.
2. `docker run` without a `--network` flag attaches the container to the `bridge` network (named `bridge`).
3. The default bridge network assigns each container a private IP in the `172.17.0.0/16` subnet. Containers can reach each other by IP, but not by name (DNS is not set up on the default bridge).
4. User-defined bridge networks (created with `docker network create`) add automatic DNS — containers can reach each other by container name. This is the preferred approach.
5. `docker network ls` lists all networks. `docker network inspect bridge` shows which containers are connected and their IPs.

**Key takeaway:** Always create a user-defined bridge network for your application — it gives you DNS resolution by container name, which the default bridge network lacks.

</details>

📖 **Theory:** [docker-networking](./08_Networking/Theory.md#docker-networking)


---

### Q19 · [Normal] · `network-drivers`

> **Name the 5 Docker network drivers: bridge, host, none, overlay, macvlan. When would you use each?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Each driver solves a different networking problem — from local development to multi-host clusters to direct L2 network access.

**How to think through this:**
1. **bridge:** Default driver. Creates a virtual switch on the host. Containers get private IPs; NAT is used to reach the outside. Use for: single-host multi-container applications (most common).
2. **host:** Removes network isolation — the container shares the host's network stack directly. No NAT overhead. Use for: high-performance networking where port mapping latency matters. Not available on Docker Desktop (Mac/Windows).
3. **none:** No networking at all. The container has only a loopback interface. Use for: batch jobs that need no network, or maximum isolation.
4. **overlay:** Creates a distributed virtual network across multiple Docker hosts (used by Docker Swarm). Containers on different machines can communicate as if on the same local network. Use for: multi-host deployments with Swarm.
5. **macvlan:** Assigns a real MAC address to the container, making it appear as a physical device on the network. Containers get IPs from your LAN. Use for: legacy apps that expect to be directly on the physical network, or network monitoring tools.

**Key takeaway:** bridge for local dev, host for performance-critical single-host, overlay for Swarm clusters, macvlan when you need the container to look like a physical machine on your LAN.

</details>

📖 **Theory:** [network-drivers](./08_Networking/Theory.md#network-drivers-overview)


---

### Q20 · [Thinking] · `bridge-network`

> **How does the default bridge network work? How do containers on the same network communicate?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
The default bridge network uses a virtual Ethernet bridge (`docker0`) on the host. Containers get a virtual NIC (`veth` pair) connected to this bridge and can reach each other by IP. On user-defined bridges, DNS resolution by name is also available.

**How to think through this:**
1. Docker creates a bridge interface `docker0` on the host (typically `172.17.0.1`). Think of it as a virtual switch.
2. When a container starts, Docker creates a `veth` (virtual Ethernet) pair — one end goes into the container as `eth0`, the other end is attached to the `docker0` bridge on the host.
3. The container gets an IP from the bridge subnet (e.g., `172.17.0.2`). The host's `docker0` IP (`172.17.0.1`) is the gateway.
4. Two containers on the same bridge can ping each other by IP. Traffic goes: container A `eth0` → host `vethXXX` → `docker0` bridge → `vethYYY` → container B `eth0`.
5. For outbound internet traffic, iptables NAT rules on the host masquerade the container's private IP as the host IP.
6. The default bridge does not set up DNS — containers must use IPs. User-defined bridges run an embedded DNS server so `ping container_name` works.

**Key takeaway:** The `docker0` bridge is a virtual switch — veth pairs are the cables connecting containers to it, and iptables handles NAT for external traffic.

</details>

📖 **Theory:** [bridge-network](./08_Networking/Theory.md#the-default-bridge-network-and-its-problem)


---

### Q21 · [Normal] · `docker-compose-basics`

> **What is Docker Compose? What does a docker-compose.yml define?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Docker Compose is a tool for defining and running multi-container applications. A `docker-compose.yml` file declaratively describes services, networks, volumes, and their relationships.

**How to think through this:**
1. Without Compose, running a multi-container app means running multiple `docker run` commands with the right flags, in the right order, managing networks and volumes manually.
2. Compose lets you define the entire application stack in a single YAML file and start everything with `docker compose up`.
3. A `docker-compose.yml` defines:
   - **services:** Each container in the stack (image or build context, ports, environment variables, volumes, dependencies).
   - **networks:** Custom networks to connect services (Compose creates a default network for the project automatically).
   - **volumes:** Named volumes used by services.
4. Key commands: `docker compose up -d` (start in background), `docker compose down` (stop and remove containers/networks), `docker compose logs`, `docker compose ps`, `docker compose build`.
5. Compose also handles startup ordering via `depends_on` and can scale services with `--scale`.

**Key takeaway:** Compose turns a complex multi-container setup into a single declarative file and two commands: `up` and `down`.

</details>

📖 **Theory:** [docker-compose-basics](./09_Docker_Compose/Theory.md#docker-compose)


---

### Q22 · [Normal] · `compose-services`

> **Write a docker-compose.yml with a web service (nginx) and a database (postgres) linked together.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**

```yaml
services:
  web:
    image: nginx:alpine
    ports:
      - "8080:80"
    volumes:
      - ./html:/usr/share/nginx/html:ro
    depends_on:
      - db
    networks:
      - app-network

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: appuser
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: appdb
    volumes:
      - pgdata:/var/lib/postgresql/data
    networks:
      - app-network

volumes:
  pgdata:

networks:
  app-network:
```

**How to think through this:**
1. Both services are on `app-network` — this gives them DNS resolution so `web` can reach `db` by the hostname `db`.
2. `depends_on` ensures Compose starts `db` before `web`. Note: this checks container start, not database readiness — for that you need a healthcheck.
3. The postgres data is stored in named volume `pgdata` so it persists across `docker compose down` (as long as you do not add `-v`).
4. The bind mount `./html:/usr/share/nginx/html:ro` mounts local HTML files into nginx as read-only.

**Key takeaway:** `depends_on` + shared network is the standard pattern — services reach each other by service name, not by IP.

</details>

📖 **Theory:** [compose-services](./09_Docker_Compose/Theory.md#docker-compose)


---

### Q23 · [Thinking] · `compose-networking`

> **How does Docker Compose networking work? How do services reach each other by name?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Compose automatically creates a default bridge network for each project and registers each service name as a DNS entry on that network. Services resolve each other by service name.

**How to think through this:**
1. When you run `docker compose up`, Compose creates a network named `<project>_default` where `<project>` is the directory name (or the value of `COMPOSE_PROJECT_NAME`).
2. Every service in the file is connected to this network unless you specify custom networks.
3. Docker's embedded DNS server (running at `127.0.0.11` inside containers) resolves service names to container IPs. So if your web app does `postgres://db:5432/...`, the hostname `db` resolves to the postgres container's IP.
4. If you define custom networks, only services on the same network can communicate by name. This lets you create network segmentation: a `frontend` network and a `backend` network where the API sits on both but the database is only on `backend`.
5. Service names are the DNS hostnames. Aliases can be added with `networks: <net>: aliases: [alias1]`.

**Key takeaway:** Compose's embedded DNS is what makes service discovery work — `db`, `redis`, `api` are all valid hostnames inside your Compose project's network.

</details>

📖 **Theory:** [compose-networking](./09_Docker_Compose/Theory.md#docker-compose)


---

### Q24 · [Normal] · `docker-registry`

> **What is a Docker registry? What is Docker Hub? How is a private registry different?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A Docker registry is a server that stores and distributes Docker images. Docker Hub is the default public registry. A private registry serves the same function but with access control and keeps images off the public internet.

**How to think through this:**
1. **Registry:** A service implementing the Docker Registry HTTP API v2. When you `docker pull nginx`, Docker contacts the configured registry (Docker Hub by default) and downloads the image layers.
2. **Docker Hub (hub.docker.com):** The default public registry. Hosts official images (nginx, postgres, python) and user images (`username/imagename`). Free tier has rate limits and requires a login for higher pull rates.
3. **Private registry:**
   - Self-hosted: `docker run -d -p 5000:5000 registry:2` spins up a basic private registry. Push to it with `docker push localhost:5000/myimage`.
   - Cloud-hosted: AWS ECR, Google Artifact Registry, Azure ACR, GitHub Container Registry, JFrog Artifactory.
   - Differences: authentication required, images are not publicly accessible, often add vulnerability scanning, signing, and RBAC.
4. To use a private registry, prefix your image name with the registry hostname: `myregistry.example.com/myapp:1.0`.

**Key takeaway:** A registry is just an image file server — Docker Hub is the public default, but any image you do not want public should go to a private registry.

</details>

📖 **Theory:** [docker-registry](./10_Docker_Registry/Theory.md#module-10--docker-registry)


---

### Q25 · [Normal] · `push-pull-images`

> **What is the workflow to build, tag, and push an image to Docker Hub?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Four steps: login, build, tag, push.

**How to think through this:**
1. **Login:** `docker login` — authenticates to Docker Hub using your Docker ID and password (or access token). Credentials are stored in `~/.docker/config.json`.
2. **Build:** `docker build -t myapp:latest .` — builds the image from the Dockerfile in the current directory and tags it locally as `myapp:latest`.
3. **Tag for Docker Hub:** `docker tag myapp:latest username/myapp:latest` — Docker Hub requires images to be namespaced under your Docker ID (`username/imagename`).
4. **Push:** `docker push username/myapp:latest` — uploads the image layers to Docker Hub. Only layers not already present on the registry are uploaded (deduplication by content hash).
5. To pull it later on another machine: `docker pull username/myapp:latest`.
6. Best practice: also push a version tag alongside `latest`: `docker tag myapp:latest username/myapp:1.2.3` then `docker push username/myapp:1.2.3`. Relying solely on `latest` makes rollbacks difficult.

**Key takeaway:** Always tag with a version in addition to `latest` — `latest` is a convenience alias, not a version control strategy.

</details>

📖 **Theory:** [push-pull-images](./10_Docker_Registry/Theory.md#tagging-and-pushing-images)


---

### Q26 · [Normal] · `private-registry`

> **How do you authenticate to a private registry? What is `docker login` doing?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
`docker login <registry>` prompts for credentials and stores an auth token in `~/.docker/config.json`. Subsequent push/pull commands automatically include this token.

**How to think through this:**
1. `docker login registry.example.com` sends your username and password to the registry's `/v2/` auth endpoint. The registry returns a bearer token.
2. The token (or base64-encoded credentials for basic auth) is stored in `~/.docker/config.json` under the registry hostname key. On systems with a credential helper (macOS Keychain, Windows Credential Manager, `pass`), the actual secret is stored in the OS keychain and only a reference is in the JSON file.
3. When you `docker push` or `docker pull` from that registry, the Docker daemon reads the stored credentials from `config.json` and includes them in the request headers.
4. For automated systems (CI/CD, Kubernetes): use `docker login` with `--password-stdin` to avoid exposing passwords in shell history: `echo $TOKEN | docker login -u $USER --password-stdin registry.example.com`. For Kubernetes, create an `imagePullSecret`.
5. `docker logout registry.example.com` removes the stored credentials.

**Key takeaway:** `docker login` is a credential handshake that stores a token — protect `~/.docker/config.json` as it contains registry access keys.

</details>

📖 **Theory:** [private-registry](./10_Docker_Registry/Theory.md#module-10--docker-registry)


---

### Q27 · [Normal] · `multi-stage-builds`

> **What is a multi-stage build? Write an example for a Go application that compiles in one stage and runs in a minimal second stage.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A multi-stage build uses multiple `FROM` instructions in a single Dockerfile. Each stage has its own base image, and you selectively copy artifacts from one stage to the next — leaving build tools behind.

```dockerfile
# Stage 1: build
FROM golang:1.22-alpine AS builder

WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /app/server .

# Stage 2: run
FROM scratch

COPY --from=builder /app/server /server

EXPOSE 8080
ENTRYPOINT ["/server"]
```

**How to think through this:**
1. Stage 1 uses the full `golang:1.22-alpine` image (~300MB) which contains the Go compiler, tools, and standard library.
2. The Go binary is compiled as a static binary (`CGO_ENABLED=0`) so it has no dynamic library dependencies.
3. Stage 2 starts `FROM scratch` — a completely empty filesystem. Only the compiled binary is copied in with `COPY --from=builder`.
4. The final image contains just the binary. No Go runtime, no compiler, no shell. Size: a few megabytes vs hundreds.
5. `FROM scratch` is extreme minimalism. `FROM gcr.io/distroless/static` is a common alternative that adds CA certificates and timezone data without a shell.

**Key takeaway:** Multi-stage builds decouple the build environment from the runtime environment — your final image ships only what is needed to run.

</details>

📖 **Theory:** [multi-stage-builds](./11_Multi_Stage_Builds/Theory.md#module-11--multi-stage-builds)


---

### Q28 · [Thinking] · `build-args`

> **What is the difference between ARG and ENV in a Dockerfile? When would you use ARG?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
ARG is a build-time variable only — it exists during the build and is not present in the running container. ENV is a runtime variable — it persists in the image and is available to the container process.

**How to think through this:**
1. **ARG:** Declared with `ARG MY_VAR=default`. Passed at build time: `docker build --build-arg MY_VAR=value .`. Available only to subsequent Dockerfile instructions during the build. Does not appear in `docker inspect` environment or inside the container.
2. **ENV:** Declared with `ENV MY_VAR=value`. Baked into the image. Available to all child processes at runtime via the environment. Visible in `docker inspect` output.
3. Use ARG for:
   - Build-time configuration that varies per environment (e.g., `APP_VERSION`, base image tags).
   - Conditional build logic.
   - Values that should not be visible in the final image (credentials passed during build — though note they are still in build cache and layer metadata, so prefer secrets mounts for sensitive values).
4. Use ENV for:
   - Default runtime configuration (log level, port, feature flags).
   - Values the application reads at startup.
5. You can combine them: `ARG MY_VAR` then `ENV MY_VAR=$MY_VAR` to accept a build arg and promote it to a runtime env var.

**Key takeaway:** ARG disappears after the build; ENV lives in the image forever — use ARG for build-time parameterization, ENV for runtime configuration.

</details>

📖 **Theory:** [build-args](./11_Multi_Stage_Builds/Theory.md#module-11--multi-stage-builds)


---

### Q29 · [Critical] · `image-size-optimization`

> **A Docker image is 2GB. List 5 techniques to reduce its size.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
The five most effective techniques are: use a minimal base image, multi-stage builds, clean up in the same RUN layer, use .dockerignore, and avoid installing unnecessary packages.

**How to think through this:**
1. **Switch to a minimal base image:** Replace `ubuntu:22.04` (~70MB) with `ubuntu:22.04-minimal`, or better, use `alpine` (~5MB) or `debian:slim`. For interpreted languages, use `-slim` variants. For compiled binaries, use `distroless` or `scratch`.
2. **Multi-stage builds:** Compile in a fat builder image, copy only the final artifact to a minimal runtime image. Eliminates all build tools, source code, and intermediate files from the final layer.
3. **Clean up in the same RUN instruction:** `RUN apt-get update && apt-get install -y build-essential && make && apt-get remove -y build-essential && rm -rf /var/lib/apt/lists/*`. If cleanup is in a separate `RUN`, the installed files are permanently captured in the previous layer.
4. **Use .dockerignore:** Exclude `node_modules/`, `.git/`, test files, docs, and local configs from the build context. A large build context inflates the COPY layer and slows builds.
5. **Avoid installing unnecessary packages:** `apt-get install --no-install-recommends` skips recommended packages. `pip install --no-cache-dir` skips the pip cache. Audit what is actually needed at runtime.

Bonus: use `docker image history <image>` to see which layers are large, and `dive` (open source tool) to inspect layer contents.

**Key takeaway:** Multi-stage builds are the single highest-impact technique — they architecturally separate what you need to build from what you need to run.

</details>

📖 **Theory:** [image-size-optimization](./11_Multi_Stage_Builds/Theory.md#the-bloated-image-problem)


---

### Q30 · [Critical] · `docker-security`

> **What are the main Docker security concerns? What is running as root inside a container?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
The main concerns are: privileged containers, running as root, exposed Docker socket, unscanned images, and excessive capabilities. Root in a container is not the same as root on the host — but the gap is smaller than it should be.

**How to think through this:**
1. **Running as root inside a container:** By default, container processes run as root (UID 0). If an attacker exploits your app and escapes the container namespace, they land on the host as root. Always add `USER appuser` in your Dockerfile.
2. **Docker socket exposure:** Mounting `/var/run/docker.sock` into a container gives it full control over the Docker daemon — equivalent to root access to the host. Avoid this in production.
3. **Privileged containers:** `docker run --privileged` disables all container isolation and gives the container near-full host access. Never use in production without a specific, understood reason.
4. **Unpatched base images:** A `FROM ubuntu:18.04` image may carry hundreds of known CVEs. Scan images regularly with Docker Scout, Trivy, or Snyk.
5. **Linux capabilities:** By default, Docker drops most capabilities but keeps some (e.g., NET_BIND_SERVICE). Use `--cap-drop ALL --cap-add <specific>` to apply least privilege.
6. **Secrets in images:** Never bake passwords or API keys into images via ENV or build args. Use Docker secrets, Kubernetes secrets, or a secrets manager.

**Key takeaway:** The biggest Docker security mistake is running containers as root with access to the Docker socket — that is effectively a root shell on the host.

</details>

📖 **Theory:** [docker-security](./12_Docker_Security/Theory.md#module-12--docker-security)


---

### Q31 · [Normal] · `rootless-containers`

> **What is a rootless container? How do you run Docker without root (rootless mode)?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Rootless Docker runs the Docker daemon itself as a non-root user. This eliminates the host-root escalation risk because the daemon process has no elevated privileges on the host.

**How to think through this:**
1. In standard Docker, `dockerd` runs as root. Even if container processes run as non-root users, a daemon compromise could lead to host root access.
2. Rootless mode (`dockerd-rootless`) runs the entire daemon — including all containers it manages — under a regular user account using user namespaces. The container's UID 0 maps to a non-privileged host UID.
3. Setup (Linux): `dockerd-rootless-setuptool.sh install` sets up rootless Docker for the current user. The daemon is managed via systemd user services.
4. Limitations: some features are not available in rootless mode — `--net=host` is restricted, exposing ports <1024 requires extra configuration, and some storage drivers may not be supported.
5. Podman is an alternative container runtime that is rootless by default — no daemon, no root, each container runs as the calling user.
6. Inside Kubernetes, `runAsNonRoot: true` in the pod security context enforces that the container process does not run as UID 0.

**Key takeaway:** Rootless Docker is defense-in-depth — if the daemon is compromised, the attacker only has your user's privileges, not root on the host.

</details>

📖 **Theory:** [rootless-containers](./12_Docker_Security/Theory.md#rootless-docker)


---

### Q32 · [Normal] · `security-scanning`

> **What is Docker Scout? What does `docker scout cves` do? Name one other container security scanning tool.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Docker Scout is Docker's built-in vulnerability analysis platform. `docker scout cves` lists known CVEs found in an image's packages and base layers. Trivy is a widely used open-source alternative.

**How to think through this:**
1. **Docker Scout:** Integrated into Docker Desktop and the CLI (available as of Docker Engine 24+). It builds a Software Bill of Materials (SBOM) for your image — a list of all packages and their versions — then cross-references against vulnerability databases (NVD, GitHub Advisory, OS-specific advisories).
2. `docker scout cves <image>`: Analyzes the image and outputs a table of CVEs by severity (critical, high, medium, low). Shows the affected package, fixed version (if available), and CVE ID. Example: `docker scout cves myapp:latest`.
3. `docker scout recommendations <image>`: Suggests a safer base image with fewer vulnerabilities.
4. `docker scout quickview <image>`: A summary dashboard of vulnerability counts.
5. **Trivy** (Aqua Security): Open source, widely adopted. `trivy image myapp:latest` scans for OS package CVEs, language-specific dependencies (pip, npm, go modules), misconfigurations, and secrets. Integrates with CI/CD pipelines easily. Other alternatives: Snyk Container, Grype (Anchore), Clair.

**Key takeaway:** Scanning images is not optional in production — knowing your CVE exposure before deployment is table stakes for container security.

</details>

📖 **Theory:** [security-scanning](./12_Docker_Security/Theory.md#module-12--docker-security)


---

### Q33 · [Normal] · `docker-swarm`

> **What is Docker Swarm? What is a node, service, and task in Swarm?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Docker Swarm is Docker's native container orchestration system. It turns a pool of Docker hosts into a single virtual cluster. A node is a host, a service is the desired state declaration, and a task is an individual running container instance.

**How to think through this:**
1. **Docker Swarm:** Built into Docker Engine — no separate installation needed. Activated with `docker swarm init` on the first host. Other hosts join as workers with `docker swarm join --token ...`. Simpler than Kubernetes but less feature-rich.
2. **Node:** A Docker host participating in the Swarm. There are two types:
   - **Manager node:** Controls the cluster state, schedules tasks, handles the Raft consensus protocol. The cluster should have an odd number (1, 3, 5) for fault tolerance.
   - **Worker node:** Executes the containers assigned to it. Has no knowledge of the overall cluster state.
3. **Service:** The declarative definition of what to run. `docker service create --name web --replicas 3 nginx` creates a service specifying: which image, how many replicas, port mappings, update policy, etc. Swarm ensures the desired replica count is always maintained.
4. **Task:** A single running instance of a service container, assigned to a specific node. A service with 3 replicas has 3 tasks. If a task fails, the scheduler creates a new one elsewhere.
5. Key commands: `docker service ls`, `docker service ps web`, `docker service scale web=5`, `docker stack deploy -c docker-compose.yml myapp`.

**Key takeaway:** Swarm's mental model is simple — you declare services (desired state), and Swarm maintains tasks (actual state) across nodes automatically.

</details>

📖 **Theory:** [docker-swarm](./13_Docker_Swarm/Theory.md#module-13--docker-swarm)


---

## 🟡 Tier 2 — Intermediate

### Q34 · [Normal] · `swarm-services`

> **What is the difference between a Docker Swarm service and a container? What do `--replicas` and `--mode global` do?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A container is a single running process instance. A Swarm service is a desired-state declaration that the Swarm manager fulfills by creating and maintaining one or more containers (called tasks) across the cluster.

**How to think through this:**
1. When you run `docker run`, you get one container on one host — no automatic recovery if it dies.
2. When you run `docker service create`, the manager records your desired state and schedules tasks across available worker nodes.
3. `--replicas 3` tells the manager to keep exactly 3 instances running at all times — if one dies, a replacement is scheduled automatically.
4. `--mode global` instead places exactly one task on every node in the swarm — useful for agents like log shippers or monitoring daemons that must run everywhere.

**Key takeaway:** A service is a self-healing contract with the cluster; a container is just a process.

</details>

📖 **Theory:** [swarm-services](./13_Docker_Swarm/Theory.md#module-13--docker-swarm)


---

### Q35 · [Normal] · `swarm-vs-k8s`

> **Compare Docker Swarm vs Kubernetes. When is Swarm still a reasonable choice?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Docker Swarm is Docker's built-in orchestrator — simple to set up and operate. Kubernetes is a far more powerful but operationally complex platform that dominates production workloads at scale.

**How to think through this:**
1. Setup: Swarm is `docker swarm init` + `docker swarm join`. Kubernetes requires kubeadm, managed control planes, CNI plugins, and more.
2. Feature set: Kubernetes has HPA, custom resource definitions, advanced scheduling, a rich ecosystem (Helm, Operators). Swarm has basic scaling and rolling updates.
3. Learning curve: Swarm uses familiar Docker CLI concepts. Kubernetes introduces a new object model (Pod, Deployment, Service, Ingress) with its own API.
4. Swarm is still reasonable when: the team is small, the workload is simple, you need orchestration without the Kubernetes ops burden, or you're already invested in Docker Compose (Swarm uses the same file format with stack deploy).

**Key takeaway:** Choose Swarm for simplicity and speed; choose Kubernetes when you need scale, ecosystem, or fine-grained control.

</details>

📖 **Theory:** [swarm-vs-k8s](./13_Docker_Swarm/Theory.md#swarm-vs-kubernetes-when-swarm-is-enough)


---

### Q36 · [Normal] · `docker-cicd`

> **How is Docker used in a CI/CD pipeline? Describe the build → test → push → deploy flow.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Docker provides a reproducible, environment-agnostic unit (the image) that moves unchanged through every stage of the pipeline.

**How to think through this:**
1. Build: The CI runner executes `docker build -t myapp:$GIT_SHA .` — the Dockerfile defines every dependency, so builds are identical regardless of the runner's OS.
2. Test: Run the freshly-built image with test flags, or use `docker compose -f docker-compose.test.yml up --abort-on-container-exit` to spin up the app and its dependencies (e.g., a test database), run the suite, and tear down.
3. Push: On a passing build of the main branch, `docker push registry/myapp:$GIT_SHA` publishes the image to a registry (Docker Hub, ECR, GCR). A `latest` or environment tag is optionally re-tagged here.
4. Deploy: The deploy step pulls the specific image tag and updates the running service — `docker service update --image registry/myapp:$GIT_SHA myapp` in Swarm, or a Kubernetes rollout in K8s.

**Key takeaway:** Docker makes the artifact — the image — the single source of truth that passes through every pipeline stage unchanged.

</details>

📖 **Theory:** [docker-cicd](./14_Docker_in_CICD/Theory.md#module-14--docker-in-cicd)


---

### Q37 · [Normal] · `dockerfile-cicd`

> **What Dockerfile techniques improve CI/CD build times? (Cache mounts, layer ordering, .dockerignore)**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Fast CI builds depend on maximizing Docker's layer cache reuse and minimizing the amount of data sent to the daemon.

**How to think through this:**
1. Layer ordering — copy dependency manifests first and install dependencies before copying source code. Since source changes often but `package.json` rarely does, the expensive install layer is cached across most commits.
2. `.dockerignore` — exclude `node_modules/`, `.git/`, test fixtures, and IDE files. This shrinks the build context sent to the daemon and prevents cache-busting from irrelevant file changes.
3. BuildKit cache mounts (`--mount=type=cache`) — persist package manager caches (pip, npm, apt) between builds on the same runner without baking them into the image layer. A pip install that normally downloads 200 MB hits disk cache instead.
4. Multi-stage builds — only the final minimal stage is pushed, so testers and deployment targets pull less data.
5. Pinning base image digests — avoids surprise cache invalidation from upstream changes.

**Key takeaway:** Order layers from least-to-most-frequently-changed and use BuildKit cache mounts to avoid re-downloading dependencies on every build.

</details>

📖 **Theory:** [dockerfile-cicd](./14_Docker_in_CICD/Theory.md#module-14--docker-in-cicd)


---

### Q38 · [Normal] · `best-practices`

> **What are the 5 most important Docker best practices for a production deployment?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
These five practices address security, image hygiene, reliability, and operational visibility.

**How to think through this:**
1. Use a minimal, pinned base image — prefer `python:3.12-slim` over `python:latest`. Smaller images reduce attack surface and eliminate surprise breakage from upstream changes.
2. Run as a non-root user — add a dedicated USER instruction. A container breakout as root on the host is catastrophic; as a low-privilege UID it is far less so.
3. Use multi-stage builds — keep build tools, compilers, and test dependencies out of the final image. Only ship what the runtime needs.
4. Set a HEALTHCHECK — Docker and orchestrators use it to detect application-level failures, not just process crashes. Without it, a deadlocked process still looks healthy.
5. Set resource limits (`--memory`, `--cpus`) — an unbound container can exhaust host resources and bring down all co-located containers. Resource limits enforce isolation.

**Key takeaway:** Secure the runtime user, minimize the image, and constrain resource usage to make containers safe and predictable in production.

</details>

📖 **Theory:** [best-practices](./15_Best_Practices/Theory.md#module-15--docker-best-practices)


---

### Q39 · [Normal] · `buildkit`

> **What is BuildKit? How does it improve Docker build performance? How do you enable it?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
BuildKit is Docker's next-generation build engine that replaces the legacy builder with parallel execution, better caching, and new mount types.

**How to think through this:**
1. Parallel stage execution — in a multi-stage Dockerfile, BuildKit can build independent stages concurrently instead of sequentially.
2. Improved cache — BuildKit tracks cache at a finer granularity and supports cache mounts that persist package manager state between builds without polluting the image.
3. Secret mounts — `--mount=type=secret` lets you pass credentials into a build step without them ever appearing in a layer.
4. Inline cache — images can embed cache metadata so remote caches can be reused across CI runners.
5. Enabling it:
   - Docker 23.0+: BuildKit is the default.
   - Older versions: set `DOCKER_BUILDKIT=1` as an environment variable, or add `{ "features": { "buildkit": true } }` to `/etc/docker/daemon.json`.
   - Use `docker buildx build` to always get BuildKit features.

**Key takeaway:** BuildKit makes builds faster through parallelism and smarter caching, and safer through secret mounts that never leak into image layers.

</details>

📖 **Theory:** [buildkit](./16_BuildKit_and_Docker_Scout/Theory.md#module-16--buildkit-and-docker-scout)


---

### Q40 · [Normal] · `docker-scout`

> **What is the difference between Docker Scout and Trivy for container security scanning? What does a SBOM do?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Both tools scan container images for known vulnerabilities, but they differ in integration and scope.

**How to think through this:**
1. Docker Scout is Docker's native advisory service — integrated into Docker Hub, Docker Desktop, and the CLI via `docker scout cves`. It tracks your images over time and alerts when new CVEs affect already-pushed images.
2. Trivy (by Aqua Security) is an open-source, standalone scanner that runs as a CLI or CI step with no external service dependency. It scans OS packages, language dependencies, IaC files, and Kubernetes manifests — broader scope than Scout.
3. SBOM (Software Bill of Materials) — a machine-readable inventory of every package, library, and component inside an image, along with their versions and licenses. It lets you quickly answer "am I affected by Log4Shell?" across your entire fleet by querying the SBOM rather than re-scanning every image. Docker Scout and Trivy both generate and consume SBOMs (typically in SPDX or CycloneDX format).

**Key takeaway:** Trivy is a flexible offline scanner; Scout is a registry-integrated advisory service — a SBOM is the artifact both use to answer "what's inside this image?"

</details>

📖 **Theory:** [docker-scout](./16_BuildKit_and_Docker_Scout/Theory.md#module-16--buildkit-and-docker-scout)


---

### Q41 · [Normal] · `docker-init`

> **What is `docker init`? What files does it generate? Why is it useful for new projects?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
`docker init` is an interactive CLI command that scaffolds production-ready Docker configuration for a new project by detecting the language and asking a few questions.

**How to think through this:**
1. You run `docker init` in an empty or existing project directory. Docker detects the language (Go, Python, Node, etc.) or asks you to select one.
2. It generates: a `Dockerfile` (multi-stage, following best practices), a `.dockerignore`, and a `compose.yaml` (the modern name for docker-compose.yml) with sensible defaults.
3. The generated Dockerfile uses the correct base image, sets a non-root user, and structures layers for cache efficiency — it encodes the best practices that many engineers skip when writing Dockerfiles by hand.
4. It removes the blank-page problem: even experienced engineers waste time looking up base image names and multi-stage syntax. `docker init` gives a correct starting point in seconds.

**Key takeaway:** `docker init` generates a best-practice Dockerfile, .dockerignore, and compose.yaml so teams start with production-grade config rather than tutorial antipatterns.

</details>

📖 **Theory:** [docker-init](./17_Docker_Init_and_Debug/Theory.md#module-17--docker-init-and-docker-debug)


---

### Q42 · [Normal] · `docker-debug`

> **What is `docker debug`? How does it differ from `docker exec`? When would you use it?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
`docker debug` is a Docker Desktop feature that attaches a debugging shell to a container — or even to a stopped container — by injecting a toolbox sidecar, without requiring the image to contain a shell or debug tools.

**How to think through this:**
1. `docker exec` requires the container to be running AND requires the tool you want (bash, curl, ps) to already exist inside the image. A distroless or scratch-based image has none of these.
2. `docker debug` works on running or stopped containers. It mounts a separate filesystem with debugging tools (busybox, strace, etc.) alongside the target container's filesystem, so you can inspect files and processes without those tools being in the image.
3. Use it when: debugging a minimal production image that has no shell, inspecting a crashed container's state, or troubleshooting startup failures where the container exits before you can exec in.

**Key takeaway:** `docker debug` makes distroless and minimal images debuggable by injecting tools from outside the image rather than requiring them to be baked in.

</details>

📖 **Theory:** [docker-debug](./17_Docker_Init_and_Debug/Theory.md#module-17--docker-init-and-docker-debug)


---

### Q43 · [Interview] · `explain-layers-junior`

> **A junior engineer asks why the same base layer isn't downloaded twice when pulling two images. Explain the layer sharing mechanism.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Docker images are built from stacked, read-only layers identified by a content hash. If two images share a layer with the same hash, the Docker daemon only stores and downloads it once.

**How to think through this:**
1. Think of layers like LEGO bricks. A base image — say `ubuntu:22.04` — is a stack of a few bricks. When you build `myapp:v1` and `myapp:v2` both FROM that base, they both reference the same bricks at the bottom.
2. Each layer has a SHA256 digest calculated from its contents. Docker's local store (by default under `/var/lib/docker/overlay2`) maps these digests to actual filesystem data.
3. When you pull a second image, Docker checks each incoming layer's digest against what it already has. If the digest matches, it skips the download entirely and just links to the existing data.
4. This is also why layer ordering in a Dockerfile matters for cache efficiency — stable layers (base OS, system packages) should come first so they are shared across many images and builds.

**Key takeaway:** Layers are content-addressed blobs — same hash means same data, so the daemon deduplicates storage and skips redundant downloads automatically.

</details>

📖 **Theory:** [explain-layers-junior](./04_Images_and_Layers/Theory.md#images-and-layers)


---

### Q44 · [Interview] · `compare-volume-bind`

> **Compare named volumes vs bind mounts for a production database. Which would you choose and why?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Named volumes are managed by Docker and stored in Docker's own storage area. Bind mounts map a specific host path directly into the container. For a production database, named volumes are the right choice.

**How to think through this:**
1. Portability — a named volume works identically on Linux, Mac, and Windows. A bind mount requires the exact host path to exist, which breaks across environments and CI runners.
2. Performance — on Linux, both are roughly equivalent. On Docker Desktop (Mac/Windows), bind mounts go through a filesystem translation layer that can be significantly slower — critical for a database doing lots of small random I/O.
3. Lifecycle management — named volumes persist independently of containers. You can back them up with `docker run --rm -v mydata:/data alpine tar ...`, inspect them with `docker volume inspect`, and they are not accidentally deleted when you remove a container (unlike anonymous volumes).
4. Security — bind mounts expose host filesystem paths and directory structure inside the container, which is an unnecessary risk for a database. Named volumes are opaque to the container.
5. Bind mounts are appropriate for development (mounting source code for live reload) but not for durable production data.

**Key takeaway:** Use named volumes for production databases — they are portable, lifecycle-managed, and not tied to host filesystem layout.

</details>

📖 **Theory:** [compare-volume-bind](./07_Volumes_and_Bind_Mounts/Theory.md#volumes-and-bind-mounts)


---

### Q45 · [Interview] · `explain-networking`

> **Explain how two containers on the same Docker network communicate. What DNS magic makes `ping postgres` work?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Docker creates a virtual network bridge on the host. Containers attached to the same bridge can reach each other by IP, and Docker's embedded DNS server resolves container names to their current IPs automatically.

**How to think through this:**
1. When you create a user-defined network (`docker network create mynet`), Docker creates a Linux bridge interface (e.g., `br-abc123`) and assigns a subnet (e.g., `172.18.0.0/16`).
2. Each container joining that network gets a virtual ethernet interface connected to the bridge and a private IP from the subnet.
3. Docker runs an embedded DNS server at `127.0.0.11` inside every container. When you `ping postgres`, the resolver in the container queries `127.0.0.11`, which looks up the current IP of the container named `postgres` and returns it.
4. This is why Docker Compose service names work as hostnames — Compose names each container after its service key and they all join the same project network.
5. The default bridge network (`docker0`) does NOT provide automatic DNS — only user-defined networks do. This is one key reason you should always create named networks.

**Key takeaway:** Docker's embedded DNS server resolves container names to IPs on user-defined networks, so containers can address each other by service name regardless of assigned IP.

</details>

📖 **Theory:** [explain-networking](./08_Networking/Theory.md#docker-networking)


---

### Q46 · [Interview] · `compare-compose-swarm`

> **Compare Docker Compose and Docker Swarm. When does Compose become insufficient?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Docker Compose orchestrates containers on a single host. Docker Swarm orchestrates services across a cluster of hosts. Compose becomes insufficient the moment you need more than one machine.

**How to think through this:**
1. Docker Compose reads a `compose.yaml`, creates networks and volumes, and starts containers — all on the local Docker daemon. It is designed for development and single-host deployments.
2. Docker Swarm uses a manager/worker topology. You `docker stack deploy` a Compose file to the swarm, and the manager schedules tasks across all worker nodes, handles node failures, and performs rolling updates.
3. Compose becomes insufficient when:
   - Your app requires more CPU/RAM than one host can provide.
   - You need high availability — if the single Compose host goes down, everything stops.
   - You need rolling zero-downtime deploys across multiple instances.
   - You need to scale individual services independently across nodes.
4. Both use the same YAML format (with some Swarm-specific keys like `deploy.replicas`), which makes the migration relatively low-friction.

**Key takeaway:** Compose is single-host coordination; Swarm adds multi-host scheduling, self-healing, and rolling updates — switch when you outgrow one machine.

</details>

📖 **Theory:** [compare-compose-swarm](./09_Docker_Compose/Theory.md#docker-compose)


---

### Q47 · [Interview] · `explain-multi-stage`

> **Explain multi-stage builds to someone who has never used them. Why does the final image not contain build tools?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A multi-stage build uses multiple FROM instructions in one Dockerfile. Each stage is a separate temporary image. You copy only the finished artifact from a build stage into a clean final stage — the build tools never make it into the image you ship.

**How to think through this:**
1. Imagine a factory assembly line. Stage 1 is the workshop — it has all the heavy machinery: compilers, test runners, build caches. Stage 2 is the shipping box — it is tiny and only contains the finished product.
2. In the Dockerfile, `FROM golang:1.22 AS builder` creates a stage with the full Go toolchain. You compile your binary there. Then `FROM alpine:3.19` starts a fresh, minimal stage. `COPY --from=builder /app/binary /app/binary` copies only the compiled binary.
3. Docker builds each stage in order but only the final stage becomes the image that is pushed and deployed. All the intermediate layers — GBs of compilers and build caches — are discarded.
4. The result: a Go binary that would have lived in a 800 MB builder image now ships in a 10 MB Alpine image. Less to pull, less attack surface, faster deploys.

**Key takeaway:** Multi-stage builds let you use heavyweight tools to build and then throw them away, shipping only the artifact in a minimal final image.

</details>

📖 **Theory:** [explain-multi-stage](./11_Multi_Stage_Builds/Theory.md#module-11--multi-stage-builds)


---

### Q48 · [Design] · `scenario-image-too-large`

> **A team's Docker image is 4GB and takes 8 minutes to build. Walk through how you'd diagnose and fix it.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Start with diagnosis before touching anything, then apply targeted fixes in order of impact.

**How to think through this:**
1. Diagnose with `docker history myimage:tag` — this shows each layer's size and the command that created it. Find the fat layers.
2. Also run `docker image inspect` and use `dive` (a CLI tool) to browse layers interactively and see which files are present in each.
3. Common causes and fixes:
   - Base image bloat: `ubuntu:latest` is ~80 MB; `ubuntu:22.04-slim` is ~30 MB; `scratch` or `distroless` for compiled languages is smaller still. Switch to the right base.
   - Build tools left in the final image: Add a multi-stage build. Compilers, headers, and test frameworks go in the builder stage only.
   - Package manager caches not cleaned: `apt-get install -y ... && rm -rf /var/lib/apt/lists/*` in the same RUN instruction.
   - Large files copied and then deleted in a later layer: the file still exists in the earlier layer. Fix by never copying it in the first place (`.dockerignore`) or doing the delete in the same `RUN` command.
   - Development dependencies: only install production deps in the final image (`pip install --no-dev`, `npm ci --omit=dev`).
4. Fix slow builds separately: order layers from least-to-most-frequently-changed, add `.dockerignore`, enable BuildKit cache mounts for package managers.

**Key takeaway:** Use `docker history` and `dive` to find fat layers, then apply multi-stage builds, minimal base images, and same-layer cleanup to shrink size.

</details>

📖 **Theory:** [scenario-image-too-large](./11_Multi_Stage_Builds/Theory.md#the-bloated-image-problem)


---

### Q49 · [Design] · `scenario-container-exit`

> **A container starts but immediately exits with code 0. How do you diagnose what happened? How is exit code 0 different from 1?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Exit code 0 means the main process completed successfully — the program ran to completion and exited cleanly. This is not a crash; it means the container did exactly what its process was told to do.

**How to think through this:**
1. Run `docker logs <container_id>` on the stopped container to see stdout/stderr from the process's lifetime.
2. Exit code 0 — the process exited normally. Common causes: the CMD is a script that runs once and finishes (a migration, a batch job), or the entrypoint printed help text and exited, or the CMD was something like `echo hello` rather than a long-running server.
3. Exit code 1 (or non-zero) — the process encountered an error. Check logs for the error message. Common causes: missing environment variable, port already bound, failed health check dependency.
4. Fix for "should have been a server": ensure the CMD starts a foreground process that does not return — e.g., `CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]`. Never use `service start` commands in CMD — they daemonize and return immediately, causing exit code 0.
5. Use `docker inspect <container_id>` to get the exact exit code and the command that was run.

**Key takeaway:** Exit code 0 means the process finished normally — check that CMD launches a foreground long-running process rather than a script that completes.

</details>

📖 **Theory:** [scenario-container-exit](./06_Containers_Lifecycle/Theory.md#rm-remove-the-container-automatically-when-it-exits)


---

### Q50 · [Design] · `scenario-volume-data-loss`

> **A developer ran `docker rm -f postgres_container` and lost their database. How would you prevent this in production?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
The data was lost because it was stored inside the container's writable layer, not in a persistent volume. The fix is to always externalize state.

**How to think through this:**
1. Root cause: if `docker run postgres` is used without a `-v` flag, Postgres writes to `/var/lib/postgresql/data` inside the container's own writable layer. `docker rm` destroys that layer.
2. Immediate fix: always mount a named volume:
   `docker run -v pgdata:/var/lib/postgresql/data postgres`
   Named volumes persist after `docker rm` and must be explicitly deleted with `docker volume rm pgdata`.
3. Production hardening:
   - Use Docker Compose or Swarm with a declared named volume in the YAML — makes the volume configuration explicit and version-controlled.
   - Never use `docker rm -f` on stateful containers without checking for volume mounts first.
   - Enable regular pg_dump backups to object storage (S3/GCS), independent of Docker.
   - Consider a managed database service (RDS, Cloud SQL) so the persistence layer is entirely outside Docker.
4. Recovery: if an anonymous volume was used (volume created automatically without a name), it may still exist under `docker volume ls` — unnamed volumes are not deleted by `docker rm` unless `docker rm -v` is used.

**Key takeaway:** Always mount named volumes for database containers — data inside a container's writable layer is destroyed the moment the container is removed.

</details>

📖 **Theory:** [scenario-volume-data-loss](./07_Volumes_and_Bind_Mounts/Theory.md#first-run-docker-copies-those-files-into-the-pgdata-volume)


---

### Q51 · [Design] · `scenario-network-isolation`

> **You have a 3-tier app: frontend, API, database. Design the Docker network topology so the database is not accessible from the internet.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Place services on separate networks, attaching each service only to the networks it legitimately needs to communicate on. The database gets no public exposure.

**How to think through this:**
1. Create two networks: `frontend-net` (frontend ↔ API) and `backend-net` (API ↔ database).
2. Frontend service: attached to `frontend-net` only. Exposes port 80/443 to the host via `-p 80:80`.
3. API service: attached to both `frontend-net` AND `backend-net` — it is the only bridge between the two tiers.
4. Database service: attached to `backend-net` only. No host port mapping (`-p`). It is entirely unreachable from the host network or internet; only the API container can address it.
5. In Docker Compose:
   ```yaml
   networks:
     frontend-net:
     backend-net:
   services:
     frontend:
       networks: [frontend-net]
       ports: ["80:80"]
     api:
       networks: [frontend-net, backend-net]
     db:
       networks: [backend-net]
   ```
6. Even if an attacker compromises the frontend container, they cannot reach the database — they would first need to pivot through the API container.

**Key takeaway:** Assign each service only the networks it needs and never publish the database port to the host — network segmentation is the first line of defense.

</details>

📖 **Theory:** [scenario-network-isolation](./08_Networking/Theory.md#docker-networking)


---

### Q52 · [Design] · `scenario-registry-auth`

> **In a CI/CD pipeline, you need to push to a private registry. How do you handle credentials securely without storing them in the Dockerfile or image?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Credentials belong in the CI system's secret store, injected as environment variables at runtime — never in the Dockerfile, source code, or image layers.

**How to think through this:**
1. Store registry credentials as encrypted secrets in your CI platform (GitHub Actions Secrets, GitLab CI Variables, Jenkins Credentials, AWS Secrets Manager). These are injected into the runner environment at job execution time.
2. Authenticate before push: `echo "$REGISTRY_PASSWORD" | docker login registry.example.com -u "$REGISTRY_USER" --password-stdin`. The `--password-stdin` flag avoids the password appearing in process lists.
3. Never use ARG or ENV in a Dockerfile for credentials — ARG values are visible in `docker history` and ENV values are baked into the image manifest.
4. For BuildKit secret mounts during build time (e.g., pulling private packages): `docker build --secret id=npmrc,src=$HOME/.npmrc .` and in the Dockerfile: `RUN --mount=type=secret,id=npmrc pip install ...`. The secret is available during the RUN step but never stored in any layer.
5. For AWS ECR specifically: use `aws ecr get-login-password` piped to `docker login` — the token is short-lived (12 hours) so even if leaked it expires quickly.
6. Rotate credentials regularly and scope them to push-only permissions.

**Key takeaway:** Inject credentials from the CI secret store at runtime using environment variables; use BuildKit secret mounts for build-time secrets so nothing sensitive lands in an image layer.

</details>

📖 **Theory:** [scenario-registry-auth](./10_Docker_Registry/Theory.md#2-authenticate-docker-to-your-ecr-registry)


---

### Q53 · [Interview] · `compare-add-copy`

> **What is the difference between ADD and COPY in a Dockerfile? When is ADD appropriate?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
COPY transfers files from the build context to the image, nothing more. ADD does the same but also auto-extracts tar archives and can fetch remote URLs. The Docker documentation recommends COPY unless you specifically need ADD's extra behavior.

**How to think through this:**
1. COPY is explicit and predictable — `COPY src/ /app/src/` copies the directory as-is. No surprises.
2. ADD with a tar file — `ADD app.tar.gz /app/` extracts the archive directly into `/app/` in one step. This is the one case where ADD is clearly useful — it saves a separate `RUN tar -xzf` command and keeps the layer count lower.
3. ADD with a URL — `ADD https://example.com/file.zip /tmp/` downloads a file at build time. This is generally discouraged: it breaks caching unpredictably (Docker cannot know if the remote file changed) and is better replaced with `RUN curl -o ...` where you control caching and error handling explicitly.
4. Security consideration: using ADD with URLs from untrusted sources is a risk — always verify checksums.
5. Best practice: use COPY for everything except extracting local tar archives, where ADD is genuinely convenient.

**Key takeaway:** Prefer COPY for clarity and predictability; use ADD only when you need its tar-extraction shortcut for a local archive.

</details>

📖 **Theory:** [compare-add-copy](./05_Dockerfile/Theory.md#copy-vs-add--putting-ingredients-in)


---

### Q54 · [Interview] · `compare-cmd-entrypoint`

> **What is the difference between CMD and ENTRYPOINT? What happens when both are present? Show an example.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
ENTRYPOINT defines the executable that always runs. CMD provides default arguments to that executable. When both are present, CMD is passed as arguments to ENTRYPOINT.

**How to think through this:**
1. ENTRYPOINT alone: `ENTRYPOINT ["python", "app.py"]` — the container always runs python. You cannot override this with `docker run myimage ls` (ls would be passed as an argument to python, not run as a command).
2. CMD alone: `CMD ["python", "app.py"]` — this is the default command, but it can be fully replaced at runtime: `docker run myimage bash` starts bash instead.
3. Both together — this is the most powerful and common production pattern:

```dockerfile
ENTRYPOINT ["python"]
CMD ["app.py"]
```

Running `docker run myimage` starts `python app.py`.
Running `docker run myimage other_script.py` starts `python other_script.py` — CMD is overridden but ENTRYPOINT is preserved.

4. This pattern is ideal for tools that always use the same binary but accept different arguments depending on environment or user input.
5. Always use JSON array (exec) form for both: `["python", "app.py"]`, not shell form `python app.py` — shell form wraps with `/bin/sh -c`, which means signals (like SIGTERM) are not forwarded to your process.

**Key takeaway:** ENTRYPOINT is the fixed executable; CMD is the swappable default argument — together they make a container that behaves like a configurable CLI tool.

</details>

📖 **Theory:** [compare-cmd-entrypoint](./05_Dockerfile/Theory.md#cmd-vs-entrypoint--what-happens-when-you-serve-the-dish)


---

### Q55 · [Design] · `scenario-secret-in-image`

> **A developer accidentally committed an AWS key into a Dockerfile RUN command and pushed the image to Docker Hub. What do you do?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Treat the key as fully compromised immediately. Revoke first, then clean up — in that order.

**How to think through this:**
1. Revoke the key now — go to AWS IAM, disable and delete the access key. Do this before anything else. Any time spent on cleanup before revocation is time the key is still live.
2. Check CloudTrail logs for unauthorized activity during the exposure window. Look for API calls from unexpected IPs or regions, new IAM users created, S3 data exfiltration, EC2 instances launched.
3. Delete the image from Docker Hub — but understand this is damage control, not a fix. Docker Hub may have been scraped by automated secret-scanning bots within minutes of the push. Treat the key as compromised regardless.
4. Remove the key from the Dockerfile. The git history also contains the Dockerfile with the key — rotate, don't try to scrub the history as the primary security action.
5. If the git repo is public, the Dockerfile commit is also a source of exposure. Use `git filter-repo` or BFG Repo Cleaner to rewrite history, then force-push. But again: the key is already rotated, so history cleanup is hygiene, not security.
6. Prevention: add pre-commit hooks (git-secrets, detect-secrets), use BuildKit `--mount=type=secret` for any credentials needed at build time, and enable GitHub's secret scanning alerts.

**Key takeaway:** Revoke first, investigate second, clean up third — a leaked key must be treated as fully compromised the moment it appears in a public image.

</details>

📖 **Theory:** [scenario-secret-in-image](./12_Docker_Security/Theory.md#bad-secret-baked-into-image-layer)


---

### Q56 · [Design] · `scenario-cicd-cache`

> **Your CI pipeline rebuilds the entire Docker image from scratch on every commit even though only the application code changed. How do you fix this?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
The cache is being invalidated too early — either by layer ordering, a missing cache source, or ephemeral runners discarding local cache. Fix by controlling layer order and providing an external cache.

**How to think through this:**
1. Diagnose — check the build output for `CACHED` vs non-cached layer messages. The first non-cached layer invalidates everything below it.
2. Layer ordering fix — the most common cause. If `COPY . .` appears before `RUN pip install -r requirements.txt`, then every code change invalidates the dependency install. Reorder:
   ```
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   ```
   Now dependency installs are cached until requirements.txt changes.
3. Ephemeral CI runners — cloud CI often spins up a fresh VM per job, so the local Docker layer cache is empty every run. Fix with registry-based cache:
   `docker buildx build --cache-from type=registry,ref=myrepo/myapp:cache --cache-to type=registry,ref=myrepo/myapp:cache,mode=max .`
   The cache layers are stored in the registry and pulled at the start of each build.
4. `.dockerignore` — ensure build context noise (test output, IDE files) is excluded to prevent spurious cache invalidation from irrelevant file changes.
5. BuildKit cache mounts — for package managers, use `--mount=type=cache` to persist pip/npm caches in a registry-backed or volume-backed location across runs.

**Key takeaway:** Fix layer ordering so stable dependencies come before application code, then add registry-based BuildKit cache so ephemeral CI runners can reuse layers across runs.

</details>

📖 **Theory:** [scenario-cicd-cache](./14_Docker_in_CICD/Theory.md#cache-strategy-registry-cache)


---

### Q57 · [Design] · `scenario-compose-override`

> **How do `docker-compose.override.yml` files work? Design a workflow that uses one config for development and another for production.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Docker Compose automatically merges `docker-compose.override.yml` on top of `docker-compose.yml` when you run `docker compose up` — no flags needed. For production, you explicitly specify which files to use.

**How to think through this:**
1. `docker-compose.yml` — the base file containing everything shared between environments: service names, network topology, volume declarations, image names. Keep it minimal and environment-agnostic.
2. `docker-compose.override.yml` — automatically loaded in development. Add dev-only config here: bind-mount source code for live reload, expose debug ports, set `DEBUG=true`, use a local SQLite instead of Postgres.
3. `docker-compose.prod.yml` — explicitly opt into for production: set restart policies (`restart: always`), resource limits, production environment variables, no source mounts, real Postgres.
4. Workflow:
   - Development: `docker compose up` — base + override merge automatically.
   - Production: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d` — base + prod file only, override is not loaded.
5. Never commit production secrets to any compose file — use environment variable substitution (`${DB_PASSWORD}`) and inject values from the host environment or a secrets manager.

**Key takeaway:** `docker-compose.override.yml` auto-merges for dev convenience; production uses explicit `-f` flags to combine only the base and production config files.

</details>

📖 **Theory:** [scenario-compose-override](./09_Docker_Compose/Theory.md#compose-overrides)


---

### Q58 · [Thinking] · `buildkit-cache-mounts`

> **What is a BuildKit cache mount (`--mount=type=cache`)? Write a Dockerfile snippet that uses one to speed up pip installs.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A BuildKit cache mount attaches a persistent directory to a `RUN` instruction that survives between builds but is never written into the image layer. It is ideal for package manager caches that would otherwise be re-downloaded on every build.

**How to think through this:**
1. Without a cache mount: every `pip install` downloads packages from PyPI. The downloaded `.whl` files are either baked into the layer (bloating the image) or deleted (losing the cache).
2. With `--mount=type=cache`: pip's cache directory is backed by a persistent store on the build host. On the first build, packages download. On subsequent builds, pip finds them in cache and skips the network.
3. The cache directory is not in the final image — it is managed separately by BuildKit. The image only contains the installed packages in the Python site-packages directory.

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "app.py"]
```

4. The `target` is pip's HTTP cache directory. BuildKit stores this between runs. `--no-cache-dir` is intentionally NOT used here — we want pip to write to and read from the mounted cache.
5. On a second build with no changes to `requirements.txt`, pip resolves all packages from the cache mount in milliseconds.

**Key takeaway:** `--mount=type=cache` gives package managers a persistent cache that speeds up rebuilds without bloating the image layer.

</details>

📖 **Theory:** [buildkit-cache-mounts](./16_BuildKit_and_Docker_Scout/Theory.md#buildkit-cache-mounts-keeping-cache-out-of-layers)


---

### Q59 · [Thinking] · `docker-contexts`

> **What is a Docker context? How do you use `docker context use` to deploy to a remote host?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A Docker context is a named configuration that tells the Docker CLI which Docker daemon to connect to. Switching contexts lets you run Docker commands against a remote host as easily as a local one.

**How to think through this:**
1. By default, Docker connects to the local daemon via a Unix socket (`unix:///var/run/docker.sock`). This is the `default` context.
2. You can create a context pointing to a remote host over SSH:
   `docker context create remote-prod --docker "host=ssh://user@prod.example.com"`
   Docker uses your existing SSH key and config — no extra daemon configuration needed on the remote host.
3. Switch to it: `docker context use remote-prod`
4. Now every Docker command runs against the remote daemon: `docker ps`, `docker service ls`, `docker stack deploy` all operate on the production host.
5. Switch back: `docker context use default`
6. List contexts: `docker context ls` — shows the endpoint and TLS info for each.
7. This is particularly useful for Swarm deployments: `docker -c remote-prod stack deploy -c docker-compose.prod.yml myapp` deploys the stack to the remote swarm without SSH-ing manually.

**Key takeaway:** Docker contexts are named daemon endpoints — `docker context use <name>` redirects all CLI commands to a different (potentially remote) Docker host transparently.

</details>

📖 **Theory:** [docker-contexts](./16_BuildKit_and_Docker_Scout/Theory.md#module-16--buildkit-and-docker-scout)


---

### Q60 · [Thinking] · `container-resource-limits`

> **What do `--memory`, `--cpus`, and `--pids-limit` do in `docker run`? What happens when a container exceeds its memory limit?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
These flags apply Linux cgroup constraints to a container, preventing it from consuming unbounded host resources.

**How to think through this:**
1. `--memory 512m` — sets a hard limit on the container's RAM usage via the cgroup memory controller. When the container tries to allocate beyond this limit, the kernel OOM killer terminates the container's process. Docker reports this as exit code 137 (128 + SIGKILL signal 9).
2. `--memory-swap` — by default, when you set `--memory`, Docker also allows the same amount of swap. Use `--memory-swap` equal to `--memory` to disable swap entirely.
3. `--cpus 1.5` — limits the container to at most 1.5 CPU cores worth of CPU time via the cgroup CPU quota. The container can burst up to 1.5 cores but cannot monopolize all host CPUs. This does not pin to specific cores — use `--cpuset-cpus` for that.
4. `--pids-limit 100` — limits the number of processes/threads the container can create. This prevents fork bomb attacks, where a process recursively spawns children until the host is exhausted.
5. Without limits: a runaway container (memory leak, infinite loop, fork bomb) can starve all other containers and services on the host.

**Key takeaway:** Resource limits enforce isolation via cgroups — a container exceeding its memory limit is OOM-killed (exit 137), not throttled, so set limits with headroom.

</details>

📖 **Theory:** [container-resource-limits](./06_Containers_Lifecycle/Theory.md#resource-limits)


---

### Q61 · [Thinking] · `dockerfile-healthcheck`

> **What does the HEALTHCHECK instruction do in a Dockerfile? How does Docker use the result? Write an example for an HTTP service.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
HEALTHCHECK defines a command Docker runs periodically inside the container to determine whether the application is functioning correctly, not just whether the process is alive.

**How to think through this:**
1. Docker polls the healthcheck command on a configurable interval. If the command exits with code 0, the container is `healthy`. If it exits non-zero three times in a row (configurable retries), the container is marked `unhealthy`.
2. Without HEALTHCHECK, a container is either `running` or `stopped` — there is no way for Docker to know that the web server inside is deadlocked and returning 500s to every request.
3. Docker Swarm uses health status: an `unhealthy` task is replaced automatically. Kubernetes has its own liveness/readiness probes and ignores Docker's HEALTHCHECK.
4. Example for an HTTP service:

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1
```

- `--interval=30s` — check every 30 seconds.
- `--timeout=5s` — fail the check if curl doesn't respond within 5 seconds.
- `--start-period=10s` — don't count failures during the first 10 seconds (app startup grace period).
- `--retries=3` — mark unhealthy only after 3 consecutive failures.

5. Check health status with `docker inspect --format='{{.State.Health.Status}}' container_name`.

**Key takeaway:** HEALTHCHECK gives Docker application-level observability — a process can be running but unhealthy, and orchestrators use this status to replace failed replicas.

</details>

📖 **Theory:** [dockerfile-healthcheck](./05_Dockerfile/Theory.md#dockerfile)


---

### Q62 · [Thinking] · `docker-compose-depends-on`

> **What does `depends_on` in docker-compose.yml guarantee? What doesn't it guarantee about service readiness?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
`depends_on` guarantees start order — that the dependency container is started before the dependent one. It does not guarantee that the application inside the dependency is ready to accept connections.

**How to think through this:**
1. What it does: `depends_on: [db]` tells Compose to start the `db` container before starting `api`. The API container will not be created until the db container exists and has started.
2. What it does not do: "started" means the container process launched. Postgres, for example, takes several seconds after process start before it is ready to accept TCP connections. Your API may crash-loop with "connection refused" during this window.
3. This is sometimes called the "started vs ready" problem — a container can be running but not ready.
4. Fix with `condition: service_healthy` — requires the dependency to have a passing HEALTHCHECK before the dependent service starts:
   ```yaml
   depends_on:
     db:
       condition: service_healthy
   ```
   This requires a HEALTHCHECK defined on the `db` service.
5. Alternatively, build retry logic into your application startup code — try to connect, back off, retry. This is more resilient than relying purely on orchestration ordering.

**Key takeaway:** `depends_on` controls start order but not application readiness — use `condition: service_healthy` with a HEALTHCHECK, or build retry logic into the app.

</details>

📖 **Theory:** [docker-compose-depends-on](./09_Docker_Compose/Theory.md#docker-compose)


---

### Q63 · [Thinking] · `image-garbage-collection`

> **What are dangling images? What is the difference between `docker image prune` and `docker system prune`?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Dangling images are image layers that are no longer referenced by any tag or by any other image — they are orphaned build artifacts. They accumulate over time and consume significant disk space.

**How to think through this:**
1. Dangling images are created when you rebuild an image with the same tag — the old layers lose their tag reference but remain on disk. They appear as `<none>:<none>` in `docker images`.
2. `docker image prune` — removes only dangling images (untagged, unreferenced layers). Safe to run regularly. Add `-a` to also remove all images not currently used by any container — more aggressive.
3. `docker system prune` — removes dangling images PLUS stopped containers, unused networks, and dangling build cache. It is a broader cleanup across all Docker resources. Add `-a` to also remove all unused images (not just dangling), and `--volumes` to also remove unused volumes (dangerous if you have important data in named volumes — it will prompt for confirmation).
4. The build cache is often the largest consumer of disk space. `docker builder prune` removes it specifically.
5. In production: automate `docker system prune -f` (without `-a` or `--volumes`) as a cron job or CI step to prevent disk exhaustion on build nodes.

**Key takeaway:** Dangling images are orphaned `<none>:<none>` layers — `docker image prune` cleans them; `docker system prune` additionally cleans containers, networks, and build cache.

</details>

📖 **Theory:** [image-garbage-collection](./04_Images_and_Layers/Theory.md#images-and-layers)


---

### Q64 · [Thinking] · `container-logging`

> **What logging drivers does Docker support? How do you configure a container to send logs to a remote syslog server?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Docker supports pluggable logging drivers that control where container stdout/stderr is routed. The default is `json-file`; production systems often use `syslog`, `fluentd`, `awslogs`, or `splunk`.

**How to think through this:**
1. Default driver (`json-file`) — writes logs as JSON to `/var/lib/docker/containers/<id>/<id>-json.log`. Works with `docker logs`. Grows unboundedly without log rotation options (`--log-opt max-size=10m --log-opt max-file=3`).
2. Common logging drivers:
   - `syslog` — sends to a local or remote syslog daemon (RFC 5424).
   - `journald` — sends to systemd journal on the host.
   - `fluentd` — sends to a Fluentd or Fluent Bit aggregator.
   - `awslogs` — sends directly to AWS CloudWatch Logs.
   - `splunk` — sends to Splunk HTTP Event Collector.
   - `none` — discards all logs (useful for very high-throughput containers where logs are handled by a sidecar).
3. Configuring syslog for a single container:
   ```
   docker run \
     --log-driver syslog \
     --log-opt syslog-address=tcp://logs.example.com:514 \
     --log-opt syslog-facility=daemon \
     --log-opt tag="myapp/{{.Name}}" \
     myapp:latest
   ```
4. Set the default for all containers in `/etc/docker/daemon.json`:
   ```json
   { "log-driver": "syslog", "log-opts": { "syslog-address": "tcp://logs.example.com:514" } }
   ```
5. Non-blocking mode: add `--log-opt mode=non-blocking` to prevent a slow log drain from blocking the application process.

**Key takeaway:** Docker's logging driver is pluggable — configure `syslog` with `--log-driver syslog` and `--log-opt syslog-address` to forward container logs to a remote aggregator.

</details>

📖 **Theory:** [container-logging](./06_Containers_Lifecycle/Theory.md#container-lifecycle)


---

### Q65 · [Critical] · `dockerfile-user`

> **Why should a Dockerfile include a USER instruction before CMD? What risk does running as UID 0 create?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
By default, processes inside a Docker container run as root (UID 0). If a vulnerability in your application allows an attacker to break out of the container, they land on the host as root — with full system access.

**How to think through this:**
1. Docker's default user is root. Unless the Dockerfile explicitly sets a USER, your web server, API, or worker runs as UID 0 inside the container.
2. Container breakout vulnerabilities — while rare, they do exist (kernel vulnerabilities, container runtime CVEs). When one is exploited in a root-running container, the attacker gains root on the host, potentially compromising every workload on the machine.
3. A non-root user dramatically limits the blast radius: the attacker lands as an unprivileged UID with no ability to write to `/etc`, install software, or access other users' data on the host.
4. Correct pattern:
   ```dockerfile
   FROM python:3.12-slim

   RUN groupadd -r appuser && useradd -r -g appuser appuser

   WORKDIR /app
   COPY --chown=appuser:appuser . .
   RUN pip install -r requirements.txt

   USER appuser
   CMD ["python", "app.py"]
   ```
5. Place USER after all install steps that require root (apt, pip with system packages) but before CMD.
6. Many minimal base images (distroless, Chainguard) default to a non-root user, which is one reason to prefer them.

**Key takeaway:** Running containers as root means a container escape = host root compromise — always add a non-root USER instruction before CMD to limit the blast radius of any vulnerability.

</details>

📖 **Theory:** [dockerfile-user](./12_Docker_Security/Theory.md#non-root-users-the-simplest-win)


---

### Q66 · [Critical] · `docker-compose-volumes`

> **What is the difference between a top-level named volume and an anonymous volume in docker-compose.yml? Which persists after `docker-compose down`?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
A named volume is declared in the top-level `volumes:` section and given an explicit name. An anonymous volume is created inline without a name. Named volumes persist after `docker compose down`; anonymous volumes do not.

**How to think through this:**
1. Named volume — declared at the top level and referenced by name in the service:
   ```yaml
   volumes:
     pgdata:

   services:
     db:
       image: postgres:16
       volumes:
         - pgdata:/var/lib/postgresql/data
   ```
   Docker creates a volume named `<project>_pgdata`. Running `docker compose down` stops and removes containers and networks, but the volume remains. `docker volume ls` will show it. You must run `docker compose down -v` to delete it.

2. Anonymous volume — declared inline with only a container path:
   ```yaml
   services:
     db:
       image: postgres:16
       volumes:
         - /var/lib/postgresql/data
   ```
   Docker creates a volume with a random hash name. It is not tracked by the compose project. `docker compose down` removes it without warning. This is effectively ephemeral and should never be used for data you care about.

3. The `-v` flag: `docker compose down -v` removes ALL volumes declared in the compose file — both named and anonymous. Use with caution in production.

4. External volumes — declared with `external: true` — reference a pre-existing volume that Compose will never create or destroy. Useful for sharing volumes across projects or protecting critical data from Compose lifecycle commands.

**Key takeaway:** Named top-level volumes survive `docker compose down` and must be explicitly deleted with `-v`; anonymous volumes are destroyed on container removal and should never hold production data.

</details>

📖 **Theory:** [docker-compose-volumes](./07_Volumes_and_Bind_Mounts/Theory.md#volumes-and-bind-mounts)


---

## 🟠 Tier 3 — Advanced

### Q67 · [Thinking] · `buildkit`

> **What is BuildKit's parallel build execution? How does it differ from the classic Docker builder? What is `--progress=plain`?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
BuildKit is the next-generation Docker build engine, enabled by default since Docker 23. The classic builder executes Dockerfile instructions sequentially — one step, then the next, in order. BuildKit treats the Dockerfile as a dependency graph and can execute independent stages in parallel.

**How to think through this:**
1. Classic builder: linear execution, each `RUN` waits for the previous, even if they are unrelated.
2. BuildKit: parses stages and their `COPY --from` references, builds a DAG, and parallelizes branches that don't depend on each other. In a multi-stage build with a `test` stage and a `production` stage that are independent, both run simultaneously.
3. `--progress=plain` disables the interactive TUI log and prints each build step as raw text, line by line — useful in CI where the interactive output is unreadable or breaks log parsers.

Additional BuildKit features: inline cache (`--cache-from`), secrets mounting (`RUN --mount=type=secret`), SSH agent forwarding (`RUN --mount=type=ssh`), and better layer cache reuse.

**Key takeaway:** BuildKit parallelizes independent build stages via a dependency graph; `--progress=plain` gives human-readable CI logs.

</details>

📖 **Theory:** [buildkit](./16_BuildKit_and_Docker_Scout/Theory.md#module-16--buildkit-and-docker-scout)


---

### Q68 · [Thinking] · `docker-scout`

> **Walk through using Docker Scout to audit an image: what commands do you run, what does the output tell you, and how do you act on CVEs?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Docker Scout is Docker's built-in vulnerability and policy analysis tool, available via `docker scout` subcommands.

**How to think through this:**
1. Run a quick CVE summary: `docker scout quickview myimage:latest` — shows a breakdown of critical, high, medium, and low CVEs, and which packages introduce them.
2. Get a detailed CVE list: `docker scout cves myimage:latest` — lists each CVE with its ID, severity, affected package, fixed version (if available), and a description.
3. Compare with a base recommendation: `docker scout recommendations myimage:latest` — suggests a base image update that would reduce the CVE count.
4. Act on findings: if a CVE has a fix, update the affected package in the Dockerfile (`RUN apt-get install -y libssl1.1=<fixed-version>`), or update the base image tag to one that includes the patch.
5. For ongoing monitoring, `docker scout watch` integrates with Docker Hub to alert when new CVEs affect an already-pushed image.

Output columns: CVE ID, CVSS score, package name, installed version, fixed version. A "fixed in" column being empty means you must wait for an upstream patch or switch base images.

**Key takeaway:** `docker scout cves` gives the full CVE list per package; act on results by pinning fixed versions or updating the base image.

</details>

📖 **Theory:** [docker-scout](./16_BuildKit_and_Docker_Scout/Theory.md#module-16--buildkit-and-docker-scout)


---

### Q69 · [Thinking] · `docker-init`

> **What does `docker init` generate for a Python project? How does it choose the Dockerfile template?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
`docker init` is an interactive CLI wizard (introduced in Docker Desktop 4.18) that scaffolds Docker-related files for a project. It detects project type and generates a `Dockerfile`, `docker-compose.yml`, and `.dockerignore`.

**How to think through this:**
1. Detection: `docker init` scans the current directory for language indicators — `requirements.txt`, `pyproject.toml`, or `setup.py` signals Python.
2. It interactively prompts for: Python version, application entry point (e.g., `app.py`), and port.
3. The generated `Dockerfile` for Python uses a multi-stage build: a `base` stage with the official `python:<version>-slim` image, a `deps` stage that installs from `requirements.txt` into a virtual environment, and a final stage that copies only the venv and app code — minimizing image size.
4. The `.dockerignore` excludes `__pycache__`, `.venv`, `.git`, and similar noise.
5. The `docker-compose.yml` wires up a service with the correct build context and port mapping.

The template choice is purely heuristic — it matches file patterns to known project types. If it detects both `package.json` and `requirements.txt`, it asks you to confirm the primary language.

**Key takeaway:** `docker init` auto-detects language from project files and generates a multi-stage, production-ready Dockerfile scaffold.

</details>

📖 **Theory:** [docker-init](./17_Docker_Init_and_Debug/Theory.md#module-17--docker-init-and-docker-debug)


---

### Q70 · [Thinking] · `docker-debug`

> **What makes `docker debug` different from `docker exec`? Can you use it on a distroless image?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
`docker debug` (Docker Desktop 4.27+) is a debugging tool that attaches a full shell environment to a running container — or even to a stopped container's filesystem — without requiring the container image itself to have any shell or debugging tools.

**How to think through this:**
1. `docker exec` enters the container's existing filesystem and process namespace. If the image is distroless (no shell, no package manager), `docker exec /bin/sh` fails immediately because `/bin/sh` doesn't exist.
2. `docker debug` works differently: it injects a sidecar debug image (a minimal toolbox with `bash`, `curl`, `strace`, `vim`, etc.) into the container's namespace. You get a shell that shares the target container's PID, network, and mount namespaces — without modifying the original image.
3. This means you can inspect files, run `curl localhost:8080`, trace processes with `strace`, and check environment variables inside a distroless or scratch-based container.
4. It also works on stopped containers by mounting the container's filesystem: `docker debug --image=<toolbox> <container-id>`.

The practical impact: distroless images are now debuggable without adding a debug build stage or bloating the production image.

**Key takeaway:** `docker debug` injects an external toolbox into the container's namespaces, making it possible to debug distroless images that have no shell.

</details>

📖 **Theory:** [docker-debug](./17_Docker_Init_and_Debug/Theory.md#module-17--docker-init-and-docker-debug)


---

### Q71 · [Thinking] · `container-runtime`

> **What is a container runtime? What is the relationship between Docker, containerd, runc, and the OCI spec?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Think of it as a layered stack, like a restaurant: the customer (you) talks to the waiter (Docker CLI), who talks to the kitchen manager (containerd), who tells the line cook (runc) to plate the dish (container). Each layer has a clear role.

**How to think through this:**
1. **OCI spec**: The Open Container Initiative defines two standards — the Image Spec (how images are structured) and the Runtime Spec (how a container is started from a bundle). It's the contract every layer agrees on.
2. **runc**: The low-level OCI runtime. It takes a root filesystem and a config JSON, calls Linux kernel APIs (`clone`, `unshare`, `pivot_root`, cgroups), and starts the container process. It does one thing: spawn a container.
3. **containerd**: A higher-level container runtime daemon. It manages the full container lifecycle — pulling images, managing snapshots, creating/starting/stopping containers — by calling runc under the hood. Kubernetes uses containerd directly via the CRI interface.
4. **Docker**: The user-facing layer. `docker run` calls the Docker daemon, which calls containerd, which calls runc. Docker adds developer UX: build, push, Compose, networking abstractions.

Since Docker 20.10, Docker ships containerd as the default image store. Removing Docker from a Kubernetes node doesn't break containers — Kubernetes was already talking to containerd directly.

**Key takeaway:** Docker → containerd → runc is the call chain; runc executes the OCI spec at the kernel level, containerd manages lifecycle, Docker provides developer UX.

</details>

📖 **Theory:** [container-runtime](./02_Docker_Architecture/Theory.md#3-containerd)


---

### Q72 · [Thinking] · `image-manifest`

> **What is a Docker image manifest? What is a multi-arch manifest list? How does `docker buildx` create one?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
An image manifest is a JSON document that describes an image: the config (environment variables, entrypoint, labels) and the list of layer blobs (their digest and size). When you `docker pull`, the registry serves the manifest first, then your client fetches only the layers you don't already have.

**How to think through this:**
1. Single-arch manifest: `{ "schemaVersion": 2, "config": {...}, "layers": [{...}, {...}] }`. Each layer is a compressed tar identified by its SHA256 digest.
2. Multi-arch manifest list (OCI Image Index): a manifest that contains a list of other manifests, each annotated with a platform (`os: linux`, `architecture: amd64` or `arm64`). When you `docker pull ubuntu`, the Docker client sends its platform to the registry, which returns the correct variant.
3. `docker buildx build --platform linux/amd64,linux/arm64 --push -t myrepo/myimage:latest .` — buildx uses QEMU emulation or remote builders to compile for each target platform, then creates a manifest list pointing to all the per-platform manifests and pushes the whole thing in one operation.
4. You can inspect the result: `docker buildx imagetools inspect myrepo/myimage:latest` shows the manifest list and all platform entries.

**Key takeaway:** A manifest list is an index of per-platform manifests; `docker buildx` builds all variants and stitches them into a single multi-arch manifest list.

</details>

📖 **Theory:** [image-manifest](./04_Images_and_Layers/Theory.md#images-and-layers)


---

### Q73 · [Thinking] · `docker-networking-advanced`

> **What is the difference between user-defined bridge networks and the default bridge? Why does Docker recommend user-defined bridges?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
The default `bridge` network (`docker0`) is created automatically when Docker starts. Every container without a `--network` flag joins it. User-defined bridge networks are created explicitly with `docker network create`.

**How to think through this:**
1. **DNS resolution**: On the default bridge, containers can only address each other by IP. On a user-defined bridge, Docker runs an embedded DNS server so containers resolve each other by container name or service name. `curl http://db:5432` just works on a user-defined network; on the default bridge, you'd need the IP or `--link` (deprecated).
2. **Isolation**: Containers on the default bridge can communicate with all other containers on that network by default. User-defined bridges are isolated from each other — a container on `frontend-net` cannot reach a container on `backend-net` unless explicitly connected to both.
3. **On-the-fly network membership**: A running container can be connected to or disconnected from a user-defined bridge without restarting it (`docker network connect`). The default bridge doesn't support this.
4. **Legacy `--link`**: `--link` was the old workaround for DNS on the default bridge. It's deprecated; user-defined bridges replace it cleanly.

Docker Compose always creates a user-defined bridge per project, which is why service names resolve automatically.

**Key takeaway:** User-defined bridges provide automatic DNS resolution by container name and network-level isolation; the default bridge offers neither.

</details>

📖 **Theory:** [docker-networking-advanced](./08_Networking/Theory.md#docker-networking)


---

### Q74 · [Thinking] · `volume-drivers`

> **What are Docker volume drivers? Give an example of using a volume driver for cloud storage (e.g., AWS EFS).**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
By default, Docker volumes are stored on the local host filesystem. Volume drivers are plugins that replace the local storage backend with an external system — NFS, cloud object storage, or distributed filesystems.

**How to think through this:**
1. A volume driver is a Docker plugin that implements the Volume Plugin API. When Docker needs to mount a volume, it calls the plugin, which handles the actual mount operation.
2. For AWS EFS (Elastic File System), the `amazon/amazon-ecs-volume-plugin` or the `rexray/efs` plugin can be used. EFS is an NFS-backed managed filesystem that multiple containers across multiple hosts can mount simultaneously — enabling shared persistent storage in multi-host deployments.
3. Example workflow:
   - Install the driver: `docker plugin install rexray/efs EFS_REGION=us-east-1`
   - Create a volume backed by EFS: `docker volume create --driver rexray/efs --name mydata`
   - Run a container: `docker run -v mydata:/app/data myimage`
4. The practical value: in a Docker Swarm cluster, two containers on different nodes can share the same EFS-backed volume, which is impossible with the default local driver.

Other common drivers: `local` (default), `nfs` (manual NFS mount config), `vieux/sshfs` (SSH-backed storage).

**Key takeaway:** Volume drivers plug in external storage backends; EFS driver allows multiple containers across hosts to share a persistent volume via AWS managed NFS.

</details>

📖 **Theory:** [volume-drivers](./07_Volumes_and_Bind_Mounts/Theory.md#volume-drivers-beyond-local-storage)


---

### Q75 · [Thinking] · `docker-compose-profiles`

> **What are Docker Compose profiles? How do you use them to conditionally start services (e.g., only start monitoring in production)?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Compose profiles let you group services and activate them selectively. Services without a profile are always started; services with a profile are only started when that profile is explicitly activated.

**How to think through this:**
1. In `docker-compose.yml`, add a `profiles` key to any service you want to make optional:
```yaml
services:
  web:
    image: myapp          # no profile — always starts

  prometheus:
    image: prom/prometheus
    profiles: ["monitoring"]

  grafana:
    image: grafana/grafana
    profiles: ["monitoring"]
```
2. Running `docker compose up` starts only `web`. Running `docker compose --profile monitoring up` starts `web`, `prometheus`, and `grafana`.
3. You can activate multiple profiles: `docker compose --profile monitoring --profile debug up`.
4. Environment variable shorthand: set `COMPOSE_PROFILES=monitoring` and `docker compose up` will activate it automatically — useful in CI or production shell environments.
5. A service can belong to multiple profiles: `profiles: ["monitoring", "debug"]`.

Common use cases: monitoring stacks, mock services for local dev, database admin UIs, debug sidecars.

**Key takeaway:** Profiles tag services as opt-in; `--profile <name>` activates them at runtime without maintaining separate Compose files.

</details>

📖 **Theory:** [docker-compose-profiles](./09_Docker_Compose/Theory.md#docker-compose)


---

## 🔵 Tier 4 — Interview / Scenario

### Q76 · [Interview] · `explain-layers-caching`

> **Explain Docker layer caching to an interviewer. Why does the order of Dockerfile instructions matter for cache efficiency?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Docker builds images as a stack of immutable layers. Each instruction in a Dockerfile (`RUN`, `COPY`, `ADD`) produces a new layer. When you rebuild, Docker checks each instruction against its cache: if the instruction and its inputs haven't changed, it reuses the cached layer and skips re-execution. The moment any layer is invalidated, all subsequent layers must be rebuilt.

**How to think through this:**
1. Cache keys: for `RUN`, the key is the instruction string. For `COPY`, the key includes the file contents (checksums). If a copied file changes, that layer and everything after it is invalidated.
2. The ordering implication: put instructions that change rarely at the top, and instructions that change often near the bottom. The classic mistake: `COPY . /app` before `RUN pip install -r requirements.txt`. Any change to any source file invalidates the pip install, even if `requirements.txt` didn't change.
3. The correct pattern:
   ```
   COPY requirements.txt .      # only changes when deps change
   RUN pip install -r requirements.txt
   COPY . /app                  # changes with every code edit — after the slow step
   ```
4. Analogy: it's like building a wall with wet cement layers. If you disturb a lower layer before it sets, you have to redo everything above it. Put the slow-drying layers (dependency installs) below the fast-changing ones (source code).

**Key takeaway:** Cache invalidation cascades downward — always order Dockerfile instructions from least-changed to most-changed to maximize cache hits.

</details>

📖 **Theory:** [explain-layers-caching](./04_Images_and_Layers/Theory.md#images-and-layers)


---

### Q77 · [Interview] · `compare-entrypoint-cmd`

> **Deep dive: explain CMD vs ENTRYPOINT with shell form vs exec form. What is PID 1 and why does it matter for signal handling?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
`ENTRYPOINT` defines the fixed executable for the container. `CMD` provides default arguments to it — or is the full command if no `ENTRYPOINT` is set. The form (shell vs exec) determines how the process runs and whether it receives OS signals.

**How to think through this:**
1. **Exec form** (`["executable", "arg1"]`): Docker runs the process directly via `execve`. The process becomes PID 1 in the container. It receives signals (SIGTERM, SIGINT) from `docker stop` directly.
2. **Shell form** (`executable arg1`): Docker runs the process as `sh -c "executable arg1"`. The shell becomes PID 1. When `docker stop` sends SIGTERM, the shell receives it — but by default, shells do not forward signals to child processes. Your app never gets SIGTERM, so Docker waits 10 seconds and sends SIGKILL (ungraceful shutdown).
3. **PID 1 responsibility**: In Linux, PID 1 is special. It must reap zombie child processes (children that exited but whose exit status hasn't been collected). A shell or poorly-written app as PID 1 may not do this, leading to zombie accumulation. Tools like `tini` solve this: `ENTRYPOINT ["/tini", "--", "myapp"]`.
4. **Override rules**: `docker run --entrypoint /bin/sh myimage` overrides `ENTRYPOINT`. Arguments after the image name in `docker run` override `CMD`.
5. Best practice: use exec form for both, set `ENTRYPOINT` to the app binary, use `CMD` for default flags.

**Key takeaway:** Always use exec form so your process is PID 1 and receives signals directly; shell form silently breaks graceful shutdown.

</details>

📖 **Theory:** [compare-entrypoint-cmd](./05_Dockerfile/Theory.md#cmd-vs-entrypoint--what-happens-when-you-serve-the-dish)


---

### Q78 · [Interview] · `explain-compose-networking`

> **Explain how Docker Compose networking works. Why does a service name resolve to a container's IP?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
When Docker Compose starts a project, it automatically creates a user-defined bridge network named `<project>_default`. Every service joins this network, and Docker's embedded DNS server handles name resolution within it.

**How to think through this:**
1. Docker runs an internal DNS resolver at `127.0.0.11` inside every container connected to a user-defined network.
2. When container `web` does a DNS lookup for `db`, the query goes to `127.0.0.11`. Docker's DNS server looks up the service name `db` in its internal records, finds the current IP of the `db` container, and returns it.
3. The DNS record is automatically created and updated when containers start or restart (which may change their IP). This is why hardcoding IPs breaks Compose apps — the name always works, the IP may not.
4. Services on different Compose-defined networks cannot reach each other by default. If you need cross-network communication (e.g., a shared database), you explicitly attach the service to both networks using the `networks` key.
5. The project name (derived from the directory name or `COMPOSE_PROJECT_NAME`) namespaces everything — network, volumes, container names — allowing multiple Compose projects to run on the same host without collision.

**Key takeaway:** Compose creates a user-defined bridge network per project; Docker's embedded DNS at `127.0.0.11` resolves service names to current container IPs automatically.

</details>

📖 **Theory:** [explain-compose-networking](./08_Networking/Theory.md#docker-networking)


---

### Q79 · [Interview] · `compare-volume-types`

> **Compare named volumes, bind mounts, and tmpfs mounts. When would you choose each in production?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Think of three types of storage lockers: a managed locker Docker owns (named volume), your own locker you bring in (bind mount), and a locker that dissolves when you leave (tmpfs).

**How to think through this:**
1. **Named volumes**: Docker manages the storage location (`/var/lib/docker/volumes/`). The volume persists independently of the container lifecycle. You reference it by name, not by path. Portable across environments. Best for: database data files, persistent app state in production. Supports volume drivers for cloud storage backends.
2. **Bind mounts**: You specify an exact host path that is mounted into the container. The host directory must exist. The container sees the host filesystem directly — changes in the container affect the host immediately. Best for: local development (hot reload of source code), mounting config files from a known host path (e.g., `/etc/myapp/config.yaml`). Avoid in production: host path dependency makes it non-portable and a security risk (a container escape could modify host files).
3. **tmpfs mounts**: Stored in host RAM only, never written to disk. Destroyed when the container stops. Best for: sensitive data that must never touch disk (tokens, session keys), high-speed scratch space (sorting large datasets), temporary caches.

Production rule of thumb: named volumes for persistence, tmpfs for secrets and ephemeral scratch, bind mounts for config injection only.

**Key takeaway:** Named volumes for durable data, bind mounts for dev/config injection, tmpfs for in-memory-only sensitive or ephemeral data.

</details>

📖 **Theory:** [compare-volume-types](./07_Volumes_and_Bind_Mounts/Theory.md#volumes-and-bind-mounts)


---

### Q80 · [Interview] · `explain-security-model`

> **Explain Docker's container isolation model. What kernel features make it work: namespaces, cgroups, capabilities?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Docker containers are not VMs — they share the host kernel. Isolation is enforced by three Linux kernel mechanisms working together: namespaces limit what a process can see, cgroups limit what it can consume, and capabilities limit what privileged operations it can perform.

**How to think through this:**
1. **Namespaces** — create isolated views of system resources:
   - `pid`: the container has its own PID space; its PID 1 is not the host's PID 1.
   - `net`: the container has its own network interfaces, routing table, and ports.
   - `mnt`: the container sees its own filesystem tree (via `pivot_root`).
   - `uts`: the container can have its own hostname.
   - `ipc`: isolated shared memory.
   - `user`: (optional) map container UID 0 to a non-root host UID.
2. **cgroups** (control groups) — enforce resource limits: CPU shares, memory limits, disk I/O throttling. Without cgroups, a container could consume 100% of host CPU/RAM.
3. **Capabilities** — Linux root is not binary; it is divided into ~40 capabilities (e.g., `CAP_NET_ADMIN`, `CAP_SYS_PTRACE`). Docker drops most capabilities by default, so even root inside the container can't do things like load kernel modules (`CAP_SYS_MODULE`) or modify iptables on the host.
4. Additional layers: seccomp profiles (syscall filtering — Docker's default profile blocks ~44 dangerous syscalls), AppArmor/SELinux for mandatory access control.

**Key takeaway:** Namespaces isolate visibility, cgroups enforce resource limits, capabilities restrict privileged syscalls — together they create a sandboxed process, not a true VM.

</details>

📖 **Theory:** [explain-security-model](./12_Docker_Security/Theory.md#module-12--docker-security)


---

### Q81 · [Design] · `scenario-production-architecture`

> **Design a production Docker deployment for a stateful application (web + DB + cache). What decisions do you make for volumes, networking, and restart policies?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**How to think through this:**
1. **Networking**: Create two user-defined bridge networks — `frontend` (web-facing) and `backend` (internal). The web service joins both. The DB and cache join only `backend`. This means the DB is unreachable from outside — defense in depth.
2. **Volumes**:
   - DB (PostgreSQL): named volume `postgres_data` mounted at `/var/lib/postgresql/data`. Named over bind mount: portable, Docker manages it, works with volume drivers for cloud backup.
   - Cache (Redis): if Redis is used as a cache only (not for session persistence), no volume needed. If used as a persistent store (AOF/RDB), named volume `redis_data`.
   - Web: no persistent volume for the app itself; config injected via environment or bind-mounted secret file.
3. **Restart policies**:
   - `restart: unless-stopped` for all services in Docker standalone.
   - In Swarm: `restart_policy: condition: on-failure, max_attempts: 3, delay: 5s` to avoid infinite restart loops on misconfiguration.
4. **Additional production decisions**: healthchecks on DB and cache with `condition: service_healthy` in `depends_on`. Resource limits (`mem_limit`, `cpus`) on all services. No `latest` tags — pin exact versions. Secrets via Docker secrets or environment variable injection from a secrets manager, not hardcoded in the Compose file.

**Key takeaway:** Isolate services on separate networks by trust zone, use named volumes for all stateful data, and define explicit restart policies and healthchecks.

</details>

📖 **Theory:** [scenario-production-architecture](./15_Best_Practices/Theory.md#the-gap-between-working-and-production-ready)


---

### Q82 · [Design] · `scenario-image-vulnerability`

> **A security scan shows 3 critical CVEs in your base image. Your app deploys daily. Design a workflow to stay up-to-date on base images automatically.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**How to think through this:**
1. **Immediate fix**: identify the CVE-affected packages (`docker scout cves`). If a patched base image tag exists, update the `FROM` line and rebuild. If no patch exists, add an explicit `RUN apt-get install -y <package>=<fixed-version>` after the `FROM` as a stopgap.
2. **Automated base image refresh**:
   - Use a scheduled CI job (nightly or weekly) that rebuilds all images from scratch — no `--cache` for the base layer — even without code changes. This picks up OS-level security patches in the base image.
   - Pin base images with a digest (`FROM python:3.11-slim@sha256:abc123`) for reproducibility, but automate digest updates via tools like `Renovate` or `Dependabot`, which open PRs when a new digest is published.
3. **Scan in CI**: integrate `docker scout cves --exit-code --only-severity critical,high` into the build pipeline. The `--exit-code` flag fails the build if critical CVEs are found, blocking deployment of vulnerable images.
4. **Registry monitoring**: enable Docker Scout's continuous monitoring on the registry. It alerts when a newly discovered CVE affects a previously clean image — catching vulnerabilities between builds.
5. **Policy**: define a maximum CVE age policy — e.g., no critical CVEs older than 7 days may reach production.

**Key takeaway:** Automate base image digest updates via Renovate/Dependabot, fail CI on critical CVEs, and run nightly rebuilds to pull patched base images without waiting for code changes.

</details>

📖 **Theory:** [scenario-image-vulnerability](./12_Docker_Security/Theory.md#bad-secret-baked-into-image-layer)


---

### Q83 · [Design] · `scenario-compose-migration`

> **A team uses docker-compose in development. You need to migrate them to Kubernetes in production. What is your migration strategy?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**How to think through this:**
1. **Map Compose concepts to Kubernetes primitives**: each Compose service becomes a `Deployment` (stateless) or `StatefulSet` (stateful). Named volumes become `PersistentVolumeClaims`. Networks become `Services` (for DNS) and `NetworkPolicies` (for isolation). Environment variables become `ConfigMaps` and `Secrets`.
2. **Use Kompose as a starting point**: `kompose convert -f docker-compose.yml` generates rough Kubernetes YAML. It is never production-ready but gives a structural starting point. Review and rewrite every generated file.
3. **Keep Compose for local dev**: don't force developers to run `minikube` locally. Maintain the `docker-compose.yml` for dev and write Kubernetes manifests for staging/prod. A `docker-compose.override.yml` can handle dev-specific config.
4. **Migration order**: start with stateless services (web/API) — easiest to move. Move stateful services (DB) last or keep them outside Kubernetes (RDS, ElastiCache) and only migrate the app tier.
5. **Readiness/liveness probes**: Compose `healthcheck` must be translated to Kubernetes `readinessProbe` and `livenessProbe` — they're not auto-converted.
6. **CI alignment**: update CI to build the same image, push to a registry, and deploy via `kubectl apply` or Helm in production — while still using `docker compose up` in dev.

**Key takeaway:** Map Compose primitives to K8s equivalents, use Kompose as a draft generator, keep Compose for dev, and migrate stateless services first.

</details>

📖 **Theory:** [scenario-compose-migration](./09_Docker_Compose/Theory.md#docker-compose)


---

### Q84 · [Design] · `scenario-registry-strategy`

> **Design a container registry strategy for a team of 50 engineers across 3 environments (dev/staging/prod). What tagging convention would you use?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**How to think through this:**
1. **Registry structure**: use a private registry (ECR, GCR, or Artifact Registry). Create separate repositories per service: `myorg/api`, `myorg/worker`, `myorg/frontend`. Avoid one monolithic repo with all services — access control and cleanup policies are cleaner per repository.
2. **Tagging convention**:
   - `git-<short-sha>` (e.g., `git-a3f9c12`): immutable, tied to a specific commit. Every CI build produces this tag. This is the canonical identifier for a build.
   - `branch-<name>` (e.g., `branch-main`, `branch-feature-x`): mutable pointer to the latest build on that branch. Used for dev/integration testing.
   - `v<semver>` (e.g., `v1.4.2`): immutable release tag, created at release time. The only tag that reaches production.
   - Never use `latest` in automation — it's ambiguous and breaks rollbacks.
3. **Environment promotion**: dev deploys `git-<sha>`, staging promotes a specific SHA to a `v<semver>` tag after QA, production deploys only semver-tagged images. Promotion is a registry-side retag, not a rebuild.
4. **Access control**: engineers can push to dev repos. Staging/prod pulls are restricted to CI service accounts. Humans cannot push directly to prod-bound repositories.
5. **Lifecycle policy**: auto-delete `branch-*` and `git-*` tags older than 30 days. Retain all semver tags indefinitely.

**Key takeaway:** Tag by git SHA for traceability, semver for releases; promote via retag (not rebuild), and enforce environment-based access control.

</details>

📖 **Theory:** [scenario-registry-strategy](./10_Docker_Registry/Theory.md#module-10--docker-registry)


---

### Q85 · [Design] · `scenario-startup-order`

> **Your docker-compose app fails because the web service starts before the database is ready. `depends_on` doesn't help. How do you solve this properly?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
`depends_on` only waits for the container to start (the process to launch), not for the service inside it to be ready. PostgreSQL takes several seconds after its process starts before it accepts connections. The web service connecting immediately will fail.

**How to think through this:**
1. **`depends_on` with `condition: service_healthy`**: add a `healthcheck` to the DB service that tests actual readiness, then use `condition: service_healthy` in `depends_on`. Compose will wait until the healthcheck passes before starting the dependent service.
```yaml
db:
  image: postgres:15
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U postgres"]
    interval: 5s
    timeout: 3s
    retries: 5

web:
  depends_on:
    db:
      condition: service_healthy
```
2. **Application-level retry logic**: the more robust and production-realistic solution. The app should implement retry with exponential backoff on database connection at startup. Infrastructure is unreliable — designing the app to tolerate transient failures is correct regardless of Compose.
3. **Wait scripts** (`wait-for-it.sh`, `dockerize`): shell scripts that poll a TCP port or HTTP endpoint before exec-ing the main process. These work but are fragile compared to option 1. They also require adding tools to the image.
4. Never use `sleep N` — it's a race condition waiting to manifest in slow environments.

**Key takeaway:** Use `healthcheck` + `condition: service_healthy` in `depends_on` for Compose; implement retry logic in the application itself for production-grade resilience.

</details>

📖 **Theory:** [scenario-startup-order](./09_Docker_Compose/Theory.md#had-to-remember-all-of-this-in-this-order-every-time)


---

### Q86 · [Interview] · `compare-docker-podman`

> **Compare Docker and Podman. What is the main architectural difference? When would you choose Podman?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Docker requires a persistent background daemon (`dockerd`) running as root. Podman is daemonless — every `podman` command is a direct fork-exec of the container without a central process.

**How to think through this:**
1. **Daemon vs. daemonless**: Docker CLI → Docker daemon (root) → containerd → runc. Podman CLI → runc directly (or via conmon). No long-running privileged daemon means one less attack surface and no single point of failure.
2. **Rootless containers**: Podman supports fully rootless containers natively — the container process runs as your user UID, using user namespaces. Docker supports rootless mode but it is more limited and less default. On systems where users cannot run privileged daemons (university clusters, hardened enterprise Linux), Podman is the practical choice.
3. **CLI compatibility**: Podman's CLI is intentionally Docker-compatible. `alias docker=podman` works for most operations. It also supports `podman-compose` (compatible with `docker-compose.yml`).
4. **Pods**: Podman natively understands the concept of pods (groups of containers sharing a network namespace) — aligning with Kubernetes concepts. `podman generate kube` can export a running pod to a Kubernetes YAML.
5. **When to choose Podman**: security-sensitive environments requiring rootless containers, RHEL/CentOS/Fedora ecosystems (Podman is the default there), Kubernetes-adjacent workflows, or when a root daemon is not permitted by policy.

**Key takeaway:** Podman is daemonless and rootless-native; choose it for security-hardened environments or RHEL ecosystems; Docker has a larger ecosystem and tooling.

</details>

📖 **Theory:** [compare-docker-podman](./02_Docker_Architecture/Theory.md#docker-architecture)


---

### Q87 · [Interview] · `compare-swarm-k8s`

> **Compare Docker Swarm and Kubernetes for production workloads. What are the 3 main reasons teams choose Kubernetes over Swarm?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Docker Swarm is Docker's built-in orchestration layer — simple to set up, uses the same Compose file format. Kubernetes is the CNCF standard orchestrator — complex to operate, but designed for large-scale, highly automated production systems.

**How to think through this:**
1. **Ecosystem and extensibility**: Kubernetes has a massive ecosystem — Helm, Operators, service meshes (Istio, Linkerd), GitOps tools (ArgoCD, Flux), autoscalers (KEDA), policy engines (OPA). Swarm has minimal third-party tooling. For anything beyond basic orchestration, Kubernetes wins.
2. **Auto-scaling**: Kubernetes has Horizontal Pod Autoscaler (scale based on CPU/memory/custom metrics), Vertical Pod Autoscaler, and Cluster Autoscaler (add nodes). Swarm has no built-in autoscaling — you scale manually or with external scripting.
3. **Managed cloud offerings**: every major cloud provider has a managed Kubernetes service (EKS, GKE, AKS) that handles control plane upgrades, etcd backups, and multi-AZ HA. There is no equivalent managed Swarm offering. Operating a Swarm control plane at scale is entirely self-managed.
4. **When Swarm still makes sense**: smaller teams, simpler applications, teams already fluent in Compose, or situations where Kubernetes operational overhead outweighs the benefits. Swarm is not wrong — it's a scope mismatch for large-scale systems.

**Key takeaway:** Teams choose Kubernetes for its ecosystem, built-in autoscaling, and managed cloud offerings; Swarm is simpler but lacks the tooling and managed services for large-scale production.

</details>

📖 **Theory:** [compare-swarm-k8s](./13_Docker_Swarm/Theory.md#module-13--docker-swarm)


---

### Q88 · [Design] · `scenario-ci-optimization`

> **A CI pipeline builds a 500MB Docker image in 12 minutes. 80% of the time is spent installing dependencies that rarely change. Design the caching strategy.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**How to think through this:**
1. **Root cause**: the slow step is dependency installation. Cache is being invalidated by source code changes that appear before the install step. Classic ordering problem.
2. **Fix instruction order**: ensure the dependency manifest is copied and installed before the application source code:
   ```
   COPY package.json package-lock.json ./
   RUN npm ci                          # cached unless lock file changes
   COPY . .                            # source code change doesn't bust dep cache
   RUN npm run build
   ```
3. **Registry-based cache**: use `--cache-from` to pull the previously built image as a cache source in CI. Even if the local CI runner has no cache, it pulls layers from the registry: `docker build --cache-from myrepo/myimage:cache --tag myrepo/myimage:latest .`
4. **BuildKit inline cache**: `docker build --build-arg BUILDKIT_INLINE_CACHE=1` embeds cache metadata in the pushed image, making it usable as a `--cache-from` source without a separate cache image.
5. **Multi-stage caching**: in multi-stage builds, split the `deps` stage from the `build` stage and cache them separately. The deps stage only rebuilds when the lock file changes.
6. **Cache mounts (BuildKit)**: `RUN --mount=type=cache,target=/root/.npm npm ci` uses a persistent BuildKit cache directory that survives across builds on the same runner — fastest option but requires the same runner.

**Key takeaway:** Fix instruction ordering first (manifest before source), then add registry-based `--cache-from` for cross-runner cache reuse.

</details>

📖 **Theory:** [scenario-ci-optimization](./14_Docker_in_CICD/Theory.md#module-14--docker-in-cicd)


---

### Q89 · [Design] · `scenario-multi-tenant`

> **You need to run containers from different customers on the same host. What isolation mechanisms do you use?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**How to think through this:**
1. **Network isolation**: put each tenant's containers on a dedicated user-defined bridge network. Add `NetworkPolicy`-equivalent rules (in Swarm: separate overlay networks with encrypted traffic `--opt encrypted`). Containers on different tenant networks cannot communicate.
2. **Resource isolation (cgroups)**: set explicit CPU and memory limits per container (`--memory`, `--cpus`). Without limits, a noisy-neighbor tenant can exhaust host resources. Use `--memory-swap` to control swap access.
3. **Filesystem isolation**: never use bind mounts pointing to shared host directories. Each tenant's volumes must be namespaced (`tenant_a_data`, `tenant_b_data`). Use separate Docker volume drivers or prefixed paths.
4. **User namespace remapping**: enable `userns-remap` in the Docker daemon config. This maps container UID 0 to a high, unprivileged host UID. A container escape grants the attacker an unprivileged host account, not root.
5. **Seccomp and AppArmor**: apply restrictive seccomp profiles per container to limit the syscall surface. Drop all capabilities and grant only what is explicitly needed (`--cap-drop ALL --cap-add <specific>`).
6. **For stricter isolation**: use gVisor (`--runtime=runsc`) or Kata Containers (`--runtime=kata-runtime`) — these add a kernel-level boundary between container and host, suitable for untrusted workloads.

**Key takeaway:** Layer isolation: network separation, cgroup resource limits, user namespace remapping, and capability dropping; use gVisor/Kata for hostile multi-tenant workloads.

</details>

📖 **Theory:** [scenario-multi-tenant](./12_Docker_Security/Theory.md#module-12--docker-security)


---

### Q90 · [Design] · `scenario-zero-downtime`

> **How do you achieve zero-downtime deployments using Docker Swarm? Walk through the update process.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**How to think through this:**
1. **Rolling update configuration**: in the service definition, set update parameters:
   - `update_config.parallelism: 1` — update one replica at a time (or N for faster rollout).
   - `update_config.delay: 10s` — wait 10 seconds between updating each replica.
   - `update_config.order: start-first` — start the new replica before stopping the old one. This is critical for zero downtime; the default `stop-first` order creates a brief capacity gap.
   - `update_config.failure_action: rollback` — automatically roll back if the new container fails its healthcheck.
2. **Healthchecks are mandatory**: Swarm considers an updated task healthy only when its healthcheck passes. Without a healthcheck, Swarm marks the new container healthy as soon as it starts — before your app is ready to serve traffic.
3. **The update flow** with `order: start-first`:
   - Swarm starts a new replica on an available node.
   - Waits for the new replica's healthcheck to pass.
   - Removes the old replica.
   - Waits `delay` seconds, then repeats for the next replica.
4. **Rollback**: `docker service rollback myservice` reverts to the previous service spec instantly.
5. **Load balancer consideration**: Swarm's internal routing mesh handles in-flight connection draining when `order: start-first` is used. External load balancers (e.g., Nginx, ALB) must have the new container registered before the old one is deregistered — `start-first` achieves this.

**Key takeaway:** Use `order: start-first` with a passing healthcheck in Swarm rolling updates; the new container must be healthy before the old one is removed.

</details>

📖 **Theory:** [scenario-zero-downtime](./13_Docker_Swarm/Theory.md#module-13--docker-swarm)


---

## 🔴 Tier 5 — Critical Thinking

### Q91 · [Logical] · `predict-layer-count`

> **How many layers does this Dockerfile create?**

```dockerfile
FROM ubuntu:22.04
RUN apt-get update
RUN apt-get install -y curl
RUN apt-get install -y git
RUN rm -rf /var/lib/apt/lists/*
COPY app.py /app/
CMD ["python3", "/app/app.py"]
```

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**6 new layers** are added on top of the ubuntu:22.04 base layers.

**How to think through this:**
1. Layer-producing instructions: `RUN`, `COPY`, and `ADD` each create a new layer. `FROM`, `CMD`, `ENV`, `EXPOSE`, `LABEL`, `ARG`, and `WORKDIR` do not create layers (they modify image metadata only).
2. Count the layer-producing instructions:
   - `RUN apt-get update` → layer 1
   - `RUN apt-get install -y curl` → layer 2
   - `RUN apt-get install -y git` → layer 3
   - `RUN rm -rf /var/lib/apt/lists/*` → layer 4
   - `COPY app.py /app/` → layer 5
   - `CMD [...]` → no layer (metadata only)
3. The `FROM ubuntu:22.04` inherits the base image's existing layers (ubuntu:22.04 itself has several layers) but does not add a new one.

Wait — the correct count on top of the base is **5**, not 6. `CMD` does not produce a layer.

**The problem with this Dockerfile**: `rm -rf /var/lib/apt/lists/*` is in a separate `RUN` command. This creates a new layer on top of the layer containing the package lists — the package list data is still in the lower layer, just hidden. The image is not actually smaller. The correct pattern squashes all apt operations into a single `RUN`:
```dockerfile
RUN apt-get update && apt-get install -y curl git && rm -rf /var/lib/apt/lists/*
```
This produces 1 layer instead of 4, and the package lists are never committed to any layer.

**Key takeaway:** `RUN` and `COPY` create layers; `CMD`/`ENV`/`EXPOSE` do not. Cleanup commands in separate `RUN` steps do not reduce image size because the data already exists in a lower layer.

</details>

📖 **Theory:** [predict-layer-count](./04_Images_and_Layers/Theory.md#images-and-layers)


---

### Q92 · [Logical] · `predict-env-override`

> **A Dockerfile sets `ENV PORT=8080`. You run `docker run -e PORT=3000 myimage`. What value does the container see for PORT? What if you used ARG instead of ENV?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
The container sees `PORT=3000`.

**How to think through this:**
1. `ENV` sets an environment variable that is baked into the image and available at container runtime. However, runtime `-e` flags override image-level `ENV` values. The `-e PORT=3000` flag sets an environment variable in the container's environment, taking precedence over the image default.
2. **ARG vs ENV**: `ARG` is a build-time variable only. It exists during `docker build` and can be passed with `--build-arg PORT=9090`. It does not persist into the container's runtime environment — a running container cannot see `ARG` values unless they were explicitly copied into an `ENV` instruction (`ENV PORT=$PORT`).
3. Concrete comparison:
   - `ENV PORT=8080` → container at runtime sees `PORT=8080` by default, overridable with `-e`.
   - `ARG PORT=8080` → available during build steps, invisible at runtime.
   - `ARG PORT=8080` then `ENV PORT=$PORT` → the ARG value is captured into an ENV, persisting to runtime.
4. Edge case: `docker run -e PORT=` (empty value) — this sets PORT to an empty string, overriding the image default with blank, which may break the app differently than not setting it at all.

**Key takeaway:** `-e` at runtime overrides `ENV` from the image; `ARG` is build-time only and never appears in the running container's environment unless explicitly promoted to `ENV`.

</details>

📖 **Theory:** [predict-env-override](./05_Dockerfile/Theory.md#env--setting-the-kitchen-temperature)


---

### Q93 · [Logical] · `predict-volume-mount`

> **A Dockerfile has `VOLUME ["/data"]`. You run `docker run myimage` without `-v`. What happens to /data? Is the data accessible after the container is removed?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
Docker automatically creates an **anonymous volume** and mounts it at `/data` inside the container.

**How to think through this:**
1. The `VOLUME` instruction in a Dockerfile tells Docker that `/data` is a mountpoint. When a container starts without an explicit `-v` flag for that path, Docker creates an anonymous volume — a named volume with a random UUID as its name — and mounts it at `/data`.
2. **During container lifetime**: writes to `/data` inside the container go to this anonymous volume, stored at `/var/lib/docker/volumes/<uuid>/_data` on the host.
3. **After `docker rm`**: `docker rm <container>` removes the container but does not remove the volume by default. The anonymous volume still exists and is accessible via `docker volume ls` (it will appear as a volume with a long UUID name). You can inspect or mount it to another container.
4. **After `docker rm -v`**: the `-v` flag on `docker rm` removes associated anonymous volumes. Named volumes (created with `-v myname:/data`) are never removed by `docker rm -v`.
5. **Key implication**: anonymous volumes accumulate silently. Running 100 containers from this image without cleanup creates 100 orphaned anonymous volumes, consuming disk space. `docker volume prune` removes all volumes not attached to a running container.

**Key takeaway:** `VOLUME` triggers automatic anonymous volume creation; the volume survives `docker rm` but not `docker rm -v`, and accumulates if not pruned.

</details>

📖 **Theory:** [predict-volume-mount](./07_Volumes_and_Bind_Mounts/Theory.md#volumes-and-bind-mounts)


---

### Q94 · [Debug] · `debug-dockerfile-fail`

> **A build fails at this step. What is wrong and how do you fix it?**

```dockerfile
FROM python:3.11
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . /app
WORKDIR /app
RUN python -c "import myapp"
```

<details>
<summary>💡 Show Answer</summary>

**Answer:**
The `WORKDIR /app` instruction is placed after `COPY . /app`, but more critically, `python -c "import myapp"` runs after `WORKDIR /app` — which is correct for the import. The actual bug is that `WORKDIR` is set after the `COPY`, which is valid but confusing. However, the real failure is likely that **Python cannot find `myapp` as a module**.

**How to think through this:**
1. `COPY . /app` copies all source files into `/app`. `WORKDIR /app` sets the working directory to `/app`. When `python -c "import myapp"` runs, Python searches `sys.path`, which includes the current directory.
2. If `myapp` is a module (a file named `myapp.py` or a directory `myapp/` with `__init__.py`), the import should work from `/app`.
3. The more likely failure: `pip install -r requirements.txt` runs before `COPY . /app`. If `requirements.txt` references a local package (e.g., `-e .` or a local path dependency), pip can't find it because the source code hasn't been copied yet.
4. **Secondary issue**: `WORKDIR /app` should be set before `COPY . /app` so the copy destination is relative to the workdir:
```dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN python -c "import myapp"
```
5. If the package needs to be installed (not just importable from the path), add `RUN pip install -e .` after copying the full source.

**Key takeaway:** Set `WORKDIR` before `COPY` so paths are consistent; if `import` fails, the package may need to be installed via `pip install -e .` rather than just copied into the workdir.

</details>

📖 **Theory:** [debug-dockerfile-fail](./05_Dockerfile/Theory.md#dockerfile)


---

### Q95 · [Debug] · `debug-network-unreachable`

> **Container A can't reach Container B. Both are running. `docker inspect` shows both containers are on the `bridge` network. What is the most likely cause and fix?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
The most likely cause is that both containers are on the **default** `bridge` network, which does not provide DNS resolution by container name.

**How to think through this:**
1. The default `bridge` network (`docker0`) does not include Docker's embedded DNS server. Containers on the default bridge can only reach each other by IP address, not by container name or hostname.
2. If container A is trying `curl http://container-b:8080`, the DNS lookup for `container-b` fails — not a routing issue, a name resolution issue.
3. **Diagnosis**: run `docker inspect container-a` and `docker inspect container-b`. If `NetworkSettings.Networks` shows `bridge` (the default), that's the cause. Verify by trying to connect via IP instead of name.
4. **Fix — option 1 (correct)**: create a user-defined bridge network and connect both containers to it:
   ```
   docker network create mynet
   docker network connect mynet container-a
   docker network connect mynet container-b
   ```
   Now container A can reach `container-b` by name.
5. **Fix — option 2 (legacy, avoid)**: use `--link container-b:container-b` on container A. This manually adds a hosts entry. Deprecated since user-defined networks exist.
6. **Alternative cause**: both containers are on different user-defined networks that happen to also be named separately. Fix: connect one container to the other's network, or connect both to a shared network.

**Key takeaway:** The default bridge network lacks DNS; create a user-defined bridge and connect both containers to it for name-based resolution.

</details>

📖 **Theory:** [debug-network-unreachable](./08_Networking/Theory.md#ping-connect-network-is-unreachable)


---

### Q96 · [Debug] · `debug-permission-denied`

> **A container fails with `Permission denied: /app/data`. The volume is mounted correctly and the directory exists on the host. What are the 3 most likely causes?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**How to think through this:**

**Cause 1 — Host directory ownership mismatch**: The host directory `/host/path/data` is owned by `root` or another user. Inside the container, the process runs as a non-root user (e.g., UID 1000). The container process does not have write permission to a root-owned directory. Fix: `chown 1000:1000 /host/path/data` on the host, matching the UID of the container's process user.

**Cause 2 — The `VOLUME` instruction overwrites the directory at runtime**: If the Dockerfile contains `VOLUME ["/app/data"]` and also copies files into `/app/data` before that instruction, Docker's volume initialization behavior can create a fresh mount owned by root. The files are there but the permissions were reset. Fix: ensure permissions are set correctly after the `VOLUME` instruction, or handle permissions at container startup via an entrypoint script.

**Cause 3 — SELinux or AppArmor label mismatch**: On SELinux-enabled hosts (RHEL, Fedora), the host directory may have an SELinux context that prevents container access. The container process gets `Permission denied` even if Unix permissions look correct. Fix: add `:z` (shared relabeling) or `:Z` (private relabeling) to the volume mount: `-v /host/data:/app/data:z`. On AppArmor systems, the container's AppArmor profile may restrict access to the mount path.

Bonus cause: the container is running as a user whose UID doesn't match any host UID and the directory has mode `700` — the process has no read/write permission by group or other.

**Key takeaway:** The three most likely causes are host directory UID mismatch, Docker volume initialization overwriting permissions, and SELinux/AppArmor context restrictions.

</details>

📖 **Theory:** [debug-permission-denied](./12_Docker_Security/Theory.md#disable-seccomp-for-debugging-only-never-production)


---

### Q97 · [Design] · `design-prod-dockerfile`

> **Write the key design decisions (not full code) for a production Dockerfile for a Node.js app: base image choice, build stages, user, caching, health check.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**How to think through this:**

1. **Base image**: use `node:<version>-slim` (Debian slim) or `node:<version>-alpine`. Alpine is smaller (~5MB vs ~70MB for slim) but uses musl libc instead of glibc — some native Node addons or binaries compiled for glibc will break. Prefer `node:20-slim` for reliability, `node:20-alpine` only if image size is a priority and you've verified compatibility. Pin the exact version, never `node:latest`.

2. **Multi-stage build**: use at least two stages — `builder` and `production`.
   - `builder` stage: install all dependencies (including devDependencies), compile TypeScript, run bundlers, generate assets.
   - `production` stage: start from a clean base image, copy only the compiled output and `node_modules` (production-only, reinstalled with `npm ci --omit=dev`). This keeps build tools, source maps, and test dependencies out of the final image.

3. **Non-root user**: create a dedicated user (`useradd -r -u 1001 nodeapp`) and switch to it with `USER nodeapp` before the `CMD`. Never run as root in production. Set ownership of the app directory to this user during build.

4. **Layer caching**: copy `package.json` and `package-lock.json` first, run `npm ci`, then copy application source. Dependency installation is cached separately from code changes.

5. **Healthcheck**: add a `HEALTHCHECK` instruction using `curl` or `wget` against the app's health endpoint: `HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -f http://localhost:3000/health || exit 1`. This enables Swarm/Compose to detect an unhealthy container automatically.

**Key takeaway:** Slim/versioned base image, multi-stage build to exclude devDependencies, non-root user, deps-before-code ordering, and an explicit HEALTHCHECK.

</details>

📖 **Theory:** [design-prod-dockerfile](./15_Best_Practices/Theory.md#the-gap-between-working-and-production-ready)


---

### Q98 · [Design] · `design-compose-prod`

> **What changes do you make when promoting a docker-compose.yml from development to production? List at least 5 production-specific changes.**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
**How to think through this:**

1. **Remove bind mounts for source code**: development uses `-v ./src:/app/src` for hot reload. Production must use the code baked into the image. Remove all source-code bind mounts.

2. **Pin image versions**: dev often uses `image: myapp:latest` or `build: .`. Production must reference a specific, immutable tag: `image: myrepo/myapp:v1.4.2` or `image: myrepo/myapp:git-a3f9c12`. Never use `latest` in production.

3. **Remove `build:` blocks**: production pulls pre-built images from a registry. The `build:` key belongs only in development. In production, building happens in CI, not on the server.

4. **Add resource limits**: set `deploy.resources.limits` (CPU and memory) on every service. Without limits, one container can starve others.

5. **Switch secrets to proper secret management**: dev uses hardcoded `environment:` variables. Production must reference Docker secrets, environment variable injection from a secrets manager (Vault, AWS SSM), or at minimum an `.env` file that is never committed.

6. **Set `restart: unless-stopped` or Swarm `restart_policy`**: dev containers can be manually restarted. Production services must auto-recover from crashes.

7. **Configure logging drivers**: dev uses the default `json-file` driver. Production should forward logs to a centralized system: `logging: driver: awslogs` or `fluentd`.

8. **Remove development-only services**: test databases, mock servers, debug UIs, documentation services — remove any service that exists only for local development.

**Key takeaway:** Production Compose removes source mounts and build steps, pins images, adds resource limits, uses proper secrets management, and configures restart and logging.

</details>

📖 **Theory:** [design-compose-prod](./09_Docker_Compose/Theory.md#docker-compose)


---

### Q99 · [Critical] · `edge-case-pid1`

> **A container ignores SIGTERM and takes 30 seconds to stop (Docker's kill timeout). What is likely happening with PID 1 inside the container? How do you fix it properly?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
The container is running with a shell as PID 1, and the shell is not forwarding the SIGTERM signal to the application process.

**How to think through this:**
1. When you run `docker stop`, Docker sends SIGTERM to PID 1 inside the container. After 10 seconds (default timeout), it sends SIGKILL. If the container takes 30 seconds, someone has configured a longer `--stop-timeout`, or the container is repeatedly being sent SIGTERM that gets ignored before SIGKILL fires.
2. **Root cause — shell form CMD**: `CMD python app.py` (shell form) runs as `/bin/sh -c "python app.py"`. The shell is PID 1. Shells typically do not forward signals to child processes. SIGTERM hits the shell, the shell does nothing with it, the app never sees the signal.
3. **Root cause — wrapper scripts**: an entrypoint shell script that exec's the app (correct) vs. one that calls the app without `exec` (wrong):
   - Wrong: `python app.py` (in a script) — script is PID 1, python is a child
   - Correct: `exec python app.py` — `exec` replaces the shell process with python, making python PID 1
4. **Fix 1 — exec form**: change `CMD python app.py` to `CMD ["python", "app.py"]`. Python becomes PID 1 and receives SIGTERM directly.
5. **Fix 2 — exec in entrypoint script**: if you need a wrapper script, end it with `exec "$@"` so the final process replaces the shell.
6. **Fix 3 — tini as init**: `ENTRYPOINT ["/tini", "--", "python", "app.py"]`. Tini is a minimal init that properly handles signal forwarding and zombie reaping. Docker Desktop includes `--init` flag (`docker run --init`) which injects tini automatically.

**Key takeaway:** Shell-form `CMD` makes the shell PID 1 which doesn't forward signals; use exec-form CMD or end entrypoint scripts with `exec "$@"` so the app process receives SIGTERM directly.

</details>

📖 **Theory:** [edge-case-pid1](./06_Containers_Lifecycle/Theory.md#p-uppercase-publish-all-exposed-ports-to-random-host-ports)


---

### Q100 · [Critical] · `edge-case-dangling-images`

> **After running `docker build` 100 times in CI, `docker images` shows 50 images tagged `<none>:<none>`. What are these, why do they appear, and how do you prevent accumulation?**

<details>
<summary>💡 Show Answer</summary>

**Answer:**
These are **dangling images** — intermediate image layers or previously tagged images that have been superseded but not deleted.

**How to think through this:**
1. **Why they appear**: every `docker build` that produces a tagged image (e.g., `myapp:latest`) creates the new image and points the tag to the new image ID. The old image that previously had that tag loses its tag reference — it becomes `<none>:<none>`. If you build `myapp:latest` 100 times, you get 99 dangling images (the 100th is current).
2. **Intermediate layer images**: with the classic builder (not BuildKit), some intermediate steps produce unnamed images that are retained for caching but appear as `<none>:<none>`. BuildKit manages this more efficiently.
3. **Disk impact**: dangling images consume disk space. 50 images at ~500MB each = 25GB of disk consumed by dead images. On a busy CI host this becomes a disk-full incident.
4. **Prevention in CI**:
   - Clean up after each job: `docker image prune -f` removes all dangling images.
   - Use `docker build --no-cache` in CI to avoid intermediate cache accumulation (trade speed for disk hygiene).
   - Use BuildKit (`DOCKER_BUILDKIT=1`) — it handles intermediate layers differently and produces fewer dangling images.
   - Run a scheduled prune job on CI hosts: `docker system prune -f --volumes` (carefully — this also removes stopped containers and unused volumes).
5. **Manual cleanup**: `docker rmi $(docker images -f "dangling=true" -q)` removes all dangling images. Or simply `docker image prune`.

**Key takeaway:** Dangling images are old tagged images superseded by new builds; prevent accumulation in CI by running `docker image prune -f` after each build job or on a schedule.

</details>

📖 **Theory:** [edge-case-dangling-images](./04_Images_and_Layers/Theory.md#dangling-images-and-cleanup)
