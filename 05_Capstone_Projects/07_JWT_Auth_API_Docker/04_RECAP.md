# Project 07 — Recap

## What You Built

You took a Python JWT authentication API and packaged it for consistent, repeatable deployment. The API — register, login, `/me` protected route — now runs identically whether you are on your laptop, your teammate's machine, a staging server, or a production VM. One command starts the entire stack. One image ships everywhere.

---

## Three Key Concepts

**Multi-stage builds** solve the tension between "I need build tools to compile my dependencies" and "I do not want build tools in my production image." The builder stage has access to gcc and libpq-dev. The runtime stage gets only the compiled output. The final image is roughly half the size of a single-stage build, has a smaller attack surface, and takes less time to push and pull from the registry. Every Python service with compiled C extensions benefits from this pattern.

**Compose networking** means that containers are not processes on the same machine — they are separate hosts on a private network. `localhost` inside one container does not reach another container. Service names become DNS hostnames. Your FastAPI app connects to `db:5432`, not `localhost:5432`. This network isolation is not just a Docker quirk — it mirrors how services communicate in Kubernetes, in ECS, and in any other container platform. Get comfortable with it here.

**Environment variable security** operates on a rule: secrets are never baked into images. A secret in a `Dockerfile ENV` instruction is visible in `docker history`, in the image layers, in any registry it is pushed to. The correct pattern is injection at runtime: `.env` files for local development, `--env-file` for manual production runs, Docker secrets or cloud provider secret managers for production orchestration. The `.env.example` template tells your team what variables are required without exposing the values.

---

## Extend It

These extensions map to real production patterns. Each one is a meaningful addition to this project.

**Add nginx as a reverse proxy.** Put an nginx container in front of FastAPI. Nginx handles TLS termination, rate limiting, and static file serving. FastAPI never sees a raw HTTPS connection. This is the standard architecture for Python APIs behind a load balancer.

```
Client → nginx:443 (TLS) → fastapi:8000 (plain HTTP inside the network)
```

**Add Redis for token blacklisting.** JWTs are stateless — once issued, you cannot revoke them without a blacklist. Add a Redis container to Compose. On logout, write the token's `jti` (JWT ID) claim to Redis with the token's remaining TTL as the expiry. On every `/me` request, check Redis before trusting the token. This adds one network call but gives you real logout capability.

**Push to Amazon ECR instead of Docker Hub.** AWS Elastic Container Registry is the private alternative. Tag as `<account>.dkr.ecr.<region>.amazonaws.com/jwt-api:1.0.0`. Authenticate with `aws ecr get-login-password | docker login`. This is the required step before deploying to ECS or EKS.

**Deploy to ECS Fargate.** ECS Fargate runs containers without managing EC2 instances. The Task Definition is the ECS equivalent of a `docker run` command. The Service keeps N tasks running and replaces unhealthy ones. Secrets live in AWS Secrets Manager, injected as environment variables at task start — the same pattern you practiced here with `.env`.

---

## 📂 Navigation

⬅️ **Prev:** [06 — Production K8s Cluster](../../05_Capstone_Projects/06_Production_K8s_Cluster/01_MISSION.md) &nbsp;&nbsp; ➡️ **Next:** [08 — E-Commerce API on K8s](../08_Ecommerce_API_K8s/01_MISSION.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
