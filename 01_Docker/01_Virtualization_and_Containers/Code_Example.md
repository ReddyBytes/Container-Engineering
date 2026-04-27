# Virtualization and Containers — Code Examples

All examples are production-quality with detailed comments explaining every decision.

---

## 1. Observing Namespaces — Container Isolation in Action

This demo shows the Linux namespace isolation that makes containers work. Run commands inside a container and compare them to the host to see the pid, net, and uts namespaces in action.

```bash
# Start a container in the background
# --name: give it a recognizable name so we can reference it later
docker run -d --name ns-demo alpine sleep 300

# -----------------------------------------------
# PID NAMESPACE: the container has its own process tree
# -----------------------------------------------

# On the host: 'sleep 300' appears with its real host PID (e.g., 12345)
ps aux | grep "sleep 300"

# Inside the container: the same 'sleep 300' process appears as PID 1
# This is the pid namespace — the container sees a completely separate numbering
docker exec ns-demo ps aux
# Output: PID 1 is 'sleep 300' — the container thinks it's the first process

# -----------------------------------------------
# NET NAMESPACE: the container has its own network interfaces
# -----------------------------------------------

# Host network interfaces (eth0, lo, docker0, veth*)
ip addr show

# Container network interfaces — only eth0 and lo, with a different IP
docker exec ns-demo ip addr show
# Notice: the container's eth0 IP is 172.17.x.x — completely separate from the host

# -----------------------------------------------
# UTS NAMESPACE: the container has its own hostname
# -----------------------------------------------

# Host hostname
hostname

# Container hostname — defaults to the container ID
docker exec ns-demo hostname
# Output: a3f9b2c1d4e5 (the container ID, not the host's hostname)

# You can set a custom hostname at run time
docker run --rm --hostname my-service alpine hostname
# Output: my-service

# Cleanup
docker stop ns-demo && docker rm ns-demo
```

---

## 2. Observing cgroups — Resource Limits on a Container

cgroups control what a process can *use*. This demo applies memory and CPU limits and then verifies them from inside and outside the container.

```bash
# Run a container with hard resource limits:
# --memory 128m: container cannot exceed 128 MB RAM
# --memory-swap 128m: setting swap equal to memory disables swap
# --cpus 0.5: container gets at most half a CPU core
docker run -d \
  --name cgroup-demo \
  --memory 128m \
  --memory-swap 128m \
  --cpus 0.5 \
  nginx

# Verify the limits Docker set via cgroups:
# memory.limit_in_bytes shows the raw byte cap (134217728 = 128 MB)
docker exec cgroup-demo cat /sys/fs/cgroup/memory/memory.limit_in_bytes
# Output: 134217728

# From the host, inspect via docker stats (live resource usage)
# CTRL+C to exit
docker stats cgroup-demo --no-stream
# Columns: CPU %, MEM USAGE/LIMIT, NET I/O, BLOCK I/O
# MEM LIMIT should show 128MiB

# Inspect the OCI config Docker generated (shows raw cgroup spec)
docker inspect cgroup-demo | python3 -m json.tool | grep -A 10 "HostConfig"
# Look for: "Memory": 134217728, "NanoCpus": 500000000

# Attempt to consume more memory than the limit — the container will be OOMKilled
docker run --rm \
  --memory 32m \
  --memory-swap 32m \
  python:3.11-slim \
  python3 -c "x = ' ' * 100 * 1024 * 1024"
# The kernel OOM killer terminates the process — exit code 137

# Cleanup
docker stop cgroup-demo && docker rm cgroup-demo
```

---

## 3. VM vs Container — Startup Time Comparison

This demo makes the startup time difference between a VM and a container concrete. You won't have a full VM setup, but you can observe container start time and understand the contrast.

```bash
# Time how long it takes to start a container and run a command
# 'time' wraps the entire docker run from cold start
time docker run --rm alpine echo "container started"
# Expected: real 0m0.4s — sub-second, because no OS to boot
# A VM boot is typically 15–60 seconds even on fast hardware

# Second run: layer is cached, even faster
time docker run --rm alpine echo "container started again"
# Expected: real 0m0.2s — image already local, container starts immediately

# Show that the container shares the host kernel — not its own
# The kernel version inside the container matches the host
uname -r                                   # host kernel
docker run --rm alpine uname -r            # container kernel — same output
# Both print the same version because containers share the host kernel
# A VM would show its own (potentially different) kernel version

# Size comparison: pull a minimal container image vs a typical VM image
# Typical VM image is 1-20 GB; containers are MBs
docker pull alpine
docker images alpine
# SIZE column: ~7MB for Alpine — a full VM base image is 400x larger minimum

# Show that multiple containers run simultaneously on the same kernel
docker run -d --name c1 alpine sleep 60
docker run -d --name c2 alpine sleep 60
docker run -d --name c3 alpine sleep 60
# Three isolated environments, one kernel — impossible with separate VMs at this cost
docker ps
docker stop c1 c2 c3 && docker rm c1 c2 c3
```

---

## 4. OCI Runtime Stack — Inspecting the Layers

This demo walks through the actual runtime stack: containerd, runc, and the shim process. You can see each layer in action.

```bash
# Start a container
docker run -d --name stack-demo nginx

# -----------------------------------------------
# LAYER 1: Docker CLI → dockerd socket
# The CLI is just a REST client. Show the socket it talks to:
# -----------------------------------------------
docker info | grep "Docker Root Dir"
# /var/lib/docker — this is where dockerd stores all data

# Show the socket file (Linux only)
ls -la /var/run/docker.sock
# srw-rw---- — 's' means Unix socket, owned by root:docker group

# -----------------------------------------------
# LAYER 2: dockerd → containerd
# containerd manages container lifecycle
# -----------------------------------------------
# On Linux, list containers via containerd directly (bypasses Docker)
# This shows containerd is independent of dockerd
sudo ctr -n moby containers list
# You'll see stack-demo in containerd's namespace "moby"

# -----------------------------------------------
# LAYER 3: containerd → shim → runc
# One shim process per container stays alive after runc exits
# -----------------------------------------------
# Find the shim process for our container
ps aux | grep containerd-shim
# Shows: containerd-shim-runc-v2 with the container ID in args
# The shim is the container's parent process — runc has already exited

# -----------------------------------------------
# LAYER 4: OCI bundle on disk
# containerd creates a rootfs bundle that runc consumes
# -----------------------------------------------
docker inspect stack-demo | python3 -m json.tool | grep -A 3 "GraphDriver"
# Shows OverlayFS layers: LowerDir (read-only image layers) + UpperDir (writable container layer)

# Cleanup
docker stop stack-demo && docker rm stack-demo
```

---

## 5. Container Immutability — Ephemeral Filesystem Demo

This demo demonstrates why containers are ephemeral and why persistent data must live in volumes. It shows the copy-on-write layer and what happens when a container is removed.

```bash
# Start a container and write some data to its filesystem
docker run -d --name ephemeral-demo alpine sleep 300

# Write a file inside the container's writable layer
docker exec ephemeral-demo sh -c "echo 'I will be lost' > /tmp/testfile.txt"
docker exec ephemeral-demo cat /tmp/testfile.txt
# Output: I will be lost

# The file ONLY exists in the container's writable (UpperDir) layer
# Prove it: the base alpine image has no such file
docker run --rm alpine cat /tmp/testfile.txt 2>&1
# Error: can't open '/tmp/testfile.txt': No such file or directory
# The base image is unaffected — copy-on-write isolated the change

# Stop and REMOVE the container — writable layer is destroyed
docker stop ephemeral-demo && docker rm ephemeral-demo

# Data is gone — no container, no writable layer, no file
docker run --rm alpine cat /tmp/testfile.txt 2>&1
# Error: file not found — confirms ephemeral nature

# -----------------------------------------------
# SOLUTION: Use a named volume for persistent data
# -----------------------------------------------
docker volume create app-data

# Mount the volume — data written here survives container removal
docker run -d \
  --name persistent-demo \
  -v app-data:/data \
  alpine sleep 300

docker exec persistent-demo sh -c "echo 'I will survive' > /data/testfile.txt"

# Remove the container
docker stop persistent-demo && docker rm persistent-demo

# Start a new container, mount the same volume — data is still there
docker run --rm \
  -v app-data:/data \
  alpine cat /data/testfile.txt
# Output: I will survive — volume outlives any individual container

# Cleanup
docker volume rm app-data
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

➡️ **Next:** [02 — Docker Architecture](../02_Docker_Architecture/Code_Example.md)
🏠 **[Home](../../README.md)**
