# Container Lifecycle — Code Examples

A complete walkthrough of nginx container management: run, inspect, log, exec, stop, and clean up.

---

## 1. Run Nginx with Port Mapping

```bash
# Pull nginx (specify version — don't use latest in scripts)
docker pull nginx:1.25

# Run in detached mode (background):
# -d: detach (run in background)
# --name: give it a predictable name
# -p 8080:80: map host port 8080 to container port 80
# --restart unless-stopped: survive crashes and daemon restarts
docker run -d \
  --name my-nginx \
  -p 8080:80 \
  --restart unless-stopped \
  nginx:1.25

# Verify it started
docker ps

# Test it's serving
curl http://localhost:8080
# Should return the nginx welcome page HTML

# View the port mapping
docker port my-nginx
# Output: 80/tcp -> 0.0.0.0:8080
```

---

## 2. Inspect the Running Container

```bash
# Full metadata dump (lots of output — good for reference)
docker inspect my-nginx

# Get specific fields with Go templates

# Container status
docker inspect --format '{{.State.Status}}' my-nginx
# Output: running

# Container PID on the HOST (not inside the container)
docker inspect --format '{{.State.Pid}}' my-nginx

# Container's IP address on the Docker bridge network
docker inspect --format '{{.NetworkSettings.IPAddress}}' my-nginx
# Output: 172.17.0.2 (or similar)

# All environment variables set in the container
docker inspect --format '{{json .Config.Env}}' my-nginx | python3 -m json.tool

# Mounts (volumes, bind mounts)
docker inspect --format '{{json .Mounts}}' my-nginx | python3 -m json.tool

# Restart policy
docker inspect --format '{{.HostConfig.RestartPolicy.Name}}' my-nginx
# Output: unless-stopped

# Resource limits (0 = no limit)
docker inspect --format 'Memory: {{.HostConfig.Memory}} NanoCPUs: {{.HostConfig.NanoCpus}}' my-nginx
```

---

## 3. Live Resource Usage

```bash
# Live CPU, memory, network, and block I/O stats (press Ctrl+C to exit)
docker stats my-nginx

# One-shot snapshot (no live update — useful in scripts)
docker stats --no-stream my-nginx

# Show stats for all running containers
docker stats

# Format output for scripts (JSON-friendly)
docker stats --no-stream --format \
  "{{.Name}}: CPU={{.CPUPerc}} MEM={{.MemUsage}} NET={{.NetIO}}" \
  my-nginx

# Running processes inside the container (like 'ps' but from outside)
docker top my-nginx
# Output: PID, USER, TIME, COMMAND — shows nginx master + worker processes
```

---

## 4. Check Logs

```bash
# Show all logs since container started
docker logs my-nginx

# Follow logs in real time (Ctrl+C to stop following)
docker logs -f my-nginx

# Show only the last 20 lines
docker logs --tail 20 my-nginx

# Show logs with timestamps
docker logs -t my-nginx

# The most useful combination: last 50 lines, follow, with timestamps
docker logs -f -t --tail 50 my-nginx

# Show logs since a specific time
docker logs --since 10m my-nginx      # last 10 minutes
docker logs --since "2024-01-15T10:00:00" my-nginx

# Redirect logs to a file (useful for analysis)
docker logs my-nginx > nginx.log 2>&1
```

---

## 5. Execute Commands Inside the Container

```bash
# === Interactive shell ===
# Opens a bash shell inside the container
# -i: keep stdin open
# -t: allocate a pseudo-TTY (makes it feel like a real terminal)
docker exec -it my-nginx bash

# If bash isn't available (Alpine-based images use sh):
docker exec -it my-nginx sh

# === Run one-off commands ===
# List nginx configuration files
docker exec my-nginx ls /etc/nginx/conf.d/

# Print the default nginx config
docker exec my-nginx cat /etc/nginx/conf.d/default.conf

# Test nginx configuration syntax (without reloading)
docker exec my-nginx nginx -t
# Output: nginx: configuration file /etc/nginx/nginx.conf test is successful

# Check nginx version and build info
docker exec my-nginx nginx -v
docker exec my-nginx nginx -V   # verbose: shows compile options

# Check what processes are running inside
docker exec my-nginx ps aux

# === Execute as a different user ===
# Sometimes you need root to inspect files owned by root
docker exec -u root my-nginx bash
docker exec -u 0 my-nginx bash   # same thing — UID 0 = root

# === Execute with environment variable ===
docker exec -e MY_VAR=hello my-nginx env | grep MY_VAR
```

---

## 6. Modify Nginx Config (exec + cp pattern)

```bash
# Create a custom nginx config on the host
cat > /tmp/custom.conf << 'EOF'
server {
    listen 80;
    server_name localhost;

    location / {
        root /usr/share/nginx/html;
        index index.html;
    }

    location /health {
        return 200 'OK';
        add_header Content-Type text/plain;
    }
}
EOF

# Copy config from host into running container
docker cp /tmp/custom.conf my-nginx:/etc/nginx/conf.d/default.conf

# Test the new config
docker exec my-nginx nginx -t

# Reload nginx (graceful reload — no downtime)
docker exec my-nginx nginx -s reload

# Test the new /health endpoint
curl http://localhost:8080/health
# Output: OK

# Copy a file OUT of the container
docker cp my-nginx:/etc/nginx/nginx.conf ./nginx-main.conf
cat ./nginx-main.conf

# Copy a directory out of the container
docker cp my-nginx:/var/log/nginx/ ./nginx-logs/
ls ./nginx-logs/
```

---

## 7. Stop, Start, and Restart

```bash
# === Graceful stop ===
# Sends SIGTERM to PID 1, waits 10 seconds, then sends SIGKILL
docker stop my-nginx

# Verify it stopped
docker ps          # should not appear
docker ps -a       # should appear as "Exited"
docker inspect --format '{{.State.Status}} (exit code: {{.State.ExitCode}})' my-nginx

# === Restart the container ===
docker start my-nginx
docker ps   # back to running

# === Restart (stop + start in one command) ===
docker restart my-nginx

# === Graceful stop with custom timeout ===
# Give the container 30 seconds to finish graceful shutdown
docker stop --time 30 my-nginx

# === Force kill (immediate, no grace period) ===
# Use only when container is stuck and not responding to SIGTERM
docker kill my-nginx

# === Send a specific signal ===
# nginx supports SIGHUP to reload config without restart
docker kill --signal SIGHUP my-nginx
```

---

## 8. Run with Resource Limits

```bash
# Remove the old container first
docker rm -f my-nginx 2>/dev/null || true

# Run nginx with resource limits
docker run -d \
  --name my-nginx-limited \
  -p 8080:80 \
  --memory 128m \             # hard memory limit: 128 MB
  --memory-swap 128m \        # no swap (memory-swap == memory)
  --cpus 0.5 \                # max 0.5 CPU cores
  --restart unless-stopped \
  nginx:1.25

# Verify limits were applied
docker inspect --format \
  'Memory: {{.HostConfig.Memory}} bytes, CPUs: {{.HostConfig.NanoCpus}} nanocpus' \
  my-nginx-limited
# NanoCPUs: 500000000 = 0.5 CPUs (1 CPU = 1,000,000,000 nanocpus)

# Check if it was ever OOM-killed
docker inspect --format '{{.State.OOMKilled}}' my-nginx-limited

# Live monitoring
docker stats --no-stream my-nginx-limited

# Clean up
docker rm -f my-nginx-limited
```

---

## 9. Cleanup Commands

```bash
# Stop and remove a single container
docker stop my-nginx
docker rm my-nginx

# Or force-remove a running container in one step
docker rm -f my-nginx

# === Bulk cleanup ===

# Remove all stopped containers
docker container prune
# Prompts for confirmation; add -f to skip

# Remove stopped containers older than 24 hours
docker container prune --filter "until=24h"

# === Full system audit ===
# See disk usage by images, containers, volumes, build cache
docker system df

# Verbose: show per-item breakdown
docker system df -v

# Remove EVERYTHING unused (containers, images, networks, build cache)
# Use with caution — you'll need to repull all images
docker system prune -a

# === List all containers (including stopped) ===
docker ps -a

# List containers filtered by status
docker ps -a --filter status=exited
docker ps -a --filter status=created
docker ps -a --filter name=nginx    # by name pattern

# === Get exit codes of all exited containers ===
docker ps -a --filter status=exited \
  --format "{{.Names}}: {{.Status}}"
```

---

## 10. Complete Lifecycle Demo Script

```bash
#!/bin/bash
# lifecycle-demo.sh
# Demonstrates the full container lifecycle end to end.
# Run: bash lifecycle-demo.sh

set -e   # exit on any error

echo "=== 1. Pull image ==="
docker pull nginx:1.25

echo ""
echo "=== 2. Create container (without starting) ==="
docker create --name lifecycle-demo -p 8888:80 nginx:1.25
docker inspect --format 'State: {{.State.Status}}' lifecycle-demo

echo ""
echo "=== 3. Start it ==="
docker start lifecycle-demo
docker inspect --format 'State: {{.State.Status}}' lifecycle-demo

echo ""
echo "=== 4. Test it ==="
sleep 1
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:8888

echo ""
echo "=== 5. Pause it ==="
docker pause lifecycle-demo
docker inspect --format 'State: {{.State.Status}}' lifecycle-demo
echo "(Container is frozen — processes stopped but still in memory)"

echo ""
echo "=== 6. Unpause it ==="
docker unpause lifecycle-demo
docker inspect --format 'State: {{.State.Status}}' lifecycle-demo

echo ""
echo "=== 7. Check logs ==="
docker logs --tail 5 lifecycle-demo

echo ""
echo "=== 8. Stop it ==="
docker stop lifecycle-demo
docker inspect --format 'State: {{.State.Status}}, Exit code: {{.State.ExitCode}}' lifecycle-demo

echo ""
echo "=== 9. Remove it ==="
docker rm lifecycle-demo
echo "Container removed"

echo ""
echo "=== Done! ==="
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

⬅️ **Prev:** [05 — Dockerfile](../05_Dockerfile/Code_Example.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [07 — Volumes and Bind Mounts](../07_Volumes_and_Bind_Mounts/Code_Example.md)
🏠 **[Home](../../README.md)**
