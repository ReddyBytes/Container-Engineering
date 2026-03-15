# Module 35 — Ephemeral Containers and Debugging Code Examples

## Example 1: Debug a Distroless Pod with an Ephemeral Container

First, create a distroless pod to simulate the scenario:

```yaml
# distroless-app.yaml
# A pod using a distroless image — no shell, no tools
apiVersion: v1
kind: Pod
metadata:
  name: distroless-app
  labels:
    app: distroless-app
spec:
  containers:
  - name: app
    image: gcr.io/distroless/static-debian12   # no shell, no package manager
    command: ["/pause"]                          # placeholder command
    resources:
      requests:
        memory: "32Mi"
        cpu: "50m"
      limits:
        memory: "64Mi"
        cpu: "100m"
```

```bash
# Apply the pod
kubectl apply -f distroless-app.yaml

# Wait for it to be running
kubectl wait --for=condition=Ready pod/distroless-app --timeout=60s

# Try kubectl exec (this WILL FAIL on distroless)
kubectl exec -it distroless-app -- /bin/sh
# Error: exec: "/bin/sh": stat /bin/sh: no such file or directory

# Use an ephemeral container instead
kubectl debug -it distroless-app \
  --image=busybox \
  --target=app
# Now you have a shell! The ephemeral container can see the pod

# Inside the ephemeral container:
ps aux              # see the app's processes (PID 1 is the distroless process)
ls /proc/1/root/    # browse the distroless container's filesystem
cat /proc/1/environ | tr '\0' '\n'  # read its environment variables
ls /proc/1/fd/      # see open file descriptors

# Exit
exit

# Verify the ephemeral container is recorded in the pod spec
kubectl describe pod distroless-app | grep -A 10 "Ephemeral Containers"
```

---

## Example 2: Network Debugging with nicolaka/netshoot

```yaml
# network-test-app.yaml
# A simple nginx pod to debug network connectivity against
apiVersion: v1
kind: Pod
metadata:
  name: web-server
  labels:
    app: web-server
spec:
  containers:
  - name: nginx
    image: nginx:1.25-alpine
    ports:
    - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: web-server
spec:
  selector:
    app: web-server
  ports:
  - port: 80
    targetPort: 80
```

```bash
# Deploy the web server and service
kubectl apply -f network-test-app.yaml

# Deploy a separate app pod that we'll debug from
kubectl run my-app \
  --image=gcr.io/distroless/static-debian12 \
  --command -- /pause

# Inject netshoot ephemeral container for network debugging
kubectl debug -it my-app \
  --image=nicolaka/netshoot \
  --target=my-app

# === Inside the ephemeral container (netshoot toolkit) ===

# 1. Test DNS resolution
dig web-server.default.svc.cluster.local
nslookup web-server.default.svc.cluster.local
# Should return the ClusterIP of the service

# 2. Test HTTP connectivity
curl -v http://web-server.default.svc.cluster.local/
# Should return nginx's default page

# 3. Check which ports are open on this pod
ss -tulpn

# 4. Look at routing table
ip route show

# 5. Check network interface
ip addr show eth0

# 6. Capture traffic (useful for TLS debugging)
# In a real scenario, let traffic flow, then capture
tcpdump -i eth0 -nn -c 50 'tcp port 80'

# 7. Test latency to another service
ping -c 5 web-server.default.svc.cluster.local

# 8. Trace the network path
traceroute web-server.default.svc.cluster.local

exit
```

---

## Example 3: Copy a Pod for Debugging (Crash Loop Scenario)

```yaml
# crashing-app.yaml
# Simulates a pod that crashes on startup
apiVersion: v1
kind: Pod
metadata:
  name: crashing-app
spec:
  containers:
  - name: app
    image: busybox
    command: ["sh", "-c", "echo 'starting...'; exit 1"]  # exits immediately
    env:
    - name: DATABASE_URL
      value: "postgres://db.internal:5432/myapp"
    - name: API_KEY
      value: "secret-key-12345"
    volumeMounts:
    - name: config
      mountPath: /etc/config
  volumes:
  - name: config
    configMap:
      name: app-config
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  app.properties: |
    log.level=INFO
    max.connections=100
```

```bash
kubectl apply -f crashing-app.yaml

# Pod is in CrashLoopBackOff — you can't exec into it
kubectl get pod crashing-app
# STATUS: CrashLoopBackOff

# Create a COPY of the pod with ubuntu image (won't crash)
kubectl debug crashing-app \
  --copy-to=crashing-app-debug \
  --set-image='*=ubuntu' \
  --share-processes \
  -it -- bash

# === Inside the debug copy ===

# Check environment variables (same as original pod)
env | grep -E 'DATABASE|API'

# Check the mounted configmap
ls /etc/config/
cat /etc/config/app.properties

# Try running the original failing command manually to see what error occurs
sh -c "echo 'starting...'; exit 1"
# Now you can see the exit code and any output

# Inspect the filesystem for expected files
ls /app/ 2>/dev/null || echo "No /app directory"

exit

# Clean up the debug copy
kubectl delete pod crashing-app-debug
```

---

## Example 4: Debug a Node

```bash
# View the nodes in your cluster
kubectl get nodes

# Start a debug session on a specific node
# This creates a privileged pod with the node's filesystem at /host
kubectl debug node/my-worker-node-1 \
  --image=ubuntu \
  --interactive \
  --tty

# === Inside the node debug pod ===

# Enter the node's root filesystem
chroot /host

# Check kubelet status
systemctl status kubelet

# View kubelet logs (last 100 lines)
journalctl -u kubelet -n 100

# Stream kubelet logs in real-time
journalctl -u kubelet -f

# List running containers at the CRI level (bypasses K8s API)
crictl ps

# List pods at the CRI level
crictl pods

# Get logs for a specific container via CRI
# (useful when K8s API is not responding)
crictl logs CONTAINER_ID

# Check node disk usage
df -h

# Check memory
free -m

# Check CPU load
uptime
top -b -n 1 | head -20

# Check network interfaces
ip addr show
ip route show

# Check for node pressure issues
cat /proc/meminfo | grep -E 'MemAvailable|MemFree'

# View kernel messages
dmesg | tail -50

# Exit the chroot and then exit the debug pod
exit  # exits chroot
exit  # exits the debug pod

# The debug pod will be cleaned up automatically
# Or clean up manually:
kubectl get pods -A | grep node-debugger
kubectl delete pod node-debugger-XXX
```

---

## Example 5: Common kubectl debug Flags Reference

```bash
# ============================================================
# kubectl debug FLAGS REFERENCE
# ============================================================

# --- Basic ephemeral container ---
kubectl debug -it POD \
  --image=IMAGE \       # image to use for ephemeral container
  --target=CONTAINER    # share PID namespace with this container

# --- Copy pod with modifications ---
kubectl debug POD \
  --copy-to=NEW_POD_NAME \    # name for the copied pod
  --set-image='*=ubuntu' \    # replace all images with ubuntu
  --set-image='app=ubuntu' \  # replace only 'app' container's image
  --share-processes \         # enable PID namespace sharing in the copy
  -it -- COMMAND              # command to run in the copied pod

# --- Node debugging ---
kubectl debug node/NODE \
  --image=ubuntu \
  -it

# --- Namespace flag (applies to all kubectl debug variants) ---
kubectl debug -it POD \
  --image=busybox \
  --target=app \
  -n my-namespace

# --- Non-interactive (run a one-shot command) ---
kubectl debug POD \
  --image=busybox \
  --target=app \
  -- ls /proc/1/root

# --- Keep the debug copy after exit ---
kubectl debug POD \
  --copy-to=debug-pod \
  --set-image='*=ubuntu' \
  -it -- bash
# The copy will keep running after you exit
# Delete manually when done:
kubectl delete pod debug-pod

# ============================================================
# QUICK REFERENCE: WHAT TO USE WHEN
# ============================================================

# Distroless pod, pod is running
kubectl debug -it MY_POD --image=nicolaka/netshoot --target=MY_CONTAINER

# Pod in CrashLoopBackOff
kubectl debug MY_POD --copy-to=debug --set-image='*=ubuntu' -it -- bash

# Network issue (DNS, service connectivity)
kubectl debug -it MY_POD --image=nicolaka/netshoot --target=MY_CONTAINER

# Need specific tool not in busybox/netshoot
kubectl debug -it MY_POD --image=ubuntu --target=MY_CONTAINER
# Inside: apt-get update && apt-get install -y strace

# Node-level problem
kubectl debug node/MY_NODE --image=ubuntu -it

# OOMKilled pod inspection
kubectl debug -it MY_POD --image=busybox --target=MY_CONTAINER
# Inside: cat /proc/1/status | grep VmRSS
```

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Ephemeral Containers Theory](./Theory.md) |
| Cheatsheet | [Ephemeral Containers Cheatsheet](./Cheatsheet.md) |
| Interview Q&A | [Ephemeral Containers Interview Q&A](./Interview_QA.md) |
| Next Module | [36 — ValidatingAdmissionPolicy](../36_ValidatingAdmissionPolicy/Theory.md) |
