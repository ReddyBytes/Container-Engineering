# Installation and Setup — Cheatsheet

## Install Commands by Platform

### macOS (Docker Desktop)
```bash
# Via Homebrew (recommended)
brew install --cask docker

# After install: launch Docker Desktop, wait for daemon to start
docker version    # verify
```

### Ubuntu / Debian (Docker Engine — official repo)
```bash
# Remove old packages
sudo apt remove docker docker-engine docker.io containerd runc 2>/dev/null

# Add Docker's GPG key + repo
sudo apt update && sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list

# Install
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin

# Start and enable
sudo systemctl enable --now docker
```

### RHEL / CentOS / Fedora
```bash
sudo yum-config-manager --add-repo \
  https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
```

### Windows (WSL2 + Docker Desktop)
```powershell
# PowerShell (Admin): enable WSL2
wsl --install
# Restart, then install Docker Desktop from docker.com
# Enable WSL2 integration in Docker Desktop settings
```

---

## Post-Install Checklist

```bash
# 1. Add user to docker group (Linux only)
sudo usermod -aG docker $USER
newgrp docker                         # apply without logout

# 2. Verify daemon is running
sudo systemctl status docker          # Linux
docker info                           # all platforms

# 3. Check client + server versions match
docker version

# 4. Run end-to-end test
docker run hello-world

# 5. Check available disk space for Docker
docker system df
```

---

## `docker info` Output Key Fields

| Field | What it means |
|---|---|
| `Server Version` | dockerd version |
| `Storage Driver` | How image layers are stored (should be `overlay2`) |
| `Cgroup Driver` | `systemd` (preferred) or `cgroupfs` |
| `Total Memory` | RAM available to Docker daemon |
| `CPUs` | CPU count available |
| `Docker Root Dir` | Where Docker stores data (`/var/lib/docker`) |
| `Registry` | Default registry (usually `https://index.docker.io/v1/`) |
| `Experimental` | Whether experimental features are enabled |
| `HTTP Proxy` / `HTTPS Proxy` | Proxy config (check if pull issues) |

---

## Key File Paths

| Path | Purpose |
|---|---|
| `/var/lib/docker/` | Docker data root |
| `/var/lib/docker/overlay2/` | Image layer storage (usually largest dir) |
| `/var/lib/docker/containers/` | Per-container metadata + logs |
| `/var/lib/docker/volumes/` | Named volume data |
| `/etc/docker/daemon.json` | Daemon configuration file |
| `/var/run/docker.sock` | Unix socket for API communication |
| `~/.docker/config.json` | Per-user config (registry auth tokens) |
| `~/.docker/daemon.json` | Rootless Docker daemon config |

---

## Docker Context Commands

```bash
docker context ls                     # list all contexts
docker context inspect default        # details of current context
docker context use <name>             # switch context

# Create context for remote server (SSH)
docker context create remote-dev \
  --docker "host=ssh://user@dev.example.com"

# Create context for remote server (TLS)
docker context create remote-prod \
  --docker "host=tcp://prod.example.com:2376,\
ca=/path/to/ca.pem,cert=/path/to/cert.pem,key=/path/to/key.pem"

# Use environment variable (overrides context)
export DOCKER_HOST=ssh://user@dev.example.com
```

---

## Common Error Messages and Fixes

| Error | Cause | Fix |
|---|---|---|
| `permission denied...docker.sock` | User not in docker group | `sudo usermod -aG docker $USER && newgrp docker` |
| `Cannot connect to Docker daemon` | Daemon not running | `sudo systemctl start docker` (Linux) or launch Docker Desktop |
| `docker: command not found` | CLI not installed or not in PATH | Reinstall; check `which docker` |
| `error pulling image: net/http: TLS handshake timeout` | Network/proxy issue | Check `HTTP_PROXY` env var; check firewall |
| `No space left on device` | Docker ran out of disk | `docker system prune -a` to clean up |
| `standard_init_linux.go: exec format error` | Running wrong CPU architecture image | Pull image for correct arch (`--platform linux/amd64`) |

---

## Daemon Configuration (`/etc/docker/daemon.json`)

```json
{
  "storage-driver": "overlay2",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "default-address-pools": [
    {"base": "172.30.0.0/16", "size": 24}
  ],
  "registry-mirrors": ["https://mirror.example.com"],
  "insecure-registries": ["registry.local:5000"],
  "data-root": "/mnt/data/docker"
}
```

After changing: `sudo systemctl restart docker`

---

## 📂 Navigation

**In this folder:**
| File | |
|---|---|
| [📖 Theory.md](./Theory.md) | Full explanation |
| ⚡ **Cheatsheet.md** | ← you are here |
| [🎯 Interview_QA.md](./Interview_QA.md) | Interview prep |

⬅️ **Prev:** [02 — Docker Architecture](../02_Docker_Architecture/Cheatsheet.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [04 — Images and Layers](../04_Images_and_Layers/Cheatsheet.md)
🏠 **[Home](../../README.md)**
