# Volumes and Bind Mounts — Code Examples

Three complete working examples: Postgres with a named volume, hot-reload dev with a bind mount, and tmpfs for secrets.

---

## 1. Named Volume for Postgres Data

```bash
# ============================================================
# EXAMPLE 1: Postgres with a Named Volume
#
# Goal: run Postgres so that database data survives container
# replacement. The named volume 'pgdata' persists independently
# of any container.
# ============================================================

# Step 1: Create the named volume explicitly
# (Optional — Docker auto-creates it on 'docker run' if it doesn't exist)
docker volume create pgdata

# Inspect the volume to see where Docker stores it on the host
docker volume inspect pgdata
# Look for "Mountpoint": "/var/lib/docker/volumes/pgdata/_data"

# Step 2: Start Postgres
# - -d: detached (background)
# - --name: predictable name
# - -e POSTGRES_PASSWORD: required env var for the postgres image
# - -e POSTGRES_DB: creates this database on first start
# - -v pgdata:/var/lib/postgresql/data: mount named volume to Postgres data dir
# - -p 5432:5432: publish Postgres port
# - --restart unless-stopped: survive crashes and host reboots
docker run -d \
  --name my-postgres \
  -e POSTGRES_PASSWORD=mysecretpassword \
  -e POSTGRES_USER=myuser \
  -e POSTGRES_DB=mydb \
  -v pgdata:/var/lib/postgresql/data \
  -p 5432:5432 \
  --restart unless-stopped \
  postgres:16

# Step 3: Wait for Postgres to be ready
# Postgres takes a few seconds to initialize on first run (creates data directory)
docker logs -f my-postgres
# Press Ctrl+C when you see: "database system is ready to accept connections"

# Step 4: Connect and create some data
docker exec -it my-postgres psql -U myuser -d mydb
# Inside psql:
#   CREATE TABLE users (id SERIAL PRIMARY KEY, name VARCHAR(100));
#   INSERT INTO users (name) VALUES ('Alice'), ('Bob');
#   SELECT * FROM users;
#   \q

# Step 5: Prove data persists — destroy and recreate the container
docker rm -f my-postgres

# The container is gone, but the VOLUME still exists
docker volume ls | grep pgdata    # still there

# Step 6: Create a fresh container mounting the same volume
docker run -d \
  --name my-postgres-v2 \
  -e POSTGRES_PASSWORD=mysecretpassword \
  -e POSTGRES_USER=myuser \
  -e POSTGRES_DB=mydb \
  -v pgdata:/var/lib/postgresql/data \
  -p 5432:5432 \
  postgres:16

# Connect and verify data survived
docker exec -it my-postgres-v2 psql -U myuser -d mydb -c "SELECT * FROM users;"
# Output: Alice, Bob — data survived container removal!

# Step 7: Backup the volume
docker run --rm \
  -v pgdata:/source:ro \
  -v $(pwd):/backup \
  alpine \
  tar czf /backup/pgdata-backup.tar.gz -C /source .

ls -lh pgdata-backup.tar.gz   # verify backup created

# Step 8: Clean up
docker rm -f my-postgres-v2
docker volume rm pgdata
```

---

## 2. Bind Mount for Dev Hot-Reload

```bash
# ============================================================
# EXAMPLE 2: Bind Mount for Development Hot-Reload
#
# Goal: run a Node.js app with nodemon inside Docker.
# Source code on the host is mounted into the container —
# editing files on your host immediately reflects in the container,
# no rebuild required.
# ============================================================

# Create project structure
mkdir -p /tmp/hotreload-demo/src
cd /tmp/hotreload-demo

# Create package.json
cat > package.json << 'EOF'
{
  "name": "hotreload-demo",
  "version": "1.0.0",
  "scripts": {
    "start": "node src/index.js",
    "dev": "nodemon src/index.js"
  },
  "dependencies": {
    "express": "^4.18.2"
  },
  "devDependencies": {
    "nodemon": "^3.0.2"
  }
}
EOF

# Create the application
cat > src/index.js << 'EOF'
const express = require('express');
const app = express();

app.get('/', (req, res) => {
  // Edit this message, save the file, see it update instantly in the container
  res.send('Hello! Edit this file on your host to see hot reload in action.\n');
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
EOF

# Create a Dockerfile for development (includes devDependencies for nodemon)
cat > Dockerfile.dev << 'EOF'
FROM node:20-alpine
WORKDIR /app

# Install dependencies including devDependencies
COPY package.json package-lock.json* ./
RUN npm install      # installs nodemon since we don't use --omit=dev

# Don't COPY src here! We'll bind mount it from the host.
# This means we can edit on the host and see changes immediately.

CMD ["npm", "run", "dev"]
EOF

# Build the dev image
docker build -f Dockerfile.dev -t hotreload-demo:dev .

# Run with bind mounts:
# 1. src/ is bind-mounted: host edits appear instantly in container
# 2. node_modules is a NAMED VOLUME: stays inside Docker VM (fast on macOS!)
#    Without this, node_modules would be bind-mounted too — very slow on macOS/Windows
docker run -d \
  --name hotreload \
  -p 3000:3000 \
  -v $(pwd)/src:/app/src \              # bind mount source code (editable from host)
  -v $(pwd)/package.json:/app/package.json:ro \   # dep manifest (read-only from host)
  -v hotreload_node_modules:/app/node_modules \   # named volume for performance
  hotreload-demo:dev

# Test it
curl http://localhost:3000/

# Now edit the source file on your HOST:
echo "// updated at $(date)" >> src/index.js
sed -i '' 's/Hello!/Hello from the updated file!/g' src/index.js

# nodemon inside the container detects the change and restarts
docker logs -f hotreload
# You'll see: [nodemon] restarting due to changes...

# Test again — new message without rebuilding
curl http://localhost:3000/

# Clean up
docker rm -f hotreload
docker volume rm hotreload_node_modules
cd /tmp && rm -rf /tmp/hotreload-demo
```

---

## 3. tmpfs for Secrets

```bash
# ============================================================
# EXAMPLE 3: tmpfs for Sensitive Data
#
# Goal: run a container that receives a secret (API token) via
# an in-memory tmpfs mount. The secret is NEVER written to disk —
# not in the container filesystem, not in the host filesystem.
# ============================================================

# Imagine you have an API token to inject into a container
# We'll simulate this with a demo script

# Create a demo image that reads and uses a secret from /run/secrets
mkdir -p /tmp/tmpfs-demo
cat > /tmp/tmpfs-demo/app.sh << 'EOF'
#!/bin/sh
# Application that reads a secret from the tmpfs mountpoint
# In a real app, this would be your API key, DB password, etc.

SECRET_FILE="/run/secrets/api_token"

if [ -f "$SECRET_FILE" ]; then
    TOKEN=$(cat "$SECRET_FILE")
    echo "Loaded secret (first 4 chars): ${TOKEN:0:4}****"
    echo "Secret file permissions: $(ls -la $SECRET_FILE)"
    echo "Is /run/secrets on tmpfs? $(mount | grep /run/secrets || echo 'check with df')"
    df -h /run/secrets 2>/dev/null || echo "(df not available on this tmpfs)"
else
    echo "No secret found at $SECRET_FILE"
    exit 1
fi

echo ""
echo "Application doing work... (simulated)"
sleep 30
EOF

cat > /tmp/tmpfs-demo/Dockerfile << 'EOF'
FROM alpine:3.19
RUN apk add --no-cache bash
COPY app.sh /app.sh
RUN chmod +x /app.sh
CMD ["/app.sh"]
EOF

cd /tmp/tmpfs-demo
docker build -t tmpfs-demo .

# === Method 1: Pass secret via tmpfs volume ===
# The tmpfs mount at /run/secrets is in RAM only
# We inject the secret by writing to the tmpfs after the container starts
docker run -d \
  --name secret-app \
  --mount type=tmpfs,target=/run/secrets,tmpfs-mode=0700,tmpfs-size=1048576 \
  tmpfs-demo

# Write the secret into the tmpfs from outside
echo "super-secret-token-abc123" | docker exec -i secret-app sh -c 'cat > /run/secrets/api_token'
docker exec secret-app chmod 0400 /run/secrets/api_token

# Check what the app sees
docker logs secret-app

# Verify: even if you stop and remove the container, the secret is gone
# It was only ever in RAM

# === Method 2: Docker Secrets (for Swarm) ===
# In Docker Swarm, secrets are properly managed:
# echo "super-secret-token" | docker secret create api_token -
# docker service create \
#   --secret api_token \    # mounted at /run/secrets/api_token in the container
#   myapp

# === Method 3: BuildKit secret (at build time) ===
# If you need a secret DURING the build (e.g., private npm token):
# docker buildx build \
#   --secret id=npm_token,env=NPM_TOKEN \
#   -t myapp .
#
# In your Dockerfile:
# RUN --mount=type=secret,id=npm_token \
#     NPM_TOKEN=$(cat /run/secrets/npm_token) npm install

# Clean up
docker rm -f secret-app
cd /tmp && rm -rf /tmp/tmpfs-demo
docker rmi tmpfs-demo
```

---

## 4. Volume Management and Inspection

```bash
# ============================================================
# EXAMPLE 4: Volume Management
# ============================================================

# Create volumes
docker volume create app-data
docker volume create app-logs
docker volume create app-cache

# List volumes (shows driver and scope)
docker volume ls

# Inspect a specific volume
docker volume inspect app-data
# Key fields:
# "Driver": "local"
# "Mountpoint": "/var/lib/docker/volumes/app-data/_data"
# "Scope": "local"
# "Labels": {}

# On Linux (not inside Docker Desktop VM), you can ls the actual mount:
# sudo ls /var/lib/docker/volumes/app-data/_data

# Run a container and use the volume
docker run -d \
  --name app \
  -v app-data:/data \
  -v app-logs:/logs \
  alpine \
  sh -c "while true; do echo 'log entry' >> /logs/app.log; sleep 5; done"

# Use the volume from another container (read the logs)
docker run --rm \
  -v app-logs:/logs:ro \
  alpine \
  tail -20 /logs/app.log

# Find unused (dangling) volumes — ones not mounted in any container
docker volume ls --filter dangling=true

# Remove unused volumes (prompts for confirmation)
docker volume prune

# Remove specific volumes (fails if a container is using them)
docker rm -f app
docker volume rm app-data app-logs app-cache

# Confirm they're gone
docker volume ls
```

---

## 5. Bind Mount Permissions (common issue on Linux)

```bash
# ============================================================
# EXAMPLE 5: Handling Bind Mount Permission Mismatches
#
# Problem: container runs as non-root (UID 1001),
# host files owned by current user (UID 1000).
# The container can't write to the bind-mounted directory.
# ============================================================

# Create a directory on the host
mkdir -p /tmp/app-output
ls -la /tmp/ | grep app-output
# Owned by your user (e.g., UID 1000)

# Try to run a container as a different user that can't write
docker run --rm \
  --user 1001:1001 \
  -v /tmp/app-output:/output \
  alpine \
  sh -c "echo 'hello' > /output/test.txt" 2>&1
# Error: can't open '/output/test.txt': Permission denied

# === Solution 1: Match the container user to the host user ===
docker run --rm \
  --user $(id -u):$(id -g) \    # run as current host user
  -v /tmp/app-output:/output \
  alpine \
  sh -c "echo 'hello' > /output/test.txt"
cat /tmp/app-output/test.txt    # works!

# === Solution 2: Grant write permission to the directory ===
chmod 777 /tmp/app-output   # allow all users to write
docker run --rm \
  --user 1001:1001 \
  -v /tmp/app-output:/output \
  alpine \
  sh -c "echo 'hello from 1001' > /output/test.txt"

# === Solution 3: Run a setup container to set ownership inside volume ===
docker volume create owned-data
docker run --rm \
  -v owned-data:/data \
  alpine \
  sh -c "chown -R 1001:1001 /data && chmod 700 /data"
# Now containers running as 1001 can write to this volume

# Clean up
rm -rf /tmp/app-output
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

⬅️ **Prev:** [06 — Container Lifecycle](../06_Containers_Lifecycle/Code_Example.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [08 — Networking](../08_Networking/Code_Example.md)
🏠 **[Home](../../README.md)**
