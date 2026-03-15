# Project 01: Dockerize a Python App

You have a Python API that works perfectly on your laptop. The classic next question is: how do you make it work everywhere else, reliably, without "it works on my machine" drama? The answer is Docker. In this project you'll take a FastAPI application from raw Python to a properly containerized, production-ready image — complete with multi-stage builds, health checks, and a push to Docker Hub.

---

## What You'll Build

A containerized FastAPI application that:

- Exposes a REST API with `/`, `/health`, and `/items` endpoints
- Uses a **multi-stage Dockerfile** to keep the final image lean (builder installs deps, runtime stage is slim Python)
- Has a `HEALTHCHECK` instruction so Docker knows if the container is actually serving traffic
- Has a `.dockerignore` so you're not copying junk into your image
- Is tagged semantically and pushed to Docker Hub

---

## Architecture

```
┌────────────────────────────────────┐
│         Docker Host                │
│                                    │
│  ┌──────────────────────────────┐  │
│  │  Container: myapi:1.0.0      │  │
│  │                              │  │
│  │  Python 3.12-slim            │  │
│  │  FastAPI + Uvicorn           │  │
│  │  Listening on :8000          │  │
│  └──────────────┬───────────────┘  │
│                 │ port 8000        │
└─────────────────┼──────────────────┘
                  │
           localhost:8000
                  │
             curl / browser
```

**Build stages:**

| Stage   | Base Image           | Purpose                          |
|---------|----------------------|----------------------------------|
| builder | python:3.12-slim     | Install dependencies via pip     |
| runtime | python:3.12-slim     | Copy installed deps, run the app |

Using two stages means build tools and pip cache never land in your final image.

---

## Skills Practiced

- Writing a production-quality Dockerfile (multi-stage, non-root user, HEALTHCHECK)
- Using `.dockerignore` correctly
- Tagging and versioning Docker images
- Inspecting image layers with `docker history`
- Pushing to Docker Hub
- Understanding image layer caching

---

## Prerequisites

| Tool          | Version  | Check command              |
|---------------|----------|----------------------------|
| Docker        | 24+      | `docker --version`         |
| Docker Hub account | any | hub.docker.com             |
| Python 3.12   | optional | Only needed to run locally |

You do **not** need Python installed locally — the Dockerfile handles everything. But having it lets you test `main.py` directly before containerizing.

---

## Folder Structure

```
01_Dockerize_a_Python_App/
├── app/
│   └── main.py              # FastAPI application
├── Dockerfile               # Multi-stage build
├── .dockerignore            # Files to exclude from build context
├── requirements.txt         # Python dependencies
├── Project_Guide.md         # This file
├── Step_by_Step.md          # Numbered walkthrough
└── Code_Example.md          # Full working code
```

---

## What You'll Build — Step Summary

1. Write `main.py` with FastAPI endpoints including `/health`
2. Write `requirements.txt` pinning your dependencies
3. Write a multi-stage `Dockerfile` with HEALTHCHECK
4. Build the image with a semantic version tag
5. Run it locally and test with curl
6. Write `.dockerignore` to slim the build context
7. Inspect layers with `docker history`
8. Tag and push to Docker Hub

By the end you'll have a real, versioned Docker image on Docker Hub that anyone can pull and run.

---

## 📂 Navigation

| | |
|---|---|
| Next | [Step_by_Step.md](./Step_by_Step.md) |
| Code | [Code_Example.md](./Code_Example.md) |
| All Projects | [04_Projects/](../) |
