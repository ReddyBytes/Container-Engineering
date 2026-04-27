"""
starter.py — K8s Manifest Generator (Starter)
==============================================
This script generates Kubernetes YAML manifests for the E-Commerce API project
programmatically using Python f-strings, then writes them to a k8s/ directory.

How to run:
    python src/starter.py

TODOs are marked with # TODO — fill these in before running.
"""

import os
import base64

# ---------------------------------------------------------------------------
# Configuration — fill these in
# ---------------------------------------------------------------------------

# TODO: Set your Docker image name and tag (e.g. "ecommerce-api:1.0.0")
IMAGE_NAME = "ecommerce-api"
IMAGE_TAG = "1.0.0"

# TODO: Set the number of API replicas to run
REPLICA_COUNT = 3

# TODO: Set resource requests and limits for the API container
APP_CPU_REQUEST = "100m"
APP_CPU_LIMIT = "500m"
APP_MEM_REQUEST = "128Mi"
APP_MEM_LIMIT = "512Mi"

# TODO: Set resource requests and limits for the PostgreSQL container
PG_CPU_REQUEST = "250m"
PG_CPU_LIMIT = "500m"
PG_MEM_REQUEST = "256Mi"
PG_MEM_LIMIT = "512Mi"

# TODO: Set the PVC storage size for PostgreSQL
PG_STORAGE = "5Gi"

# TODO: Set the external hostname for the Ingress rule
INGRESS_HOST = "shop.local"

# TODO: Set the HPA min and max replicas
HPA_MIN = 2
HPA_MAX = 10
HPA_CPU_TARGET = 50  # percent average utilisation

# Credentials — base64 encode them
POSTGRES_PASSWORD_PLAIN = "changeme"   # TODO: change before use
JWT_SECRET_PLAIN = "changejwtsecret"   # TODO: change before use

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
        f.write(content)
    print(f"  wrote {path}")


# ---------------------------------------------------------------------------
# Manifest generators — complete these
# ---------------------------------------------------------------------------

def namespace_yaml() -> str:
    # TODO: Return a YAML string for a Namespace named "ecommerce"
    return ""


def configmap_yaml() -> str:
    # TODO: Return a YAML string for a ConfigMap named "ecommerce-config" in
    #       namespace "ecommerce". Include keys:
    #       POSTGRES_DB, POSTGRES_USER, POSTGRES_HOST, POSTGRES_PORT, APP_ENV, LOG_LEVEL
    return ""


def secret_yaml() -> str:
    # TODO: Return a YAML string for an Opaque Secret named "ecommerce-secret"
    #       with base64-encoded POSTGRES_PASSWORD and SECRET_KEY.
    #       Use the b64() helper above.
    return ""


def postgres_pvc_yaml() -> str:
    # TODO: Return a YAML string for a PersistentVolumeClaim named "postgres-pvc"
    #       in namespace "ecommerce". Access mode: ReadWriteOnce, storage: PG_STORAGE
    return ""


def postgres_deployment_yaml() -> str:
    # TODO: Return a YAML string for a Deployment named "postgres" in namespace
    #       "ecommerce". Use image postgres:15-alpine, 1 replica, mount the PVC
    #       at /var/lib/postgresql/data, inject env from ConfigMap and Secret.
    return ""


def postgres_service_yaml() -> str:
    # TODO: Return a YAML string for a ClusterIP Service named "postgres-service"
    #       in namespace "ecommerce". Port 5432 → targetPort 5432.
    return ""


def app_deployment_yaml() -> str:
    # TODO: Return a YAML string for the ecommerce-api Deployment.
    #       Use IMAGE_NAME:IMAGE_TAG, REPLICA_COUNT replicas,
    #       imagePullPolicy: Never, inject all env from ConfigMap + Secret,
    #       add readinessProbe and livenessProbe on /health:8000,
    #       set resource requests/limits from APP_* constants above,
    #       and a RollingUpdate strategy with maxSurge:1, maxUnavailable:0.
    return ""


def app_service_yaml() -> str:
    # TODO: Return a YAML string for a ClusterIP Service named "app-service"
    #       in namespace "ecommerce". Port 80 → targetPort 8000.
    return ""


def ingress_yaml() -> str:
    # TODO: Return a YAML string for an Ingress named "ecommerce-ingress"
    #       in namespace "ecommerce". Host: INGRESS_HOST, path /api(/|$)(.*),
    #       rewrite-target annotation, backend: app-service:80.
    return ""


def hpa_yaml() -> str:
    # TODO: Return a YAML string for a HorizontalPodAutoscaler named
    #       "ecommerce-api-hpa" targeting the ecommerce-api Deployment.
    #       Use HPA_MIN, HPA_MAX, HPA_CPU_TARGET.
    return ""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    output_dir = "k8s"
    print(f"Generating manifests into {output_dir}/")

    manifests = {
        "namespace.yaml": namespace_yaml(),
        "configmap.yaml": configmap_yaml(),
        "secret.yaml": secret_yaml(),
        "postgres-pvc.yaml": postgres_pvc_yaml(),
        "postgres-deployment.yaml": postgres_deployment_yaml(),
        "postgres-service.yaml": postgres_service_yaml(),
        "app-deployment.yaml": app_deployment_yaml(),
        "app-service.yaml": app_service_yaml(),
        "ingress.yaml": ingress_yaml(),
        "hpa.yaml": hpa_yaml(),
    }

    for filename, content in manifests.items():
        if content.strip():
            write_file(output_dir, filename, content)
        else:
            print(f"  skipped {filename} (not yet implemented)")

    print("\nDone. Apply with: kubectl apply -f k8s/")


if __name__ == "__main__":
    main()
