# 04 — Recap: Multi-Container App with Docker Compose

---

## 🏁 What You Built

A production-pattern three-service stack, described as code, reproducible on any machine with Docker installed.

```
docker compose up -d
         │
         ├── Postgres container     (persistent data volume)
         ├── Redis container        (ephemeral cache, AOF backup)
         └── FastAPI container      (waits for both, then starts)
                  │
                  └── localhost:8000  ←  curl / browser
```

You did not wire any of this manually. Compose handled network creation, DNS registration, startup ordering, and health-check gating.

---

## 🧠 Key Concepts

**Service discovery by name** is one of Compose's most useful features. On a Compose-managed bridge network, every service is reachable at its service name. Your API reaches Postgres at hostname `db` and Redis at hostname `cache` — no IP addresses, no `/etc/hosts` edits. Docker's embedded DNS resolver handles the lookup.

**Health checks with `condition: service_healthy`** prevent the startup race condition. Without it, the API container starts, immediately tries to open a Postgres connection, finds Postgres still initializing, and crashes. With health-check gating, Compose holds the API until `pg_isready` returns success.

**Named volumes** store data outside the container lifecycle. When you run `docker compose down`, containers are deleted but named volumes survive. The `-v` flag is the deliberate, irreversible action required to delete them.

**Cache invalidation strategy** in this project is write-through delete: on every write, delete the cached key. The next read will be a cache miss, hit the database, and repopulate the cache. This is simple and correct for a list endpoint with low write frequency.

**Override files** let you separate dev and prod configuration. `docker-compose.override.yml` is auto-merged by Compose when present. It adds a bind mount and `--reload` for fast iteration in development without touching the production `docker-compose.yaml`.

---

## 📊 What the Source Field Shows You

| Request | Redis key exists? | `"source"` in response | What happened |
|---|---|---|---|
| First `GET /items` | No | `"database"` | Cache miss — Postgres was queried |
| Second `GET /items` (within 60s) | Yes | `"cache"` | Cache hit — Redis returned the data |
| After `POST /items` | Deleted | `"database"` on next GET | Cache invalidated by write |
| After 60 seconds | Expired (TTL) | `"database"` on next GET | Redis TTL expired naturally |

---

## 🚀 Extend It

- **Add pagination:** take `limit` and `offset` query params and return a slice of the items list with a `"total"` count
- **Add an items delete endpoint:** `DELETE /items/{id}` — remember to invalidate the cache
- **Add a Compose health dashboard:** run `watch docker compose ps` in a terminal split to see health state in real time
- **Replace Redis TTL with cache tags:** instead of deleting `items:all` on write, tag cache entries by table name and invalidate by tag
- **Add pgAdmin as a fourth service:** the `dpage/pgadmin4` image lets you browse Postgres through a web UI — connect it to the `app-network`
- **Test the startup ordering:** comment out the `depends_on` block, bring the stack up, and observe the race condition crash in `docker compose logs api`

---

⬅️ **Prev:** [01 — Dockerize a Python App](../01_Dockerize_a_Python_App/01_MISSION.md) &nbsp;&nbsp; ➡️ **Next:** [03 — Deploy App to Kubernetes](../03_Deploy_App_to_Kubernetes/01_MISSION.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
