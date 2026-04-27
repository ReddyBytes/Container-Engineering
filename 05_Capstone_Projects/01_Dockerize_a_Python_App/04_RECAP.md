# 04 — Recap: Dockerize a Python App

---

## 🏁 What You Built

You took a Python FastAPI application and packaged it into a portable, production-grade Docker image. Along the way you made real engineering decisions — not just "write a Dockerfile" but the right kind of Dockerfile.

```
app/main.py  +  requirements.txt  +  Dockerfile  +  .dockerignore
        │
        ▼  docker build -t myapi:1.0.0 .
        │
   myapi:1.0.0   (~185MB, non-root, health-checked)
        │
        ▼  docker push
        │
   Docker Hub  →  pullable by anyone, anywhere
```

---

## 🧠 Key Concepts

**Multi-stage builds** are the single biggest lever for image size. A naive single-stage build that runs pip install leaves pip itself, its cache, and any build tools in the final image. Multi-stage builds discard all of that — only the installed packages travel to the runtime stage.

**Layer caching** is Docker's incremental build system. Each instruction in a Dockerfile that modifies the filesystem creates a new layer. If the instruction and all preceding inputs are unchanged, Docker reuses the cached layer. Copying `requirements.txt` before `app/` exploits this: dependency installation is only re-run when requirements change, not on every code edit.

**Non-root containers** reduce the blast radius if an attacker exploits the application. Running as `appuser` (UID 1001) means even a full container escape gives the attacker only non-root access to the host.

**HEALTHCHECK** turns Docker's container status from a binary running/stopped into a three-state system: starting, healthy, unhealthy. Orchestrators like Kubernetes and Docker Swarm use this signal to route traffic only to healthy containers.

**.dockerignore** controls the build context — the set of files sent to the Docker daemon before the build starts. Excluding `venv/`, `.git/`, and test artifacts can reduce the build context from hundreds of megabytes to kilobytes.

---

## 📊 What the Numbers Show

| Approach | Image size | Why |
|---|---|---|
| Single-stage (naive pip install) | ~450MB | pip cache, build tools, intermediate files |
| Multi-stage (this project) | ~185MB | Only installed packages, no build artifacts |

---

## 🚀 Extend It

- **Add environment variable support:** read `APP_VERSION` from an env var and return it in the root endpoint
- **Pin the base image digest:** replace `python:3.12-slim` with `python:3.12-slim@sha256:...` for fully reproducible builds
- **Add a GitHub Actions workflow:** build and push automatically on every merge to main
- **Scan for vulnerabilities:** run `docker scout cves myapi:1.0.0` or `trivy image myapi:1.0.0` against your image
- **Try distroless:** swap the runtime base for `gcr.io/distroless/python3` and see how much smaller the image gets (and what you lose)
- **Multi-arch build:** use `docker buildx build --platform linux/amd64,linux/arm64` to produce an image that runs on both Intel and Apple Silicon

---

⬅️ **Prev:** none (first project) &nbsp;&nbsp; ➡️ **Next:** [02 — Multi-Container App with Compose](../02_Multi_Container_App_Compose/01_MISSION.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
