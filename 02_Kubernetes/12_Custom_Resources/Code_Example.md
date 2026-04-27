# Custom Resources — Code Examples

All examples are production-quality with detailed comments explaining every decision.

---

## 1. Creating a CRD and Your First Custom Resource

```yaml
# widget-crd.yaml
# A CRD is a schema registration — it teaches K8s about a new resource type
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: widgets.example.com            # MUST be <plural>.<group> — this is enforced
spec:
  group: example.com                   # API group — appears in apiVersion field of CRs
  scope: Namespaced                    # or Cluster for cluster-scoped resources
  names:
    plural: widgets                    # kubectl get widgets
    singular: widget                   # kubectl get widget
    kind: Widget                       # Used in kind: field of the custom resource
    shortNames:
    - wgt                              # kubectl get wgt (short alias)
  versions:
  - name: v1
    served: true                       # This version accepts API requests
    storage: true                      # This version is stored in etcd (only one can be true)
    schema:
      openAPIV3Schema:                 # Validation schema — K8s rejects CRs that don't match
        type: object
        properties:
          spec:
            type: object
            required: ["replicas", "image"]   # These fields are mandatory
            properties:
              replicas:
                type: integer
                minimum: 1             # Must be at least 1
                maximum: 100           # Sanity cap
              image:
                type: string           # Container image for the widget
              color:
                type: string
                enum: ["red", "blue", "green"]   # Only these values allowed
          status:
            type: object               # Status is written by the operator, not users
            properties:
              phase:
                type: string
              readyReplicas:
                type: integer
    subresources:
      status: {}                       # Enables the /status subresource (operator writes status)
```

```bash
# Register the CRD with the API server (writes schema to etcd)
kubectl apply -f widget-crd.yaml

# Verify it's registered — K8s now knows about Widget resources
kubectl get crd widgets.example.com
kubectl describe crd widgets.example.com

# K8s created a new API endpoint for this resource type:
kubectl api-resources | grep widget
# widgets   wgt   example.com/v1   true   Widget
```

```yaml
# my-widget.yaml
# A Custom Resource — an instance of the Widget CRD
apiVersion: example.com/v1            # group/version from the CRD
kind: Widget                          # kind from the CRD
metadata:
  name: my-first-widget
  namespace: default
spec:
  replicas: 3                         # Validated against the CRD schema
  image: nginx:1.25
  color: blue                         # Must be red, blue, or green per CRD enum
```

```bash
kubectl apply -f my-widget.yaml

# Interact with it exactly like any built-in resource
kubectl get widgets
kubectl get wgt                        # Short name works
kubectl describe widget my-first-widget
kubectl get widget my-first-widget -o yaml

# Try creating an invalid widget — CRD schema validation blocks it
kubectl apply -f - <<EOF
apiVersion: example.com/v1
kind: Widget
metadata:
  name: bad-widget
spec:
  replicas: 0                          # Below minimum: 1 — will be rejected
  image: nginx:1.25
  color: purple                        # Not in enum [red, blue, green] — rejected
EOF
# Error: The Widget "bad-widget" is invalid: spec.replicas: Invalid value: 0: must be >= 1
```

---

## 2. Writing a Simple Operator (Python with kopf)

An operator is a controller that watches CRs and reconciles cluster state to match.

```python
# widget_operator.py
# A minimal operator using kopf (Python operator framework)
# Run with: kopf run widget_operator.py

import kopf
import kubernetes
import logging

# kopf calls this function every time a Widget CR is created
@kopf.on.create('widgets.example.com', 'v1', 'widgets')
def on_widget_create(spec, name, namespace, logger, **kwargs):
    """
    Reconcile function — called when a Widget is created.
    Our job: create a Deployment matching the Widget's spec.
    """
    replicas = spec.get('replicas', 1)   # Read desired state from the CR spec
    image = spec.get('image')

    # Build the Deployment that represents this Widget
    deployment_body = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": f"widget-{name}",    # Naming convention: widget-<cr-name>
            "namespace": namespace,
            "labels": {"managed-by": "widget-operator", "widget": name},
        },
        "spec": {
            "replicas": replicas,
            "selector": {"matchLabels": {"widget": name}},
            "template": {
                "metadata": {"labels": {"widget": name}},
                "spec": {
                    "containers": [{"name": "app", "image": image}]
                },
            },
        },
    }

    # Create the Deployment via the Kubernetes API
    api = kubernetes.client.AppsV1Api()
    api.create_namespaced_deployment(namespace=namespace, body=deployment_body)
    logger.info(f"Created Deployment for Widget {name} with {replicas} replicas")

    # Return data to write into the Widget's status subresource
    return {"phase": "Running", "readyReplicas": 0}


# kopf calls this when a Widget is updated
@kopf.on.update('widgets.example.com', 'v1', 'widgets')
def on_widget_update(spec, name, namespace, old, new, logger, **kwargs):
    """
    Handle spec changes — scale the Deployment if replicas changed.
    """
    new_replicas = new['spec'].get('replicas', 1)

    api = kubernetes.client.AppsV1Api()
    deployment = api.read_namespaced_deployment(name=f"widget-{name}", namespace=namespace)
    deployment.spec.replicas = new_replicas     # Update only what changed
    api.patch_namespaced_deployment(name=f"widget-{name}", namespace=namespace, body=deployment)
    logger.info(f"Scaled Widget {name} to {new_replicas} replicas")


# kopf calls this when a Widget is deleted
@kopf.on.delete('widgets.example.com', 'v1', 'widgets')
def on_widget_delete(name, namespace, logger, **kwargs):
    """
    Cleanup — delete the Deployment when the Widget CR is deleted.
    """
    api = kubernetes.client.AppsV1Api()
    api.delete_namespaced_deployment(name=f"widget-{name}", namespace=namespace)
    logger.info(f"Deleted Deployment for Widget {name}")
```

```bash
# Install kopf and run the operator locally (watches the cluster from your laptop)
pip install kopf kubernetes
kopf run widget_operator.py

# In another terminal — create a Widget and watch the operator react
kubectl apply -f my-widget.yaml
# Operator log: "Created Deployment for Widget my-first-widget with 3 replicas"

# Verify the Deployment was created by the operator
kubectl get deployment widget-my-first-widget

# Update replicas — operator reconciles
kubectl patch widget my-first-widget --type=merge -p '{"spec":{"replicas":5}}'
# Operator log: "Scaled Widget my-first-widget to 5 replicas"

kubectl get deployment widget-my-first-widget   # Should show 5 replicas
```

---

## 3. Real Operator: cert-manager CRDs in Practice

```bash
# Install cert-manager (installs its CRDs + operator)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.yaml

# Wait for cert-manager pods to be ready
kubectl rollout status deployment cert-manager -n cert-manager
kubectl rollout status deployment cert-manager-webhook -n cert-manager

# See what CRDs cert-manager added — these are now first-class K8s resources
kubectl get crds | grep cert-manager
# certificates.cert-manager.io
# certificaterequests.cert-manager.io
# clusterissuers.cert-manager.io
# issuers.cert-manager.io
# orders.acme.cert-manager.io
# challenges.acme.cert-manager.io
```

```yaml
# lets-encrypt-issuer.yaml
# ClusterIssuer is a cert-manager CRD — not a built-in K8s resource
apiVersion: cert-manager.io/v1
kind: ClusterIssuer                    # Custom resource defined by cert-manager's CRD
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com           # Notifications for certificate expiry
    privateKeySecretRef:
      name: letsencrypt-prod-key       # cert-manager creates this Secret automatically
    solvers:
    - http01:
      ingress:
        class: nginx                   # Use nginx ingress for the ACME HTTP-01 challenge
---
# certificate.yaml
# Certificate is another cert-manager CRD — cert-manager's operator watches these
apiVersion: cert-manager.io/v1
kind: Certificate                      # Custom resource: cert-manager will issue a real TLS cert
metadata:
  name: api-tls-cert
  namespace: production
spec:
  secretName: api-tls-secret           # cert-manager will create this Secret with the TLS cert
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer                # Reference to the ClusterIssuer we created above
  dnsNames:
  - api.example.com                    # cert-manager will issue a cert for this domain
```

```bash
kubectl apply -f lets-encrypt-issuer.yaml
kubectl apply -f certificate.yaml

# Watch cert-manager's operator reconcile the Certificate CR
kubectl describe certificate api-tls-cert -n production
# You'll see Events from cert-manager: "Issuing certificate" → "Certificate issued"

# The operator created a Secret with the actual TLS certificate
kubectl get secret api-tls-secret -n production
kubectl describe secret api-tls-secret -n production   # Shows tls.crt, tls.key data
```

---

## 4. CRD Versioning — Evolving Your API

```yaml
# widget-crd-v2.yaml
# Adding a new v2 version alongside v1 — backward compatible evolution
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: widgets.example.com
spec:
  group: example.com
  scope: Namespaced
  names:
    plural: widgets
    singular: widget
    kind: Widget
  versions:
  - name: v1
    served: true                       # v1 still accepts API requests
    storage: false                     # v1 is no longer the storage version
    schema:
      openAPIV3Schema:
        type: object
        properties:
          spec:
            type: object
            properties:
              replicas:
                type: integer
              image:
                type: string
  - name: v2
    served: true                       # v2 accepts API requests
    storage: true                      # v2 is now stored in etcd
    schema:
      openAPIV3Schema:
        type: object
        properties:
          spec:
            type: object
            properties:
              replicas:
                type: integer
              image:
                type: string
              color:
                type: string
              maxSurge:
                type: integer          # New field added in v2
                default: 1
```

```bash
kubectl apply -f widget-crd-v2.yaml

# Old v1 resources still work — K8s converts between versions automatically
kubectl get widget my-first-widget                   # Still accessible
kubectl get widget my-first-widget -o yaml           # Returned in v2 format

# Create a new v2 resource with the new fields
kubectl apply -f - <<EOF
apiVersion: example.com/v2
kind: Widget
metadata:
  name: new-v2-widget
spec:
  replicas: 2
  image: nginx:1.25
  color: green
  maxSurge: 2                          # New field only available in v2
EOF

# Deprecate v1 by setting served: false (users get errors if they use v1 apiVersion)
# Only do this after migrating all existing v1 resources to v2
```

---

## 📂 Navigation

**In this folder:**
| File | |
|---|---|
| [📖 Theory.md](./Theory.md) | Full explanation |
| [⚡ Cheatsheet.md](./Cheatsheet.md) | Quick reference |
| [🎯 Interview_QA.md](./Interview_QA.md) | Interview prep |
| 💻 **Code_Example.md** | ← you are here |

⬅️ **Prev:** [RBAC](../11_RBAC/Code_Example.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [DaemonSets and StatefulSets](../13_DaemonSets_and_StatefulSets/Code_Example.md)
🏠 **[Home](../../README.md)**
