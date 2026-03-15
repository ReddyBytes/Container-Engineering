# Virtualization and Containers — Cheatsheet

## VM vs Container: At a Glance

| Property | Virtual Machine | Container |
|---|---|---|
| **Isolation unit** | Full OS + kernel | Process + userspace |
| **Boot time** | 1–5 minutes | < 1 second |
| **Image size** | 1–20 GB | 5 MB – 1 GB |
| **Memory overhead** | High (full OS per VM) | Low (shared kernel) |
| **OS flexibility** | Any OS on any host | Must share host kernel type |
| **Density** | Tens per host | Hundreds per host |
| **Portability** | Possible but heavy | Lightweight, fast pull |
| **Persistent storage** | VM disk (persistent) | Ephemeral by default |
| **Security boundary** | Hypervisor | Kernel namespaces + cgroups |
| **Best for** | Legacy apps, full OS isolation, mixed OS | Microservices, CI/CD, cloud-native |
| **Examples** | VMware, VirtualBox, KVM, Hyper-V | Docker, containerd, Podman |

---

## Container Core Concepts Glossary

| Term | Definition |
|---|---|
| **Container** | An isolated process (or process group) running on a host OS, with its own filesystem, network, and PID space |
| **Image** | A read-only, layered filesystem bundle that a container is created from |
| **Container Runtime** | Software that creates and manages containers (runc, containerd, crun) |
| **Namespace** | Linux kernel feature that isolates what a process can *see* (PID, network, filesystem, etc.) |
| **cgroup** | Linux kernel feature that limits what a process can *use* (CPU, memory, I/O) |
| **Host OS** | The operating system running directly on the physical machine |
| **Guest OS** | The OS running inside a VM (does not exist in containers — they share the host kernel) |
| **Hypervisor** | Software that creates and manages VMs (Type 1: bare-metal, Type 2: hosted) |
| **Ephemeral** | Temporary; container filesystem changes are lost when the container is removed |
| **Immutable** | Cannot be changed after creation; container images are immutable |
| **Registry** | A service for storing and distributing container images (Docker Hub, ECR, GCR) |
| **Tag** | A human-readable label on an image version (e.g., `nginx:1.25`, `ubuntu:22.04`) |
| **Digest** | A content-addressed SHA256 hash uniquely identifying an image layer or manifest |

---

## Linux Namespaces Reference

| Namespace | Isolates | Example effect |
|---|---|---|
| `pid` | Process IDs | Container's first process is PID 1; host PIDs hidden |
| `net` | Network interfaces, routes, firewall | Container gets its own `eth0` |
| `mnt` | Filesystem mounts | Container sees only its own filesystem tree |
| `uts` | Hostname, domain name | Container can have hostname `myapp`, host stays `myserver` |
| `ipc` | IPC: message queues, semaphores | Containers can't IPC across boundaries |
| `user` | UIDs/GIDs | Container root (UID 0) maps to unprivileged host UID |
| `cgroup` | cgroup hierarchy view | Container can't see host cgroup tree |
| `time` | System clock offsets | Experimental; per-container clock adjustment |

---

## OCI, containerd, runc Relationship

```
Docker CLI  →  dockerd  →  containerd  →  runc  →  Linux kernel
     │              │             │           │
     │              │             │           └── Creates actual process
     │              │             │               using namespaces + cgroups
     │              │             └── Manages lifecycle, images, snapshots
     │              └── Docker API, networking, volumes, build
     └── User-facing commands: run, build, pull, push
```

| Component | What it is | Who maintains it |
|---|---|---|
| **OCI Image Spec** | Standard for container image format | OCI (Linux Foundation) |
| **OCI Runtime Spec** | Standard for how to launch a container | OCI (Linux Foundation) |
| **runc** | Reference OCI runtime; does the actual `clone()` syscall | OCI / Docker donated |
| **containerd** | High-level runtime; pulls images, manages snapshots, calls runc | CNCF |
| **dockerd** | Full Docker engine; build, network, volumes, REST API | Docker Inc. |
| **Podman** | Daemonless Docker alternative, OCI-compliant | Red Hat |
| **crun** | Faster OCI runtime written in C (alternative to runc) | Red Hat |

---

## When to Use VMs vs Containers

**Choose VMs when:**
- You need to run a different OS kernel (e.g., Windows containers on Linux host, or vice versa)
- Strong kernel-level isolation is a hard security requirement (PCI-DSS, untrusted workloads)
- The application requires direct hardware access (GPU pass-through, specific drivers)
- You're running legacy monolithic applications not worth containerizing

**Choose Containers when:**
- You want fast deployments and iteration cycles
- You're building microservices or cloud-native applications
- You need high density (many apps per host)
- CI/CD pipelines need reproducible, fast build environments
- You want dev/staging/prod environment parity

**Use both when:**
- You want the security boundary of VMs *and* the density/speed of containers
- This is exactly how AWS ECS on EC2, GKE, and most Kubernetes platforms work — containers run inside VMs

---

## 📂 Navigation

**In this folder:**
| File | |
|---|---|
| [📖 Theory.md](./Theory.md) | Full explanation |
| ⚡ **Cheatsheet.md** | ← you are here |
| [🎯 Interview_QA.md](./Interview_QA.md) | Interview prep |

➡️ **Next:** [02 — Docker Architecture](../02_Docker_Architecture/Cheatsheet.md)
🏠 **[Home](../../README.md)**
