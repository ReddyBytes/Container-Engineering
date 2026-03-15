# Docker Networking — Interview Q&A

## Beginner

**Q1: What is the default network mode in Docker, and what does it mean?**

When you run a container without specifying a network, it attaches to the **default bridge network** named `bridge`. In this mode, Docker creates a virtual bridge interface (`docker0`) on the host. Each container gets a virtual ethernet interface pair — one end inside the container's network namespace, one end attached to the bridge.

Containers on the default bridge can communicate with each other by IP, but NOT by name — there's no automatic DNS. They also have outbound internet access via NAT (iptables masquerading). Their ports are NOT accessible from outside the host unless published with `-p`.

For real multi-container applications, the default bridge is insufficient. Use user-defined bridge networks for automatic DNS and better isolation.

---

**Q2: Why do containers on the default bridge network fail to communicate by name?**

The default `bridge` network does not run Docker's embedded DNS server. When a container on the default bridge tries to resolve `db` (another container's name), there's no DNS service to answer that query — the system falls through to the host's resolvers, which don't know about Docker containers.

Docker's embedded DNS (`127.0.0.11`) only activates on user-defined networks. Create a network with `docker network create mynet` and add containers to it — then container names resolve automatically.

```bash
# This fails (default bridge):
docker run -d --name db postgres:16
docker run -it --rm ubuntu ping db    # "ping: db: Name or service not known"

# This works (user-defined):
docker network create mynet
docker run -d --name db --network mynet postgres:16
docker run -it --rm --network mynet ubuntu ping db    # works
```

---

**Q3: How does port publishing work? What happens when you run `docker run -p 8080:80 nginx`?**

When you use `-p 8080:80`, Docker sets up an iptables NAT rule on the host. Any traffic arriving at host port 8080 is redirected (NAT'd) to the container's internal IP at port 80.

The container itself is still bound to port 80 on its virtual network interface. The iptables rule is the translation layer between the host port and the container port.

You can see the rule:
```bash
sudo iptables -t nat -L DOCKER -n --line-numbers
# You'll see a rule forwarding 0.0.0.0:8080 to <container-ip>:80
```

This means:
- `localhost:8080` on the host → container port 80
- The container still sees requests arriving at port 80 (it doesn't know about 8080)
- The container IP is assigned by Docker and not directly reachable from outside the host

---

**Q4: What is the difference between `--network host` and the default bridge?**

With the default bridge, the container has its own isolated network namespace — its own virtual network interface, its own IP address, its own routing table. Traffic between the container and the outside world goes through a bridge and NAT.

With `--network host`, the container has NO network namespace isolation — it shares the host's network namespace directly. The container sees the same network interfaces as the host. If the container runs nginx on port 80, it binds to port 80 on the host's real network interface — no port mapping needed.

Trade-off: `host` has better performance (no NAT, no bridge) but no isolation. A container running as root on the host network can bind privileged ports, interfere with host network services, and is more dangerous if compromised.

---

## Intermediate

**Q5: How does Docker's embedded DNS work? What is `127.0.0.11`?**

When you attach a container to a user-defined network, Docker automatically configures the container's `/etc/resolv.conf` to point to `127.0.0.11` as the DNS resolver:

```
nameserver 127.0.0.11
options ndots:0
```

`127.0.0.11` is a special virtual IP managed by Docker inside the container's network namespace. It runs a lightweight DNS resolver (handled by the Docker daemon via `dockerd`'s internal DNS machinery).

When the container queries `db`, the request goes to `127.0.0.11`, which looks up which containers on the same network have the name `db`, and returns their IP address. The lookup is real-time — if a container's IP changes (e.g., it restarts), the DNS answer reflects the new IP.

This is also why you can use service names in `docker-compose.yaml` to connect containers — Compose puts all services on a user-defined network, so DNS just works.

---

**Q6: A two-container application (web + database) was working, but after restarting the database container, the web container can't connect. It seems to be using an old IP. What's happening and how do you fix it?**

The web container is likely hard-coded to use the database's IP address instead of its container name. When the database container restarted, Docker assigned it a new IP (IPs are not guaranteed to be stable — they're assigned from the bridge network's subnet).

**Diagnosis:**
```bash
# Get new IP of db container
docker inspect --format '{{.NetworkSettings.IPAddress}}' db

# Compare with what the web container is configured to use
docker exec web env | grep DATABASE
docker exec web cat /etc/myapp/config
```

**Fix:**
Always configure services to connect via container name (or Compose service name), not IP:

```bash
# WRONG (hardcoded IP — breaks on restart)
DATABASE_URL=postgresql://5.5.5.172:5432/mydb

# CORRECT (container name — Docker DNS resolves it)
DATABASE_URL=postgresql://db:5432/mydb
```

For this to work, both containers must be on the same user-defined network. Docker's embedded DNS ensures that `db` always resolves to the current IP of the `db` container, regardless of restarts.

---

**Q7: What are network aliases and when are they useful?**

A network alias is an additional name by which a container can be reached within a network, separate from its container name.

```bash
docker run -d \
  --name my-postgres-container-v2 \
  --network mynet \
  --network-alias database \
  postgres:16
```

Now other containers on `mynet` can reach this container as either `my-postgres-container-v2` OR `database`. If you later upgrade to v3 and give the new container the same `--network-alias database`, all other containers automatically start talking to the new container — no reconfiguration needed.

This is also how Docker Swarm implements service-level load balancing: multiple replicas of a service all share the same network alias (the service name). When you query the service name DNS, Docker round-robins across all healthy replicas.

---

## Advanced

**Q8: How does Docker networking work under the hood on Linux? What kernel features are involved?**

Docker networking is built on several Linux kernel features:

1. **Network namespaces:** Each container gets its own `net` namespace with its own set of virtual interfaces, routing table, iptables rules, and socket table. This is what makes containers believe they have their own network stack.

2. **veth pairs (virtual Ethernet pairs):** When a container attaches to a bridge network, Docker creates a veth pair — two virtual interfaces linked together so that traffic in one end comes out the other. One end goes inside the container namespace (appears as `eth0`), the other attaches to the bridge on the host.

3. **Linux bridge:** The Docker bridge network creates a software bridge (`docker0` or `br-xxxxxxxx`). All the veth host-ends attach to this bridge. The bridge forwards traffic between attached interfaces — like a software switch.

4. **iptables (NAT + filtering):**
   - MASQUERADE rule: traffic from containers going outbound is NAT'd to appear as coming from the host IP
   - DNAT rule: traffic arriving at a published host port is redirected to the container IP
   - FORWARD chain rules: control which containers can reach each other

5. **DNS (127.0.0.11):** Docker inserts iptables rules to intercept DNS queries to `127.0.0.11` and route them to an internal DNS proxy managed by the Docker daemon.

---

**Q9: You have a three-tier application: frontend (public), API (internal), database (private). Design the Docker network topology to isolate each tier appropriately.**

Correct design uses three separate networks with the API container bridging two of them:

```bash
# Create networks
docker network create frontend-net    # public traffic
docker network create backend-net     # internal services only

# Database: ONLY on backend-net — cannot be reached from frontend
docker run -d \
  --name db \
  --network backend-net \
  -e POSTGRES_PASSWORD=secret \
  postgres:16

# API: connected to BOTH networks — mediates between tiers
docker run -d \
  --name api \
  --network backend-net \
  myapi

docker network connect frontend-net api

# Frontend: ONLY on frontend-net — published to internet
docker run -d \
  --name frontend \
  --network frontend-net \
  -p 80:80 -p 443:443 \
  myfrontend

# Verify isolation:
# frontend → api: ALLOWED (same frontend-net)
# api → db: ALLOWED (same backend-net)
# frontend → db: BLOCKED (different networks, no direct path)
```

This mirrors the classic DMZ architecture: the API container is the only component that can talk to both tiers. A compromised frontend container cannot directly reach the database.

---

**Q10: How does overlay networking work in Docker Swarm? What protocol does it use?**

Overlay networks in Docker Swarm allow containers on different hosts to communicate as if on the same local network. The technology:

**VXLAN (Virtual Extensible LAN):**
- Container A on Host 1 sends a packet to Container B on Host 2
- The packet has destination IP = Container B's overlay IP (e.g., `10.0.0.3`)
- The Docker overlay driver encapsulates this packet in a VXLAN UDP packet (UDP port 4789)
- The outer packet's destination is Host 2's real IP
- The packet traverses the physical network between Host 1 and Host 2
- Host 2's overlay driver decapsulates the VXLAN packet
- Container B receives the original packet as if it came from the local network

**Swarm overlay specifics:**
- The overlay network uses a distributed key-value store (built into Swarm) to track which container is on which host
- Docker uses **IPVS** (IP Virtual Server) for service-level load balancing within overlay networks — DNS for the service name returns a virtual IP, and IPVS round-robins to the actual container IPs
- Control plane traffic is encrypted with TLS by default
- Data plane traffic can optionally be encrypted with AES-GCM (`docker network create --opt encrypted overlay mynet`)

Required open ports for Swarm overlay:
- TCP/UDP 2377 (Swarm cluster management)
- TCP/UDP 7946 (container network discovery)
- UDP 4789 (VXLAN data plane)

---

## 📂 Navigation

**In this folder:**
| File | |
|---|---|
| [📖 Theory.md](./Theory.md) | Full explanation |
| [⚡ Cheatsheet.md](./Cheatsheet.md) | Quick reference |
| 🎯 **Interview_QA.md** | ← you are here |
| [💻 Code_Example.md](./Code_Example.md) | Working code |

⬅️ **Prev:** [07 — Volumes and Bind Mounts](../07_Volumes_and_Bind_Mounts/Interview_QA.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [09 — Docker Compose](../09_Docker_Compose/Interview_QA.md)
🏠 **[Home](../../README.md)**
