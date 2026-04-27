# Installation and Setup — Code Examples

All examples are production-quality with detailed comments explaining every decision.

---

## 1. Linux Installation — Ubuntu/Debian (Official Repository)

Always install from Docker's official repository. The version in Ubuntu's default apt repo (`docker.io`) is outdated and may be missing security patches.

```bash
# ============================================================
# STEP 1: Clean up any old Docker installations
# Removes packages from the distro's repo (docker.io) or prior attempts
# 2>/dev/null: suppress errors if packages aren't installed
# ============================================================
sudo apt remove \
  docker docker-engine docker.io \
  containerd runc 2>/dev/null || true

# ============================================================
# STEP 2: Install prerequisites for adding a third-party apt repo
# ca-certificates: validates TLS cert of Docker's download server
# gnupg: used to verify the GPG key signature
# lsb-release: provides $(lsb_release -cs) → e.g., "jammy" for Ubuntu 22.04
# ============================================================
sudo apt update
sudo apt install -y ca-certificates curl gnupg lsb-release

# ============================================================
# STEP 3: Add Docker's official GPG signing key
# -m 0755: set directory permissions
# -d: create directory (and parents) if needed
# curl -fsSL: fail silently on error, follow redirects, suppress progress
# gpg --dearmor: convert from ASCII armor to binary format apt expects
# ============================================================
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg  # readable by all users, apt runs as root

# ============================================================
# STEP 4: Add the Docker stable repository
# signed-by: apt verifies packages against this key (prevents tampering)
# $(dpkg --print-architecture): amd64 or arm64 — correct for your machine
# $(lsb_release -cs): distro codename — "jammy", "focal", "bookworm", etc.
# ============================================================
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# ============================================================
# STEP 5: Install Docker Engine and plugins
# docker-ce: the daemon (dockerd)
# docker-ce-cli: the docker CLI
# containerd.io: container lifecycle manager
# docker-buildx-plugin: BuildKit-based build system (multi-arch builds)
# docker-compose-plugin: 'docker compose' subcommand (v2 Compose)
# ============================================================
sudo apt update
sudo apt install -y \
  docker-ce \
  docker-ce-cli \
  containerd.io \
  docker-buildx-plugin \
  docker-compose-plugin

# ============================================================
# STEP 6: Start the daemon and configure it to start on boot
# systemctl start: start now
# systemctl enable: configure systemd to start docker on next boot
# ============================================================
sudo systemctl start docker
sudo systemctl enable docker

# Verify daemon is running
sudo systemctl status docker
```

---

## 2. Post-Installation — Critical Linux Steps

Without these steps, every `docker` command requires `sudo`. Skip them and you'll spend time debugging permission errors.

```bash
# ============================================================
# Add your user to the docker group
# ============================================================
# The Docker socket (/var/run/docker.sock) is owned by root:docker
# Members of 'docker' group can read/write the socket without sudo
# SECURITY: docker group membership = effective root on this host
sudo usermod -aG docker "$USER"

# Group membership takes effect on next login session
# For immediate effect in the current shell without logging out:
newgrp docker

# Confirm the group was added
groups
# Output: ... docker ...

# ============================================================
# Verify the installation end-to-end
# ============================================================

# Show both client and server (daemon) versions
# If server version is missing, the daemon isn't running
docker version
# Client:
#  Version:           26.x.x
# Server: Docker Engine - Community
#  Engine:
#   Version:          26.x.x

# Show full system info: storage driver, cgroup driver, registries, etc.
docker info
# Look for:
#   Storage Driver: overlay2        ← correct for modern Linux
#   Cgroup Driver: systemd          ← should match your init system
#   Default Runtime: runc
#   Docker Root Dir: /var/lib/docker

# Run hello-world: this confirms image pull, container creation, and execution all work
docker run hello-world
# Expect: "Hello from Docker! This message shows that your installation is working correctly."
```

---

## 3. Docker Storage Layout — What Lives Where

Understanding the directory structure helps you diagnose space issues and understand how Docker persists data.

```bash
# ============================================================
# Show Docker's disk usage summary
# ============================================================
docker system df
# TYPE            TOTAL     ACTIVE    SIZE      RECLAIMABLE
# Images          12        3         2.4GB     1.8GB (75%)
# Containers      5         2         140MB     80MB (57%)
# Local Volumes   3         2         500MB     200MB (40%)
# Build Cache     27        0         800MB     800MB

# Verbose breakdown — shows every image and container
docker system df -v

# ============================================================
# Key directories (Linux Docker Engine)
# ============================================================

# Where ALL Docker data lives
sudo du -sh /var/lib/docker/
# Typically the largest directory on a Docker host

# Image layer data — usually 90% of /var/lib/docker space
# Each subdirectory is one OverlayFS layer identified by content hash
sudo du -sh /var/lib/docker/overlay2/
sudo ls /var/lib/docker/overlay2/ | wc -l   # number of layers

# Per-container metadata, logs, config.json
sudo ls /var/lib/docker/containers/
sudo du -sh /var/lib/docker/containers/

# Named volume data — persists after container removal
sudo ls /var/lib/docker/volumes/
sudo du -sh /var/lib/docker/volumes/

# Docker daemon configuration
# Edit this to change storage driver, logging driver, insecure registries, etc.
cat /etc/docker/daemon.json 2>/dev/null || echo "no daemon.json — using defaults"

# ============================================================
# Reclaim space: remove stopped containers, dangling images, unused volumes
# WARNING: 'docker system prune' is destructive — check first with 'docker system df'
# ============================================================
docker system prune         # removes: stopped containers, dangling images, unused networks
docker system prune -a      # also removes: images not used by any running container
docker system prune --volumes  # also removes: unused volumes (DATA LOSS if not careful)
```

---

## 4. Docker Contexts — Switching Between Environments

Contexts let you manage a dev server, staging, and prod from one terminal without SSH-ing between machines.

```bash
# ============================================================
# Inspect the default context
# ============================================================
docker context ls
# NAME       TYPE  DESCRIPTION                        DOCKER ENDPOINT
# default *  moby  Current DOCKER_HOST configuration  unix:///var/run/docker.sock

docker context inspect default
# Shows: socket path, TLS config, Kubernetes endpoint (if configured)

# ============================================================
# Create a context for a remote Docker host over SSH
# Requires: SSH access to the remote host, Docker installed there
# 'host=ssh://...' uses your existing SSH key + agent forwarding
# ============================================================
docker context create staging-server \
  --description "Staging server via SSH" \
  --docker "host=ssh://deploy@staging.example.com"

# ============================================================
# Create a context for a local Docker Desktop on macOS
# (useful when both Docker Desktop and Rancher Desktop are installed)
# ============================================================
docker context create docker-desktop \
  --docker "host=unix:///Users/$USER/.docker/run/docker.sock"

# ============================================================
# Use a context for one-off commands (without switching global context)
# --context flag overrides the active context for this command only
# ============================================================
docker --context staging-server ps
docker --context staging-server images

# ============================================================
# Switch the active context permanently
# ============================================================
docker context use staging-server
docker ps                    # ← now running against staging

# Switch back to local
docker context use default

# ============================================================
# Environment variable override (useful in scripts and CI)
# DOCKER_CONTEXT overrides whatever context is set in ~/.docker/contexts/
# ============================================================
DOCKER_CONTEXT=staging-server docker ps

# Remove a context
docker context rm staging-server
```

---

## 5. Diagnosing Common Installation Problems

These are the exact commands to run when facing the most common post-install errors.

```bash
# ============================================================
# PROBLEM: "Got permission denied while trying to connect to the Docker daemon socket"
# CAUSE: Current user is not in the docker group, or session hasn't refreshed
# ============================================================

# Check current group memberships
groups
# If 'docker' is missing:
sudo usermod -aG docker "$USER"
newgrp docker    # apply immediately without logout

# Verify the socket permissions
ls -la /var/run/docker.sock
# Expected: srw-rw---- 1 root docker
# If permissions are different, fix them:
sudo chown root:docker /var/run/docker.sock

# ============================================================
# PROBLEM: "Cannot connect to the Docker daemon at unix:///var/run/docker.sock"
# CAUSE: dockerd is not running
# ============================================================

# Check daemon status
sudo systemctl status docker

# Start the daemon
sudo systemctl start docker

# If it fails to start, check the journal for errors
sudo journalctl -u docker --no-pager -n 50

# ============================================================
# PROBLEM: Docker Desktop on macOS is very slow with bind mounts
# CAUSE: VirtioFS/osxfs overhead on host-to-VM filesystem crossing
# ============================================================

# Check which file sharing implementation is active
docker info | grep "File Sharing"

# Best practice: use named volumes for data, not bind mounts
# Slow:
docker run -v "$(pwd):/app" node:20 npm install
# Fast — node_modules lives in a Docker volume, not on the macOS filesystem:
docker volume create node_modules_cache
docker run \
  -v "$(pwd):/app" \          # source code (read-mostly, acceptable)
  -v node_modules_cache:/app/node_modules \  # ← volume, not bind mount
  node:20 npm install

# ============================================================
# GENERAL: Confirm every component is present and correct version
# ============================================================
docker version                      # client + server versions
docker info | grep -E "Runtime|Storage|Cgroup"
containerd --version                # containerd version
runc --version                      # runc version
docker buildx version               # BuildKit version
docker compose version              # Compose plugin version
```

---

## 📂 Navigation

**In this folder:**
| File | |
|---|---|
| [📖 Theory.md](./Theory.md) | Full explanation |
| [⚡ Cheatsheet.md](./Cheatsheet.md) | Quick reference |
| [🎯 Interview_QA.md](./Interview_QA.md) | Interview prep |
| 💻 **Code_Example.md** | ← you are here |

⬅️ **Prev:** [02 — Docker Architecture](../02_Docker_Architecture/Code_Example.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [04 — Images and Layers](../04_Images_and_Layers/Code_Example.md)
🏠 **[Home](../../README.md)**
