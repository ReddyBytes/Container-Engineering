# Dockerfile — Code Examples

All examples are production-quality with detailed comments explaining every decision.

---

## 1. Simple Python Flask App (Best Practices)

```
project/
├── app.py
├── requirements.txt
└── Dockerfile
```

**`requirements.txt`**
```
flask==3.0.0
gunicorn==21.2.0
```

**`app.py`**
```python
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({"status": "ok", "message": "Hello from Docker!"})

@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

**`Dockerfile`**
```dockerfile
# ============================================================
# Stage 1 (only stage): Build and run the Flask app
# ============================================================

# Use a specific version tag — never 'latest' in production
# 'slim' variant: Debian base, Python only — no extra packages
FROM python:3.11-slim

# WORKDIR creates the directory if it doesn't exist,
# and sets it as the CWD for all subsequent instructions.
# Use an absolute path — /app is the conventional choice.
WORKDIR /app

# -----------------------------------------------
# LAYER CACHING OPTIMIZATION: install deps first
#
# Copy ONLY the requirements file before copying source code.
# This layer is cached as long as requirements.txt doesn't change.
# If we did COPY . . first, any .py file change would bust this cache
# and re-run pip install — which is slow.
# -----------------------------------------------
COPY requirements.txt .

# Install dependencies.
# --no-cache-dir: don't save pip's download cache to disk (smaller image)
# Using the cached layer until requirements.txt changes.
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the application source code.
# This layer is invalidated on every code change —
# but that's fine because pip install (the expensive step) is already cached above.
COPY app.py .

# -----------------------------------------------
# SECURITY: Don't run as root
#
# Create a system user with:
# --system: no home dir, disabled login, UID in system range (< 1000)
# --no-create-home: no /home/appuser directory
# --shell: set to nologin to prevent direct logins
# -----------------------------------------------
RUN useradd --system --no-create-home --shell /usr/sbin/nologin appuser

# Switch to the non-root user.
# All subsequent RUN, CMD, ENTRYPOINT run as this user.
USER appuser

# EXPOSE is documentation — it tells users and tooling what port the app uses.
# It does NOT publish the port; -p flag at runtime does that.
EXPOSE 5000

# HEALTHCHECK: tells Docker how to determine if this container is healthy.
# --interval=30s: check every 30 seconds
# --timeout=5s: fail the check if it takes more than 5 seconds
# --start-period=10s: give the app 10 seconds to start before checks count
# --retries=3: mark unhealthy after 3 consecutive failures
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" \
    || exit 1

# ENTRYPOINT: exec form — python is PID 1, receives signals directly.
# Using gunicorn for production (multi-worker WSGI server, not Flask dev server).
# The Flask dev server (app.run) is NOT for production.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
```

**Build and run:**
```bash
cd project/

# Build the image
docker build -t myflask:1.0 .

# Run it (maps host port 5000 to container port 5000)
docker run -d --name myflask -p 5000:5000 myflask:1.0

# Test it
curl http://localhost:5000/
curl http://localhost:5000/health

# Check health status
docker inspect --format '{{.State.Health.Status}}' myflask

# Stop and remove
docker stop myflask && docker rm myflask
```

---

## 2. Node.js App with Proper Cache-Busting

```
node-app/
├── src/
│   └── index.js
├── package.json
├── package-lock.json
├── Dockerfile
└── .dockerignore
```

**`package.json`**
```json
{
  "name": "my-node-app",
  "version": "1.0.0",
  "scripts": {
    "start": "node src/index.js"
  },
  "dependencies": {
    "express": "^4.18.2"
  }
}
```

**`src/index.js`**
```javascript
const express = require('express');
const app = express();
const PORT = process.env.PORT || 3000;

app.get('/', (req, res) => {
  res.json({ status: 'ok', message: 'Hello from Node.js in Docker!' });
});

app.get('/health', (req, res) => {
  res.json({ status: 'healthy' });
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Server listening on port ${PORT}`);
});
```

**`Dockerfile`**
```dockerfile
# Use a specific Node.js LTS version on Alpine (very small base image)
# Alpine-based images are ~50MB; full node images can be ~1GB
FROM node:20-alpine

# Set working directory
WORKDIR /app

# -----------------------------------------------
# KEY: copy package files BEFORE source code
#
# package.json and package-lock.json define dependencies.
# npm ci only re-runs when these files change.
# Changing index.js does NOT re-run npm ci.
# This is the #1 Docker optimization for Node.js apps.
# -----------------------------------------------
COPY package.json package-lock.json ./

# npm ci = clean install (respects package-lock.json exactly, faster in CI)
# --omit=dev: skip devDependencies in production image
RUN npm ci --omit=dev

# Now copy application source
# Changes here only rebuild this layer and below
COPY src/ ./src/

# Create and switch to non-root user
# Alpine uses addgroup/adduser (not useradd which is Debian-specific)
RUN addgroup -S appgroup && adduser -S -G appgroup appuser
USER appuser

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost:3000/health || exit 1

# node is PID 1, receives signals, can gracefully shut down
CMD ["node", "src/index.js"]
```

**`.dockerignore`**
```
# Never include these
.git
.gitignore
.env
.env.*
*.log
*.md

# Node modules go inside the container, not from host
# (They may be for different OS/arch than the container)
node_modules

# Docker files themselves
Dockerfile
.dockerignore
docker-compose*.yml

# Dev artifacts
coverage/
.nyc_output/
dist/
```

**Build and run:**
```bash
# Build
docker build -t mynode:1.0 .

# Run with environment variable override
docker run -d \
  --name mynode \
  -p 3000:3000 \
  -e PORT=3000 \
  mynode:1.0

# Test cache behavior: change only source code
echo "// updated" >> src/index.js
time docker build -t mynode:1.1 .
# You should see: npm ci step says "CACHED"
```

---

## 3. Non-Root User — Multiple Approaches

```dockerfile
# ============================================================
# Approach A: useradd (Debian/Ubuntu-based images)
# ============================================================
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create system user with specific UID (makes host-side chown easier)
RUN useradd --uid 1001 --system --no-create-home appuser

# Copy files with ownership pre-set (avoids a separate chown RUN)
COPY --chown=1001:1001 . .

USER 1001   # use UID, not name — more robust (name might not exist in base image)

CMD ["python", "app.py"]


# ============================================================
# Approach B: adduser (Alpine-based images)
# Alpine uses BusyBox adduser, different syntax
# ============================================================
FROM python:3.11-alpine

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# -S = system user, -G = group, -D = no password, -H = no home dir
RUN addgroup -S appgroup && \
    adduser -S -u 1001 -G appgroup -H -D appuser

COPY --chown=1001:1001 . .
USER 1001

CMD ["python", "app.py"]


# ============================================================
# Approach C: Use a pre-built non-root base image
# Google's 'distroless' images come with a nonroot user
# distroless has no shell, no package manager — minimal attack surface
# ============================================================
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt
COPY . .

# Final image: distroless Python (no shell, runs as nonroot:65532)
FROM gcr.io/distroless/python3-debian12
COPY --from=builder /install /usr/local
COPY --from=builder /app /app
WORKDIR /app
# distroless nonroot user is UID 65532
USER 65532
CMD ["app.py"]
```

---

## 4. .dockerignore Example (Complete, Annotated)

```
# ============================================================
# .dockerignore
# Every line is a pattern to EXCLUDE from the build context.
# Without this file, COPY . . might accidentally include secrets.
# ============================================================

# Version control — never include .git
# It can be hundreds of MB and exposes your entire repo history
.git
.gitignore
.gitattributes

# Secrets and credentials — CRITICAL
# If these get into an image, they're very hard to truly remove
.env
.env.local
.env.*.local
.env.production
*.pem
*.key
*.crt
id_rsa
id_ed25519
credentials.json
service-account.json
.aws/
.ssh/

# Language-specific dependency directories
# These should be installed fresh inside the container for correct OS/arch
node_modules/
vendor/               # Go or PHP vendor directory
.venv/                # Python virtual environment
__pycache__/
*.pyc
*.pyo
*.egg-info/
dist-info/

# Build artifacts (for multi-stage builds, the builder stage handles these)
dist/
build/
target/
*.o
*.a

# Logs
*.log
logs/
npm-debug.log*
yarn-debug.log*

# Test and coverage reports (not needed in production image)
coverage/
.nyc_output/
.pytest_cache/
tests/
test/
spec/
__tests__/

# IDE and editor files
.vscode/
.idea/
*.swp
*.swo
.DS_Store
Thumbs.db

# Docker files themselves
# (including them would just bloat the context)
Dockerfile
Dockerfile.*
.dockerignore
docker-compose.yml
docker-compose.*.yml

# Documentation
*.md
docs/
README*
LICENSE

# CI/CD configs (not needed in container)
.github/
.gitlab-ci.yml
.travis.yml
Jenkinsfile
```

---

## 5. Build Commands Reference

```bash
# ============================================================
# Build variants
# ============================================================

# Standard build (. = current directory is build context)
docker build -t myapp:1.0 .

# Build with a custom Dockerfile name/location
docker build -f Dockerfile.prod -t myapp:1.0 .

# Build from a different context directory (Dockerfile in current dir, context elsewhere)
docker build -f ./Dockerfile -t myapp:1.0 ../src

# Pass build arguments
docker build \
  --build-arg APP_VERSION=1.2.3 \
  --build-arg NODE_ENV=production \
  -t myapp:1.0 .

# Build without cache (full rebuild — useful when upstream packages updated)
docker build --no-cache -t myapp:1.0 .

# Build only a specific stage (multi-stage build)
docker build --target builder -t myapp-builder:debug .

# Show all output (no progress spinner) — great for CI logs
docker build --progress=plain -t myapp:1.0 . 2>&1 | tee build.log

# Inspect what the build WOULD do (doesn't actually build)
# Useful for debugging layer cache behavior:
docker build --progress=plain --no-cache -t myapp:test . 2>&1 | grep -E "^(#[0-9]| =>|CACHED)"

# Multi-platform build with buildx
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag myrepo/myapp:1.0 \
  --push \
  .

# BuildKit secret at build time (doesn't appear in image layers)
docker buildx build \
  --secret id=my_secret,src=$HOME/.secret_file \
  -t myapp:1.0 .
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

⬅️ **Prev:** [04 — Images and Layers](../04_Images_and_Layers/Code_Example.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [06 — Container Lifecycle](../06_Containers_Lifecycle/Code_Example.md)
🏠 **[Home](../../README.md)**
