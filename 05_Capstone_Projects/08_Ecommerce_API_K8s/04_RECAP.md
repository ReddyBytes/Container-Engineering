# 08 — Recap: Deploy E-Commerce API to Kubernetes

## What You Built

You started with a working FastAPI application running in Docker Compose and promoted it to a proper Kubernetes deployment. Along the way you wrote every manifest by hand, which means you now understand not just what each resource does but why it exists and what breaks without it.

The finished system:

- **Namespace** isolating all project resources from the rest of the cluster
- **ConfigMap + Secret** replacing `.env` files with cluster-native configuration
- **PostgreSQL** backed by a PersistentVolumeClaim so data survives pod restarts and node reboots
- **App Deployment** with liveness/readiness probes, resource guardrails, and a zero-downtime rolling update strategy
- **ClusterIP Services** providing stable internal DNS for pod-to-pod communication
- **Ingress** routing external HTTP traffic into the cluster with path rewriting
- **HorizontalPodAutoscaler** scaling the API automatically under load

---

## 3 Key Concepts

### 1. Declarative Infrastructure

You never told Kubernetes *how* to create the pods. You told it *what you wanted* — three replicas, these resource limits, this image — and it figured out the rest. This is the core shift from imperative scripting (`docker run`, shell scripts) to declarative infrastructure. The manifest is the source of truth; `kubectl apply` reconciles reality with that truth every time you run it.

### 2. Rolling Updates

A **rolling update** means Kubernetes replaces pods one at a time rather than destroying all three and starting fresh. With `maxUnavailable: 0` the service has zero downtime during a deployment — users never hit a pod that is being terminated. With `maxSurge: 1` the cluster temporarily runs four pods instead of three to absorb traffic during the transition. This pattern is why large teams can deploy dozens of times per day without maintenance windows.

### 3. Horizontal Scaling

A **HorizontalPodAutoscaler** decouples the question "how many replicas do I need right now?" from the question "how many did I put in the manifest?" The HPA watches real CPU metrics and continuously adjusts the replica count within your declared bounds. The result is a system that is cheap at 2am and handles Black Friday traffic at 2pm — automatically, without anyone touching a config file.

---

## Extend It

These challenges turn the project into a production-grade system:

**TLS with cert-manager**
Install cert-manager and a Let's Encrypt ClusterIssuer. Add the `cert-manager.io/cluster-issuer` annotation to your Ingress and a `tls:` section. The API will serve HTTPS with an automatically renewed certificate.

**Deploy to EKS**
Replace `imagePullPolicy: Never` with an ECR image URI. Create an EKS cluster with `eksctl`, configure `aws-load-balancer-controller` for Ingress, and apply the same manifests. Almost nothing changes except the image source and the Ingress class.

**Prometheus and Grafana monitoring**
Install the `kube-prometheus-stack` Helm chart. Add the `prometheus.io/scrape: "true"` annotation to the app Deployment. Build a Grafana dashboard showing request rate, error rate, and pod CPU — the three signals that tell you whether a rollout is healthy.

**NetworkPolicy**
Add a NetworkPolicy that allows the app pods to talk only to the postgres Service, and blocks all other ingress to the postgres pod. This is the minimum security posture for any database in Kubernetes.

---

⬅️ **Prev:** [07 — JWT Auth API Docker](../07_JWT_Auth_API_Docker/01_MISSION.md) &nbsp;&nbsp; ➡️ **Next:** [09 — Containerize RAG System](../09_RAG_System_Containerized/01_MISSION.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
