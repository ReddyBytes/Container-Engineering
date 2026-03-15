# Container Lifecycle — Cheatsheet

## Container States and Transitions

```
[image] ──docker run──► Running ──docker stop──► Stopped ──docker rm──► [gone]
                            │                        │
                     docker pause              docker start
                            │                        │
                         Paused ──docker unpause──► Running
```

```bash
# Check container state
docker inspect --format '{{.State.Status}}' <container>
# Returns: created | running | paused | exited | dead
```

---

## Core Container Commands

```bash
# === CREATE / RUN ===
docker run IMAGE                          # run in foreground
docker run -d IMAGE                       # detached (background)
docker run -it IMAGE bash                 # interactive with shell
docker run --rm IMAGE                     # remove after exit
docker run --name myname IMAGE            # named container
docker create IMAGE                       # create without starting

# === START / STOP ===
docker start CONTAINER                    # start stopped container
docker stop CONTAINER                     # SIGTERM → SIGKILL (10s)
docker stop --time 30 CONTAINER          # 30s grace period
docker kill CONTAINER                     # immediate SIGKILL
docker kill --signal SIGHUP CONTAINER    # send specific signal
docker restart CONTAINER                  # stop + start

# === PAUSE / RESUME ===
docker pause CONTAINER                    # freeze (SIGSTOP all processes)
docker unpause CONTAINER                  # thaw (SIGCONT)

# === REMOVE ===
docker rm CONTAINER                       # remove stopped container
docker rm -f CONTAINER                    # force remove (running or stopped)
docker container prune                    # remove all stopped containers
docker container prune --filter "until=24h"

# === EXEC / ATTACH ===
docker exec -it CONTAINER bash            # new interactive shell
docker exec -it CONTAINER sh              # if bash unavailable
docker exec CONTAINER command             # run command, non-interactive
docker exec -u root CONTAINER bash        # exec as root
docker exec -w /path CONTAINER bash      # set working dir
docker attach CONTAINER                   # attach to PID 1 (careful!)

# === LOGS ===
docker logs CONTAINER                     # all logs
docker logs -f CONTAINER                  # follow
docker logs --tail 100 CONTAINER         # last 100 lines
docker logs -t CONTAINER                  # with timestamps
docker logs --since 30m CONTAINER        # last 30 minutes
docker logs --since "2024-01-01" CONTAINER

# === INSPECT ===
docker inspect CONTAINER                  # full JSON metadata
docker stats CONTAINER                    # live resource usage
docker stats --no-stream CONTAINER       # one-shot stats
docker top CONTAINER                      # running processes
docker port CONTAINER                     # published ports

# === COPY ===
docker cp CONTAINER:/path /host/path     # container → host
docker cp /host/path CONTAINER:/path     # host → container
```

---

## `docker run` Flags Reference

| Flag | Short | Example | Effect |
|---|---|---|---|
| `--detach` | `-d` | `-d` | Run in background |
| `--interactive` | `-i` | `-i` | Keep stdin open |
| `--tty` | `-t` | `-t` | Allocate pseudo-TTY |
| `--rm` | | `--rm` | Remove on exit |
| `--name` | | `--name web` | Named container |
| `--publish` | `-p` | `-p 8080:80` | Publish port |
| `--publish-all` | `-P` | `-P` | Publish all EXPOSE'd |
| `--env` | `-e` | `-e KEY=val` | Environment variable |
| `--env-file` | | `--env-file .env` | Env file |
| `--volume` | `-v` | `-v vol:/data` | Volume/bind mount |
| `--network` | | `--network net` | Network |
| `--memory` | | `--memory 512m` | Memory limit |
| `--cpus` | | `--cpus 0.5` | CPU limit |
| `--restart` | | `--restart always` | Restart policy |
| `--user` | `-u` | `-u 1001` | Run as user |
| `--workdir` | `-w` | `-w /app` | Working directory |
| `--entrypoint` | | `--entrypoint sh` | Override entrypoint |
| `--hostname` | `-h` | `-h myhostname` | Container hostname |
| `--add-host` | | `--add-host host:ip` | Add /etc/hosts entry |
| `--read-only` | | `--read-only` | Read-only filesystem |
| `--cap-drop` | | `--cap-drop ALL` | Drop capabilities |
| `--privileged` | | `--privileged` | Full privileges (unsafe) |

---

## Restart Policies

| Policy | Restart on crash? | Restart on daemon start? | Respects manual stop? |
|---|---|---|---|
| `no` (default) | No | No | — |
| `always` | Yes | Yes | No |
| `on-failure` | Yes (non-zero exit only) | Yes (if was running) | Yes |
| `on-failure:N` | Yes, up to N times | Yes | Yes |
| `unless-stopped` | Yes | Yes | Yes |

**Best practice for production services:** `--restart unless-stopped`

---

## Inspect Format Strings

```bash
docker inspect --format '{{.State.Status}}' c            # running, exited, etc.
docker inspect --format '{{.State.ExitCode}}' c          # exit code
docker inspect --format '{{.State.Pid}}' c               # host PID
docker inspect --format '{{.State.StartedAt}}' c         # start time
docker inspect --format '{{.State.FinishedAt}}' c        # stop time
docker inspect --format '{{.State.Health.Status}}' c     # healthy/unhealthy
docker inspect --format '{{.NetworkSettings.IPAddress}}' c  # container IP
docker inspect --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' c
docker inspect --format '{{.HostConfig.RestartPolicy.Name}}' c
docker inspect --format '{{.HostConfig.Memory}}' c       # memory limit (bytes)
docker inspect --format '{{json .Mounts}}' c | jq .      # volume mounts
```

---

## Resource Limit Quick Reference

```bash
--memory 256m                    # 256 MB hard limit
--memory 1g                      # 1 GB hard limit
--memory-swap 512m               # total memory+swap limit
--cpus 0.5                       # 50% of one CPU
--cpus 2                         # 2 full CPUs
--cpu-shares 512                 # relative weight (default: 1024)
--pids-limit 100                 # max processes/threads in container
--ulimit nofile=1024:1024        # file descriptor limit (soft:hard)
--device-read-bps /dev/sda:1mb   # disk read rate limit
--device-write-bps /dev/sda:1mb  # disk write rate limit
```

---

## 📂 Navigation

**In this folder:**
| File | |
|---|---|
| [📖 Theory.md](./Theory.md) | Full explanation |
| ⚡ **Cheatsheet.md** | ← you are here |
| [🎯 Interview_QA.md](./Interview_QA.md) | Interview prep |
| [💻 Code_Example.md](./Code_Example.md) | Working code |

⬅️ **Prev:** [Dockerfile](../05_Dockerfile/Interview_QA.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Volumes and Bind Mounts](../07_Volumes_and_Bind_Mounts/Theory.md)
🏠 **[Home](../../README.md)**
