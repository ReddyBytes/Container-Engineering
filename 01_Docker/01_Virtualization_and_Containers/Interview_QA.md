# Virtualization and Containers — Interview Q&A

## Beginner

**Q1: What is the main difference between a VM and a container?**

A VM virtualizes an entire computer — it includes its own OS kernel, system libraries, and applications. Each VM needs a hypervisor to translate between its virtual hardware and the real hardware beneath it.

A container is just a process (or a group of processes) running on the host OS, isolated using Linux kernel features (namespaces and cgroups). Containers share the host's kernel — they don't have one of their own. This makes containers much lighter, faster to start, and more resource-efficient than VMs.

The analogy: a VM is like renting an entire apartment (your own utilities, your own structure). A container is like renting a room in a shared house (shared structure, shared utilities, but your own locked space).

---

**Q2: What does "ephemeral" mean in the context of containers, and why does it matter?**

Ephemeral means temporary — lasting only as long as the container is running. When a container is stopped and removed, any data written to its internal filesystem is gone.

This matters because developers coming from a VM background often treat containers like persistent servers. If your application writes log files, uploaded images, or database records directly into the container filesystem, you will lose that data the moment the container is replaced. Persistent data must be stored in **volumes** (external storage that survives container removal).

---

**Q3: What is Docker Hub?**

Docker Hub is a public registry — a cloud-hosted service where container images are stored and shared. When you run `docker pull nginx`, Docker downloads the `nginx` image from Docker Hub. You can also push your own images there (publicly or privately). It's analogous to what GitHub is for source code, but for container images.

---

**Q4: Can you run a Windows application in a container on a Linux host?**

Not directly. Containers share the host OS kernel. A Windows application needs the Windows kernel's system calls, which a Linux kernel cannot provide. To run Windows containers, you need a Windows host (or a Windows VM on a Linux host). This is one area where VMs are still necessary.

---

**Q5: What is the OCI, and why does it exist?**

OCI stands for Open Container Initiative. It's a standards body under the Linux Foundation that defines open specifications for container image formats and container runtimes.

It exists because when Docker became dominant, the industry was concerned about vendor lock-in. OCI ensures that any OCI-compliant tool can build images that any OCI-compliant runtime can run. For example, you can build an image with Buildah and run it with containerd — because both follow the OCI spec.

---

## Intermediate

**Q6: Explain Linux namespaces and cgroups. How do they work together to create container isolation?**

**Namespaces** control visibility — what a process can *see*. Each namespace type isolates a different resource:
- `pid` namespace: the container's processes have their own PID numbering (its init process is PID 1, even if the host calls it PID 4782)
- `net` namespace: the container has its own network stack (interfaces, routes, iptables rules)
- `mnt` namespace: the container has its own view of the filesystem hierarchy
- `uts` namespace: the container has its own hostname
- `user` namespace: UIDs/GIDs are remapped (container root ≠ host root)

**cgroups** control resource consumption — what a process can *use*:
- Limit CPU time (e.g., "this container may use at most 50% of one core")
- Limit memory (e.g., "kill this container if it exceeds 512 MB")
- Throttle disk and network I/O

Together: namespaces make a container *think* it's alone on a machine; cgroups prevent one container from starving others of resources.

---

**Q7: What is the difference between runc, containerd, and dockerd?**

They form a layered stack, each building on the one below:

- **runc** is the lowest-level OCI runtime. Given a filesystem bundle and a runtime config, it makes the actual Linux syscalls (`clone()`, `unshare()`, etc.) to create the isolated process. It does nothing else — no image pulling, no networking.

- **containerd** is a higher-level runtime that manages the container lifecycle. It pulls images, manages layered snapshots (the container filesystem), sets up networking via plugins (CNI), and calls runc to actually create containers. It exposes a gRPC API. Kubernetes uses containerd directly.

- **dockerd** is the full Docker engine. It provides the Docker REST API, handles `docker build`, manages Docker networking and volumes, and delegates container operations to containerd. It's what the `docker` CLI talks to.

---

**Q8: Why might you use containers inside VMs in a production cloud environment?**

Because you want the benefits of both:

- **VMs** provide a strong security boundary at the kernel level. If one tenant's container exploits a kernel vulnerability, the blast radius is limited to that VM — not the entire physical host. This is why AWS ECS, GKE, and EKS all run containers inside VMs.

- **Containers** provide density and speed within a VM. Instead of running one app per VM, you can run dozens of containers on a single VM, sharing its OS kernel, and deploy/scale them in seconds.

The common pattern: each VM (called a "node" in Kubernetes) runs a container runtime, which runs many containers. The VM is the security boundary; the container is the deployment unit.

---

**Q9: What is a Type 1 vs Type 2 hypervisor? Give examples of each.**

A **Type 1 (bare-metal) hypervisor** runs directly on the physical hardware, with no host OS underneath. It manages hardware resources directly and creates guest VMs on top. Examples: VMware ESXi, Microsoft Hyper-V (server), KVM (Linux Kernel-based VM — technically integrated into the kernel), Xen. Used in data centers and cloud providers.

A **Type 2 (hosted) hypervisor** runs as an application on top of a host OS. It relies on the host OS to handle hardware access. Examples: VirtualBox, VMware Workstation, Parallels Desktop. Used on developer workstations.

Type 1 hypervisors have lower overhead and better performance because they don't have to go through a host OS. Type 2 is easier to set up on a laptop.

---

## Advanced

**Q10: A security team says your containerized application is not secure enough because containers share the host kernel. What options do you have to address this concern without switching to full VMs?**

Several technologies exist that provide stronger isolation while keeping container workflows:

1. **gVisor (Google):** Implements a user-space kernel (called the "Sentry") that intercepts container syscalls before they reach the host kernel. The container's syscalls never directly touch the host kernel. Used in Google Cloud Run. Adds some latency but dramatically reduces kernel attack surface.

2. **Kata Containers:** Each container (or pod) runs in its own lightweight VM with its own minimal kernel. From the outside, it looks and behaves like a container (OCI-compatible). Provides VM-level kernel isolation with near-container startup speed.

3. **Firecracker (AWS):** Micro-VMs used in AWS Lambda and Fargate. Very lightweight VMs (128 MB overhead, 125 ms startup) that give full kernel isolation. Lambda functions run in Firecracker VMs.

4. **User namespaces + seccomp + AppArmor/SELinux:** Harden standard containers without alternative runtimes. User namespaces prevent container root from being host root. seccomp profiles whitelist allowed syscalls, blocking most kernel attack surface. AppArmor/SELinux add mandatory access control.

The right answer depends on the threat model: for multi-tenant untrusted code, Kata or gVisor; for typical enterprise workloads, hardened standard containers with seccomp and user namespaces.

---

**Q11: Explain what happens at the Linux kernel level when `docker run ubuntu` is executed.**

At a high level:

1. `docker` CLI sends a `POST /containers/create` request to dockerd via the Docker socket.
2. dockerd checks if the `ubuntu` image is available locally. If not, it instructs containerd to pull it from the registry.
3. containerd unpacks the image layers into an OverlayFS snapshot.
4. dockerd instructs containerd to create and start the container.
5. containerd prepares an OCI bundle (the rootfs + `config.json` describing namespaces, cgroups, capabilities, etc.) and calls runc.
6. runc calls `clone()` with the relevant namespace flags (`CLONE_NEWPID`, `CLONE_NEWNET`, `CLONE_NEWNS`, `CLONE_NEWUTS`, `CLONE_NEWIPC`). This creates a new process in new namespaces.
7. runc applies cgroup limits by writing to the cgroup filesystem (`/sys/fs/cgroup/...`).
8. runc performs the `pivot_root()` syscall to change the process's root filesystem to the container's rootfs.
9. runc `exec()`s the container's entry point process (e.g., `/bin/bash`).
10. The resulting process is the container. runc exits; containerd monitors the container process.

---

**Q12: When would you NOT use containers?**

Containers are not always the right tool:

- **Applications requiring a different OS kernel:** Windows apps on Linux hosts (or vice versa). Containers can't bridge kernel architectures.
- **Stateful legacy monoliths:** Applications tightly coupled to a specific server configuration, local filesystem paths, or that use OS-level services (systemd, cron daemons) in complex ways may be more trouble than they're worth to containerize.
- **Bare-metal performance requirements:** HPC workloads, real-time systems, or anything needing direct hardware access (e.g., custom NIC drivers, GPU compute with complex driver needs) may perform better on bare metal.
- **Strong isolation requirements with untrusted code:** Standard containers share the host kernel. For running arbitrary untrusted code (e.g., customer-submitted code), VMs or sandboxed runtimes like gVisor are safer.
- **Very simple, infrequently deployed scripts:** The operational overhead of containerizing a shell script that runs once a month may not be worth it.
- **Regulatory environments with strict change-control:** Some auditors are unfamiliar with containers and require additional compliance documentation, slowing adoption.

---

## 📂 Navigation

**In this folder:**
| File | |
|---|---|
| [📖 Theory.md](./Theory.md) | Full explanation |
| [⚡ Cheatsheet.md](./Cheatsheet.md) | Quick reference |
| 🎯 **Interview_QA.md** | ← you are here |

➡️ **Next:** [02 — Docker Architecture](../02_Docker_Architecture/Interview_QA.md)
🏠 **[Home](../../README.md)**
