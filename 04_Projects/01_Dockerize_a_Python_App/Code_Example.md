# Code Examples: Dockerize a Python App

All code here is complete and functional. Copy it exactly, then experiment from there.

---

## app/main.py

```python
# app/main.py
# FastAPI application with health endpoint and basic CRUD in memory.
# In production you'd swap the in-memory list for a real database.

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import os

app = FastAPI(
    title="My Dockerized API",
    version="1.0.0",
    description="A FastAPI app containerized with Docker best practices.",
)

# In-memory store — resets every time the container restarts.
# Good enough for learning. See Project 02 for Postgres persistence.
items_db: List[dict] = []
counter = {"value": 0}


class Item(BaseModel):
    name: str
    price: float


class ItemResponse(BaseModel):
    id: int
    name: str
    price: float


@app.get("/")
def root():
    """Welcome endpoint — confirms the API is reachable."""
    return {
        "message": "Hello from Dockerized FastAPI!",
        "version": app.version,
    }


@app.get("/health")
def health():
    """
    Health check endpoint.
    Docker's HEALTHCHECK instruction calls this URL.
    Return 200 OK with {"status": "ok"} when the app is ready.
    Return 503 if something is wrong (e.g., DB unreachable).
    """
    return {"status": "ok"}


@app.get("/items")
def list_items():
    """Return all items in the in-memory store."""
    return {"items": items_db}


@app.post("/items", response_model=ItemResponse, status_code=201)
def create_item(item: Item):
    """Add a new item to the store."""
    counter["value"] += 1
    new_item = {"id": counter["value"], "name": item.name, "price": item.price}
    items_db.append(new_item)
    return new_item


@app.get("/items/{item_id}", response_model=ItemResponse)
def get_item(item_id: int):
    """Retrieve a single item by ID."""
    for item in items_db:
        if item["id"] == item_id:
            return item
    raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
```

---

## requirements.txt

```
# Pin exact versions so your image is reproducible across builds and environments.
# To upgrade: update versions here, rebuild, and test.

fastapi==0.111.0
uvicorn[standard]==0.29.0
pydantic==2.7.1

# curl is installed in the Dockerfile for the HEALTHCHECK.
# No Python packages needed for that.
```

---

## Dockerfile

```dockerfile
# =============================================================================
# STAGE 1 — builder
# =============================================================================
# We use a full Python image here because we need pip and build tools.
# Nothing from this stage ends up in the final image except the installed
# packages — that's the point of a multi-stage build.
FROM python:3.12-slim AS builder

# Prevent Python from writing .pyc files to disk (unnecessary in containers).
ENV PYTHONDONTWRITEBYTECODE=1
# Prevent Python from buffering stdout/stderr (logs appear immediately).
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy only requirements first.
# Docker caches each layer. If requirements.txt doesn't change,
# the pip install layer is reused on the next build — fast!
COPY requirements.txt .

# Install dependencies to a custom prefix so we can COPY them cleanly.
# --no-cache-dir: don't store pip's download cache in the image.
# --prefix=/install: install to /install instead of the system Python path.
RUN pip install --upgrade pip --no-cache-dir && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

# =============================================================================
# STAGE 2 — runtime
# =============================================================================
# Start fresh from the same slim base. No build tools, no pip cache.
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install curl so the HEALTHCHECK can call the /health endpoint.
# Clean up apt cache afterward to keep the layer small.
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Create a non-root user.
# Running as root inside a container is a security risk.
# If someone exploits the app, they get non-root access to the host.
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --no-create-home appuser

WORKDIR /app

# Copy installed Python packages from the builder stage.
# /install contains site-packages, bin, etc.
COPY --from=builder /install /usr/local

# Copy application source code.
# Do this AFTER copying dependencies — if only your app code changes,
# only this layer is invalidated. Dependencies stay cached.
COPY app/ ./app/

# Change ownership so appuser can read the files.
RUN chown -R appuser:appgroup /app

# Switch to non-root user.
USER appuser

# Declare which port the app listens on.
# This is documentation; it doesn't actually publish the port.
# Use -p or -P with docker run to publish it.
EXPOSE 8000

# Health check: poll the /health endpoint every 30 seconds.
# --interval=30s  how often Docker checks
# --timeout=10s   how long to wait for a response before marking unhealthy
# --start-period=5s  grace period after container starts (don't penalize slow startup)
# --retries=3     how many consecutive failures before marking unhealthy
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start uvicorn. Use exec form (JSON array) so the process receives signals
# directly — enabling graceful shutdown when Docker sends SIGTERM.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## .dockerignore

```
# Python artifacts
__pycache__/
*.pyc
*.pyo
*.pyd
*.egg-info/
dist/
build/

# Virtual environments — never copy these into the image
.venv/
venv/
env/

# Secrets and local config
.env
.env.*
*.key
*.pem

# Version control
.git/
.gitignore
.gitattributes

# Documentation (don't need docs in a runtime image)
*.md
docs/

# Test artifacts
tests/
.pytest_cache/
htmlcov/
.coverage
coverage.xml

# IDE files
.vscode/
.idea/
*.swp
*.swo

# OS files
.DS_Store
Thumbs.db
```

---

## Notes

**Why multi-stage?**

Compare image sizes:

```bash
# Single-stage (naive)
docker build -f Dockerfile.naive -t myapi:naive .
docker images myapi:naive
# SIZE: ~450MB

# Multi-stage (this project)
docker build -t myapi:1.0.0 .
docker images myapi:1.0.0
# SIZE: ~185MB
```

The difference is pip's build cache, intermediate files, and build tools that single-stage builds leave behind.

**Why pin requirements?**

```bash
# This is a ticking time bomb:
fastapi
uvicorn

# This is reproducible:
fastapi==0.111.0
uvicorn[standard]==0.29.0
```

Unpinned deps mean your image built today may differ from your image built next month. CI pipelines break unexpectedly. Production diverges from local. Pin everything.

---

## 📂 Navigation

| | |
|---|---|
| Guide | [Project_Guide.md](./Project_Guide.md) |
| Steps | [Step_by_Step.md](./Step_by_Step.md) |
| All Projects | [04_Projects/](../) |
