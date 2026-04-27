# 01 — Dockerize a Python App

> Difficulty: 🟢 Fully Guided

---

## 🎯 The Mission

Imagine you just finished building a Python API. It works perfectly on your laptop. Your colleague pulls the code, runs it, and immediately hits a version mismatch. "It works on my machine" is one of the oldest frustrations in software. **Docker** eliminates it by packaging your app and every dependency it needs into a single, portable unit called a **container image**.

In this project you will take a FastAPI application from raw Python to a properly containerized image — ready to run anywhere Docker is installed.

---

## 🏗️ What You'll Build

A containerized FastAPI application that:

- Exposes a REST API with `/`, `/health`, and `/items` endpoints
- Uses a **multi-stage Dockerfile** to keep the final image lean
- Has a `HEALTHCHECK` instruction so Docker can monitor container health
- Has a `.dockerignore` so build noise stays out of the image
- Is tagged semantically and pushed to Docker Hub

---

## 🛠️ Skills Practiced

| Skill | Why it matters |
|---|---|
| Multi-stage Dockerfile | Produces small, production-grade images |
| `.dockerignore` | Keeps build context clean and fast |
| Image tagging and versioning | Enables safe rollbacks and traceability |
| `docker history` | Reveals layer composition and sizes |
| Docker Hub push | Shares images across machines and teams |
| Layer caching | Speeds up iterative builds |

---

## 📋 Prerequisites

| Tool | Version | Check command |
|---|---|---|
| Docker | 24+ | `docker --version` |
| Docker Hub account | any | hub.docker.com |
| Python 3.12 | optional | Only needed to run locally without Docker |

You do **not** need Python installed locally. The Dockerfile handles everything. Having it lets you test before containerizing, but it is not required.

---

## 🗺️ Step Summary

1. Write `main.py` — FastAPI app with `/`, `/health`, `/items` endpoints
2. Write `requirements.txt` — pinned dependencies
3. Write a multi-stage `Dockerfile` with `HEALTHCHECK`
4. Build the image with a semantic version tag
5. Run and test locally with curl
6. Write `.dockerignore` to slim the build context
7. Inspect image layers with `docker history`
8. Tag and push to Docker Hub

By the end you will have a real, versioned Docker image on Docker Hub that anyone can pull and run with a single command.

---

⬅️ **Prev:** none (first project) &nbsp;&nbsp; ➡️ **Next:** [02 — Multi-Container App with Compose](../02_Multi_Container_App_Compose/01_MISSION.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
