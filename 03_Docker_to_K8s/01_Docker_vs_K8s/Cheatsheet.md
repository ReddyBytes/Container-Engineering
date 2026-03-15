# Module 01 — Docker vs Kubernetes Cheatsheet

## Docker CLI → kubectl Command Equivalents

| What You Want To Do | Docker Command | kubectl Equivalent |
|---|---|---|
| Run a container / pod | `docker run nginx` | `kubectl run nginx --image=nginx` |
| List running containers | `docker ps` | `kubectl get pods` |
| List all containers (incl. stopped) | `docker ps -a` | `kubectl get pods -A` (all namespaces) |
| View container logs | `docker logs <container>` | `kubectl logs <pod>` |
| Follow live logs | `docker logs -f <container>` | `kubectl logs -f <pod>` |
| Exec into a container | `docker exec -it <container> sh` | `kubectl exec -it <pod> -- sh` |
| Stop a container | `docker stop <container>` | `kubectl delete pod <pod>` |
| Remove a container | `docker rm <container>` | `kubectl delete pod <pod>` |
| Inspect a container | `docker inspect <container>` | `kubectl describe pod <pod>` |
| Build an image | `docker build -t myapp:v1 .` | `docker build -t myapp:v1 .` (same — K8s doesn't build) |
| Push an image | `docker push myrepo/myapp:v1` | `docker push myrepo/myapp:v1` (same) |
| Deploy an app | `docker run -d myapp:v1` | `kubectl apply -f deployment.yaml` |
| Scale replicas | `docker-compose up --scale web=3` | `kubectl scale deployment web --replicas=3` |
| View environment | `docker inspect` → `Env` | `kubectl exec <pod> -- env` |
| Copy files | `docker cp <container>:/path ./local` | `kubectl cp <pod>:/path ./local` |
| Port forward | `docker run -p 8080:80` | `kubectl port-forward pod/<pod> 8080:80` |
| View resource usage | `docker stats` | `kubectl top pods` |
| Pull image | `docker pull nginx:latest` | _(K8s pulls automatically on deploy)_ |

---

## Docker Compose → Kubernetes Commands

| Docker Compose Action | kubectl Equivalent |
|---|---|
| `docker-compose up` | `kubectl apply -f k8s/` |
| `docker-compose down` | `kubectl delete -f k8s/` |
| `docker-compose up --build` | `docker build + docker push + kubectl apply` |
| `docker-compose ps` | `kubectl get pods` |
| `docker-compose logs` | `kubectl logs <pod>` |
| `docker-compose exec web sh` | `kubectl exec -it <pod> -- sh` |
| `docker-compose scale web=3` | `kubectl scale deployment web --replicas=3` |
| `docker-compose restart web` | `kubectl rollout restart deployment/web` |
| `docker-compose pull` | _(K8s pulls on deploy — no separate command needed)_ |
| `docker-compose config` | `kubectl get deployment <name> -o yaml` |

---

## Concept Mapping Table

| Docker / Compose Concept | Kubernetes Equivalent | Notes |
|---|---|---|
| Container | Pod | A Pod wraps one or more containers |
| `docker run` options | Pod spec | Image, env vars, ports, volumes all live in the Pod spec |
| `docker-compose.yml` service | Deployment + Service | Split into two K8s objects |
| Docker Compose file | K8s YAML manifests | Usually one file per resource type |
| `restart: unless-stopped` | `restartPolicy: Always` | Default in Deployments |
| Docker network (bridge) | Kubernetes Service | K8s flat network + Service for DNS/routing |
| `docker network connect` | NetworkPolicy | Controls which Pods can talk to each other |
| `docker volume` | PersistentVolume (PV) | Cluster-level storage resource |
| Volume mount | PersistentVolumeClaim (PVC) | Pod-level request for storage |
| `.env` file | ConfigMap | Non-sensitive key-value config |
| `.env` file (secrets) | Secret | Base64-encoded, sensitive values |
| `docker secret` (Swarm) | Secret | K8s equivalent is `kind: Secret` |
| `-p 8080:80` port mapping | Service (NodePort / LoadBalancer) | Or `kubectl port-forward` for local dev |
| `healthcheck:` | livenessProbe + readinessProbe | K8s has two separate probe types |
| `depends_on:` | initContainers + readinessProbe | More robust than Compose's version |
| `deploy.replicas:` | `spec.replicas` in Deployment | |
| `deploy.resources.limits:` | `resources.limits` | CPU and memory |
| `deploy.resources.reservations:` | `resources.requests` | Minimum guaranteed resources |
| `docker service` (Swarm) | Deployment | K8s Deployments manage replica sets |
| Docker Swarm | Kubernetes | Both are orchestrators — K8s is dominant |
| `docker push` to Hub | `docker push` to any registry | ECR, GCR, GHCR, Docker Hub all work |

---

## When-To-Use Guide

### Use Docker alone when:
- Building and testing images locally
- Running a single container for a task or experiment
- CI/CD pipeline steps (building, pushing)

### Use Docker Compose when:
- Running a multi-container app on a single machine
- Local development environments
- Simple single-server production deployments
- When K8s overhead is not worth it (small app, small team)

### Use kubectl (Kubernetes) when:
- Deploying to a multi-node cluster
- You need auto-scaling, self-healing, or rolling updates
- Running production workloads that require high availability
- Managing many services with teams working independently

---

## Quick Workflow Reference

```bash
# The complete image-to-running-pod workflow
docker build -t myrepo/myapp:v1 .          # Build the image
docker push myrepo/myapp:v1                # Push to registry
kubectl apply -f deployment.yaml           # Deploy to K8s
kubectl get pods                           # Check it's running
kubectl logs <pod-name>                    # Check logs

# Update a running deployment
docker build -t myrepo/myapp:v2 .          # New version
docker push myrepo/myapp:v2               # Push new version
kubectl set image deployment/myapp \
  myapp=myrepo/myapp:v2                    # Update image in cluster
kubectl rollout status deployment/myapp    # Watch the rollout
kubectl rollout undo deployment/myapp      # Rollback if something breaks
```

---

## 📂 Navigation

⬅️ **Prev:** [Docker - Best Practices](../../01_Docker/17_Docker_Init_and_Debug/Interview_QA.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Compose to K8s Migration](../02_Compose_to_K8s_Migration/Theory.md)

| File | Description |
|---|---|
| [Theory.md](./Theory.md) | Docker vs Kubernetes — full explanation |
| [Cheatsheet.md](./Cheatsheet.md) | You are here — quick reference |
| [Interview_QA.md](./Interview_QA.md) | Interview questions and answers |
