# Images and Layers — Interview Q&A

## Beginner

**Q1: What is a Docker image?**

A Docker image is a read-only, layered template for creating containers. Think of it like a class in object-oriented programming — you instantiate it to create containers (the objects). The image contains everything the application needs: the OS libraries it depends on, the runtime, the application code, and metadata describing how to run it (entry point, environment variables, exposed ports).

Images are immutable — once built, they don't change. Any time you want to update an image, you build a new one. This immutability is what makes them reliable as deployment artifacts.

---

**Q2: What is the difference between an image tag and a digest?**

A **tag** is a mutable, human-readable label — like `nginx:1.25.3` or `myapp:latest`. The word "mutable" is key: a tag can be updated to point to a different underlying image at any time. Whoever controls the repository can push a new image under the same tag. This is why `nginx:latest` today might be a different image than `nginx:latest` next week.

A **digest** is an immutable, content-addressed identifier — a SHA256 hash of the image manifest. `nginx@sha256:d711f485f2dd...` will always refer to exactly that specific image content, forever. If you need guaranteed reproducibility, use digests.

Best practice: use version tags during development (easier to read), use digests or immutable version tags (like `nginx:1.25.3`) in production Dockerfiles and deployment configs.

---

**Q3: What are dangling images and how do you clean them up?**

Dangling images are layers that have no tag and aren't referenced by any other image. They appear as `<none>:<none>` in `docker images` output. They accumulate when you rebuild images — each rebuild produces a new image ID, and the old image loses its tag to the new one, becoming dangling.

They waste disk space but are otherwise harmless.

```bash
# See dangling images
docker images --filter dangling=true

# Remove dangling images
docker image prune

# Remove ALL unused images (not just dangling)
docker image prune -a

# Full disk audit
docker system df
```

---

**Q4: What does `docker pull` actually download?**

When you run `docker pull nginx`, Docker:

1. Contacts the registry (Docker Hub by default) and fetches the **image manifest** — a JSON document listing all the layers in the image and their SHA256 digests.
2. Checks which layers already exist locally (by digest).
3. Downloads only the layers that are missing (printing "Pull complete" for each downloaded layer and "Already exists" for cached ones).
4. Decompresses and stores each layer.

The manifest and layers are stored in `/var/lib/docker/` (or inside the Docker Desktop VM). The next time you pull a different image that shares a layer (e.g., another Python-based image), that shared layer is reused — downloaded only once.

---

## Intermediate

**Q5: Explain how Docker's layer cache works for build performance. How would you structure a Dockerfile to maximize cache hits?**

Docker's build cache is keyed on the Dockerfile instruction plus the state of all layers below it. The rule: if a layer changes (or any layer below it changes), that layer and all subsequent layers are rebuilt from scratch, ignoring the cache.

For maximum cache hits:

1. **Put the most stable instructions first** (base image, system package installs).
2. **Copy dependency manifests before source code** — copy only `package.json` / `requirements.txt` / `go.mod` first, install dependencies, then copy the rest of the source code. This way, dependencies are reinstalled only when they change, not every time you save a `.js` or `.py` file.
3. **Avoid instructions that change frequently early in the file** — things like `COPY . .` should be near the end.
4. **Be careful with `RUN apt update`** — it will always run if cache is busted above it, but changes its output each day. Combine it with the install command: `RUN apt update && apt install -y curl`.

```dockerfile
# Maximizing cache for a Python app
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .    # only this file — cache busts only when deps change
RUN pip install -r requirements.txt
COPY . .                   # copy source last — cache busts on every code change
CMD ["python", "app.py"]
```

---

**Q6: What is the difference between `docker image inspect` and `docker history`?**

`docker history <image>` shows the **build history** — the list of Dockerfile instructions (layers) that created the image, their timestamps, and the disk size of each layer. It's a build-time view, focused on how the image was constructed.

`docker inspect <image>` shows the **full metadata** of the image: the complete JSON manifest including architecture, OS, environment variables, entrypoint, cmd, working directory, exposed ports, labels, volume definitions, and the list of layer digests (but not the Dockerfile commands). It's a runtime-configuration view.

Use `history` when you want to understand what's in an image or debug layer sizes. Use `inspect` when you want to know how a container from this image will be configured.

---

**Q7: You're told your Docker builds are slow because `npm install` runs on every build even when `package.json` hasn't changed. Diagnose and fix this.**

The problem is almost certainly that `COPY . .` (copying all source files) appears *before* `RUN npm install` in the Dockerfile. Because the source files change on every commit, that `COPY` layer is never cached, and every layer after it (including `npm install`) is rebuilt.

Diagnosis:
```bash
docker build --progress=plain .  # see which layers say "CACHED" vs rebuilding
docker history myapp:latest      # see which layers are large (npm install should be big)
```

Fix: split the COPY instruction — copy the package files first, install, then copy source:

```dockerfile
# Before (slow)
FROM node:20-alpine
WORKDIR /app
COPY . .                          # any .js change busts cache here...
RUN npm ci                        # ...so this ALWAYS runs

# After (fast)
FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json ./   # only copy dependency manifests
RUN npm ci                        # cached until package*.json changes
COPY . .                          # source changes only rebuild this layer
CMD ["node", "src/index.js"]
```

With the fix, `npm ci` is cached for every build where `package.json` and `package-lock.json` are unchanged — which is most builds during normal development.

---

## Advanced

**Q8: How does the OverlayFS "upperdir" / "lowerdir" / "merged" architecture work concretely for a running Docker container?**

When Docker starts a container from an image with N layers, it sets up an OverlayFS mount like this:

```
mount -t overlay overlay \
  -o lowerdir=/var/lib/docker/overlay2/LAYER_N:...:/var/lib/docker/overlay2/LAYER_1,\
     upperdir=/var/lib/docker/overlay2/CONTAINER_HASH/diff,\
     workdir=/var/lib/docker/overlay2/CONTAINER_HASH/work \
  /var/lib/docker/overlay2/CONTAINER_HASH/merged
```

- **lowerdir:** colon-separated list of read-only image layer directories, ordered top to bottom
- **upperdir:** the container's writable directory — all new writes go here
- **workdir:** a scratch directory OverlayFS requires internally for atomic operations
- **merged:** the unified view the container process sees (its `/`)

When the container reads `/etc/nginx/nginx.conf`:
- OverlayFS checks the upperdir first (no, not modified)
- Then walks down the lowerdir stack until it finds the file in the nginx image's layer
- Returns that file

When the container writes to `/etc/nginx/nginx.conf`:
- OverlayFS copies the file from lowerdir to upperdir (copy-on-write)
- Writes the modification to the upperdir copy
- Future reads see the upperdir version

When the container is deleted, `docker rm` deletes the upperdir. The lowerdir image layers remain untouched for future container instances.

---

**Q9: What is a multi-platform (multi-arch) image manifest, and how does Docker choose the right image automatically?**

A multi-platform image is stored in a registry as an **OCI image index** (also called a "fat manifest") — a top-level manifest that contains a list of platform-specific manifest references:

```json
{
  "schemaVersion": 2,
  "mediaType": "application/vnd.oci.image.index.v1+json",
  "manifests": [
    {
      "mediaType": "application/vnd.oci.image.manifest.v1+json",
      "digest": "sha256:abc...",
      "platform": { "os": "linux", "architecture": "amd64" }
    },
    {
      "mediaType": "application/vnd.oci.image.manifest.v1+json",
      "digest": "sha256:def...",
      "platform": { "os": "linux", "architecture": "arm64" }
    }
  ]
}
```

When you pull `nginx` on an `amd64` machine, Docker fetches the image index, reads the platform list, and automatically selects and downloads the `amd64` variant. On an M2 Mac (arm64), it selects the `arm64` variant. Same tag, automatic selection.

You can override with `--platform`:
```bash
docker pull --platform linux/amd64 nginx
```

This is useful in CI: if your CI runner is ARM64 but your production is AMD64, you want to build and test the AMD64 image explicitly.

---

**Q10: What is image squashing and when would you use it? What are the trade-offs?**

Image squashing merges all of an image's layers into a single layer. You can do this with BuildKit using multi-stage builds (copy everything from a builder into a fresh final stage) or with `docker build --squash` (experimental flag).

**Why squash?**
- Remove secrets or large files that were added in one layer and deleted in a later layer (deleted files still exist in the lower layer even if whiteout markers hide them — squashing truly removes them)
- Reduce the number of layers (marginally simpler to inspect)
- Shrink images where many temp files were created and deleted during build

**Trade-offs against squashing:**
- **No layer sharing:** a squashed image has a unique single layer. If 100 containers use `ubuntu:22.04` as their base, they share that base layer. If you squash your app image, your app's single layer is unique — no sharing with other images.
- **Slower pulls:** the entire image must be pulled each time (no "Already exists" layer optimization)
- **Larger diffs on update:** updating the app re-downloads the entire single layer

Better practice: use multi-stage builds to produce a clean final image from scratch — you get a minimal image without the squash trade-offs.

---

## 📂 Navigation

**In this folder:**
| File | |
|---|---|
| [📖 Theory.md](./Theory.md) | Full explanation |
| [⚡ Cheatsheet.md](./Cheatsheet.md) | Quick reference |
| 🎯 **Interview_QA.md** | ← you are here |
| [💻 Code_Example.md](./Code_Example.md) | Working code |

⬅️ **Prev:** [03 — Installation and Setup](../03_Installation_and_Setup/Interview_QA.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [05 — Dockerfile](../05_Dockerfile/Interview_QA.md)
🏠 **[Home](../../README.md)**
