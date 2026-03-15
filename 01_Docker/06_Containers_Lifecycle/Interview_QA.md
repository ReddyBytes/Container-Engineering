# Container Lifecycle — Interview Q&A

## Beginner

**Q1: What are the possible states a Docker container can be in?**

A Docker container can be in five states:

1. **Created** — The container exists (Docker has allocated its filesystem and applied configuration) but the main process hasn't started yet. Created by `docker create`.
2. **Running** — The main process is executing.
3. **Paused** — The container's processes are frozen. Docker sends SIGSTOP to all processes in the container's cgroup. No CPU usage, no progress — as if time stopped inside the container. Useful for taking filesystem snapshots without a running app interfering.
4. **Exited (Stopped)** — The main process has terminated, either normally (exit code 0) or with an error (non-zero exit code). The container still exists on disk with its writable layer — it can be restarted or inspected.
5. **Removed** — The container has been deleted with `docker rm`. The writable layer is gone; the container configuration is gone.

---

**Q2: What is the difference between `docker exec` and `docker attach`?**

`docker exec` runs a **new process** inside the container alongside the main process. It's the correct way to debug a running container:

```bash
docker exec -it mycontainer bash    # starts a new bash process in the container
```

`docker attach` connects your terminal to the **existing main process** (PID 1) — its stdin/stdout/stderr. You're not starting anything new; you're connecting to the process already running.

The danger with `docker attach`: if you press `Ctrl+C`, you send SIGINT to PID 1, which may terminate the container. The safe detach sequence is `Ctrl+P, Ctrl+Q`. Most people forget this and accidentally stop their containers.

**Prefer `docker exec`** for interactive debugging. Use `docker attach` only if you specifically need to interact with the container's PID 1 (e.g., a Node.js REPL that was started as PID 1).

---

**Q3: What does `docker run --rm` do and when should you use it?**

`--rm` tells Docker to automatically delete the container when it exits. Without `--rm`, stopped containers accumulate on your system (they still consume disk for their writable layer and metadata).

Use `--rm` for:
- One-off commands: `docker run --rm ubuntu echo "hello"`
- Tools run from images: `docker run --rm -v $(pwd):/app node:20 npm install`
- CI pipeline steps where you want clean state
- Any time you don't need to inspect or restart the container after it exits

Don't use `--rm` if:
- You need to inspect the container after it exits (logs, exit code, filesystem)
- You have a restart policy (`--restart`) — `--rm` and `--restart` conflict

---

**Q4: What is the difference between `docker stop` and `docker kill`?**

`docker stop` sends **SIGTERM** to PID 1 of the container, waits for the container to exit gracefully (default 10 seconds), then sends **SIGKILL** if it hasn't stopped.

`docker kill` sends **SIGKILL** immediately (or a specified signal with `--signal`). The process is terminated immediately without any cleanup.

Always use `docker stop` for production containers. Well-behaved applications catch SIGTERM and use the grace period to:
- Finish handling in-flight requests
- Close database connections
- Write any pending data
- Update load balancer health state

`docker kill` is for containers that are stuck (not responding to SIGTERM) or for emergency situations.

---

## Intermediate

**Q5: Explain Docker restart policies. Which one would you use for a production web service and why?**

Docker has four restart policies:

- **`no` (default):** Container never automatically restarts. If it crashes, it stays stopped.
- **`always`:** Restarts automatically regardless of exit code. Also starts on Docker daemon startup — even if you stopped the container manually before the daemon restarted.
- **`on-failure[:N]`:** Restarts only if the container exits with a non-zero exit code. Optionally limit to N retries.
- **`unless-stopped`:** Like `always`, but respects manual stops. If you `docker stop` the container, it won't restart on daemon start. If it crashes, it restarts.

**For a production web service:** `unless-stopped`.

It provides automatic recovery from crashes and restarts the service when the Docker daemon starts (e.g., after a server reboot). But unlike `always`, it respects an operator's decision to manually stop the container for maintenance. With `always`, if you `docker stop` for maintenance and the daemon restarts, the container starts automatically — potentially interfering with your maintenance window.

```bash
docker run -d --restart unless-stopped --name web nginx
```

---

**Q6: How would you investigate a container that has stopped unexpectedly?**

Systematic approach:

```bash
# 1. Find the stopped container
docker ps -a   # -a shows stopped containers too

# 2. Check the exit code
docker inspect --format '{{.State.ExitCode}}' mycontainer
# Exit code 0 = clean exit
# Exit code 1 = general error
# Exit code 137 = killed by SIGKILL (137 = 128 + 9)
# Exit code 139 = segfault (128 + 11)
# Exit code 143 = killed by SIGTERM (128 + 15)

# 3. Check start/stop times
docker inspect --format '{{.State.StartedAt}} → {{.State.FinishedAt}}' mycontainer

# 4. Read the logs (the most important step)
docker logs mycontainer
docker logs --tail 100 mycontainer

# 5. Check if health checks were failing
docker inspect --format '{{json .State.Health}}' mycontainer | jq .

# 6. Check resource limits — was it OOM killed?
docker inspect --format '{{.State.OOMKilled}}' mycontainer
# true = container was killed by the kernel for exceeding memory limit

# 7. If you need to investigate the filesystem
docker start mycontainer     # restart it
docker exec -it mycontainer sh   # get in and look around
```

Exit code 137 (OOM kill) is a common cause of mysterious container deaths in production. Solution: increase the `--memory` limit or fix the memory leak.

---

**Q7: How do resource limits (`--memory`, `--cpus`) work technically? What happens when a container exceeds its memory limit?**

Resource limits are implemented via **cgroups** (control groups) — a Linux kernel feature.

**Memory limits:**
When you run `docker run --memory 512m`, Docker writes the limit to the container's cgroup filesystem:
```
/sys/fs/cgroup/memory/<container>/memory.limit_in_bytes = 536870912 (512 MB)
```

The Linux kernel enforces this. When the container's processes try to allocate more memory than the limit:
1. The kernel first tries to free memory via page reclamation (swap out pages)
2. If memory still can't be allocated, the **OOM Killer** fires — it picks a process in the cgroup and sends it SIGKILL
3. Usually this kills the container's PID 1, stopping the container
4. `docker inspect` will show `"OOMKilled": true`

**CPU limits:**
`--cpus 0.5` translates to CPU quota settings in cgroups:
```
cpu.cfs_quota_us = 50000
cpu.cfs_period_us = 100000
```
The kernel allows the container to use at most 50ms of CPU time per 100ms period. Unlike memory limits, CPU limits don't kill processes — they just throttle them (processes are descheduled until their quota resets).

---

## Advanced

**Q8: A container keeps restarting in a crash loop. How would you debug it when it exits so fast you can't `docker exec` into it?**

When a container exits in milliseconds, you can't exec into it. Several approaches:

**Approach 1: Override the entrypoint to prevent the crash**
```bash
docker run -it --entrypoint /bin/sh myapp
# Now you're in a shell inside the container, app didn't start
# Investigate the filesystem, run the app manually to see the error
```

**Approach 2: Read the logs**
```bash
# The logs are preserved even after the container exits
docker logs myapp
docker logs --tail 50 myapp
```

**Approach 3: Check the exit code**
```bash
docker inspect --format '{{.State.ExitCode}}' myapp
# 1 = application error, 137 = OOM killed, 127 = command not found, etc.
```

**Approach 4: Check environment**
```bash
# Start a new container from the same image with a shell
docker run --rm -it \
  --env-file .env \                      # same env as the crashing container
  --entrypoint /bin/sh \
  myapp \
  -c "env"                               # print environment and exit
```

**Approach 5: Use --restart-delay to buy time**
```bash
# on-failure with a delay gives you time to exec in before next restart
docker run --restart on-failure myapp
# Quick! After it exits and before it restarts:
docker exec -it myapp sh
```

**Approach 6: Inspect the image's entrypoint**
```bash
docker inspect --format '{{json .Config.Entrypoint}}' myapp
docker inspect --format '{{json .Config.Cmd}}' myapp
# Understand what command is being run, then test it manually
```

---

**Q9: What is the difference between `--memory` and `--memory-swap` in Docker?**

`--memory` sets the hard limit for RAM usage.

`--memory-swap` sets the total combined limit for RAM + swap. The amount of swap available is: `--memory-swap` minus `--memory`.

Examples:

```bash
# Container gets 512 MB RAM and 512 MB swap (1 GB total)
docker run --memory 512m --memory-swap 1g myapp

# Container gets 512 MB RAM and NO swap
# (memory-swap = memory means 0 swap)
docker run --memory 512m --memory-swap 512m myapp

# Container gets 512 MB RAM and unlimited swap (-1 = unlimited)
docker run --memory 512m --memory-swap -1 myapp

# --memory only, no --memory-swap set:
# Default behavior = container gets 2x --memory as swap
docker run --memory 512m myapp    # = 512m RAM + 512m swap
```

For production services, disabling swap (`--memory-swap` equals `--memory`) is recommended. If your service is using swap, it's under memory pressure and will be very slow. Better to OOM-kill and restart it than to limp along with swapping.

---

**Q10: Explain how `docker pause` works internally and when you would use it.**

`docker pause` sends **SIGSTOP** to every process in the container's cgroup. SIGSTOP is a signal that cannot be caught or ignored — it unconditionally freezes the process. The process remains in memory, retaining all its state and open file handles, but no instructions execute.

```bash
docker pause mydb        # freeze
# processes are now completely stopped — no CPU usage, no I/O
docker unpause mydb      # thaw — continues exactly where it stopped
```

Internally, Docker uses the cgroup freezer subsystem (`cgroup.freeze`) on cgroupv2 systems, or sends SIGSTOP to all processes in the cgroup on older systems.

**Use cases:**

1. **Consistent filesystem snapshots:** Pause a database container before taking a filesystem snapshot (not a database dump — an OS-level snapshot). Without pausing, the database might be mid-write when you snapshot, resulting in a corrupt backup.

2. **Resource management:** In development environments with many containers, pause containers that aren't actively needed to free CPU, while keeping them "warm" (no restart delay when you unpause).

3. **Debugging complex race conditions:** Pause one service to isolate behavior of another.

**Important:** Paused containers still hold their memory. Pausing doesn't free RAM — it only stops CPU execution. Don't pause containers to "save memory."

---

**Q11: What is a zombie container, and how can it happen?**

A zombie container is a container stuck in a state where it appears to be running (or at least not cleanly removed) but is no longer functional — its process has exited but its entry persists, or it has somehow gotten into a state where it won't stop or remove cleanly.

The more technically precise term is a **zombie process** inside a container. In Linux, when a process exits, it remains in the process table as a "zombie" (state `Z`) until its parent process calls `wait()` to collect its exit status. In a container, if PID 1 doesn't properly handle `SIGCHLD` or call `wait()` for its child processes, those children become zombies.

This commonly happens when:
- Your app forks child processes (e.g., a shell script that spawns subprocesses) without reaping them
- You use a non-init process as PID 1 that doesn't clean up children

Solutions:
1. Use `--init` flag: `docker run --init myapp` — this adds a tiny init process (tini) as PID 1 that properly reaps zombies
2. Use a proper init system in your image (like `dumb-init` or `tini`)
3. Write your PID 1 process to handle SIGCHLD and call `wait()`

```bash
# Check for zombie processes inside a container
docker top mycontainer aux | grep defunct
# or
docker exec mycontainer ps aux | grep 'Z '
```

---

**Q12: How do graceful shutdowns work with SIGTERM in Docker, and how should an application be written to handle them?**

When you run `docker stop`, Docker sends SIGTERM to PID 1 of the container. The application has the length of the grace period (default 10 seconds, configurable with `--time`) to finish what it's doing and exit cleanly. After the grace period, Docker sends SIGKILL.

A well-behaved application should:
1. **Catch SIGTERM** — register a signal handler
2. **Stop accepting new work** — for a web server, stop accepting new connections
3. **Finish in-flight work** — complete requests already being handled
4. **Clean up resources** — close database connections, flush buffers, write pending data
5. **Exit with code 0** — signal clean shutdown

Example in Python:
```python
import signal
import sys

def handle_sigterm(signum, frame):
    print("SIGTERM received, shutting down...")
    # close DB connections, flush writes, etc.
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_sigterm)
```

**Important:** If your entrypoint is a shell script, SIGTERM is sent to the shell (PID 1), not the actual application process. The shell does not forward signals to its children by default. Always use `exec` in shell scripts to replace the shell with the application:

```bash
#!/bin/sh
# Wrong: shell is PID 1, doesn't forward SIGTERM to myapp
./myapp

# Right: exec replaces the shell — myapp becomes PID 1 and receives SIGTERM directly
exec ./myapp
```

You can verify how your container handles SIGTERM:
```bash
docker run -d --name myapp myapp
docker stop --time 30 myapp   # give it 30 seconds
docker inspect --format '{{.State.ExitCode}}' myapp
# 0 = clean exit (handled SIGTERM)
# 137 = killed (didn't exit within grace period, got SIGKILL)
# 143 = terminated by SIGTERM (process exited when SIGTERM received)
```

---

## 📂 Navigation

**In this folder:**
| File | |
|---|---|
| [📖 Theory.md](./Theory.md) | Full explanation |
| [⚡ Cheatsheet.md](./Cheatsheet.md) | Quick reference |
| 🎯 **Interview_QA.md** | ← you are here |
| [💻 Code_Example.md](./Code_Example.md) | Working code |

⬅️ **Prev:** [Dockerfile](../05_Dockerfile/Interview_QA.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Volumes and Bind Mounts](../07_Volumes_and_Bind_Mounts/Theory.md)
🏠 **[Home](../../README.md)**
