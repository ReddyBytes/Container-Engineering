# Docker Networking

## The Problem: How Do Containers Talk?

Picture a busy office building. Inside, different departments need to communicate — finance talks to HR, HR talks to IT. But some communications should be isolated: the executive suite shouldn't be directly reachable by random visitors, the server room is only accessible to IT staff. The building has an internal phone network and an external line, with receptionists and security controlling what goes where.

Docker containers face the same challenge. A web application container needs to talk to its database container. A frontend container needs to reach a backend API. But the database shouldn't be reachable from the internet. A container might need to reach external APIs. All of this needs to work reliably, predictably, and securely.

Docker's networking model handles all of this through **network drivers** — different strategies for how containers connect to each other and to the outside world.

---

## Network Drivers Overview

| Driver | Use Case | Container-to-container DNS? | Multi-host? |
|---|---|---|---|
| **bridge** (default) | Single-host container communication | Only on user-defined bridges | No |
| **host** | Maximum performance, no isolation | N/A (shares host network) | N/A |
| **none** | Complete network isolation | No | No |
| **overlay** | Multi-host container communication (Swarm) | Yes | Yes |
| **macvlan** | Container needs its own MAC/IP on the LAN | No DNS | No (same LAN) |
| **ipvlan** | Similar to macvlan, fewer kernel privileges | No DNS | No |

---

## The Default Bridge Network and Its Problem

When you install Docker, it creates a default network called `bridge`. If you run a container without specifying a network, it attaches to this default bridge:

```bash
docker run -d nginx      # attached to 'bridge' by default
docker network inspect bridge   # see the containers attached
```

The default bridge network has a critical limitation: **it has no automatic DNS**. Containers can communicate by IP address, but not by name.

```bash
# These two containers are on the default bridge
docker run -d --name web nginx
docker run -d --name db postgres:16 -e POSTGRES_PASSWORD=pass

# Try to ping by name from web container — FAILS
docker exec web ping db
# ping: db: Name or service not known

# Ping by IP — works (but fragile: IPs change)
DB_IP=$(docker inspect --format '{{.NetworkSettings.IPAddress}}' db)
docker exec web ping $DB_IP   # works
```

Hardcoding IPs is fragile — Docker assigns IPs dynamically. This makes the default bridge network unsuitable for anything beyond the simplest experiments.

---

## User-Defined Bridge Networks: The Right Way

When you create a **user-defined bridge network**, Docker automatically provides DNS resolution. Containers on the same user-defined network can resolve each other by container name (and by any `--network-alias` you assign).

```bash
# Create a custom bridge network
docker network create my-app-network

# Run containers on the custom network
docker run -d --name web --network my-app-network nginx
docker run -d --name db  --network my-app-network postgres:16 -e POSTGRES_PASSWORD=pass

# Now DNS works! Containers can reach each other by name
docker exec web ping db      # works: 'db' resolves to db container's IP
docker exec db ping web      # works: 'web' resolves to web container's IP
```

This is the correct way to connect containers on the same host. Docker runs an embedded DNS server (`127.0.0.11`) inside each container's namespace, which resolves container names on the same network.

---

## Network Architecture Diagrams

### Container-to-Container (User-Defined Bridge)

```mermaid
graph TD
    subgraph Host["Docker Host"]
        subgraph AppNet["Docker Network: app-network (bridge)"]
            WEB["web container\n172.20.0.2"]
            DB["db container\n172.20.0.3"]
            API["api container\n172.20.0.4"]
            DNS["Embedded DNS\n127.0.0.11"]
            BR["Bridge interface\ndocker0 / br-xxxx"]
        end
        IPTABLES["iptables / NAT"]
    end
    INTERNET["Internet / External network"]

    WEB -->|"db:5432 → DNS resolves\nto 172.20.0.3"| DNS
    DNS -->|"routes to"| DB
    WEB -->|"→ BR → NAT"| INTERNET
    API -->|"→ BR → NAT"| INTERNET
    INTERNET -->|"published port: -p 8080:80"| WEB

    style AppNet fill:#e8f4f8,stroke:#4a90d9
```

### Container-to-Host Network

```mermaid
graph LR
    subgraph Host["Docker Host (host network)"]
        APP["Container with --network host\nshares host's network namespace\nNo isolation!"]
        HS["Host Services\n(e.g., already-running nginx)"]
    end
    INTERNET["Internet"]

    APP <-->|"same interfaces as host"| INTERNET
    APP <-->|"same localhost"| HS

    style APP fill:#ffe0e0
```

---

## Port Publishing

By default, container ports are not accessible from outside the host. To make them accessible, you **publish** (map) them:

```bash
# Publish container port 80 to host port 8080
# Now: curl http://localhost:8080 → container port 80
docker run -p 8080:80 nginx

# Publish to a specific host IP (restrict to loopback only)
docker run -p 127.0.0.1:8080:80 nginx

# Publish UDP port
docker run -p 5353:53/udp dns-server

# Publish all EXPOSE'd ports to random host ports
docker run -P nginx
docker port <container-id>    # see which host ports were assigned

# Publish multiple ports
docker run -p 80:80 -p 443:443 nginx
```

Internally, Docker uses **iptables** rules (or nftables on newer systems) to NAT the traffic from the host port to the container's IP and port.

---

## The `host` Network Driver

With `--network host`, the container shares the host's network namespace entirely. There are no virtual interfaces, no bridge, no NAT — the container binds directly to the host's network interfaces.

```bash
docker run --network host nginx
# nginx listens on the host's port 80 directly — no -p needed
# curl http://localhost:80 works from the host
```

Benefits:
- Maximum network performance (no bridge overhead, no NAT)
- Useful for monitoring/networking tools that need to see all host network traffic

Drawbacks:
- No network isolation at all — the container can bind any port on the host
- Port conflicts are possible (if the host already uses port 80)
- Only works on Linux (Docker Desktop on macOS/Windows runs containers in a VM, `--network host` connects to the VM's network, not your Mac/Windows machine's network)

---

## The `none` Network Driver

`--network none` gives the container a network namespace with only a loopback interface (`lo`). No external connectivity whatsoever.

```bash
docker run --network none ubuntu ping google.com
# ping: connect: Network is unreachable
```

Use cases:
- Security-sensitive batch jobs that should have no network access
- Testing network-isolated components
- Containers that communicate only via shared volumes or IPC

---

## Container DNS on Named Networks

Docker's embedded DNS server (`127.0.0.11`) is automatically configured inside each container that's on a user-defined network. It provides:

1. **Name resolution by container name:** `ping db` → resolves to the `db` container's IP
2. **Name resolution by network alias:** `docker run --network-alias myalias ...` → other containers can reach it by `myalias`
3. **Service discovery in Compose:** services can reach each other by their service name

```bash
docker network create demo-net

docker run -d --name postgres-server --network demo-net \
  -e POSTGRES_PASSWORD=pass postgres:16

docker run -d --name myapp --network demo-net \
  -e DATABASE_URL=postgresql://postgres:pass@postgres-server:5432/postgres \
  myapp

# 'postgres-server' is resolved by Docker DNS inside myapp container
```

---

## Overlay Networks (Multi-Host)

Overlay networks allow containers on different Docker hosts to communicate as if they were on the same local network. Used with Docker Swarm (and in a different form, by Kubernetes).

Overlay networks use **VXLAN** tunneling — they encapsulate container-to-container traffic in UDP packets, allowing it to travel over any IP network between hosts.

```bash
# Initialize Docker Swarm (required for overlay networks)
docker swarm init

# Create an overlay network
docker network create --driver overlay my-overlay

# Services on any Swarm node can join this network
docker service create --name web --network my-overlay nginx
docker service create --name db --network my-overlay postgres:16

# 'web' containers can reach 'db' by name, even on different physical hosts
```

Overlay networks also provide **service-level DNS** in Swarm — all replicas of a service share one DNS name, and Docker load-balances traffic across them.

---

## Connecting a Container to Multiple Networks

A container can be connected to multiple networks. This is how you create a DMZ pattern — a frontend container on a public-facing network and an internal network, while the database is only on the internal network:

```bash
docker network create public-net
docker network create private-net

# Database: only on private-net (not reachable from public-net)
docker run -d --name db --network private-net \
  -e POSTGRES_PASSWORD=pass postgres:16

# API: connected to both networks (bridges public and private)
docker run -d --name api --network private-net myapi

# Connect api to public-net too (after creation)
docker network connect public-net api

# Frontend: only on public-net (can reach api, can't reach db)
docker run -d --name frontend --network public-net \
  -p 80:80 myfrontend

# frontend → api: works (both on public-net)
# api → db: works (both on private-net)
# frontend → db: BLOCKED (different networks)
```

---

## Network Troubleshooting

```bash
# Inspect a network
docker network inspect my-app-network

# List all networks
docker network ls

# See which containers are on a network
docker network inspect --format '{{json .Containers}}' my-app-network | jq .

# Test DNS resolution inside a container
docker exec myapp nslookup db
docker exec myapp cat /etc/resolv.conf    # should show 127.0.0.11

# Test connectivity between containers
docker exec web curl -s http://api:8080/health
docker exec web ping -c 3 db

# Check published ports
docker port myapp
docker inspect --format '{{json .NetworkSettings.Ports}}' myapp | jq .

# Check all IPs assigned to a container
docker inspect --format '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}' myapp
```

---

## Summary

- Docker has multiple network drivers: bridge (default), host, none, overlay, macvlan.
- The **default bridge** has no DNS. Never use it for multi-container apps.
- **User-defined bridge networks** have automatic DNS — containers find each other by name.
- Port publishing with `-p` exposes container ports to the host via iptables NAT.
- `--network host` gives maximum performance but no isolation. Linux only.
- Overlay networks let containers across multiple hosts communicate (Swarm/Kubernetes).
- Connect a container to multiple networks to implement network segmentation.
- Always test connectivity with `docker exec <container> ping <other-container>`.

---

## 📂 Navigation

**In this folder:**
| File | |
|---|---|
| 📖 **Theory.md** | ← you are here |
| [⚡ Cheatsheet.md](./Cheatsheet.md) | Quick reference |
| [🎯 Interview_QA.md](./Interview_QA.md) | Interview prep |
| [💻 Code_Example.md](./Code_Example.md) | Working code |

⬅️ **Prev:** [07 — Volumes and Bind Mounts](../07_Volumes_and_Bind_Mounts/Theory.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [09 — Docker Compose](../09_Docker_Compose/Theory.md)
🏠 **[Home](../../README.md)**
