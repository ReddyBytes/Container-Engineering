# Docker Architecture — Cheatsheet

## Component Summary

| Component | Role | Listens On | Language |
|---|---|---|---|
| `docker` CLI | User-facing command tool | — (client only) | Go |
| `dockerd` | Docker daemon — API, build, networks, volumes | `/var/run/docker.sock` (Unix) or TCP | Go |
| `containerd` | Container lifecycle manager — pull, start, stop | gRPC socket | Go |
| `containerd-shim` | Per-container shim; keeps container alive if containerd restarts | — | Go |
| `runc` | OCI runtime — makes Linux kernel calls to create container | — (called by shim) | Go |

---

## Key File Paths

| Path | Purpose |
|---|---|
| `/var/run/docker.sock` | Docker Unix socket — how CLI talks to daemon |
| `/var/lib/docker/` | Docker data root — images, containers, volumes |
| `/var/lib/docker/overlay2/` | OverlayFS layer storage |
| `/var/lib/docker/containers/` | Container metadata, configs, log files |
| `/var/lib/docker/volumes/` | Named Docker volumes |
| `/etc/docker/daemon.json` | Docker daemon configuration file |
| `/var/log/docker.log` | Docker daemon log (varies by OS) |
| `~/.docker/config.json` | Per-user Docker config (registry auth tokens) |

---

## Docker Socket Security Quick Reference

| Risk | Mitigation |
|---|---|
| Mounting socket in CI container | Use docker-socket-proxy (allow-list API endpoints) |
| `docker` group = root equivalent | Only add trusted users; prefer rootless Docker |
| Exposed TCP socket (2375) | Never expose without TLS; use 2376 (TLS) |
| Container escaping via socket | Don't mount socket; use Docker-in-Docker (dind) sidecar carefully |
| Rootless Docker | Run dockerd as non-root; requires kernel ≥ 5.11, user namespaces |

---

## OverlayFS / Layer Concepts

| Term | Meaning |
|---|---|
| **Image layer** | Read-only filesystem diff (set of added/changed/deleted files) |
| **Writable layer** | Thin layer added on container creation; deleted with container |
| **OverlayFS** | Union filesystem used by Docker to merge layers into one view |
| **Copy-on-write (CoW)** | When container modifies a read-only file, it's copied to writable layer first |
| **lowerdir** | OverlayFS term for the read-only image layers |
| **upperdir** | OverlayFS term for the writable container layer |
| **merged** | The unified view presented to the container process |
| **Dangling layer** | Layer no longer referenced by any image tag |

---

## Docker Registry URL Patterns

| Image reference | Expands to |
|---|---|
| `nginx` | `docker.io/library/nginx:latest` |
| `nginx:1.25` | `docker.io/library/nginx:1.25` |
| `myuser/myapp` | `docker.io/myuser/myapp:latest` |
| `ghcr.io/org/app:v1` | GitHub Container Registry |
| `123456789.dkr.ecr.us-east-1.amazonaws.com/myapp:v1` | AWS ECR |
| `registry.example.com:5000/myapp:latest` | Self-hosted private registry |

---

## Useful Diagnostic Commands

```bash
# Check Docker installation and daemon info
docker version                        # client + server version
docker info                           # daemon configuration, driver info

# Inspect the daemon directly
sudo systemctl status docker          # systemd service status
sudo journalctl -u docker -f          # live daemon logs

# Socket connectivity
ls -la /var/run/docker.sock           # check socket file exists
docker context ls                     # list Docker contexts (local, remote)

# Layer and image inspection
docker image history nginx            # show layers and commands that created them
docker image inspect nginx            # full metadata (JSON)

# containerd (if you have ctr or crictl installed)
sudo ctr images ls                    # containerd image list
sudo ctr containers ls                # containerd container list
```

---

## 📂 Navigation

**In this folder:**
| File | |
|---|---|
| [📖 Theory.md](./Theory.md) | Full explanation |
| ⚡ **Cheatsheet.md** | ← you are here |
| [🎯 Interview_QA.md](./Interview_QA.md) | Interview prep |

⬅️ **Prev:** [01 — Virtualization and Containers](../01_Virtualization_and_Containers/Cheatsheet.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [03 — Installation and Setup](../03_Installation_and_Setup/Cheatsheet.md)
🏠 **[Home](../../README.md)**
