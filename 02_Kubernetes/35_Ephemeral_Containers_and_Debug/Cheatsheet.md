# Module 35 — Ephemeral Containers and Debugging Cheatsheet

## Core kubectl debug Commands

```bash
# Inject ephemeral container into a running pod (basic)
kubectl debug -it POD_NAME --image=busybox --target=CONTAINER_NAME

# Debug with netshoot (full network toolkit)
kubectl debug -it POD_NAME --image=nicolaka/netshoot --target=CONTAINER_NAME

# Debug with ubuntu
kubectl debug -it POD_NAME --image=ubuntu --target=CONTAINER_NAME

# Copy a pod with a replaced image (for pods that crash immediately)
kubectl debug POD_NAME \
  --copy-to=debug-pod \
  --set-image='*=ubuntu' \
  --share-processes \
  -it -- bash

# Copy a pod, replace only one container's image
kubectl debug POD_NAME \
  --copy-to=debug-pod \
  --set-image=mycontainer=ubuntu \
  -it -- bash

# Debug a node (creates privileged pod with host filesystem mounted)
kubectl debug node/NODE_NAME --image=ubuntu -it

# List ephemeral containers in a pod
kubectl get pod POD_NAME -o jsonpath='{.spec.ephemeralContainers}'

# Describe a pod (shows ephemeral containers section)
kubectl describe pod POD_NAME
```

---

## Debug Image Quick Reference

| Image | Size | Best For | Key Tools |
|-------|------|----------|-----------|
| `busybox` | ~1MB | Quick shell, basic filesystem | sh, ls, cat, ps, wget, ping |
| `nicolaka/netshoot` | ~300MB | Network/DNS debugging | curl, dig, tcpdump, nmap, ss, traceroute, iperf3 |
| `ubuntu` | ~75MB | General purpose, apt-get | bash, apt-get for any tool |
| `alpine` | ~7MB | Lightweight with apk | sh, apk package manager |
| `curlimages/curl` | ~12MB | HTTP testing only | curl |

---

## Process Namespace Sharing

```bash
# --target flag shares PID namespace with the named container
kubectl debug -it my-pod --image=busybox --target=app

# Inside ephemeral container: see target's processes
ps aux

# Access target container's filesystem via /proc
ls /proc/1/root/          # target's root filesystem
ls /proc/1/fd/            # target's open file descriptors
cat /proc/1/environ       # target's environment variables (null-separated)
cat /proc/1/maps          # target's memory maps
```

---

## Network Debugging Inside an Ephemeral Container

```bash
# DNS resolution
dig kubernetes.default.svc.cluster.local
nslookup my-service.my-namespace.svc.cluster.local

# HTTP connectivity
curl -v http://my-service.my-namespace.svc.cluster.local:8080/health
curl -k https://my-service:443/api

# TCP port check
nc -zv my-service 8080

# Capture traffic
tcpdump -i eth0 -w /tmp/capture.pcap port 8080
tcpdump -i eth0 -nn 'tcp port 80'

# Show open connections
ss -tulpn
netstat -an

# Traceroute
traceroute my-service.my-namespace.svc.cluster.local
```

---

## Node Debugging

```bash
# Start node debug pod
kubectl debug node/NODE_NAME --image=ubuntu -it

# Inside node debug pod
chroot /host                         # enter node's root filesystem
systemctl status kubelet
journalctl -u kubelet --since "30m ago"
crictl ps                            # list containers via CRI
crictl pods                          # list pods via CRI
crictl logs CONTAINER_ID             # container logs via CRI
df -h                                # disk usage
free -m                              # memory
top                                  # CPU/memory per process
```

---

## Ephemeral Container Constraints

| Can configure | Cannot configure |
|---------------|-----------------|
| image | ports |
| command / args | livenessProbe |
| env / envFrom | readinessProbe |
| volumeMounts | startupProbe |
| securityContext | resources (after creation) |
| stdin / tty | lifecycle hooks |

---

## Useful Patterns

```bash
# Check why a distroless app is failing (OOM, crash)
# 1. Get pod name
kubectl get pods -n production

# 2. Attach ephemeral container
kubectl debug -it my-pod -n production \
  --image=nicolaka/netshoot --target=my-app

# 3. Inside: check memory
cat /proc/1/status | grep -E 'VmRSS|VmPeak|VmSize'

# 4. Check what files are open
ls -la /proc/1/fd

# 5. Check environment
cat /proc/1/environ | tr '\0' '\n'

# Verify service-to-service connectivity
kubectl debug -it my-pod --image=nicolaka/netshoot --target=app
# Inside:
curl http://payment-service.payments.svc.cluster.local:8080/health
dig payment-service.payments.svc.cluster.local
```

---

## Version Notes

| Feature | K8s Version |
|---------|-------------|
| Ephemeral containers (alpha) | 1.16 |
| Ephemeral containers (beta) | 1.23 |
| Ephemeral containers (stable/GA) | 1.25 |
| `kubectl debug` command | 1.18+ |
| Node debugging | 1.20+ |

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Ephemeral Containers Theory](./Theory.md) |
| Interview Q&A | [Ephemeral Containers Interview Q&A](./Interview_QA.md) |
| Code Examples | [Ephemeral Containers Code Examples](./Code_Example.md) |
| Next Module | [36 — ValidatingAdmissionPolicy](../36_ValidatingAdmissionPolicy/Theory.md) |
