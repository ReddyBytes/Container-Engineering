# Installation and Setup — Interview Q&A

## Beginner

**Q1: Why does Docker on macOS or Windows require a VM? Can't it just run natively?**

No — containers are a Linux technology. They rely on Linux kernel features (namespaces, cgroups, OverlayFS). macOS has the Darwin kernel (XNU), and Windows has the Windows NT kernel. Neither provides the Linux syscalls that containers need.

Docker Desktop solves this by bundling a lightweight Linux VM:
- On macOS: uses Apple's Virtualization Framework (or HyperKit on older Macs)
- On Windows: uses WSL2 (Windows Subsystem for Linux 2) or Hyper-V

From your terminal, the `docker` CLI talks to a proxy socket that forwards API calls into the Linux VM where the actual Docker daemon runs. The performance overhead is generally invisible for development work, but is why production workloads always run on Linux.

---

**Q2: What is the `docker` group on Linux, and why do you need to be in it?**

The Docker daemon socket (`/var/run/docker.sock`) is owned by root with group ownership set to `docker`. By default, only root can read/write this socket.

Adding your user to the `docker` group grants that user permission to communicate with the daemon socket — which is required to run `docker` commands without `sudo`.

```bash
sudo usermod -aG docker $USER
```

Important caveat: being in the `docker` group is effectively equivalent to having root access on the machine. Anyone in this group can start a privileged container, mount the host filesystem, and escape to root. Only trusted users should be in the docker group.

---

**Q3: What is the difference between `docker version` and `docker info`?**

`docker version` shows version numbers for both the client (CLI) and server (daemon). It's the first command to run when troubleshooting — if the client can't connect, the Server section will show an error.

`docker info` shows detailed configuration and status of the Docker daemon: storage driver, logging driver, cgroup driver, total memory/CPU, number of running containers, data directory, registry settings, and more. Use it to understand how Docker is configured on a machine.

---

**Q4: What is WSL2 and why does Docker on Windows benefit from it?**

WSL2 (Windows Subsystem for Linux version 2) runs a real Linux kernel inside a lightweight Hyper-V VM managed by Windows. Unlike WSL1 (which translated Linux syscalls to Windows syscalls), WSL2 runs an actual Linux kernel.

This means Docker can run natively inside WSL2, with full support for all Linux kernel features containers need. Benefits:
- Full syscall compatibility (WSL1 missed many kernel calls Docker needs)
- Better filesystem performance within Linux filesystems
- Seamless integration: run Docker commands from your Windows terminal or any WSL2 distro
- Shared networking: containers are accessible from Windows and vice versa

---

## Intermediate

**Q5: How would you configure Docker to use a custom data directory instead of `/var/lib/docker`?**

Edit (or create) `/etc/docker/daemon.json`:

```json
{
  "data-root": "/mnt/large-disk/docker"
}
```

Then restart Docker:
```bash
sudo systemctl restart docker
```

You'd do this when your root partition is small and you have a larger disk mounted at another path. After changing the data root, existing images and containers won't be visible (they're in the old location). You'd need to either migrate the data manually or repull images.

To migrate:
```bash
sudo systemctl stop docker
sudo rsync -aP /var/lib/docker/ /mnt/large-disk/docker/
# update daemon.json, then:
sudo systemctl start docker
```

---

**Q6: How do you configure Docker to pull from a private registry that uses a self-signed certificate?**

Two options:

**Option 1: Add the CA certificate to Docker's trusted certificates**
```bash
sudo mkdir -p /etc/docker/certs.d/registry.example.com:5000
sudo cp ca.crt /etc/docker/certs.d/registry.example.com:5000/ca.crt
# No daemon restart needed for this approach
```

**Option 2: Mark the registry as insecure (HTTP or unverified HTTPS)**
In `/etc/docker/daemon.json`:
```json
{
  "insecure-registries": ["registry.example.com:5000"]
}
```
Restart Docker after this change. Option 1 is preferred for production because it still uses TLS; Option 2 means Docker will accept any certificate (or use plain HTTP), which is a security risk.

---

**Q7: A developer says `docker run hello-world` works, but `docker run -p 80:80 nginx` doesn't — it can't access port 80. What would you check?**

Systematically, check:

1. **Is the container actually running?** `docker ps` — confirm nginx container appears in running state.

2. **Is the port mapped correctly?** `docker ps` shows port mappings. Look for `0.0.0.0:80->80/tcp` or `:::80->80/tcp`.

3. **Is the port already in use on the host?** `sudo lsof -i :80` or `sudo ss -tlnp | grep :80` — another process may have port 80.

4. **Is a host firewall blocking port 80?** On Linux: `sudo iptables -L` or `sudo ufw status`. On macOS: System Settings → Firewall.

5. **On macOS/Windows: are you accessing the right address?** Docker Desktop containers are accessible at `localhost` / `127.0.0.1`. You can't use the container IP directly from your Mac.

6. **Is nginx actually starting successfully?** `docker logs <container-id>` — maybe nginx is failing to start due to a config error.

---

## Advanced

**Q8: Explain the difference between the `cgroupv1` and `cgroupv2` drivers in Docker, and when you might need to configure them.**

Docker's `--cgroup-driver` (set in `daemon.json`) controls how Docker interacts with Linux control groups:

- **`cgroupfs`:** Docker directly manages files in `/sys/fs/cgroup`. Simpler, less integrated with systemd.
- **`systemd`:** Docker delegates cgroup management to systemd (via `systemd-cgroups`). Required on systems where systemd is PID 1 and uses unified cgroup hierarchy (cgroupv2).

Modern Linux distributions (Ubuntu 22.04+, RHEL 9+) use **cgroupv2** (unified hierarchy) by default, managed by systemd. On these systems, you must set:

```json
{
  "exec-opts": ["native.cgroupdriver=systemd"]
}
```

Using `cgroupfs` on a systemd cgroupv2 system causes resource limits to not work correctly (containers might ignore memory limits). Kubernetes also requires `systemd` cgroup driver when using cgroupv2.

You can check which cgroup version your system uses:
```bash
stat -f /sys/fs/cgroup    # Type 0x63677270 = cgroupv1, Type 0x63677271 = cgroupv2
# or
docker info | grep "Cgroup"
```

---

**Q9: How would you set up Docker to work behind a corporate HTTP proxy?**

Docker needs proxy settings for two separate purposes: (1) the daemon pulling images, and (2) containers making outbound connections.

**For the daemon (image pulls):**
On systemd-based Linux, create a drop-in for the docker service:

```bash
sudo mkdir -p /etc/systemd/system/docker.service.d
sudo tee /etc/systemd/system/docker.service.d/http-proxy.conf > /dev/null <<EOF
[Service]
Environment="HTTP_PROXY=http://proxy.example.com:3128"
Environment="HTTPS_PROXY=http://proxy.example.com:3128"
Environment="NO_PROXY=localhost,127.0.0.1,.example.com"
EOF
sudo systemctl daemon-reload && sudo systemctl restart docker
```

**For containers (runtime outbound traffic):**
In `~/.docker/config.json`:
```json
{
  "proxies": {
    "default": {
      "httpProxy": "http://proxy.example.com:3128",
      "httpsProxy": "http://proxy.example.com:3128",
      "noProxy": "localhost,127.0.0.1,.example.com"
    }
  }
}
```
These proxy settings are injected as environment variables into every container automatically.

---

**Q10: What is Docker BuildKit and how do you enable it? Why is it preferred over the legacy builder?**

BuildKit is Docker's next-generation build engine. It's been the default since Docker 23.0.

Advantages over the legacy builder:
- **Parallel build stages:** Multi-stage builds can execute independent stages in parallel
- **Better caching:** More intelligent cache invalidation; supports external cache backends (registry, S3, GHA cache)
- **Secret mounting:** Mount secrets at build time without baking them into layers (`--mount=type=secret`)
- **SSH forwarding:** Forward SSH agents into builds for private git repos (`--mount=type=ssh`)
- **Faster:** Skips building stages not needed for the final output
- **Better output:** Progress display with detailed per-step output

Enable on older Docker versions:
```bash
# Per-command:
DOCKER_BUILDKIT=1 docker build .

# Permanently, in daemon.json:
{
  "features": { "buildkit": true }
}
```

On Docker 23.0+, BuildKit is the default. Use `docker buildx build` (the BuildKit CLI) for the full feature set including multi-platform builds.

---

## 📂 Navigation

**In this folder:**
| File | |
|---|---|
| [📖 Theory.md](./Theory.md) | Full explanation |
| [⚡ Cheatsheet.md](./Cheatsheet.md) | Quick reference |
| 🎯 **Interview_QA.md** | ← you are here |

⬅️ **Prev:** [02 — Docker Architecture](../02_Docker_Architecture/Interview_QA.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [04 — Images and Layers](../04_Images_and_Layers/Interview_QA.md)
🏠 **[Home](../../README.md)**
