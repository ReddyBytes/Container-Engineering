# Module 35 — Ephemeral Containers and Debugging Interview Q&A

---

## Q1: What problem do ephemeral containers solve that `kubectl exec` cannot?

**Answer:**

`kubectl exec` requires the target container to have a shell and the tools you want to run. If the container is **distroless** (no shell, no package manager, minimal OS), `kubectl exec` fails immediately because there is literally nothing to execute.

Ephemeral containers solve this by injecting a **temporary, separately-imaged container** into the running pod. The debug image (e.g., `nicolaka/netshoot`) has all the tools you need. The ephemeral container shares namespaces with the target container, so you can see its processes, network, and filesystem — without needing to modify the production image at all.

Key difference: with `kubectl exec` you run a command *inside* the existing container. With ephemeral containers, you bring your own container image that joins the pod's namespace context.

---

## Q2: What Kubernetes version made ephemeral containers stable (GA)?

**Answer:**

Ephemeral containers reached **GA (stable) in Kubernetes 1.25** (released August 2022). They were:
- Alpha in K8s 1.16
- Beta in K8s 1.23
- GA in K8s 1.25

For practical purposes, any cluster running K8s 1.25+ has ephemeral container support enabled by default with no feature gates required.

---

## Q3: What does the `--target` flag do in `kubectl debug`?

**Answer:**

The `--target` flag specifies which container in the pod to **share the PID namespace with**. Without `--target`, the ephemeral container gets its own isolated PID namespace and cannot see the other containers' processes.

With `--target=app`:
- The ephemeral container can run `ps aux` and see PID 1 as the app process
- You can access the target's filesystem via `/proc/1/root/`
- You can inspect open file descriptors at `/proc/1/fd/`
- You can read environment variables from `/proc/1/environ`

Essentially, `--target` makes the ephemeral container a "neighbor" in the same process tree, enabling deep introspection of the target container.

---

## Q4: How do you debug a pod that crashes immediately before you can attach to it?

**Answer:**

Use the **pod copy** approach:

```bash
kubectl debug POD_NAME \
  --copy-to=debug-pod \
  --set-image='*=ubuntu' \
  --share-processes \
  -it -- bash
```

This creates a new pod (`debug-pod`) that is a copy of the original spec, but with all container images replaced with `ubuntu`. The new pod won't crash immediately because it's running a bash shell instead of the original crashing process.

You can then:
- Inspect the filesystem, environment variables, and mounted secrets
- Manually run the original command to reproduce the crash in an interactive session
- Examine mounted volumes

Note: this is a different pod — it won't have the live process state of the crashing pod. But it will have the same configuration and volumes.

---

## Q5: What namespaces does an ephemeral container share with the target container?

**Answer:**

An ephemeral container shares:

1. **Network namespace**: same IP address, same network interfaces, same ports. `curl localhost:8080` from the ephemeral container hits the app's listening socket.

2. **PID namespace** (when `--target` is specified): the ephemeral container can see all processes in the pod. Without `--target`, PID namespace is not shared.

3. **Volume mounts**: the ephemeral container can mount the same volumes defined in the pod spec.

What is NOT automatically shared:
- **Filesystem/overlay**: each container has its own root filesystem. The target's filesystem is accessible via `/proc/1/root/` but is not the default working directory.
- **IPC namespace**: shared if the pod has `shareProcessNamespace: true` set, otherwise isolated.

---

## Q6: What are the limitations of ephemeral containers compared to regular containers?

**Answer:**

Ephemeral containers cannot have:
- **Ports**: they cannot expose ports or be added to Services
- **Probes**: no liveness, readiness, or startup probes
- **Resource limit changes**: you can set initial resource requests, but they cannot be modified after the container is added
- **Lifecycle hooks**: no preStop or postStart hooks
- **Removal**: once added, ephemeral containers cannot be removed from a pod's spec. The pod must be deleted.
- **Restart**: if an ephemeral container exits, it is not restarted (unlike regular or init containers)

These constraints exist because ephemeral containers are intended as temporary diagnostic tools, not persistent workloads.

---

## Q7: How does `kubectl debug node/NODE_NAME` work, and what can you do with it?

**Answer:**

`kubectl debug node/NODE_NAME --image=ubuntu -it` creates a **privileged pod** on the specified node that has:
- **Host PID namespace**: can see all processes on the node
- **Host network namespace**: full access to the node's network interfaces
- **Node root filesystem mounted at `/host`**: read access to everything on the node's disk

Once inside, you can:

```bash
chroot /host              # Chroot into the node's OS
systemctl status kubelet  # Check kubelet health
journalctl -u kubelet     # Kubelet logs
crictl ps                 # List containers at CRI level (bypasses K8s API)
crictl logs CONTAINER_ID  # Container logs via CRI
```

This is essential for diagnosing:
- Kubelet crashes or certificate issues
- CNI (network plugin) problems
- Node disk pressure or filesystem issues
- kube-proxy behavior

---

## Q8: Why is adding debugging tools to production images considered a security anti-pattern?

**Answer:**

Adding tools like `bash`, `curl`, `wget`, `nc`, `nmap` to production container images creates unnecessary attack surface:

1. **Post-exploitation capability**: if an attacker achieves code execution (e.g., via a deserialization vulnerability), having `curl` or `wget` lets them exfiltrate data, download malware, or communicate with C2 servers. A distroless image severely limits what they can do.

2. **Principle of least privilege**: production containers should have only what they need to run. Debug tools are needed only during debugging.

3. **Larger image size**: tools add megabytes to every image, increasing pull times and storage costs.

4. **Compliance concerns**: security scanners flag unnecessary binaries. CVEs in bundled tools (even unused ones) create compliance findings.

Ephemeral containers eliminate this tradeoff: keep production images lean and distroless, bring tools only when you need them.

---

## Q9: What is the `nicolaka/netshoot` image and when should you use it over `busybox`?

**Answer:**

`nicolaka/netshoot` is a community-maintained debug image that includes a comprehensive network troubleshooting toolkit:

- **DNS tools**: `dig`, `nslookup`, `host`
- **HTTP tools**: `curl`, `wget`, `httpie`
- **Network analysis**: `tcpdump`, `wireshark` (tshark), `nmap`, `iperf3`
- **Connection inspection**: `ss`, `netstat`, `ip`, `ifconfig`
- **Routing**: `traceroute`, `mtr`, `ping`
- **Kubernetes-aware**: includes `kubectl`

**Use `busybox` when**: you just need a quick shell and basic UNIX commands — filesystem inspection, simple `wget` test, checking environment variables. Busybox is ~1MB and starts instantly.

**Use `netshoot` when**: you're diagnosing network problems — DNS resolution failures, service-to-service connectivity, TLS issues, packet capture. Network problems require specific tools that busybox doesn't have.

---

## Q10: Can you use ephemeral containers with pods managed by a Deployment? What happens to the pod after you're done?

**Answer:**

Yes, you can attach an ephemeral container to any running pod regardless of whether it's managed by a Deployment, StatefulSet, DaemonSet, or is standalone.

What happens to the pod afterward:

1. **The ephemeral container stops** when you exit the shell (or it exits for any reason). It does NOT restart.

2. **The pod continues running** — the original containers are completely unaffected by the ephemeral container's lifecycle.

3. **The ephemeral container entry remains in the pod spec** (`kubectl describe pod` will show it under "Ephemeral Containers") but it's in a `Terminated` or `Completed` state.

4. **Pod replacement**: when the Deployment eventually replaces the pod (due to a rolling update or node failure), the new replacement pod will NOT have the ephemeral container. It's gone permanently from that pod lineage.

5. **Cleanup**: to fully clean up, just delete the pod — the Deployment controller will create a fresh one.

---

## Q11: How do you access a distroless container's filesystem from an ephemeral container?

**Answer:**

When using `--target`, the target container's filesystem is accessible through the Linux `/proc` filesystem:

```bash
# Target container's full filesystem
ls /proc/1/root/

# Navigate into it
ls /proc/1/root/app/
ls /proc/1/root/etc/

# Read a config file from the distroless container
cat /proc/1/root/etc/ssl/certs/ca-certificates.crt

# Or copy a file out
cp /proc/1/root/app/config.json /tmp/config.json
```

`/proc/PID/root` is a Linux kernel feature that exposes the root filesystem as seen by a specific process, following that process's mount namespace. Since PID 1 is the distroless app's process, its root is the container's root filesystem.

This works even though the distroless image has no shell — you're reading its filesystem from your own shell in the ephemeral container.

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Ephemeral Containers Theory](./Theory.md) |
| Cheatsheet | [Ephemeral Containers Cheatsheet](./Cheatsheet.md) |
| Code Examples | [Ephemeral Containers Code Examples](./Code_Example.md) |
| Next Module | [36 — ValidatingAdmissionPolicy](../36_ValidatingAdmissionPolicy/Theory.md) |
