# Docker Security — Interview Q&A

---

## Beginner

**Q1: What are the main security risks with Docker containers?**

The main risks are:
1. **Running as root** — default behavior; if the app is exploited, the attacker has root inside the container
2. **Docker socket exposure** — mounting `/var/run/docker.sock` gives a container full control over the host's Docker daemon
3. **Privileged containers** — `--privileged` disables nearly all container isolation
4. **Secrets in environment variables** — visible in `docker inspect`, logs, and crash dumps
5. **Unscanned base images** — images with known CVEs that you inherit unknowingly
6. **Excessive Linux capabilities** — containers have more OS permissions than they need

---

**Q2: How do you run a container as a non-root user?**

Add a `USER` directive in your Dockerfile after creating the user:

```dockerfile
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --no-create-home appuser
USER appuser
CMD ["python", "app.py"]
```

After `USER appuser`, all subsequent `RUN`, `CMD`, and `ENTRYPOINT` instructions run as that user. You can verify with `docker run my-app whoami`.

---

**Q3: Why is it dangerous to use environment variables for secrets?**

Environment variables are not secret. They are:
- Visible in `docker inspect <container>` — anyone with Docker access can read them
- Available to any process inside the container (visible in `/proc/self/environ`)
- Often accidentally logged by frameworks that dump env vars on startup or crash
- Visible in CI/CD pipeline logs if commands are echoed

Use Docker secrets (files mounted at `/run/secrets/`), Vault, AWS Secrets Manager, or mounted secret files instead.

---

**Q4: What is `--cap-drop ALL` and when should you use it?**

Linux capabilities break root privileges into ~40 granular permissions. Docker grants a default subset (~14 capabilities). `--cap-drop ALL` removes all of them, then you add back only what your application actually needs:

```bash
docker run --cap-drop ALL --cap-add NET_BIND_SERVICE my-web-app
```

Use it whenever running a web service or API that doesn't need special OS-level permissions. It limits what an attacker can do if they exploit your app.

---

**Q5: What does `docker run --read-only` do?**

It makes the container's root filesystem read-only. The running process cannot write to it — it cannot create files, modify binaries, or install backdoors. Applications that need to write to disk use `--tmpfs` for in-memory directories or mounted volumes for persistent data:

```bash
docker run --read-only --tmpfs /tmp -v my-logs:/app/logs my-app
```

---

## Intermediate

**Q6: What is the Docker socket and why is mounting it dangerous?**

`/var/run/docker.sock` is the Unix socket the Docker daemon listens on for API requests. Every `docker` CLI command talks to the daemon through this socket. Mounting it into a container gives the container full control over all Docker operations on the host — it can start new containers, mount host directories, inspect running containers, and even escape isolation entirely:

```bash
# From inside a container with the socket mounted:
docker run --privileged -v /:/host --rm -it alpine chroot /host
# The attacker now has a root shell with full access to the host filesystem
```

Legitimate use cases (CI builders) should use Kaniko, Buildah, or a remote Docker daemon with TLS instead.

---

**Q7: How do you use Docker BuildKit build secrets to avoid leaking credentials into image layers?**

Use `--mount=type=secret` in a `RUN` instruction. The secret is made available only during that specific instruction and is never stored in any image layer:

```dockerfile
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc \
    npm install
```

Build with:
```bash
docker build --secret id=npmrc,src=~/.npmrc .
```

Without this, if you `COPY .npmrc .` and then `RUN npm install`, even if you `RUN rm .npmrc` afterward, the file is still in the intermediate layer and can be extracted with `docker history` and `docker export`.

---

**Q8: What is the difference between seccomp and AppArmor?**

Both restrict what a containerized process can do, but at different levels:

- **Seccomp** operates at the system call level. It specifies which Linux syscalls (the interface between processes and the kernel) are allowed. Docker's default profile blocks ~44 dangerous syscalls like `kexec_load`, `ptrace`, and `unshare`. An attacker can't use a syscall that seccomp blocks.

- **AppArmor** operates at the resource level. It restricts which files, directories, network operations, and capabilities a process can access, based on a profile. `docker-default` profile prevents common escape vectors.

They complement each other and both are active by default.

---

**Q9: What is Trivy and how do you integrate it into CI/CD?**

Trivy is an open-source vulnerability scanner by Aqua Security. It scans container images, Dockerfiles, filesystems, and Kubernetes manifests for known CVEs. In CI, you integrate it as a build step that fails the pipeline on critical findings:

```yaml
# GitHub Actions example
- name: Scan image for vulnerabilities
  run: |
    trivy image \
      --exit-code 1 \
      --severity CRITICAL \
      --no-progress \
      my-app:${{ github.sha }}
```

`--exit-code 1` causes Trivy to exit with code 1 if any matching vulnerabilities are found, which fails the GitHub Actions step.

---

**Q10: What does rootless Docker mean?**

Rootless Docker runs the entire Docker daemon as a non-root user. When a container process runs as UID 0 (root) inside the container, that maps to a non-privileged UID on the host via Linux user namespaces. A container breakout only gives the attacker a non-root UID on the host — significantly limiting blast radius compared to traditional Docker where a container root = host root.

```bash
# Set up rootless Docker for current user
dockerd-rootless-setuptool.sh install
systemctl --user start docker
export DOCKER_HOST=unix://$XDG_RUNTIME_DIR/docker.sock
```

---

## Advanced

**Q11: How would you design a fully hardened Docker security posture for a production API?**

A hardened production API container would have:

1. **Non-root user** — fixed UID/GID, referenced in SecurityContext
2. **Read-only filesystem** — `--read-only` with `--tmpfs /tmp`
3. **No new privileges** — `--security-opt no-new-privileges`
4. **Drop all capabilities** — `--cap-drop ALL`, add back only `NET_BIND_SERVICE` if needed
5. **Custom seccomp profile** — only syscalls the app actually uses
6. **Distroless or alpine base** — no package manager, minimal attack surface
7. **Pinned base image by digest** — reproducible, tamper-evident
8. **Trivy in CI** — gate on CRITICAL/HIGH findings
9. **No secrets in ENV** — use mounted secret files or Vault
10. **No Docker socket** — if building in CI, use Kaniko

In Kubernetes, this translates to a SecurityContext with `runAsNonRoot: true`, `readOnlyRootFilesystem: true`, and `allowPrivilegeEscalation: false`.

---

**Q12: Explain the supply chain attack risk and how to mitigate it.**

A supply chain attack targets the build inputs rather than the running system. Attack vectors include:
- Typosquatting base images: `FROM ubuntuu:22.04` pointing to a malicious image
- Compromised official images: an attacker gains push access to a legitimate image
- Malicious dependencies in package managers (like the `event-stream` npm incident)

Mitigations:
1. **Pin base images by digest** — `FROM python:3.12.3-slim@sha256:...` — digest cannot be spoofed
2. **Use only official or verified publisher images** — published by Docker or the original vendor
3. **Image signing with Docker Content Trust (DCT) or Sigstore** — cryptographically verify image provenance
4. **Private registry with replication** — pull approved images to your own registry; applications pull from your registry only
5. **SBOM (Software Bill of Materials)** — generate and store the list of all components in every image at build time

---

**Q13: What is the difference between Docker Content Trust (DCT) and image digest pinning?**

**Digest pinning** is simpler and more widely used. You use the exact SHA256 hash of an image manifest in your `FROM` or `docker pull` command. Docker verifies the image matches the digest. This prevents tag mutation — even if someone moves the tag, you'll only get the image with that exact hash.

**Docker Content Trust (DCT)** uses Notary for cryptographic signing. Publishers sign images with their private key. Consumers verify the signature with the publisher's public key. It provides assurance about who built the image, not just what the image contains. Enable with `DOCKER_CONTENT_TRUST=1`.

For most teams, digest pinning for base images combined with scanning provides sufficient supply chain security. DCT adds complexity but is warranted in environments with strict provenance requirements.

---

## 📂 Navigation

| | Link |
|---|---|
| Previous | [11 · Multi-Stage Builds](../11_Multi_Stage_Builds/Interview_QA.md) |
| Theory | [Security Theory](./Theory.md) |
| Cheatsheet | [Security Cheatsheet](./Cheatsheet.md) |
| Next | [13 · Docker Swarm](../13_Docker_Swarm/Interview_QA.md) |
