# Module 06 — Code Examples: Services

## Example 1: ClusterIP Service (Internal Backend)

```yaml
# backend-deployment.yaml
# The deployment we'll expose with a Service
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend                         # Label used by Service selector
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: hashicorp/http-echo:latest  # Simple HTTP server that echoes a message
        args:
        - "-text=Hello from backend pod $(HOSTNAME)"
        ports:
        - containerPort: 5678
        env:
        - name: HOSTNAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name     # Injects the pod name
---
# backend-service.yaml
# ClusterIP: only accessible from inside the cluster
apiVersion: v1
kind: Service
metadata:
  name: backend                            # DNS name: backend.default.svc.cluster.local
spec:
  type: ClusterIP                          # Default — omit if you want
  selector:
    app: backend                           # Route to pods with this label
  ports:
  - name: http                             # Named ports are required when multiple ports exist
    port: 80                               # Service listens on port 80
    targetPort: 5678                       # Pod's container listens on 5678
    protocol: TCP
```

```bash
kubectl apply -f backend-deployment.yaml
kubectl apply -f backend-service.yaml

# Check the service was created
kubectl get svc backend
# NAME      TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)   AGE
# backend   ClusterIP   10.96.102.100   <none>        80/TCP    10s

# Check the endpoints (pod IPs backing the service)
kubectl get endpoints backend
# NAME      ENDPOINTS                                   AGE
# backend   10.244.0.5:5678,10.244.0.6:5678,10.244.1.2:5678  10s

# Test from inside the cluster
kubectl run test --image=busybox --rm -it --restart=Never -- \
  wget -qO- http://backend
# Hello from backend pod backend-7d4b9c8f5-abc12

# Call it multiple times — you get different pods (load balancing)
for i in 1 2 3 4 5; do
  kubectl run test-$i --image=busybox --rm --restart=Never -- \
    wget -qO- http://backend 2>/dev/null
done
```

---

## Example 2: NodePort Service (Dev Access)

```yaml
# nodeport-service.yaml
# NodePort: accessible from outside the cluster on each node's IP
apiVersion: v1
kind: Service
metadata:
  name: backend-nodeport
spec:
  type: NodePort
  selector:
    app: backend                           # Same backend pods as before
  ports:
  - name: http
    port: 80                               # ClusterIP port (internal)
    targetPort: 5678                       # Pod port
    nodePort: 30080                        # External port on each node (30000-32767)
                                           # Omit this to get a random port assigned
```

```bash
kubectl apply -f nodeport-service.yaml

kubectl get svc backend-nodeport
# NAME               TYPE       CLUSTER-IP     EXTERNAL-IP   PORT(S)        AGE
# backend-nodeport   NodePort   10.96.105.200  <none>        80:30080/TCP   10s

# Access from outside the cluster
# First, get the node IP (minikube)
MINIKUBE_IP=$(minikube ip)
curl http://$MINIKUBE_IP:30080

# Or use minikube service shortcut
minikube service backend-nodeport --url
minikube service backend-nodeport   # opens in browser
```

---

## Example 3: LoadBalancer Service (Production)

```yaml
# loadbalancer-service.yaml
# LoadBalancer: cloud provider creates an external load balancer
apiVersion: v1
kind: Service
metadata:
  name: backend-public
  annotations:
    # AWS-specific: use an internal load balancer (optional)
    service.beta.kubernetes.io/aws-load-balancer-internal: "true"
spec:
  type: LoadBalancer
  selector:
    app: backend
  ports:
  - name: http
    port: 80
    targetPort: 5678
  # Optional: restrict access to specific IP ranges
  loadBalancerSourceRanges:
  - 10.0.0.0/8           # Only allow internal IPs (for internal services)
```

```bash
kubectl apply -f loadbalancer-service.yaml

# Watch for the external IP to be assigned (takes 1-2 min in cloud)
kubectl get svc backend-public --watch
# NAME             TYPE           CLUSTER-IP      EXTERNAL-IP     PORT(S)        AGE
# backend-public   LoadBalancer   10.96.110.50    <pending>       80:31234/TCP   10s
# backend-public   LoadBalancer   10.96.110.50    34.120.50.100   80:31234/TCP   90s

# Once EXTERNAL-IP is assigned, access it
curl http://34.120.50.100

# In minikube: run this in a separate terminal to get an IP
minikube tunnel
# Now check again — EXTERNAL-IP should be 127.0.0.1 or a local IP
```

---

## Example 4: Headless Service (for StatefulSet)

```yaml
# headless-service.yaml
# Headless service: clusterIP: None
# DNS returns pod IPs directly instead of a virtual IP
apiVersion: v1
kind: Service
metadata:
  name: database                           # Each pod gets: <pod-name>.database.default.svc.cluster.local
spec:
  clusterIP: None                          # Makes it headless — no virtual IP
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
---
# statefulset-postgres.yaml
# StatefulSet uses the headless service for stable pod DNS names
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
spec:
  serviceName: database                    # MUST reference the headless service name
  replicas: 3
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15
        env:
        - name: POSTGRES_PASSWORD
          value: "example"
        ports:
        - containerPort: 5432
```

```bash
kubectl apply -f headless-service.yaml

# Check the service — no ClusterIP
kubectl get svc database
# NAME       TYPE        CLUSTER-IP   EXTERNAL-IP   PORT(S)    AGE
# database   ClusterIP   None         <none>        5432/TCP   10s

# With a StatefulSet and headless service, pods get DNS names:
# postgres-0.database.default.svc.cluster.local
# postgres-1.database.default.svc.cluster.local
# postgres-2.database.default.svc.cluster.local

# Test DNS (shows individual pod IPs, not a single virtual IP)
kubectl run dns-test --image=busybox --rm -it --restart=Never -- \
  nslookup database
# Returns all three pod IPs
```

---

## Example 5: Service with Multiple Ports

```yaml
# multi-port-service.yaml
# Applications often expose both HTTP and HTTPS, or HTTP and metrics
apiVersion: v1
kind: Service
metadata:
  name: web-server
spec:
  type: LoadBalancer
  selector:
    app: web
  ports:
  - name: http                             # Name required when there are multiple ports
    port: 80
    targetPort: 8080
    protocol: TCP
  - name: https
    port: 443
    targetPort: 8443
    protocol: TCP
  - name: metrics                          # Prometheus scrape endpoint
    port: 9090
    targetPort: 9090
    protocol: TCP
```

---

## Example 6: ExternalName Service

```yaml
# externalname-service.yaml
# Maps a Service name to an external DNS — no proxying, just DNS CNAME
apiVersion: v1
kind: Service
metadata:
  name: external-db                        # Pods use this as the hostname
  namespace: default
spec:
  type: ExternalName
  externalName: my-rds.xyz.us-east-1.rds.amazonaws.com  # Resolves to this
```

```bash
kubectl apply -f externalname-service.yaml

# From inside a pod, "external-db" resolves to the RDS hostname
kubectl run test --image=busybox --rm -it --restart=Never -- \
  nslookup external-db
# Returns: my-rds.xyz.us-east-1.rds.amazonaws.com

# The app can connect to "external-db:5432" and K8s DNS routes it to the real host
# This means if you later migrate the DB into the cluster, you only change this Service
# — the application code stays the same
```

---

## Navigation

| File | Description |
|------|-------------|
| [Theory.md](./Theory.md) | Services explained |
| [Cheatsheet.md](./Cheatsheet.md) | Quick reference commands |
| [Interview_QA.md](./Interview_QA.md) | Interview questions and answers |
| [Code_Example.md](./Code_Example.md) | You are here — working YAML examples |

**Previous:** [05_Deployments_and_ReplicaSets](../05_Deployments_and_ReplicaSets/Code_Example.md) |
**Next:** [07_ConfigMaps_and_Secrets](../07_ConfigMaps_and_Secrets/Theory.md)
