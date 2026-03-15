# Docker Networking — Cheatsheet

## Network Drivers at a Glance

| Driver | Isolation | DNS by name | Multi-host | Use case |
|---|---|---|---|---|
| `bridge` (default) | Container-level | No (default bridge) / Yes (user-defined) | No | Single-host apps |
| `host` | None (shares host namespace) | N/A | No | High performance, tools |
| `none` | Complete | No | No | Secure batch jobs |
| `overlay` | Container-level | Yes (service names) | Yes | Docker Swarm |
| `macvlan` | Container gets own MAC | No | No | Legacy systems, bare LAN access |
| `ipvlan` | Similar to macvlan | No | No | Fewer kernel privileges than macvlan |

---

## Core Network Commands

```bash
# === List / inspect ===
docker network ls                           # list all networks
docker network inspect NETWORK              # full metadata
docker network inspect --format '{{json .Containers}}' NETWORK | jq .

# === Create ===
docker network create mynet                 # user-defined bridge
docker network create --driver bridge mynet # explicit bridge driver
docker network create --driver overlay myswarmnet  # overlay (requires Swarm)
docker network create \
  --subnet 192.168.100.0/24 \
  --gateway 192.168.100.1 \
  --ip-range 192.168.100.128/25 \
  custom-net

# === Connect / disconnect ===
docker network connect NETWORK CONTAINER    # add container to network
docker network disconnect NETWORK CONTAINER # remove container from network

# === Remove ===
docker network rm NETWORK                  # remove (fails if containers attached)
docker network prune                       # remove all unused networks
```

---

## Port Publishing

```bash
# Publish specific port
docker run -p HOST_PORT:CONTAINER_PORT image

# Examples
docker run -p 8080:80 nginx               # host 8080 → container 80
docker run -p 127.0.0.1:8080:80 nginx    # bind to localhost only
docker run -p 80:80 -p 443:443 nginx     # multiple ports
docker run -p 8080:80/tcp nginx          # explicit TCP
docker run -p 53:53/udp dnsserver        # UDP port

# Publish ALL EXPOSE'd ports to random host ports
docker run -P nginx

# See what ports a container has published
docker port CONTAINER
docker inspect --format '{{json .NetworkSettings.Ports}}' CONTAINER | jq .
```

---

## DNS in User-Defined Networks

```bash
# Default bridge — NO DNS
docker run -d --name a nginx
docker run -d --name b alpine ping a       # FAILS: unknown host

# User-defined bridge — DNS works
docker network create mynet
docker run -d --name a --network mynet nginx
docker run -d --name b --network mynet alpine ping a   # WORKS

# Check DNS config inside container
docker exec CONTAINER cat /etc/resolv.conf
# Should show: nameserver 127.0.0.11

# Network aliases
docker run -d --name db --network mynet --network-alias database postgres:16
# Now reachable as both 'db' and 'database'
```

---

## Multi-Network (DMZ Pattern)

```bash
# Create networks
docker network create frontend-net
docker network create backend-net

# DB: internal only
docker run -d --name db --network backend-net postgres:16

# API: bridges both networks
docker run -d --name api --network backend-net myapi
docker network connect frontend-net api

# Frontend: public-facing only
docker run -d --name web --network frontend-net -p 80:80 mywebapp

# Verify isolation
docker exec web ping db     # FAILS: different networks
docker exec web ping api    # WORKS: same frontend-net
docker exec api ping db     # WORKS: same backend-net
```

---

## Troubleshooting

```bash
# Test DNS resolution
docker exec CONTAINER nslookup SERVICE_NAME
docker exec CONTAINER dig SERVICE_NAME

# Test HTTP connectivity
docker exec CONTAINER curl -s http://other-service:8080/health

# Test TCP connectivity
docker exec CONTAINER nc -zv other-service 5432

# Check container's IP on each network
docker inspect --format '{{range .NetworkSettings.Networks}}{{.NetworkID}}: {{.IPAddress}}{{"\n"}}{{end}}' CONTAINER

# Check which network a container is on
docker inspect --format '{{json .NetworkSettings.Networks}}' CONTAINER | jq 'keys'

# See iptables rules Docker created (Linux only)
sudo iptables -t nat -L DOCKER --line-numbers -n
```

---

## Network Driver When to Use Summary

**Use `bridge` (user-defined):** All multi-container apps on a single host. Default choice.

**Use `host`:** Performance-critical apps where the NAT overhead matters. Monitoring tools that need to see all network traffic. Linux only.

**Use `none`:** Jobs with no legitimate network needs. Maximum isolation.

**Use `overlay`:** Docker Swarm multi-host services. Kubernetes uses its own CNI (not overlay).

**Use `macvlan`:** When containers need to appear as physical devices on the LAN (legacy apps that rely on MAC addresses, DHCP assignment from the physical network).

---

## 📂 Navigation

**In this folder:**
| File | |
|---|---|
| [📖 Theory.md](./Theory.md) | Full explanation |
| ⚡ **Cheatsheet.md** | ← you are here |
| [🎯 Interview_QA.md](./Interview_QA.md) | Interview prep |
| [💻 Code_Example.md](./Code_Example.md) | Working code |

⬅️ **Prev:** [07 — Volumes and Bind Mounts](../07_Volumes_and_Bind_Mounts/Cheatsheet.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [09 — Docker Compose](../09_Docker_Compose/Cheatsheet.md)
🏠 **[Home](../../README.md)**
