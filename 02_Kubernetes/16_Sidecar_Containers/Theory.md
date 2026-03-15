# Module 16: Sidecar Containers

## The Story: The Wingman

In aviation, a wingman flies alongside the lead aircraft — not flying the mission themselves, but providing support, protection, and capabilities that the lead needs to succeed. The wingman doesn't replace the lead; they complement it.

In Kubernetes, a sidecar container is exactly this: a helper container that runs alongside the main application container in the same pod, sharing network and storage, providing capabilities that the main app doesn't need to implement itself.

This pattern is so powerful that entire infrastructure products — service meshes, log collectors, configuration systems — are built on it.

> **🐳 Coming from Docker?**
>
> In Docker Compose, you can run multiple containers in the same `docker-compose.yml` — but they're independent processes on separate network stacks. They communicate over the network, not via shared localhost. Kubernetes sidecars in a Pod share the SAME network namespace — the sidecar and main container both listen on `localhost`, share the same IP, and can use shared volumes as an in-process filesystem. It's a fundamentally tighter coupling than anything Docker Compose offers: the sidecar is less like a "companion container" and more like a second process in the same runtime environment.

---

## What is a Sidecar?

A sidecar is any additional container in a pod that supports the main application container. Since all containers in a pod share:
- **The same network namespace** (same IP address, can communicate via localhost)
- **The same storage volumes** (can read/write the same files)
- **The same lifecycle** (start and stop together)

...a sidecar can transparently intercept traffic, tail log files, reload config, or handle TLS — all without the main app knowing or caring.

---

## Common Sidecar Patterns

### 1. Log Shipper

The main app writes logs to stdout/stderr or to a shared volume. The sidecar reads those logs and ships them to a centralized logging system (Elasticsearch, Splunk, Loki).

**Why sidecar, not DaemonSet?** A DaemonSet log collector reads from the node filesystem. A sidecar is needed when the app writes to a specific file path, needs log parsing per-application, or runs in environments where node-level access is restricted.

```
Main App → writes to /var/log/app.log
Sidecar  → reads /var/log/app.log, parses, ships to Elasticsearch
```

### 2. Service Mesh Proxy (Envoy/Istio)

Istio automatically injects an Envoy proxy sidecar into every pod. The Envoy proxy intercepts all inbound and outbound network traffic, providing:
- Mutual TLS (mTLS) between services
- Traffic metrics (request rate, latency, error rate)
- Request retries and circuit breaking
- Traffic splitting for canary deployments

The main app container is completely unaware of the proxy — it just sees network traffic as usual.

### 3. Config Reloader

The main app reads configuration from a file. The sidecar watches a ConfigMap or Vault path and writes updated config to a shared volume, then signals the main app to reload (via SIGHUP or a reload endpoint).

This enables zero-downtime config updates without restarting the pod.

### 4. TLS Termination / Auth Proxy

Instead of every app implementing TLS or OAuth, a sidecar handles it. The main app listens on plain HTTP (localhost:8080). The sidecar listens on HTTPS (0.0.0.0:443), terminates TLS, and forwards to the main app.

This is how ambassador proxies like oauth2-proxy work.

---

## Init Containers vs Sidecar Containers

This is a common source of confusion:

| Feature | Init Container | Sidecar Container |
|---|---|---|
| When it runs | Before app containers start | Alongside app containers |
| Lifecycle | Runs once, then exits | Runs for the lifetime of the pod |
| Purpose | Setup, initialization, waiting | Ongoing support |
| Failure behavior | Pod fails to start if init fails | Pod stays running if sidecar fails (unless critical) |

**Init container use cases**:
- Wait for a database to be ready before starting the app
- Clone a Git repository before the web server starts
- Run database migrations before the API starts
- Copy or transform configuration files

**Sidecar use cases**: Everything in the list above (log shipper, proxy, config reloader).

---

## Pod Network Sharing

```mermaid
graph TD
    subgraph Pod - single IP address: 10.0.0.5
        subgraph Volumes
            V1[/var/log shared volume]
            V2[/config shared volume]
        end

        A[Main App Container\nlistens on :8080\nwrites to /var/log/app.log]
        B[Sidecar: Log Shipper\nreads /var/log/app.log\nships to Elasticsearch]
        C[Sidecar: Envoy Proxy\nlistens on :443\nforwards to localhost:8080]

        A -- writes --> V1
        B -- reads --> V1
        C -- localhost:8080 --> A
        A -- reads --> V2
        D[Init: Config Setup\nwrites to /config] -- writes --> V2
    end

    E[External Traffic\nHTTPS :443] --> C
    B --> F[Elasticsearch]
```

---

## Native Sidecar Containers (Kubernetes 1.29+)

Before Kubernetes 1.29, sidecars were just regular containers — there was no way to express "this container should stay alive for the pod's lifetime and restart if it crashes." This caused a subtle problem: if a sidecar exited, it might take the pod down, or conversely, Jobs would never complete because the sidecar kept running.

Kubernetes 1.29 introduced **native sidecar containers** via the `restartPolicy: Always` field in `initContainers`. This is counterintuitive but intentional: init containers with `restartPolicy: Always` are treated as sidecars:

- They start before app containers
- They run alongside app containers
- They are restarted if they crash (without failing the pod)
- Jobs complete even if sidecars are running (sidecars are terminated after the Job pod completes)

```yaml
initContainers:
  - name: log-shipper
    image: fluent/fluent-bit:2.2.0
    restartPolicy: Always    # makes this a native sidecar (K8s 1.29+)
```

This solves the CronJob/Job problem where log sidecars prevented Job completion.

---

## The Ambassador Pattern

The Ambassador pattern uses a sidecar as a proxy to simplify the main app's interaction with external services. Instead of the main app knowing how to connect to, authenticate with, and route to an external service, the sidecar ambassador handles all of that. The main app just talks to `localhost`.

Example: The main app talks to `localhost:6380`. The ambassador sidecar connects to the appropriate Redis cluster in the right region, handles auth, and proxies the connection.

---

## The Adapter Pattern

The Adapter pattern uses a sidecar to normalize the main app's output into a standard format expected by the infrastructure.

Example: A legacy application outputs logs in a proprietary format. The adapter sidecar reads those logs, transforms them to JSON, and writes them to stdout — where the log infrastructure can pick them up normally.

---

## When Not to Use Sidecars

Sidecars add overhead: each sidecar consumes CPU and memory, and adds operational complexity. Consider alternatives:

- **Use a library instead**: If you want metrics, a Prometheus client library in your app is simpler than a metrics-scraping sidecar.
- **Use a DaemonSet**: For cluster-wide log collection from all containers' stdout, a DaemonSet is more efficient than a sidecar on every pod.
- **Use a service mesh**: Istio/Linkerd automatically injects proxy sidecars — you don't need to add them manually.

---

## 📂 Navigation

| | Link |
|---|---|
| Previous | [15_Deployment_Strategies](../15_Deployment_Strategies/Theory.md) |
| Next | [17_Jobs_and_CronJobs](../17_Jobs_and_CronJobs/Theory.md) |
| Cheatsheet | [Cheatsheet.md](./Cheatsheet.md) |
| Interview Q&A | [Interview_QA.md](./Interview_QA.md) |
