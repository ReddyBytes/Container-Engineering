# Volumes and Bind Mounts — Cheatsheet

## Storage Types Comparison

| Feature | Named Volume | Bind Mount | tmpfs |
|---|---|---|---|
| **Managed by** | Docker | Host OS | Docker (RAM) |
| **Location** | `/var/lib/docker/volumes/` | Any host path | Memory only |
| **Persists after `docker rm`** | Yes | Yes (host files unchanged) | No |
| **Survives host reboot** | Yes | Yes | No |
| **Cross-platform** | Yes | No (path depends on host) | Yes |
| **Pre-populated from image** | Yes (first use) | No | No |
| **Multi-container sharing** | Easy | Yes (same path needed) | No |
| **Best for** | Databases, app data | Dev hot-reload, config | Secrets, temp files |
| **macOS/Windows performance** | Fast (inside VM) | Slower (cross-VM I/O) | Fast |

---

## Core Volume Commands

```bash
# === Create / list / inspect ===
docker volume create mydata              # create named volume
docker volume ls                         # list all volumes
docker volume ls --filter dangling=true  # unused volumes
docker volume inspect mydata             # full metadata + host path
docker volume inspect --format '{{.Mountpoint}}' mydata  # host path only

# === Remove ===
docker volume rm mydata                  # remove specific volume (fails if in use)
docker volume prune                      # remove all unused volumes
docker volume prune -a                   # include anonymous volumes
docker volume prune --filter "label=env=test"
```

---

## Mount Syntax: `-v` vs `--mount`

### Named Volume

```bash
# -v (short form)
docker run -v mydata:/var/lib/postgresql/data postgres:16

# --mount (explicit form — recommended)
docker run --mount type=volume,source=mydata,target=/var/lib/postgresql/data postgres:16
```

### Bind Mount

```bash
# -v (short form) — must be absolute path
docker run -v /home/user/app:/app myapp
docker run -v $(pwd):/app myapp          # current directory

# --mount
docker run --mount type=bind,source=$(pwd),target=/app myapp

# Read-only bind mount
docker run -v /etc/myapp.conf:/etc/myapp.conf:ro myapp
docker run --mount type=bind,source=/etc/myapp.conf,target=/etc/myapp.conf,readonly myapp
```

### tmpfs

```bash
# -v form doesn't support tmpfs — use --mount
docker run --mount type=tmpfs,target=/tmp myapp

# With size limit (bytes)
docker run --mount type=tmpfs,target=/tmp,tmpfs-size=104857600 myapp
# 104857600 bytes = 100 MB
```

---

## Common Volume Patterns

```bash
# === Postgres with persistent data ===
docker volume create pgdata
docker run -d \
  --name postgres \
  -e POSTGRES_PASSWORD=secret \
  -v pgdata:/var/lib/postgresql/data \
  --restart unless-stopped \
  postgres:16

# === Dev hot-reload (bind mount source code) ===
docker run -d \
  --name myapp-dev \
  -p 3000:3000 \
  -v $(pwd)/src:/app/src \             # source code
  -v $(pwd)/package.json:/app/package.json:ro \  # dep manifest (read-only)
  -v node_modules:/app/node_modules \  # named volume for node_modules (fast!)
  myapp:dev

# === Nginx with custom config (bind mount config file) ===
docker run -d \
  --name nginx \
  -p 80:80 \
  -v $(pwd)/nginx.conf:/etc/nginx/nginx.conf:ro \
  -v $(pwd)/html:/usr/share/nginx/html:ro \
  nginx:1.25

# === Redis with persistent storage ===
docker volume create redis-data
docker run -d \
  --name redis \
  -v redis-data:/data \
  redis:7 redis-server --save 60 1 --loglevel warning

# === Secrets via tmpfs ===
docker run -d \
  --name myapp \
  --mount type=tmpfs,target=/run/secrets,tmpfs-mode=0700 \
  myapp
```

---

## Inspect Mounts on a Running Container

```bash
# Show all mounts
docker inspect --format '{{json .Mounts}}' mycontainer | python3 -m json.tool

# Quick mount summary
docker inspect --format \
  '{{range .Mounts}}Type={{.Type}} Src={{.Source}} Dst={{.Destination}} RW={{.RW}}{{"\n"}}{{end}}' \
  mycontainer
```

---

## Volume Backup and Restore

```bash
# === Backup a named volume to a tar file ===
docker run --rm \
  -v mydata:/source:ro \
  -v $(pwd):/backup \
  alpine \
  tar czf /backup/mydata-backup.tar.gz -C /source .

# === Restore from tar file ===
docker volume create mydata-restored
docker run --rm \
  -v mydata-restored:/target \
  -v $(pwd):/backup \
  alpine \
  sh -c "tar xzf /backup/mydata-backup.tar.gz -C /target"
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

⬅️ **Prev:** [06 — Container Lifecycle](../06_Containers_Lifecycle/Cheatsheet.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [08 — Networking](../08_Networking/Cheatsheet.md)
🏠 **[Home](../../README.md)**
