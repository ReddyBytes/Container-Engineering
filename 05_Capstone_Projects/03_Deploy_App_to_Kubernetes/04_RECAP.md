# 04 — Recap: Deploy an App to Kubernetes

---

## 🏁 What You Built

You took a containerized FastAPI app and deployed it as a Kubernetes-native workload — replicated, health-monitored, configurable without image rebuilds, and capable of zero-downtime updates and instant rollbacks.

```
docker image
     │
     ▼
k8s/deployment.yaml   →  3 pods, resource limits, probes
k8s/service.yaml      →  stable endpoint, load balancing
k8s/configmap.yaml    →  env config without rebuilding
k8s/secret.yaml       →  credentials without hardcoding
     │
     ▼  kubectl apply -f k8s/
     │
Kubernetes reconciler
     │
     └──▶ 3 Running pods reachable at :30080
```

---

## 🧠 Key Concepts

**Declarative management** means you describe the desired state, not the steps to get there. `kubectl apply -f k8s/` is idempotent — run it once or a hundred times, the cluster converges to the same state. This is fundamentally different from imperative commands like `docker run`.

**The Deployment controller** is the reconciliation loop that watches your pods. If you have `replicas: 3` and a pod crashes, the controller creates a replacement automatically, on any available node, within seconds.

**Readiness vs liveness probes** serve different purposes. Readiness controls traffic: a pod that fails readiness is removed from the Service's endpoint list until it recovers. Liveness controls restarts: a pod that fails liveness is killed and replaced. Setting liveness `initialDelaySeconds` higher than readiness prevents a restart loop during slow startup.

**Resource requests and limits** are the contract between your pod and the scheduler. Requests are the minimum the node must have free to place the pod — they guarantee headroom. Limits are the ceiling — CPU is throttled above the limit, memory gets the pod OOMKilled. Setting both is required for predictable scheduling.

**ConfigMap and Secret separation** keeps your image generic. The same image runs in dev, staging, and production with different ConfigMaps. Credentials never land in the image or in a `.env` file committed to git. In production, replace `Secret` with a secrets manager (Vault, External Secrets Operator, Sealed Secrets).

**Rolling updates with `maxUnavailable: 0`** guarantee zero downtime. Kubernetes creates the new pod and waits for its readiness probe to pass before terminating the old one. Traffic is never interrupted.

---

## 📊 kubectl Command Reference

```bash
# Check state
kubectl get pods -l app=myapi
kubectl get deployment myapi
kubectl get service myapi-svc

# Debug
kubectl describe pod <pod-name>          # events, probe results
kubectl logs <pod-name>                  # app stdout
kubectl exec -it <pod-name> -- /bin/sh   # shell into pod

# Scale
kubectl scale deployment myapi --replicas=5

# Update
kubectl set image deployment/myapi myapi=IMAGE:TAG
kubectl rollout status deployment/myapi

# Rollback
kubectl rollout history deployment/myapi
kubectl rollout undo deployment/myapi
kubectl rollout undo deployment/myapi --to-revision=1

# Inspect config
kubectl get configmap myapi-config -o yaml
kubectl get secret myapi-secret -o jsonpath='{.data.DB_PASSWORD}' | base64 -d
```

---

## 🚀 Extend It

- **Add a namespace:** create a `namespace.yaml` and deploy everything into `namespace: myapp-dev` instead of `default`
- **Add pod disruption budget:** write a `PodDisruptionBudget` with `minAvailable: 2` so cluster maintenance cannot take down more than one pod at a time
- **Add horizontal pod autoscaling:** write an `HPA` that scales `myapi` between 2 and 10 replicas based on CPU utilization above 60%
- **Add an Ingress:** deploy the nginx ingress controller and write an `Ingress` resource that routes `myapp.local/api` to `myapi-svc`
- **Add Postgres as a StatefulSet:** see Project 04 — running stateful workloads in Kubernetes requires `StatefulSet`, `PersistentVolumeClaim`, and headless Services
- **Use Kustomize:** replace the four static YAML files with a `kustomization.yaml` that patches image tags per environment

---

⬅️ **Prev:** [02 — Multi-Container App with Compose](../02_Multi_Container_App_Compose/01_MISSION.md) &nbsp;&nbsp; ➡️ **Next:** [04 — Full Stack on K8s](../04_Full_Stack_on_K8s/01_MISSION.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
