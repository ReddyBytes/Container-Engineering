# solution.py
# Project 03: Deploy an App to Kubernetes — complete solution
#
# This file covers two things:
# 1. The FastAPI application (app/main.py equivalent)
# 2. The four Kubernetes manifests as docstrings — copy each block to its own .yaml file
#
# Application code starts below. Kubernetes manifests are at the bottom.

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import os

app = FastAPI(
    title="My Dockerized API",
    version="1.0.0",
)

items_db: List[dict] = []
counter = {"value": 0}

# Read config from environment — injected by ConfigMap and Secret via envFrom
APP_ENV = os.getenv("APP_ENV", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
DB_USER = os.getenv("DB_USER", "")       # ← from Secret
DB_PASSWORD = os.getenv("DB_PASSWORD", "")


class Item(BaseModel):
    name: str
    price: float


class ItemResponse(BaseModel):
    id: int
    name: str
    price: float


@app.get("/")
def root():
    return {
        "message": "Hello from Kubernetes!",
        "version": app.version,
        "env": APP_ENV,         # ← confirms ConfigMap injection
        "log_level": LOG_LEVEL, # ← confirms ConfigMap injection
    }


@app.get("/health")
def health():
    """
    Used by both readiness and liveness probes.
    Must return HTTP 200 and a JSON body.
    """
    return {"status": "ok"}


@app.get("/items")
def list_items():
    return {"items": items_db}


@app.post("/items", response_model=ItemResponse, status_code=201)
def create_item(item: Item):
    counter["value"] += 1
    new_item = {"id": counter["value"], "name": item.name, "price": item.price}
    items_db.append(new_item)
    return new_item


@app.get("/items/{item_id}", response_model=ItemResponse)
def get_item(item_id: int):
    for item in items_db:
        if item["id"] == item_id:
            return item
    raise HTTPException(status_code=404, detail=f"Item {item_id} not found")


# =============================================================================
# KUBERNETES MANIFESTS
# Copy each block below into its own file in k8s/
# =============================================================================

CONFIGMAP_YAML = """
# k8s/configmap.yaml
# Non-sensitive configuration. Injected as env vars via envFrom.configMapRef.

apiVersion: v1
kind: ConfigMap
metadata:
  name: myapi-config
  labels:
    app: myapi
    environment: development
data:
  APP_ENV: "development"
  LOG_LEVEL: "info"
  WORKERS: "1"
"""

SECRET_YAML = """
# k8s/secret.yaml
# Sensitive values stored base64-encoded.
# To generate: echo -n "value" | base64
# In production use Sealed Secrets, Vault, or External Secrets Operator.

apiVersion: v1
kind: Secret
metadata:
  name: myapi-secret
  labels:
    app: myapi
type: Opaque
data:
  DB_USER: YXBwdXNlcg==         # echo -n "appuser"     | base64
  DB_PASSWORD: c3VwZXJzZWNyZXQ= # echo -n "supersecret" | base64
  DB_NAME: YXBwZGI=              # echo -n "appdb"       | base64
"""

DEPLOYMENT_YAML = """
# k8s/deployment.yaml

apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapi
  labels:
    app: myapi
spec:
  replicas: 3  # ← three pods means one crash doesn't take down the service

  selector:
    matchLabels:
      app: myapi  # ← must match spec.template.metadata.labels

  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1         # ← allow 1 extra pod during the update
      maxUnavailable: 0   # ← never reduce below desired count (zero-downtime)

  template:
    metadata:
      labels:
        app: myapi
        version: "1.0.0"
    spec:
      containers:
        - name: myapi
          image: YOUR_USERNAME/myapi:1.0.0  # ← replace with your Docker Hub username
          imagePullPolicy: Always

          ports:
            - containerPort: 8000
              name: http

          # Inject all keys from ConfigMap and Secret as environment variables
          envFrom:
            - configMapRef:
                name: myapi-config
            - secretRef:
                name: myapi-secret

          resources:
            requests:
              cpu: "100m"      # ← 100 millicores = 0.1 CPU core (scheduling minimum)
              memory: "128Mi"
            limits:
              cpu: "500m"      # ← throttled (not killed) if exceeded
              memory: "256Mi"  # ← OOMKilled if exceeded

          # Readiness — is the pod ready to receive traffic?
          # K8s removes the pod from Service endpoints until this passes.
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5   # ← wait before first check
            periodSeconds: 10
            failureThreshold: 3

          # Liveness — is the pod still functioning?
          # K8s restarts the container if this fails.
          # Higher delay than readiness to prevent restart loops on slow startup.
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 15
            periodSeconds: 20
            failureThreshold: 3

      terminationGracePeriodSeconds: 30  # ← give uvicorn time to finish in-flight requests
"""

SERVICE_YAML = """
# k8s/service.yaml
# Service provides a stable ClusterIP and DNS name for the Deployment.
# NodePort exposes it on every node at port 30080 for local access.

apiVersion: v1
kind: Service
metadata:
  name: myapi-svc
  labels:
    app: myapi
spec:
  selector:
    app: myapi  # ← targets all pods with this label

  type: NodePort  # ← use LoadBalancer in cloud environments, Ingress for HTTP routing

  ports:
    - name: http
      protocol: TCP
      port: 8000        # ← ClusterIP port (internal cluster access)
      targetPort: 8000  # ← pod container port
      nodePort: 30080   # ← static port on each node (must be 30000-32767)
"""
