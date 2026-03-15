# Image to Deployment Workflow — Interview Q&A

---

## Beginner

**Q1: How does a Docker image get into Kubernetes?**

A Docker image gets into Kubernetes through a container registry — a storage service for container images. The flow is:

1. You build the image locally: `docker build -t myapp:v1 .`
2. You push it to a registry: `docker push myrepo/myapp:v1`
3. You write a Deployment YAML that references the image: `image: myrepo/myapp:v1`
4. You apply the Deployment: `kubectl apply -f deployment.yaml`
5. Kubernetes schedules Pods on nodes
6. The kubelet on each node pulls the image from the registry
7. containerd starts the container from the image

Kubernetes never uses your local Docker daemon. The image must be in a registry that the cluster nodes can reach — Docker Hub, AWS ECR, GCR, GHCR, or a private registry.

---

**Q2: What is imagePullPolicy and what are the options?**

`imagePullPolicy` controls when Kubernetes pulls the container image from the registry when starting a Pod.

**Options:**

| Value | Behavior |
|---|---|
| `Always` | Always contact the registry and pull the latest image for the tag |
| `IfNotPresent` | Use the cached image on the node if it exists; only pull if missing |
| `Never` | Never pull — fail if the image isn't already on the node |

**Default behavior** (when you don't specify imagePullPolicy):
- Tag is `latest` → `Always`
- Any other tag → `IfNotPresent`

**Best practice for production**: Use versioned tags (not `latest`) with `IfNotPresent`. This gives you predictable, fast startup using the node cache, while ensuring you can control exactly which version runs by changing the tag.

---

**Q3: What is a container registry and which ones work with Kubernetes?**

A container registry is a storage service for container images. When Kubernetes needs to run a container, its kubelet agent pulls the image from a registry.

Common registries that work with Kubernetes:
- **Docker Hub** (`docker.io`) — the default public registry
- **AWS ECR** (Elastic Container Registry) — managed registry on AWS
- **Google Container Registry / Artifact Registry** (`gcr.io`) — managed registry on GCP
- **GitHub Container Registry** (`ghcr.io`) — integrated with GitHub repos
- **Azure Container Registry** (`azurecr.io`) — managed registry on Azure
- **Harbor** — open-source self-hosted option

Any OCI-compliant registry works. For private registries, you need to configure `imagePullSecrets` in Kubernetes so nodes can authenticate.

---

**Q4: What happens when you run `kubectl apply -f deployment.yaml`?**

A chain of events fires across multiple Kubernetes components:

1. **API Server** receives the request, validates the YAML schema, and runs admission webhooks
2. **etcd** stores the desired state (3 replicas of this Deployment)
3. **Scheduler** notices unscheduled Pods and assigns each to a node based on resource availability
4. **Kubelet** on each assigned node sees new Pods assigned to it
5. **Kubelet** tells containerd to pull the image from the registry
6. **containerd** downloads image layers and creates the container process
7. **Kubelet** reports Pod status back to the API Server
8. Pod status becomes `Running`

The declarative model means you describe what you want, and Kubernetes figures out how to make it happen.

---

**Q5: Why should you never use the `latest` tag in Kubernetes?**

Two problems with `latest`:

**Problem 1 — Unpredictable behavior**: If `imagePullPolicy` is `IfNotPresent` (the default for non-latest tags), nodes with a cached `latest` image won't pull the new one when you deploy. Different nodes may run different versions.

**Problem 2 — No auditability**: You can't tell from the Deployment YAML what code is actually running. `latest` gives you no version history or rollback capability.

**Solution**: Use a specific, immutable tag for every deployment:
- Semantic version: `v1.2.3`
- Git commit SHA: `abc1234def5` (best for traceability)
- CI build number: `build-1423`

With a unique tag per deployment, `IfNotPresent` works correctly (the new tag isn't cached), rollback means switching back to a previous tag, and your deployment history tells you exactly what ran when.

---

## Intermediate

**Q6: How do you authenticate to a private registry in Kubernetes?**

Kubernetes uses `imagePullSecrets` — a special Secret containing registry credentials that are passed to the kubelet when pulling images.

**Create the pull secret:**
```bash
kubectl create secret docker-registry regcred \
  --docker-server=ghcr.io \
  --docker-username=myusername \
  --docker-password=$GITHUB_TOKEN \
  --namespace=production
```

**Reference it in the Deployment:**
```yaml
spec:
  template:
    spec:
      imagePullSecrets:
        - name: regcred
      containers:
        - name: myapp
          image: ghcr.io/myorg/myapp:v1
```

**Attach to a ServiceAccount** (so all Pods in a namespace get it automatically):
```bash
kubectl patch serviceaccount default -n production \
  -p '{"imagePullSecrets": [{"name": "regcred"}]}'
```

For AWS ECR, the credentials expire every 12 hours — in production, use the ECR Credential Helper or the `amazon-ecr-credential-helper` to rotate credentials automatically. For GKE, Workload Identity eliminates the need for pull secrets entirely.

---

**Q7: What is a rolling update and how does Kubernetes ensure zero downtime?**

A rolling update replaces Pods gradually — bringing up new Pods with the new image before taking down old ones — so traffic is never completely interrupted.

The rollout strategy is controlled by two settings:
```yaml
rollingUpdate:
  maxSurge: 1        # Allow 1 extra Pod beyond desired count during update
  maxUnavailable: 0  # Never reduce running Pods below desired count
```

With `replicas: 3`, `maxSurge: 1`, `maxUnavailable: 0`:
1. K8s creates Pod 4 (new image) — now 4 Pods running (3 old, 1 new)
2. K8s waits for Pod 4's readiness probe to pass
3. Pod 4 enters the Service's endpoint list (traffic starts going to it)
4. K8s terminates Pod 1 (old image) — back to 3 Pods (2 old, 1 new)
5. Repeat until all Pods run the new image

The readiness probe is what makes this zero-downtime: a new Pod doesn't receive traffic until it proves it's ready. If the probe never passes (bad deployment), the rollout stalls and old Pods continue serving traffic.

---

**Q8: How do you rollback a deployment in Kubernetes?**

Kubernetes keeps previous ReplicaSets around (controlled by `revisionHistoryLimit`, default 10) specifically to support fast rollbacks.

```bash
# Rollback to the previous version
kubectl rollout undo deployment/myapp -n production

# View history first (to pick a specific revision)
kubectl rollout history deployment/myapp -n production

# Rollback to a specific revision
kubectl rollout undo deployment/myapp --to-revision=3 -n production

# Verify the rollback is complete
kubectl rollout status deployment/myapp -n production

# Confirm which image is now running
kubectl get deployment myapp -n production \
  -o jsonpath='{.spec.template.spec.containers[0].image}'
```

`kubectl rollout undo` works by restoring the previous ReplicaSet to the desired replica count — it's extremely fast because the old Pods don't need to be rescheduled or have images pulled (they're already on the nodes). The rollout takes the same rolling update path, just in reverse.

---

**Q9: What is the difference between a Service of type ClusterIP, NodePort, and LoadBalancer?**

| Service Type | Accessible From | Use Case |
|---|---|---|
| `ClusterIP` | Inside the cluster only | Service-to-service communication (default) |
| `NodePort` | Cluster nodes' IPs + a static port | On-prem or local testing, not recommended for production |
| `LoadBalancer` | External internet (via cloud LB) | Direct external access for non-HTTP services |
| `Ingress` | External internet via HTTP/HTTPS rules | Production HTTP/HTTPS routing (not a Service type — uses a ClusterIP Service behind it) |

**For most production HTTP services**, the recommended pattern is:
- ClusterIP Service (internal routing)
- Ingress (external routing with hostname/path rules + TLS termination)

This keeps your Services internal and uses a single LoadBalancer (the Ingress controller) to route all external traffic.

---

**Q10: How do resource requests and limits affect image deployment and pod scheduling?**

`resources.requests` and `resources.limits` don't affect image pulling, but they directly affect whether Pods can be scheduled and how they behave under load.

**Requests** (the minimum):
- The Scheduler uses requests to decide which node has enough capacity for the Pod
- If no node has enough CPU/memory request capacity, the Pod stays `Pending`
- Without requests, Pods are scheduled anywhere — they can end up on overloaded nodes

**Limits** (the maximum):
- If a container exceeds its memory limit, Kubernetes kills it (`OOMKilled`)
- If a container exceeds its CPU limit, it's throttled (not killed)

**Correct pattern for production:**
```yaml
resources:
  requests:
    cpu: "100m"      # Guaranteed minimum
    memory: "128Mi"
  limits:
    cpu: "500m"      # Maximum allowed
    memory: "512Mi"
```

Containers without limits can consume all node resources and starve other workloads — always set both requests and limits.

---

## Advanced

**Q11: How do you implement image promotion across environments (dev → staging → production)?**

Image promotion is the practice of using the same image artifact across environments, rather than rebuilding for each environment. This ensures that what you test in staging is exactly what runs in production.

**The pattern:**
1. **CI builds once** — on every merge to main, build and push with the git SHA as the tag:
   ```bash
   docker build -t myrepo/myapp:$GIT_SHA .
   docker push myrepo/myapp:$GIT_SHA
   ```

2. **Deploy SHA to dev automatically** — CD pipeline applies the Deployment with the new SHA tag

3. **Promote to staging** — copy the same SHA tag with a human-readable alias:
   ```bash
   docker buildx imagetools create \
     --tag myrepo/myapp:staging-v1.2.3 \
     myrepo/myapp:$GIT_SHA
   ```

4. **Promote to production** — after staging approval:
   ```bash
   docker buildx imagetools create \
     --tag myrepo/myapp:prod-v1.2.3 \
     myrepo/myapp:$GIT_SHA
   ```

The critical property: no image rebuild at promotion. You're moving a pointer (the tag) to the same image layers. The SHA is the source of truth; environment-specific tags are aliases.

In Kubernetes, update the Deployment's image tag via GitOps (update the tag in git, let the CD tool apply it) rather than direct `kubectl set image` calls.

---

**Q12: What is image signing and verification in Kubernetes?**

Image signing is a way to cryptographically prove that an image was built by a trusted source and hasn't been tampered with. Kubernetes can be configured to reject unsigned images.

**The problem**: Anyone with registry push access can push a malicious image. Without signing, Kubernetes can't distinguish a legitimate image from a tampered one.

**Tools:**
- **Cosign** (from the Sigstore project) — the standard for signing OCI images:
  ```bash
  # Sign an image after pushing
  cosign sign --key cosign.key ghcr.io/myorg/myapp:v1

  # Verify before using
  cosign verify --key cosign.pub ghcr.io/myorg/myapp:v1
  ```

- **Notation** — another signing standard, used by Docker Hub and ACR

**Enforcement in Kubernetes:**
- **Connaisseur** or **Kyverno** admission webhook: validates image signatures before allowing Pods to start
- A Pod with an unsigned image is rejected before it's scheduled

**In practice**, image signing is required in regulated industries (PCI-DSS, HIPAA) and is increasingly standard in security-conscious organizations. The integration point is an admission controller that calls out to Cosign/Notation on every Pod creation.

---

**Q13: How does GitOps automate the entire build-push-deploy workflow?**

GitOps is a deployment model where git is the single source of truth for both application code and infrastructure state. The workflow is fully automated and auditable.

**The GitOps pipeline:**

1. **Developer pushes code** to a feature branch → opens PR
2. **CI pipeline** (GitHub Actions, GitLab CI) runs tests, builds image, pushes with SHA tag
3. **CI updates the Deployment YAML** in a separate git repo (the "config repo") with the new image tag:
   ```bash
   # In CI, after building
   sed -i "s|image: .*|image: ghcr.io/myorg/myapp:$GIT_SHA|" k8s/deployment.yaml
   git commit -m "Update myapp to $GIT_SHA"
   git push
   ```
4. **GitOps controller** (ArgoCD or Flux) watches the config repo
5. Controller detects the change and applies it to the cluster automatically
6. The cluster state is now in sync with git state

**Why this is powerful:**
- **Audit trail**: Every deployment is a git commit with author, timestamp, and PR link
- **Rollback**: Revert the git commit → ArgoCD automatically rolls back the cluster
- **Drift detection**: If someone does `kubectl set image` directly, ArgoCD detects the drift and restores git state
- **PR-based approvals**: Production deployments can require a PR review before the config repo is updated

ArgoCD and Flux are the two dominant GitOps controllers. The pattern eliminates `kubectl apply` from developer hands and makes all deployments go through git.

---

**Q14: What common image pull failures occur in Kubernetes and how do you diagnose them?**

The most common image pull failures:

**1. `ImagePullBackOff` / `ErrImagePull`**
```bash
kubectl describe pod <pod-name> -n production
# Look at Events section at the bottom
# Common messages:
# "unauthorized: authentication required" → missing or wrong imagePullSecret
# "not found" → wrong image name or tag that doesn't exist
# "connection refused" → registry is unreachable from nodes
```

**Diagnosis flow:**
```bash
# Check Pod events
kubectl describe pod <pod-name>

# Is the imagePullSecret correct?
kubectl get secret regcred -n production -o jsonpath='{.data.\.dockerconfigjson}' | base64 -d

# Does the image exist in the registry?
docker manifest inspect ghcr.io/myorg/myapp:v1

# Can the node reach the registry? (debug with a pod on the same node)
kubectl debug node/<node-name> -it --image=busybox
```

**Common causes and fixes:**
| Error | Cause | Fix |
|---|---|---|
| `unauthorized` | Missing imagePullSecret | Create and reference regcred |
| `not found` | Wrong tag or wrong image name | Verify tag exists in registry |
| `timeout` | Registry unreachable | Check network policy / firewall |
| `ImagePullBackOff` | Repeated failures — K8s backing off | Check underlying error in `describe` |

---

## 📂 Navigation

⬅️ **Prev:** [Compose to K8s Migration](../02_Compose_to_K8s_Migration/Interview_QA.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Projects](../../04_Projects/01_Dockerize_a_Python_App/Theory.md)

| File | Description |
|---|---|
| [Theory.md](./Theory.md) | Image to Deployment — full explanation |
| [Cheatsheet.md](./Cheatsheet.md) | Quick reference commands |
| [Interview_QA.md](./Interview_QA.md) | You are here — interview questions and answers |
