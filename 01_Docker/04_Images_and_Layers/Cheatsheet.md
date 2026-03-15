# Images and Layers — Cheatsheet

## Core Image Commands

```bash
# Pull images
docker pull nginx                          # pull latest tag
docker pull nginx:1.25.3                   # pull specific tag
docker pull nginx@sha256:<digest>          # pull by digest (immutable)
docker pull --platform linux/amd64 nginx   # pull specific platform

# List images
docker images                              # all local images
docker images nginx                        # filter by name
docker images --digests                    # show digest column
docker images -q                           # quiet: only image IDs
docker images --filter dangling=true       # untagged images only
docker images --filter "label=env=prod"    # filter by label

# Inspect
docker inspect <image>                     # full metadata (JSON)
docker inspect --format '{{.Id}}' <image> # extract single field
docker history <image>                     # show layers + commands
docker history --no-trunc <image>          # full commands, not truncated

# Tagging
docker tag nginx myrepo/nginx:1.25.3       # add new tag to existing image
docker tag <image-id> myrepo/app:latest    # tag by ID

# Push
docker push myrepo/app:1.0                 # push to registry
docker push myrepo/app --all-tags          # push all tags

# Remove
docker rmi nginx                           # remove image by tag
docker rmi <image-id>                      # remove by ID
docker image prune                         # remove dangling images
docker image prune -a                      # remove all unused images
docker image prune -a --filter "until=24h" # unused images older than 24h

# Cleanup everything
docker system prune -a                     # images + containers + networks + build cache
docker system df                           # disk usage summary
docker system df -v                        # per-item breakdown
```

---

## Image Naming: Full Format

```
[registry/][namespace/]repository[:tag][@digest]
```

| Short form | Expands to |
|---|---|
| `nginx` | `docker.io/library/nginx:latest` |
| `nginx:1.25` | `docker.io/library/nginx:1.25` |
| `user/app` | `docker.io/user/app:latest` |
| `ghcr.io/org/app:v1` | GitHub Container Registry |
| `123.dkr.ecr.us-east-1.amazonaws.com/app:v1` | AWS ECR |

---

## Tags vs Digests vs Image IDs

| Identifier | Example | Mutable? | Use case |
|---|---|---|---|
| **Tag** | `nginx:1.25.3` | Yes (tag can be updated) | Human-readable, development |
| **Image ID** | `a8780b506fa4` | N/A (local only) | Local inspection only |
| **Digest** | `nginx@sha256:d711...` | No (content-addressed) | Production pinning, security |

Always use digests or specific version tags (not `latest`) in production Dockerfiles and deployment manifests.

---

## Layer Caching Rules

| Rule | Example |
|---|---|
| Cache hit: instruction unchanged + all parents cached | Identical `RUN apt install` with same preceding layers |
| Cache miss: any instruction changed | Edited `RUN` command, changed `ENV` value |
| Cache miss: `COPY`/`ADD` file changed | Any source file modified |
| All layers after miss: also miss | Changing layer 3 rebuilds layers 4, 5, 6... |

**Order strategy: stable → changing**

```
FROM [rarely changes]
RUN apt install [infrequently changes]
COPY requirements.txt [changes when deps change]
RUN pip install [cached if requirements.txt unchanged]
COPY . . [changes every commit]
```

---

## Useful `docker inspect` Format Strings

```bash
# Image creation date
docker inspect --format '{{.Created}}' nginx

# Image architecture
docker inspect --format '{{.Architecture}}' nginx

# Working directory set in image
docker inspect --format '{{.Config.WorkingDir}}' nginx

# Entrypoint
docker inspect --format '{{json .Config.Entrypoint}}' nginx

# Default CMD
docker inspect --format '{{json .Config.Cmd}}' nginx

# All labels
docker inspect --format '{{json .Config.Labels}}' nginx | jq .

# Layer digests
docker inspect --format '{{json .RootFS.Layers}}' nginx | jq .
```

---

## Multi-Platform Images

```bash
# Inspect supported platforms for an image
docker buildx imagetools inspect nginx

# Pull specific platform
docker pull --platform linux/arm64 nginx

# Build and push multi-platform image
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag myrepo/app:latest \
  --push .
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

⬅️ **Prev:** [03 — Installation and Setup](../03_Installation_and_Setup/Cheatsheet.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [05 — Dockerfile](../05_Dockerfile/Cheatsheet.md)
🏠 **[Home](../../README.md)**
