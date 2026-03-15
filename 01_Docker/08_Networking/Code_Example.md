# Docker Networking — Code Examples

Hands-on examples: custom bridge network, container DNS resolution, multi-network segmentation, and port publishing.

---

## 1. Create a Custom Bridge Network and Demonstrate DNS

```bash
# ============================================================
# DEMO 1: User-defined bridge vs default bridge
# Shows why user-defined networks are required for DNS to work
# ============================================================

# --- Part A: Default bridge (DNS does NOT work) ---

# Run two containers on the default bridge
docker run -d --name net-demo-web nginx:1.25
docker run -d --name net-demo-db \
  -e POSTGRES_PASSWORD=pass \
  postgres:16

# Try to ping by name — this FAILS
docker exec net-demo-web ping -c 2 net-demo-db
# Error: ping: net-demo-db: Name or service not known

# We can only communicate by IP (fragile)
DB_IP=$(docker inspect --format '{{.NetworkSettings.IPAddress}}' net-demo-db)
echo "DB container IP: $DB_IP"
docker exec net-demo-web ping -c 2 $DB_IP   # This works, but IPs change!

# Clean up
docker rm -f net-demo-web net-demo-db

# --- Part B: User-defined bridge (DNS WORKS) ---

# Create a user-defined bridge network
docker network create app-demo-net

# Inspect it — note the subnet assigned automatically
docker network inspect app-demo-net | grep -A 5 '"IPAM"'

# Run containers on the custom network
docker run -d \
  --name web \
  --network app-demo-net \
  nginx:1.25

docker run -d \
  --name db \
  --network app-demo-net \
  -e POSTGRES_PASSWORD=pass \
  postgres:16

# Now DNS works! Containers find each other by name
docker exec web ping -c 3 db
# PING db (172.20.0.X): 56 data bytes — works!

# Verify the DNS configuration inside the container
docker exec web cat /etc/resolv.conf
# Shows: nameserver 127.0.0.11 — Docker's embedded DNS

# Verify DNS resolution
docker exec web nslookup db
# Shows: Server: 127.0.0.11, db resolves to 172.20.0.X

# Clean up
docker rm -f web db
docker network rm app-demo-net
```

---

## 2. Run App and Database on the Same Network

```bash
# ============================================================
# DEMO 2: Complete web app + database on a shared network
# App container connects to database using the container name
# ============================================================

# Create the application network
docker network create webapp-net

# Start Postgres on the network
docker run -d \
  --name postgres \
  --network webapp-net \
  -e POSTGRES_USER=appuser \
  -e POSTGRES_PASSWORD=apppassword \
  -e POSTGRES_DB=appdb \
  postgres:16

# Wait for Postgres to be ready (it takes a few seconds to initialize)
echo "Waiting for Postgres to start..."
docker exec postgres sh -c "until pg_isready -U appuser; do sleep 1; done" 2>/dev/null || \
  sleep 5   # fallback: wait 5 seconds

# Verify Postgres is up
docker exec postgres psql -U appuser -d appdb -c "\conninfo"

# Run a simple app that connects to Postgres by container name
# We'll use the psql client in a separate container as a stand-in for "the app"
docker run -it --rm \
  --name app \
  --network webapp-net \
  -e PGPASSWORD=apppassword \
  postgres:16 \
  psql -h postgres -U appuser -d appdb -c "SELECT 'Connected to Postgres by container name!' AS result;"

# Note: '-h postgres' uses the container name 'postgres' as the hostname
# Docker DNS resolves 'postgres' to the container's IP on webapp-net

# Clean up
docker rm -f postgres
docker network rm webapp-net
```

---

## 3. Port Publishing and Verification

```bash
# ============================================================
# DEMO 3: Port publishing patterns
# ============================================================

# Basic port publishing: host:8080 → container:80
docker run -d \
  --name nginx-published \
  -p 8080:80 \
  nginx:1.25

# Verify the port mapping
docker port nginx-published
# Output: 80/tcp -> 0.0.0.0:8080

# Test from host
curl -s -o /dev/null -w "HTTP %{http_code}" http://localhost:8080
# HTTP 200

# Check the iptables rule Docker created (Linux only; skip on macOS/Windows)
# sudo iptables -t nat -L DOCKER -n --line-numbers | grep 8080

# Inspect the port mapping in container metadata
docker inspect --format '{{json .NetworkSettings.Ports}}' nginx-published | python3 -m json.tool
# Shows: "80/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8080"}]

# Bind to localhost only (not reachable from other machines on your network)
docker run -d \
  --name nginx-local \
  -p 127.0.0.1:8081:80 \
  nginx:1.25

docker port nginx-local
# Output: 80/tcp -> 127.0.0.1:8081

# Publish ALL EXPOSE'd ports to random host ports
docker run -d \
  --name nginx-random \
  -P \
  nginx:1.25

docker port nginx-random
# Output: 80/tcp -> 0.0.0.0:49XXX (random port)

# Publish multiple ports (nginx serving HTTP + HTTPS)
docker run -d \
  --name nginx-multi \
  -p 8443:443 \
  -p 8080:80 \
  nginx:1.25

docker port nginx-multi
# 80/tcp -> 0.0.0.0:8080
# 443/tcp -> 0.0.0.0:8443

# Clean up
docker rm -f nginx-published nginx-local nginx-random nginx-multi
```

---

## 4. Multi-Network Segmentation (DMZ Pattern)

```bash
# ============================================================
# DEMO 4: Network segmentation
# frontend-net: public traffic → frontend and API
# backend-net: private → API and database
# Database is unreachable from frontend (different network)
# ============================================================

# Create two separate networks
docker network create frontend-net
docker network create backend-net

echo "Networks created:"
docker network ls | grep -E "frontend-net|backend-net"

# Database: only on backend-net
docker run -d \
  --name db \
  --network backend-net \
  -e POSTGRES_PASSWORD=secret \
  postgres:16

# API service: starts on backend-net
docker run -d \
  --name api \
  --network backend-net \
  --entrypoint sh \
  alpine -c "while true; do sleep 3600; done"   # placeholder that stays running

# Connect API to frontend-net too — it bridges both networks
docker network connect frontend-net api

# Frontend: only on frontend-net, port published to host
docker run -d \
  --name frontend \
  --network frontend-net \
  --entrypoint sh \
  -p 8080:80 \
  alpine -c "while true; do sleep 3600; done"   # placeholder

# === Demonstrate the isolation ===

echo ""
echo "=== Network connectivity tests ==="

# api → db: SHOULD WORK (same backend-net)
echo -n "api → db (should work): "
docker exec api sh -c "ping -c 1 -W 2 db > /dev/null 2>&1 && echo PASS || echo FAIL"

# frontend → api: SHOULD WORK (same frontend-net)
echo -n "frontend → api (should work): "
docker exec frontend sh -c "ping -c 1 -W 2 api > /dev/null 2>&1 && echo PASS || echo FAIL"

# frontend → db: SHOULD FAIL (different networks, no path)
echo -n "frontend → db (should fail): "
docker exec frontend sh -c "ping -c 1 -W 2 db > /dev/null 2>&1 && echo UNEXPECTED-PASS || echo EXPECTED-FAIL"

# Verify what networks each container is on
echo ""
echo "=== Container network memberships ==="
docker inspect --format '{{.Name}}: {{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' db api frontend

# Clean up
docker rm -f db api frontend
docker network rm frontend-net backend-net
```

---

## 5. Network Troubleshooting Toolkit

```bash
# ============================================================
# DEMO 5: Useful network debugging techniques
# ============================================================

# Set up a demo network with containers to troubleshoot
docker network create troubleshoot-net

docker run -d --name server \
  --network troubleshoot-net \
  nginx:1.25

docker run -d --name client \
  --network troubleshoot-net \
  alpine sleep 3600

# === Tool 1: DNS lookup ===
docker exec client nslookup server
# Shows DNS server IP (127.0.0.11) and the resolved IP of 'server'

# === Tool 2: Check /etc/resolv.conf ===
docker exec client cat /etc/resolv.conf
# nameserver 127.0.0.11
# options ndots:0

# === Tool 3: HTTP connectivity ===
docker exec client wget -qO- http://server/
# Downloads nginx welcome page — proves HTTP connectivity

# === Tool 4: TCP port check ===
docker exec client sh -c "echo > /dev/tcp/server/80 && echo 'Port 80 is open'" 2>/dev/null || \
  docker exec client nc -zv server 80 2>&1 || \
  echo "Use 'docker exec client wget -qO- http://server/' to test"

# === Tool 5: Container IP information ===
# IP assigned on troubleshoot-net
docker inspect --format \
  '{{range .NetworkSettings.Networks}}Network: {{.NetworkID}} → IP: {{.IPAddress}}{{end}}' \
  server

# Get just the IP on a specific network
docker inspect --format \
  '{{(index .NetworkSettings.Networks "troubleshoot-net").IPAddress}}' \
  server

# === Tool 6: All container network memberships ===
docker network inspect troubleshoot-net --format '{{json .Containers}}' | \
  python3 -m json.tool

# === Tool 7: Check published ports ===
docker port server    # (no output — server is not publishing ports to the host)

# Run nginx with a published port and recheck
docker run -d --name server-public -p 9090:80 nginx:1.25
docker port server-public
# 80/tcp -> 0.0.0.0:9090

# === Tool 8: See all Docker networks ===
docker network ls

# Clean up
docker rm -f server client server-public
docker network rm troubleshoot-net
```

---

## 6. Network Alias for Service Discovery

```bash
# ============================================================
# DEMO 6: Network aliases
# Multiple containers share one DNS name (blue/green deploy pattern)
# ============================================================

docker network create alias-demo-net

# Run version 1 of the database — accessible as 'database'
docker run -d \
  --name db-v1 \
  --network alias-demo-net \
  --network-alias database \
  -e POSTGRES_PASSWORD=pass \
  postgres:15

# App connects to 'database' (the alias)
docker run -d \
  --name app \
  --network alias-demo-net \
  alpine sleep 3600

# App can reach 'db-v1' by its alias 'database'
docker exec app nslookup database
# Resolves to db-v1's IP

# Simulate a zero-downtime upgrade:
# Start the new version ALSO with the same alias
docker run -d \
  --name db-v2 \
  --network alias-demo-net \
  --network-alias database \
  -e POSTGRES_PASSWORD=pass \
  postgres:16

# Now 'database' resolves to BOTH db-v1 and db-v2 (Docker round-robins)
docker exec app nslookup database
# May show multiple IPs

# Remove old version — alias now only points to db-v2
docker rm -f db-v1

docker exec app nslookup database
# Only resolves to db-v2's IP

# Clean up
docker rm -f db-v2 app
docker network rm alias-demo-net
```

---

## 📂 Navigation

**In this folder:**
| File | |
|---|---|
| [📖 Theory.md](./Theory.md) | Full explanation |
| [⚡ Cheatsheet.md](./Cheatsheet.md) | Quick reference |
| [🎯 Interview_QA.md](./Interview_QA.md) | Interview prep |
| 💻 **Code_Example.md** | ← you are here |

⬅️ **Prev:** [07 — Volumes and Bind Mounts](../07_Volumes_and_Bind_Mounts/Code_Example.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [09 — Docker Compose](../09_Docker_Compose/Code_Example.md)
🏠 **[Home](../../README.md)**
