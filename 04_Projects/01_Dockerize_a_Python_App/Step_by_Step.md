# Step-by-Step: Dockerize a Python App

Follow these steps in order. Every command is copy-pasteable. Expected output is shown so you know when something worked.

---

## Step 1 — Write the FastAPI App

Create the `app/` directory and write `main.py`.

```bash
mkdir -p app
```

Create `app/main.py` with the following content (see Code_Example.md for the full file).

The app exposes three routes:
- `GET /` — welcome message
- `GET /health` — health check (returns `{"status": "ok"}`)
- `GET /items` — returns a list of sample items
- `POST /items` — adds an item to an in-memory list

**Expected:** File created at `app/main.py`.

---

## Step 2 — Write requirements.txt

Create `requirements.txt` at the project root:

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
```

Pin your versions. Unpinned dependencies are a future debugging session waiting to happen.

**Expected:** File created at `requirements.txt`.

---

## Step 3 — Write the Dockerfile

Create `Dockerfile` at the project root (see Code_Example.md for the full annotated file).

Key decisions in this Dockerfile:
- **Multi-stage build**: a `builder` stage installs deps, the `runtime` stage is a clean slim image
- **Non-root user**: the app runs as `appuser`, not root
- **HEALTHCHECK**: Docker will poll `/health` every 30 seconds
- **Explicit WORKDIR**: `/app` — no guessing where files are

**Expected:** File created at `Dockerfile`.

---

## Step 4 — Build the Image

```bash
docker build -t myapi:1.0.0 .
```

Watch the output. You'll see Docker executing each layer. On your first build, every step runs. On subsequent builds, unchanged layers come from cache (they'll say `CACHED`).

**Expected output (last few lines):**
```
 => exporting to image
 => => exporting layers
 => => writing image sha256:abc123...
 => => naming to docker.io/library/myapi:1.0.0
```

Verify the image exists:
```bash
docker images myapi
```

**Expected:**
```
REPOSITORY   TAG       IMAGE ID       CREATED         SIZE
myapi        1.0.0     abc123def456   5 seconds ago   185MB
```

The image should be under 200MB. If it's 800MB+, your multi-stage build isn't working — check the Dockerfile.

---

## Step 5 — Run Locally

```bash
docker run -d --name myapi-test -p 8000:8000 myapi:1.0.0
```

Flags:
- `-d` — detached (runs in background)
- `--name myapi-test` — gives the container a name so you can reference it
- `-p 8000:8000` — maps host port 8000 to container port 8000

Check it started:
```bash
docker ps
```

**Expected:**
```
CONTAINER ID   IMAGE         COMMAND                  CREATED         STATUS                   PORTS                    NAMES
a1b2c3d4e5f6   myapi:1.0.0   "uvicorn app.main:ap…"   3 seconds ago   Up 2 seconds (healthy)   0.0.0.0:8000->8000/tcp   myapi-test
```

Note the `(healthy)` status — that means your HEALTHCHECK is passing.

---

## Step 6 — Test the API

```bash
curl http://localhost:8000
```

**Expected:**
```json
{"message": "Hello from Dockerized FastAPI!", "version": "1.0.0"}
```

```bash
curl http://localhost:8000/health
```

**Expected:**
```json
{"status": "ok"}
```

```bash
curl http://localhost:8000/items
```

**Expected:**
```json
{"items": []}
```

Add an item:
```bash
curl -X POST http://localhost:8000/items \
  -H "Content-Type: application/json" \
  -d '{"name": "laptop", "price": 999.99}'
```

**Expected:**
```json
{"id": 1, "name": "laptop", "price": 999.99}
```

Fetch the list again to confirm it persisted (within the running container):
```bash
curl http://localhost:8000/items
```

**Expected:**
```json
{"items": [{"id": 1, "name": "laptop", "price": 999.99}]}
```

Stop the test container before continuing:
```bash
docker stop myapi-test && docker rm myapi-test
```

---

## Step 7 — Write .dockerignore

Create `.dockerignore` at the project root:

```
__pycache__/
*.pyc
*.pyo
.env
.venv/
venv/
.git/
.gitignore
*.md
tests/
.pytest_cache/
```

Now rebuild and compare:
```bash
docker build -t myapi:1.0.0 .
```

The build context sent to Docker will be smaller. You can see the size in the first line of output:
```
[+] Building 0.3s (12/12) FINISHED
 => [internal] load build context
 => => transferring context: 3.2kB
```

Without `.dockerignore`, that number could be megabytes if you have a `venv/` or large test fixtures.

---

## Step 8 — Inspect Image Layers

```bash
docker history myapi:1.0.0
```

**Expected output:**
```
IMAGE          CREATED         CREATED BY                                      SIZE      COMMENT
abc123def456   2 minutes ago   CMD ["uvicorn" "app.main:app" "--host" "0.…   0B
<missing>      2 minutes ago   HEALTHCHECK &{["CMD" "curl" "-f" "http://l…   0B
<missing>      2 minutes ago   EXPOSE map[8000/tcp:{}]                         0B
<missing>      2 minutes ago   USER appuser                                    0B
<missing>      2 minutes ago   COPY /app/app /app/app                          8.19kB
<missing>      2 minutes ago   COPY /install /usr/local/lib/python3.12/si…    45.8MB
<missing>      2 minutes ago   RUN /bin/sh -c pip install --upgrade pip        6.21MB
...
```

Notice: the fat layer is `COPY /install` — that's your pip dependencies copied from the builder stage. Everything else is thin metadata or tiny file copies.

For a more detailed view:
```bash
docker inspect myapi:1.0.0 | jq '.[0].RootFS.Layers | length'
```

**Expected:** a number like `8` — each instruction that modifies the filesystem creates a layer.

---

## Step 9 — Push to Docker Hub

First, tag your image with your Docker Hub username:

```bash
docker tag myapi:1.0.0 YOUR_DOCKERHUB_USERNAME/myapi:1.0.0
docker tag myapi:1.0.0 YOUR_DOCKERHUB_USERNAME/myapi:latest
```

Log in (if you haven't already):
```bash
docker login
```

**Expected:**
```
Login Succeeded
```

Push both tags:
```bash
docker push YOUR_DOCKERHUB_USERNAME/myapi:1.0.0
docker push YOUR_DOCKERHUB_USERNAME/myapi:latest
```

**Expected output:**
```
The push refers to repository [docker.io/YOUR_DOCKERHUB_USERNAME/myapi]
abc123def456: Pushed
...
1.0.0: digest: sha256:xyz789... size: 1234
```

Verify on Docker Hub by visiting: `https://hub.docker.com/r/YOUR_DOCKERHUB_USERNAME/myapi`

Anyone can now pull and run your image:
```bash
docker run -p 8000:8000 YOUR_DOCKERHUB_USERNAME/myapi:1.0.0
```

---

## Cleanup

Remove local containers and images when done:

```bash
docker rm -f myapi-test 2>/dev/null || true
docker rmi myapi:1.0.0 YOUR_DOCKERHUB_USERNAME/myapi:1.0.0 YOUR_DOCKERHUB_USERNAME/myapi:latest
```

---

## 📂 Navigation

| | |
|---|---|
| Guide | [Project_Guide.md](./Project_Guide.md) |
| Code | [Code_Example.md](./Code_Example.md) |
| All Projects | [04_Projects/](../) |
