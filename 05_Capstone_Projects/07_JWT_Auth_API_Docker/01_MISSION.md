# Project 07 — Containerize and Deploy JWT Auth API

## 🎯 The Mission

You built a JWT authentication API in Python — registration, login, protected routes, bcrypt passwords, expiring tokens. It works on your machine. It works in your virtual environment. And that is exactly the problem.

"Works on my machine" is not a deployment strategy. When your teammate pulls the code, they need the same Python version, the same library versions, the same PostgreSQL version, the same environment variables in the same places. When you push to staging, the server needs the same setup. When you roll back at 2am, you need confidence that the image you're deploying is byte-for-byte identical to the one you tested.

**Containers** solve this. A Docker image is a sealed, reproducible snapshot of your entire runtime: OS layer, Python interpreter, dependencies, app code. Build it once, run it anywhere — your laptop, your teammate's laptop, staging, prod — same behavior every time.

This project takes your JWT API and packages it properly: a **multi-stage Dockerfile** that keeps the final image small, a **Docker Compose** setup that wires the API to PostgreSQL locally, environment variable management that keeps secrets out of your image, health checks so orchestrators know when your app is ready, and a prod-vs-dev split that lets you hot-reload in development without changing your production image.

---

## 📋 What You Will Build

| Artifact | Purpose |
|---|---|
| `Dockerfile` | Multi-stage build: install deps in builder, copy only what's needed to runtime |
| `docker-compose.yml` | Run FastAPI + PostgreSQL together with one command |
| `docker-compose.override.yml` | Dev overlay: hot reload, port exposure, relaxed health checks |
| `.env.example` | Template for required environment variables (safe to commit) |
| `.env` | Actual secrets (never commit this) |
| `src/solution.py` | Full JWT auth app: register, login, `/me` protected route |

---

## 🛠️ Skills You Will Practice

**Multi-stage builds** — understand why the builder stage exists and why the runtime stage is separate. A builder image can be 1GB+; the runtime image should be under 200MB.

**Compose networking** — FastAPI and PostgreSQL talk to each other over a **named bridge network**, not `localhost`. The service name becomes the DNS hostname. `postgres://db:5432` works; `postgres://localhost:5432` does not.

**Environment variable security** — three-tier hierarchy: `.env.example` (template, committed), `.env` (real values, gitignored), Docker secrets (prod). Never bake secrets into your image with `ENV` instructions.

**Health checks** — Docker and Compose can poll your app to know if it is ready. Without health checks, Compose starts PostgreSQL and immediately starts the API — which crashes because the database isn't ready yet. With health checks, the API waits.

---

## ✅ Prerequisites

| Skill | Where to Learn |
|---|---|
| Docker basics: build, run, images, layers | Projects 01–02 in this repo |
| Docker Compose: services, volumes, networks | Project 02 in this repo |
| JWT auth concepts: tokens, bcrypt, protected routes | Python-DSA-API-Mastery, Capstone Project 05 |

---

## 📊 Project Info

| | |
|---|---|
| Difficulty | Fully Guided |
| Estimated Time | 3 hours |
| Docker Concepts | Multi-stage builds, Compose networking, health checks, env vars |
| App Stack | FastAPI + PostgreSQL 15 + python:3.12-slim |

---

## 📂 Navigation

⬅️ **Prev:** [06 — Production K8s Cluster](../../05_Capstone_Projects/06_Production_K8s_Cluster/01_MISSION.md) &nbsp;&nbsp; ➡️ **Next:** [08 — E-Commerce API on K8s](../08_Ecommerce_API_K8s/01_MISSION.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
