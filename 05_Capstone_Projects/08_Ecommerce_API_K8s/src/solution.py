"""
solution.py — K8s Manifest Generator (Solution)
================================================
Generates all Kubernetes YAML manifests for the E-Commerce API project and
writes them to a k8s/ directory ready for `kubectl apply -f k8s/`.

How to run:
    python src/solution.py

Adjust the configuration block at the top before running.
"""

import os
import base64

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

IMAGE_NAME = "ecommerce-api"
IMAGE_TAG = "1.0.0"
REPLICA_COUNT = 3

APP_CPU_REQUEST = "100m"
APP_CPU_LIMIT = "500m"
APP_MEM_REQUEST = "128Mi"
APP_MEM_LIMIT = "512Mi"

PG_CPU_REQUEST = "250m"
PG_CPU_LIMIT = "500m"
PG_MEM_REQUEST = "256Mi"
PG_MEM_LIMIT = "512Mi"

PG_STORAGE = "5Gi"
INGRESS_HOST = "shop.local"

HPA_MIN = 2
HPA_MAX = 10
HPA_CPU_TARGET = 50

POSTGRES_PASSWORD_PLAIN = "mysecretpassword"
JWT_SECRET_PLAIN = "supersecretjwtkey"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def b64(value: str) -> str:
    """Base64-encode a string for use in a Kubernetes Secret."""
    return base64.b64encode(value.encode()).decode()


def write_file(directory: str, filename: str, content: str) -> None:
    """Write content to directory/filename, creating the directory if needed."""
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, filename)
    with open(path, "w") as f:
        f.write(content.lstrip("\n"))
    print(f"  wrote {path}")


# ---------------------------------------------------------------------------
# Manifest generators
# ---------------------------------------------------------------------------

def namespace_yaml() -> str:
    return f"""
apiVersion: v1
kind: Namespace
metadata:
  name: ecommerce
"""


def configmap_yaml() -> str:
    return f"""
apiVersion: v1
kind: ConfigMap
metadata:
  name: ecommerce-config
  namespace: ecommerce
data:
  POSTGRES_DB: ecommerce
  POSTGRES_USER: appuser
  POSTGRES_HOST: postgres-service   # K8s DNS name of the postgres Service
  POSTGRES_PORT: "5432"
  APP_ENV: production
  LOG_LEVEL: INFO
"""


def secret_yaml() -> str:
    pg_pass = b64(POSTGRES_PASSWORD_PLAIN)
    jwt_key = b64(JWT_SECRET_PLAIN)
    return f"""
apiVersion: v1
kind: Secret
metadata:
  name: ecommerce-secret
  namespace: ecommerce
type: Opaque
data:
  POSTGRES_PASSWORD: {pg_pass}
  SECRET_KEY: {jwt_key}
"""


def postgres_pvc_yaml() -> str:
    return f"""
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
  namespace: ecommerce
spec:
  accessModes:
    - ReadWriteOnce           # one node can mount read-write at a time
  resources:
    requests:
      storage: {PG_STORAGE}
"""


def postgres_deployment_yaml() -> str:
    return f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: ecommerce
spec:
  replicas: 1                 # databases are not horizontally scaled with plain Deployments
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: db
          image: postgres:15-alpine
          ports:
            - containerPort: 5432
          env:
            - name: POSTGRES_DB
              valueFrom:
                configMapKeyRef:
                  name: ecommerce-config
                  key: POSTGRES_DB
            - name: POSTGRES_USER
              valueFrom:
                configMapKeyRef:
                  name: ecommerce-config
                  key: POSTGRES_USER
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: ecommerce-secret
                  key: POSTGRES_PASSWORD
          resources:
            requests:
              cpu: {PG_CPU_REQUEST}
              memory: {PG_MEM_REQUEST}
            limits:
              cpu: {PG_CPU_LIMIT}
              memory: {PG_MEM_LIMIT}
          volumeMounts:
            - name: postgres-data
              mountPath: /var/lib/postgresql/data
      volumes:
        - name: postgres-data
          persistentVolumeClaim:
            claimName: postgres-pvc
"""


def postgres_service_yaml() -> str:
    return f"""
apiVersion: v1
kind: Service
metadata:
  name: postgres-service        # this name is the DNS hostname inside the cluster
  namespace: ecommerce
spec:
  selector:
    app: postgres
  ports:
    - port: 5432
      targetPort: 5432
  type: ClusterIP               # internal only, not reachable from outside
"""


def app_deployment_yaml() -> str:
    return f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ecommerce-api
  namespace: ecommerce
spec:
  replicas: {REPLICA_COUNT}
  selector:
    matchLabels:
      app: ecommerce-api
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1               # allow 1 extra pod during rollout
      maxUnavailable: 0         # zero downtime: never remove a pod before replacement is ready
  template:
    metadata:
      labels:
        app: ecommerce-api
    spec:
      containers:
        - name: app
          image: {IMAGE_NAME}:{IMAGE_TAG}
          imagePullPolicy: Never    # use locally built image in minikube
          ports:
            - containerPort: 8000
          env:
            - name: POSTGRES_HOST
              valueFrom:
                configMapKeyRef:
                  name: ecommerce-config
                  key: POSTGRES_HOST
            - name: POSTGRES_PORT
              valueFrom:
                configMapKeyRef:
                  name: ecommerce-config
                  key: POSTGRES_PORT
            - name: POSTGRES_DB
              valueFrom:
                configMapKeyRef:
                  name: ecommerce-config
                  key: POSTGRES_DB
            - name: POSTGRES_USER
              valueFrom:
                configMapKeyRef:
                  name: ecommerce-config
                  key: POSTGRES_USER
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: ecommerce-secret
                  key: POSTGRES_PASSWORD
            - name: SECRET_KEY
              valueFrom:
                secretKeyRef:
                  name: ecommerce-secret
                  key: SECRET_KEY
            - name: APP_ENV
              valueFrom:
                configMapKeyRef:
                  name: ecommerce-config
                  key: APP_ENV
          resources:
            requests:
              cpu: {APP_CPU_REQUEST}
              memory: {APP_MEM_REQUEST}
            limits:
              cpu: {APP_CPU_LIMIT}      # container throttled if it exceeds this
              memory: {APP_MEM_LIMIT}   # container OOM-killed if it exceeds this
          readinessProbe:
            httpGet:
              path: /health             # traffic only sent to pods returning 200 here
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 5
            failureThreshold: 3
          livenessProbe:
            httpGet:
              path: /health             # pod restarted if this fails 3 times
              port: 8000
            initialDelaySeconds: 30     # longer: app must fully initialise first
            periodSeconds: 10
            failureThreshold: 3
"""


def app_service_yaml() -> str:
    return f"""
apiVersion: v1
kind: Service
metadata:
  name: app-service
  namespace: ecommerce
spec:
  selector:
    app: ecommerce-api
  ports:
    - port: 80            # Ingress hits this port
      targetPort: 8000    # FastAPI container listens here
  type: ClusterIP
"""


def ingress_yaml() -> str:
    return f"""
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ecommerce-ingress
  namespace: ecommerce
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /$2   # strip /api prefix before forwarding
spec:
  ingressClassName: nginx
  rules:
    - host: {INGRESS_HOST}
      http:
        paths:
          - path: /api(/|$)(.*)        # capture group $2 used in rewrite-target annotation
            pathType: Prefix
            backend:
              service:
                name: app-service
                port:
                  number: 80
"""


def hpa_yaml() -> str:
    return f"""
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ecommerce-api-hpa
  namespace: ecommerce
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ecommerce-api
  minReplicas: {HPA_MIN}      # availability floor
  maxReplicas: {HPA_MAX}     # cost ceiling
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: {HPA_CPU_TARGET}  # scale out when average CPU exceeds this
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    output_dir = "k8s"
    print(f"Generating manifests into {output_dir}/\n")

    manifests = [
        ("namespace.yaml",            namespace_yaml()),
        ("configmap.yaml",            configmap_yaml()),
        ("secret.yaml",               secret_yaml()),
        ("postgres-pvc.yaml",         postgres_pvc_yaml()),
        ("postgres-deployment.yaml",  postgres_deployment_yaml()),
        ("postgres-service.yaml",     postgres_service_yaml()),
        ("app-deployment.yaml",       app_deployment_yaml()),
        ("app-service.yaml",          app_service_yaml()),
        ("ingress.yaml",              ingress_yaml()),
        ("hpa.yaml",                  hpa_yaml()),
    ]

    for filename, content in manifests:
        write_file(output_dir, filename, content)

    print(f"\nAll manifests written to {output_dir}/")
    print("\nNext steps:")
    print("  1. eval $(minikube docker-env)")
    print("  2. docker build -t ecommerce-api:1.0.0 .")
    print("  3. kubectl apply -f k8s/")
    print("  4. kubectl get all -n ecommerce")
    print(f"  5. echo \"$(minikube ip)  {INGRESS_HOST}\" | sudo tee -a /etc/hosts")
    print(f"  6. curl http://{INGRESS_HOST}/api/health")


if __name__ == "__main__":
    main()
