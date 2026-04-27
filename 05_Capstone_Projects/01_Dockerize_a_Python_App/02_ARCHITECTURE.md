# 02 — Architecture: Dockerize a Python App

---

## 🗺️ System Overview

Think of a container as a shipping container on a cargo ship. Before shipping containers existed, every port had different loading procedures, and cargo was handled differently everywhere. Shipping containers standardized everything — same box, same crane, same handling, any port in the world. Docker does the same for software.

Your application becomes the cargo. The container image is the standardized box.

---

## 🖥️ Runtime Diagram

```
┌────────────────────────────────────┐
│         Docker Host                │
│  (your laptop, VM, or cloud node)  │
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

---

## 🔨 Build Pipeline Diagram

```
Source Files                      Docker Build
─────────────                     ────────────

app/main.py   ─────────────────▶  STAGE 1: builder
requirements.txt                    python:3.12-slim
Dockerfile                          pip install --prefix=/install
.dockerignore                       ↓ (only /install directory exits this stage)

                                  STAGE 2: runtime
                                    python:3.12-slim (fresh)
                                    COPY /install from builder
                                    COPY app/ source
                                    Non-root user
                                    HEALTHCHECK
                                    ↓

                                  Final Image: myapi:1.0.0
                                  (~185MB — no build tools, no pip cache)
```

---

## 📦 Multi-Stage Build: Why Two Stages?

A single-stage build that runs pip install and then packages the app results in an image that contains pip itself, its download cache, compiler tools, and other build artifacts. None of that is needed at runtime.

| Stage | Base Image | Purpose | Ends up in final image? |
|---|---|---|---|
| builder | python:3.12-slim | Install dependencies via pip | No — only the installed packages |
| runtime | python:3.12-slim | Run the application | Yes — this is the final image |

The builder stage does all the heavy lifting. The runtime stage starts clean and only receives the output of the build.

---

## 🗂️ Folder Structure

```
01_Dockerize_a_Python_App/
├── app/
│   └── main.py              # FastAPI application
├── Dockerfile               # Multi-stage build definition
├── .dockerignore            # Files excluded from build context
├── requirements.txt         # Pinned Python dependencies
└── src/
    ├── starter.py           # Scaffolded app — fill in the TODOs
    └── solution.py          # Complete working solution
```

---

## 🔄 Data Flow

```
HTTP Request
     │
     ▼
Docker Host port 8000
     │
     ▼ (port mapping -p 8000:8000)
Container port 8000
     │
     ▼
Uvicorn (ASGI server)
     │
     ▼
FastAPI application (app/main.py)
     │
     ├──▶ GET /         → {"message": "Hello...", "version": "1.0.0"}
     ├──▶ GET /health   → {"status": "ok"}
     ├──▶ GET /items    → {"items": [...]}
     └──▶ POST /items   → {"id": 1, "name": "...", "price": ...}
```

---

## 🧱 Tech Stack

| Component | Technology | Purpose |
|---|---|---|
| Web framework | FastAPI | Request routing, validation, serialization |
| ASGI server | Uvicorn | Runs FastAPI, handles HTTP connections |
| Data validation | Pydantic v2 | Request/response schemas |
| Base image | python:3.12-slim | Minimal Python runtime, Debian-based |
| Health check | curl | Polls `/health` from inside the container |

---

⬅️ **Prev:** none (first project) &nbsp;&nbsp; ➡️ **Next:** [02 — Multi-Container App with Compose](../02_Multi_Container_App_Compose/01_MISSION.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
