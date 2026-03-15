# Images and Layers — Code Examples

All commands below are runnable. Replace placeholder values (registry URLs, usernames) with your own where marked.

---

## 1. Pull an Image and Explore It

```bash
# Pull the official nginx image (latest tag)
docker pull nginx

# Pull a specific version — better practice for reproducibility
docker pull nginx:1.25.3

# Pull by digest — the most reproducible option (immutable)
# Use 'docker inspect' or 'docker pull nginx:1.25.3' first to get the digest,
# then pin with the digest for production use:
docker pull nginx@sha256:d711f485f2dd1dee407a80973c8f129f00d54604d2c90732e8e320e5038a0348

# List all locally available nginx images
docker images nginx

# Show ALL local images including their digests
docker images --digests nginx
```

---

## 2. Inspect Layer History with `docker history`

```bash
# Show all layers of the nginx image, newest layer first
# Columns: IMAGE (layer hash), CREATED, CREATED BY (Dockerfile instruction), SIZE, COMMENT
docker history nginx

# Don't truncate the "CREATED BY" column — show full Dockerfile commands
docker history --no-trunc nginx

# Custom format: just show size and command (useful for finding fat layers)
docker history --format "{{printf \"%-10s\" .Size}}\t{{.CreatedBy}}" nginx | head -20

# Compare layers across two versions of the same image
echo "=== nginx:1.24 ===" && docker history nginx:1.24
echo "=== nginx:1.25 ===" && docker history nginx:1.25
```

**What to look for in `docker history`:**
- Layers with 0B size are metadata-only (ENV, EXPOSE, CMD, etc.)
- Large layers usually contain package installs or large file copies
- A layer that adds then deletes files will show the ADD size — the deleted content still takes space in the layer (this is why multi-stage builds help)

---

## 3. Inspect Image Metadata with `docker inspect`

```bash
# Full image metadata as pretty-printed JSON
docker inspect nginx

# Extract specific fields using Go template syntax

# When was this image built?
docker inspect --format '{{.Created}}' nginx

# What architecture is this image for?
docker inspect --format '{{.Architecture}} / {{.Os}}' nginx

# What environment variables are baked into the image?
docker inspect --format '{{json .Config.Env}}' nginx | python3 -m json.tool

# What's the entry point?
docker inspect --format '{{json .Config.Entrypoint}}' nginx | python3 -m json.tool

# What's the default CMD?
docker inspect --format '{{json .Config.Cmd}}' nginx | python3 -m json.tool

# What ports does this image expose?
docker inspect --format '{{json .Config.ExposedPorts}}' nginx | python3 -m json.tool

# List all layer SHAs that make up this image
docker inspect --format '{{json .RootFS.Layers}}' nginx | python3 -m json.tool

# All labels
docker inspect --format '{{json .Config.Labels}}' nginx | python3 -m json.tool
```

---

## 4. Tag and Retag an Image

```bash
# Pull an image to use as our starting point
docker pull python:3.11-slim

# Create a new tag pointing to the same image
# Useful for: pushing to your own registry, versioning, aliasing
docker tag python:3.11-slim myregistry.example.com/base/python:3.11-slim

# Verify: both tags point to the same Image ID
docker images python
docker images myregistry.example.com/base/python

# You can also tag by Image ID
IMAGE_ID=$(docker inspect --format '{{.Id}}' python:3.11-slim | cut -c8-19)
docker tag $IMAGE_ID myapp/python-base:latest

# Tag with a date stamp (useful for manual versioning)
DATE_TAG=$(date +%Y%m%d)
docker tag myapp:latest myapp:$DATE_TAG

# List all tags for 'myapp' locally
docker images myapp
```

---

## 5. Push an Image to a Registry

```bash
# Before pushing, you must log in to the registry

# Docker Hub
docker login
# Enter your Docker Hub username and password/token

# AWS ECR (replace with your account ID and region)
# aws ecr get-login-password --region us-east-1 | \
#   docker login --username AWS --password-stdin \
#   123456789012.dkr.ecr.us-east-1.amazonaws.com

# GitHub Container Registry
# echo $GITHUB_TOKEN | docker login ghcr.io --username YOUR_GITHUB_USERNAME --password-stdin

# Tag your image for the target registry
# Replace 'yourusername' with your actual Docker Hub username
docker tag nginx:1.25.3 yourusername/my-nginx:1.25.3
docker tag nginx:1.25.3 yourusername/my-nginx:latest

# Push both tags
docker push yourusername/my-nginx:1.25.3
docker push yourusername/my-nginx:latest

# Or push all tags at once
docker push --all-tags yourusername/my-nginx

# Verify the push by pulling it back (from a clean state)
docker rmi yourusername/my-nginx:1.25.3   # remove local copy
docker pull yourusername/my-nginx:1.25.3  # re-download from registry
```

---

## 6. Inspect OverlayFS Layers on Disk (Linux only)

```bash
# This shows the actual filesystem structure Docker uses to store images
# Note: requires access to /var/lib/docker (usually needs sudo)

# See overall disk usage
docker system df
docker system df -v   # verbose: per-image and per-container breakdown

# List the overlay2 directories (each directory is a layer)
sudo ls /var/lib/docker/overlay2/ | head -20

# Pick a layer directory and look inside
LAYER_DIR=$(sudo ls /var/lib/docker/overlay2/ | head -1)
sudo ls /var/lib/docker/overlay2/$LAYER_DIR/

# Typically contains:
#   diff/   — the actual filesystem changes for this layer
#   link    — a short name used in OverlayFS lowerdir
#   lower   — contains the link names of layers below this one
#   work/   — OverlayFS working directory (for writable/container layers)
#   merged/ — the merged view (only present on running containers)

sudo ls /var/lib/docker/overlay2/$LAYER_DIR/diff/
```

---

## 7. Layer Cache Demonstration

```bash
# Create a test directory
mkdir /tmp/cache-demo && cd /tmp/cache-demo

# Create a simple requirements file
cat > requirements.txt << 'EOF'
flask==3.0.0
requests==2.31.0
EOF

# Create a simple app
cat > app.py << 'EOF'
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello from Docker!'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
EOF

# Write a Dockerfile with GOOD cache ordering
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Step 1: Copy ONLY the requirements file
# This layer is cached as long as requirements.txt doesn't change
COPY requirements.txt .

# Step 2: Install dependencies
# This expensive step uses the cache whenever requirements.txt is unchanged
RUN pip install --no-cache-dir -r requirements.txt

# Step 3: Copy source code last
# Changes to app.py only rebuild this layer and those below it
COPY app.py .

CMD ["python", "app.py"]
EOF

# First build (no cache — everything runs)
echo "=== First build (no cache) ==="
time docker build -t cache-demo:v1 .

# Second build with no changes (everything should be cached)
echo "=== Second build (no changes — all cached) ==="
time docker build -t cache-demo:v2 .

# Simulate changing only app code (not dependencies)
echo "# updated" >> app.py

echo "=== Third build (app.py changed — only last COPY rebuilds) ==="
time docker build -t cache-demo:v3 .

# Check build history to see layer sizes
docker history cache-demo:v1

# Clean up
cd /tmp && rm -rf /tmp/cache-demo
docker rmi cache-demo:v1 cache-demo:v2 cache-demo:v3 2>/dev/null || true
```

---

## 8. Cleanup: Dangling Images and Disk Reclamation

```bash
# See what's taking up space
docker system df

# List dangling images (shows as <none>:<none>)
docker images --filter dangling=true

# Remove only dangling images
docker image prune
# Confirm with: y

# Remove ALL images not used by at least one container
docker image prune -a
# WARNING: this removes everything not currently running — repull needed

# Targeted cleanup: remove images older than 48 hours that aren't tagged
docker image prune -a --filter "until=48h"

# Remove a specific image
docker rmi nginx:1.24

# See what docker system prune would remove (dry run simulation)
# Note: docker doesn't have a built-in dry-run, but you can check individually:
docker images --filter dangling=true      # images to be removed
docker ps -a --filter status=exited       # containers to be removed
docker volume ls --filter dangling=true   # volumes to be removed
docker network ls --filter type=custom    # networks to be removed

# Nuclear cleanup: remove everything unused
docker system prune -a --volumes
# This removes: stopped containers, unused networks, all unused images, build cache, unused volumes

# Verify disk reclaimed
docker system df
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

⬅️ **Prev:** [03 — Installation and Setup](../03_Installation_and_Setup/Theory.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [05 — Dockerfile](../05_Dockerfile/Code_Example.md)
🏠 **[Home](../../README.md)**
