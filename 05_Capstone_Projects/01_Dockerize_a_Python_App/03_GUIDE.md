# 03 — Guide: Dockerize a Python App

Follow each step in order. Every command is copy-pasteable. Expected output is shown so you know when something worked.

---

## ## Step 1 — Write the FastAPI App

Create the `app/` directory and `main.py`:

```bash
mkdir -p app
```

The app exposes four routes:
- `GET /` — welcome message with version
- `GET /health` — returns `{"status": "ok"}` (used by the Docker HEALTHCHECK)
- `GET /items` — returns the in-memory item list
- `POST /items` — adds an item to the list

<details>
<summary>💡 Hint</summary>

Use FastAPI's `BaseModel` from Pydantic to define request and response schemas. The health endpoint just needs to return a 200 OK with `{"status": "ok"}` — nothing else. Keep the in-memory store as a plain Python list at module level.

</details>

<details>
<summary>✅ Answer</summary>

See `src/solution.py` for the complete implementation. Key points:

- `items_db: List[dict] = []` and `counter = {"value": 0}` at module level
- `/health` returns `{"status": "ok"}` — nothing fancy needed
- `POST /items` increments the counter, appends the new item, and returns it
- Pydantic `Item` model validates the request body

</details>

**Expected:** File created at `app/main.py`.

---

## ## Step 2 — Write requirements.txt

Create `requirements.txt` at the project root:

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
pydantic==2.7.1
```

Pin your versions. Unpinned dependencies are a future debugging session waiting to happen. An image built today with `fastapi` (no version) may behave differently from one built next month.

**Expected:** File created at `requirements.txt`.

---

## ## Step 3 — Write the Dockerfile

Create `Dockerfile` at the project root.

Key decisions to make:
- Use a `builder` stage to install dependencies with `pip install --prefix=/install`
- Use a `runtime` stage (fresh `python:3.12-slim`) that only copies `/install`
- Add a non-root user named `appuser`
- Install `curl` in the runtime stage (needed for the `HEALTHCHECK` command)
- Set `HEALTHCHECK` to poll `http://localhost:8000/health` every 30 seconds

<details>
<summary>💡 Hint</summary>

The trick to a clean multi-stage build is `--prefix=/install` in the pip command. This installs packages to `/install` instead of the system Python path, making it trivial to `COPY --from=builder /install /usr/local` in the runtime stage.

For the non-root user:
```dockerfile
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --no-create-home appuser
```

For the HEALTHCHECK:
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
```

</details>

<details>
<summary>✅ Answer</summary>

```dockerfile
FROM python:3.12-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip --no-cache-dir && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --no-create-home appuser
WORKDIR /app
COPY --from=builder /install /usr/local
COPY app/ ./app/
RUN chown -R appuser:appgroup /app
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

</details>

**Expected:** File created at `Dockerfile`.

---

## ## Step 4 — Build the Image

```bash
docker build -t myapi:1.0.0 .
```

Watch the output. On your first build, every layer runs. On subsequent builds, unchanged layers show `CACHED`.

**Expected output (last few lines):**
```
 => exporting to image
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

The image should be under 200MB. If it is 800MB or more, the multi-stage build is not working — check that you are starting the second `FROM` statement with a fresh base.

---

## ## Step 5 — Run Locally

```bash
docker run -d --name myapi-test -p 8000:8000 myapi:1.0.0
```

Flags:
- `-d` — detached, runs in the background
- `--name myapi-test` — gives the container a name you can reference
- `-p 8000:8000` — maps host port 8000 to container port 8000

Check that it started:
```bash
docker ps
```

**Expected:**
```
CONTAINER ID   IMAGE         STATUS                   PORTS                    NAMES
a1b2c3d4e5f6   myapi:1.0.0   Up 2 seconds (healthy)   0.0.0.0:8000->8000/tcp   myapi-test
```

The `(healthy)` status confirms your HEALTHCHECK is passing.

---

## ## Step 6 — Test the API

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

Fetch all items again to confirm it persisted within the running container:
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

## ## Step 7 — Write .dockerignore

Create `.dockerignore` at the project root:

```
__pycache__/
*.pyc
*.pyo
.env
.venv/
venv/
.git/
*.md
tests/
.pytest_cache/
```

<details>
<summary>💡 Hint</summary>

The `.dockerignore` file controls what gets sent to the Docker daemon as the build context. Everything in the directory is sent by default — including `venv/` (which can be hundreds of megabytes), `.git/`, and test fixtures. The smaller the build context, the faster the build.

</details>

<details>
<summary>✅ Answer</summary>

Rebuild and check the build context size in the first line of output:

```bash
docker build -t myapi:1.0.0 .
```

Look for:
```
 => [internal] load build context
 => => transferring context: 3.2kB
```

Without `.dockerignore`, that number would be much larger if you have a virtual environment or test fixtures in the directory.

</details>

---

## ## Step 8 — Inspect Image Layers

```bash
docker history myapi:1.0.0
```

**Expected output (abbreviated):**
```
IMAGE          CREATED BY                                      SIZE
abc123def456   CMD ["uvicorn" "app.main:app" ...]              0B
<missing>      HEALTHCHECK ...                                  0B
<missing>      USER appuser                                     0B
<missing>      COPY /app/app /app/app                           8.19kB
<missing>      COPY /install /usr/local/lib/...                 45.8MB
<missing>      RUN pip install ...                              6.21MB
```

The fat layer is `COPY /install` — that is your pip dependencies copied from the builder stage. Everything else is thin metadata.

Count the layers:
```bash
docker inspect myapi:1.0.0 | jq '.[0].RootFS.Layers | length'
```

**Expected:** a number like `8`.

---

## ## Step 9 — Push to Docker Hub

Tag with your Docker Hub username:
```bash
docker tag myapi:1.0.0 YOUR_DOCKERHUB_USERNAME/myapi:1.0.0
docker tag myapi:1.0.0 YOUR_DOCKERHUB_USERNAME/myapi:latest
```

Log in:
```bash
docker login
```

Push both tags:
```bash
docker push YOUR_DOCKERHUB_USERNAME/myapi:1.0.0
docker push YOUR_DOCKERHUB_USERNAME/myapi:latest
```

Anyone can now pull and run your image:
```bash
docker run -p 8000:8000 YOUR_DOCKERHUB_USERNAME/myapi:1.0.0
```

---

## ## Cleanup

```bash
docker rm -f myapi-test 2>/dev/null || true
docker rmi myapi:1.0.0 YOUR_DOCKERHUB_USERNAME/myapi:1.0.0 YOUR_DOCKERHUB_USERNAME/myapi:latest
```

---

⬅️ **Prev:** none (first project) &nbsp;&nbsp; ➡️ **Next:** [02 — Multi-Container App with Compose](../02_Multi_Container_App_Compose/01_MISSION.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
