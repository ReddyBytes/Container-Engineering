# Volumes and Bind Mounts — Interview Q&A

## Beginner

**Q1: Why can't you just write data to a container's filesystem and expect it to persist?**

A container's filesystem is made up of two parts: the read-only image layers (which never change) and a thin writable layer added when the container starts. The writable layer is tied to the container's lifetime — when the container is removed with `docker rm`, the writable layer is deleted.

Even without `docker rm`, the writable layer is specific to that particular container instance. If you run a new container from the same image, it gets a fresh, empty writable layer — your previous writes are not there.

This is by design: it enforces immutability (you can trust that your image hasn't been modified), enables density (stopped containers don't bloat disk indefinitely by default), and supports the pattern of replacing containers rather than modifying them in place.

For data that must outlive a container, use volumes or bind mounts.

---

**Q2: What is the difference between a named volume and a bind mount?**

A **named volume** is storage managed by Docker. You create it with `docker volume create`, and Docker decides where it lives on the host (`/var/lib/docker/volumes/<name>/_data`). You only refer to it by name — you don't care about its host path.

A **bind mount** is a specific directory on your host filesystem that you map into the container. You provide the exact host path, and the container gets a view of that directory.

Key differences:

| | Named Volume | Bind Mount |
|---|---|---|
| Path control | Docker manages it | You provide host path |
| Pre-populated | Yes (from image data) | No (host dir overlays image path) |
| Dev workflow | Not ideal (files inside Docker VM) | Perfect (you edit on host) |
| Portability | High (name only, no path) | Low (host path must exist) |
| Typical use | Databases, persistent data | Dev hot-reload, config injection |

---

**Q3: What is a tmpfs mount? When would you use it?**

A tmpfs mount stores data in the host machine's RAM (and optionally swap). It's never written to disk.

Use it when:
- You need to store sensitive data (secrets, tokens, keys) that should never touch disk — even temporarily
- You need a fast scratch space for temporary files that an application writes and reads frequently
- A container processes sensitive data you want to ensure is completely gone when the container stops

Example:
```bash
# The /run/secrets path is in RAM only — never written to disk
docker run \
  --mount type=tmpfs,target=/run/secrets,tmpfs-mode=0700 \
  myapp
```

Tmpfs mounts are automatically destroyed when the container stops. They're not shared between containers and can't be inspected from outside.

---

## Intermediate

**Q4: What is volume pre-population and how does it work?**

When you mount an **empty named volume** to a path that has files in the container image, Docker copies the image's files into the volume before the container starts. This only happens once — the first time — when the volume is empty.

```bash
# First run: pgdata volume is empty
# Docker copies postgres's default data directory files into pgdata
docker run -v pgdata:/var/lib/postgresql/data postgres:16
# Postgres initializes in that volume

# Second run: pgdata volume already has data
# Docker does NOT overwrite — uses what's there
docker run -v pgdata:/var/lib/postgresql/data postgres:16
```

This is why Postgres works correctly with a named volume on first run. The image has default initialization files at `/var/lib/postgresql/data`, and Docker seeds the volume with them.

Important: this pre-population does NOT happen with bind mounts. If you bind-mount a host directory to a container path, the host directory's contents completely overlay the image path — if the host directory is empty, the container sees an empty path.

---

**Q5: Why is `--mount` preferred over `-v` for new code and scripts?**

The `-v` syntax is terse and does different things depending on what you pass:
- `docker run -v myname:/path` → named volume
- `docker run -v /host/path:/path` → bind mount
- `docker run -v /path` → anonymous volume

The distinction between a named volume and a bind mount depends entirely on whether you used an absolute path or just a name — easy to mix up, and easy to misread.

`--mount` is explicit:
```bash
# Named volume — obviously a volume
docker run --mount type=volume,source=mydata,target=/data

# Bind mount — obviously binding to host
docker run --mount type=bind,source=/host/path,target=/data

# Read-only — clearly labeled
docker run --mount type=bind,source=/config,target=/config,readonly
```

Additionally, `--mount` provides better error messages. With `-v`, if you accidentally specify a relative path as a bind mount source, Docker silently creates a volume with that relative path as its name. With `--mount type=bind`, Docker returns an error if the source path doesn't exist.

---

**Q6: You're running a development Node.js app in Docker using a bind mount. Performance is terrible on macOS. Why? What can you do?**

On macOS (and Windows), Docker Desktop runs containers inside a Linux VM. Bind mounts require files to be shared between your macOS filesystem and the Linux VM, going through a filesystem sync layer (VirtioFS on newer Docker Desktop, osxfs on older versions). Every file read/write by the container has to cross this VM boundary, which adds latency.

This is especially painful for Node.js because `node_modules` can contain hundreds of thousands of small files, and the filesystem sync overhead multiplies.

**Solutions:**

1. **Use a named volume for `node_modules`** (avoid syncing this directory from host to VM):
```bash
docker run \
  -v $(pwd)/src:/app/src \            # bind mount only source code
  -v node_modules:/app/node_modules \ # named volume (inside VM — fast!)
  myapp
```

2. **Use Docker's VirtioFS** (faster than old osxfs). Enable in Docker Desktop settings: General → "Use VirtioFS for file sharing." Requires newer Docker Desktop.

3. **Use "delegated" cache mode** (deprecated/removed in newer Docker, but was: `-v $(pwd):/app:delegated`).

4. **For production-like testing, avoid bind mounts entirely** — build the image and run it, don't bind-mount source.

---

## Advanced

**Q7: How would you back up and restore a Docker named volume?**

Named volumes are just directories on the host. The simplest backup technique uses a temporary container to access the volume and create an archive:

```bash
# BACKUP: run a temporary alpine container
# - mount the source volume read-only at /source
# - mount the current directory at /backup
# - tar up /source into /backup/mydata.tar.gz
docker run --rm \
  -v mydata:/source:ro \
  -v $(pwd):/backup \
  alpine \
  tar czf /backup/mydata-backup.tar.gz -C /source .

# The backup file appears at ./mydata-backup.tar.gz on your host
```

```bash
# RESTORE: create a fresh volume and unpack the archive into it
docker volume create mydata-restored

docker run --rm \
  -v mydata-restored:/target \
  -v $(pwd):/backup:ro \
  alpine \
  tar xzf /backup/mydata-backup.tar.gz -C /target

# Verify
docker run --rm -v mydata-restored:/data alpine ls /data
```

This technique works because Docker volumes are just directories — `tar` doesn't care whether the path is backed by a volume or a regular filesystem.

For database backups specifically, use the database's dump tools (pg_dump, mysqldump) rather than raw filesystem backups, which produce portable SQL that works across versions.

---

**Q8: Explain volume drivers. When would you use a non-local volume driver in production?**

By default, named volumes use the `local` driver — data is stored on the host's local disk. Volume drivers are plugins that replace `local` with other storage backends.

You'd use a non-local volume driver in production when:

1. **High availability / failover:** You need containers on multiple hosts to access the same data. If container A on host 1 fails and container B starts on host 2, they need to share the same volume. Local storage can't do this — the data is on host 1's disk. NFS or distributed storage (Portworx, GlusterFS) can.

2. **Cloud storage integration:** You want persistent volumes backed by cloud block storage (AWS EBS, GCP Persistent Disk, Azure Disk) that can survive host replacement. These are typically managed by your Kubernetes storage classes, not Docker volume drivers directly.

3. **Shared storage for stateless workers:** Multiple containers on multiple hosts all writing to the same S3-backed or NFS-backed volume (e.g., shared uploads folder).

Example with NFS using the built-in local driver:
```bash
docker volume create \
  --driver local \
  --opt type=nfs4 \
  --opt o=addr=nfs-server.example.com,rw,nfsvers=4 \
  --opt device=:/exports/myapp \
  nfs-appdata

docker run -v nfs-appdata:/data myapp
```

---

**Q9: What happens when you mount a volume to a path that already has files in the container image? What about a bind mount?**

**Named volume (empty, first mount):** Docker copies the image's files into the volume before the container starts. The container sees both the original image files AND has a persistent volume for future writes.

**Named volume (already has data):** Docker uses the existing volume contents. The image's original files at that path are shadowed by the volume — if the volume has different files, the container sees the volume's version.

**Bind mount:** The host directory completely overlays the container path — no copying. If the host directory is empty, the container sees an empty directory, even if the image had files there. This is a common footgun: developers bind-mount an empty directory expecting the image's files to show through, but they don't.

```bash
# This WORKS: named volume pre-populates on first run
docker run -v mydb:/var/lib/postgresql/data postgres:16

# This does NOT work as expected: bind mount hides the postgres data directory
docker run -v /empty/host/dir:/var/lib/postgresql/data postgres:16
# Postgres will fail — it sees an empty data directory, no config files
```

---

**Q10: How would you design persistent storage for a stateful application deployed across multiple hosts without a shared filesystem?**

Without shared storage, you have several architectural options:

1. **Stateful services on dedicated nodes with local volumes:** Use Docker Swarm/Kubernetes to pin the stateful container to a specific node. Use a local named volume on that node. The trade-off: if that node dies, you lose the data (without backup) and need manual recovery.

2. **Replicated distributed databases:** Instead of having Docker share one filesystem, run databases that replicate internally. PostgreSQL with streaming replication, Redis Sentinel, MongoDB replica sets — data is replicated across nodes at the application layer, not the filesystem layer.

3. **Cloud-native persistent volumes:** In cloud environments (EKS, GKE, AKS), use the cloud provider's storage classes (AWS EBS, GCP Persistent Disk). These volumes can be detached from one node and attached to another. The orchestrator handles the mount/unmount lifecycle during failover. The volume is not truly "shared" between nodes simultaneously — only one node mounts it at a time, but it can be moved.

4. **External object storage:** For uploads, media, and documents, don't put them on a volume at all. Use S3-compatible object storage (AWS S3, MinIO). The application reads and writes to the object store via API — no filesystem sharing needed. Multiple container instances on multiple hosts all access the same data through the S3 API.

Option 4 (external object store) is the most scalable and cloud-native approach for most data types. Options 2 and 3 cover database state.

---

**Q11: How do you share data between two containers using a volume?**

Named volumes can be mounted in multiple containers simultaneously. All containers see the same underlying directory at their respective mount points.

```bash
# Create a shared volume
docker volume create shared-logs

# Application container writes logs to the volume
docker run -d --name app \
  -v shared-logs:/var/log/myapp \
  myapp-image

# Log processor reads from the same volume (read-only)
docker run -d --name log-shipper \
  -v shared-logs:/var/log/myapp:ro \
  filebeat:8
```

In Docker Compose, this is the sidecar pattern:

```yaml
services:
  app:
    image: myapp
    volumes:
      - logs:/var/log/myapp

  shipper:
    image: filebeat:8
    volumes:
      - logs:/var/log/myapp:ro
      - ./filebeat.yml:/usr/share/filebeat/filebeat.yml:ro

volumes:
  logs:
```

**Critical warning:** Docker volumes provide no file locking. If two containers write to the same file concurrently, the result is undefined — you can get corrupt data. Safe patterns: one writer + multiple read-only readers, or use separate subdirectories per container with one aggregator.

---

**Q12: What is an anonymous volume, and how is it different from a named volume?**

An anonymous volume is created by Docker automatically when:
1. A Dockerfile declares a `VOLUME /path` instruction
2. You run `docker run -v /path` with no name (just a container path, no `name:` prefix)

Docker generates a random ID for it (a long hex string), and it behaves exactly like a named volume — except you didn't choose the name, so it's hard to reference later.

```bash
# Anonymous volume — Docker picks a name
docker run -v /data myapp
docker volume ls   # shows something like "a3f8c2d1..." with no friendly name

# Named volume — you pick the name
docker run -v mydata:/data myapp
docker volume ls   # shows "mydata"
```

Key difference in lifecycle:
- **Named volumes** survive `docker rm` and `docker-compose down` (unless `-v` is passed).
- **Anonymous volumes** are considered disposable. `docker rm -v container` removes both the container and its anonymous volumes. `docker-compose down` removes them too (even without `-v`).

**Dockerfile `VOLUME` instruction:** When an image has `VOLUME /data`, Docker creates an anonymous volume for that path on every `docker run` unless you explicitly mount something there. This ensures the data path is a volume, but since it's anonymous, you need to name it at run time if you want to keep the data:

```bash
# Without -v: anonymous volume created, data lost on docker rm
docker run myapp-with-volume-directive

# With -v: named volume used instead, data persists
docker run -v mydata:/data myapp-with-volume-directive
```

---

## 📂 Navigation

**In this folder:**
| File | |
|---|---|
| [📖 Theory.md](./Theory.md) | Full explanation |
| [⚡ Cheatsheet.md](./Cheatsheet.md) | Quick reference |
| 🎯 **Interview_QA.md** | ← you are here |
| [💻 Code_Example.md](./Code_Example.md) | Working code |

⬅️ **Prev:** [Container Lifecycle](../06_Containers_Lifecycle/Interview_QA.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Networking](../08_Networking/Theory.md)
🏠 **[Home](../../README.md)**
