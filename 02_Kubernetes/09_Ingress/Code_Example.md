# Module 09 — Code Examples: Ingress

## Example 1: Install nginx-ingress via Helm

```bash
# Add the ingress-nginx Helm repository
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

# Install the nginx Ingress controller
# Creates a LoadBalancer service in the ingress-nginx namespace
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.replicaCount=2 \
  --set controller.nodeSelector."kubernetes\.io/os"=linux

# Verify the controller is running
kubectl get pods -n ingress-nginx
# NAME                                       READY   STATUS    RESTARTS   AGE
# ingress-nginx-controller-7d4b9c8f5-abc12   1/1     Running   0          60s
# ingress-nginx-controller-7d4b9c8f5-xyz34   1/1     Running   0          60s

# Get the Ingress controller's external IP
kubectl get svc -n ingress-nginx ingress-nginx-controller
# NAME                       TYPE           CLUSTER-IP     EXTERNAL-IP    PORT(S)
# ingress-nginx-controller   LoadBalancer   10.96.100.50   34.120.50.100  80:31080/TCP,443:31443/TCP

# In minikube: use the built-in addon instead
minikube addons enable ingress
```

---

## Example 2: Backend and Frontend Deployments + Services

```yaml
# apps.yaml
# Two applications we'll route to via Ingress
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-backend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
      - name: api
        image: hashicorp/http-echo:latest
        args: ["-text=Hello from API service!"]
        ports:
        - containerPort: 5678
---
apiVersion: v1
kind: Service
metadata:
  name: api-service
spec:
  selector:
    app: api
  ports:
  - port: 80
    targetPort: 5678
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: frontend
        image: hashicorp/http-echo:latest
        args: ["-text=Hello from Frontend!"]
        ports:
        - containerPort: 5678
---
apiVersion: v1
kind: Service
metadata:
  name: frontend-service
spec:
  selector:
    app: frontend
  ports:
  - port: 80
    targetPort: 5678
```

---

## Example 3: Path-Based Routing Ingress

```yaml
# path-based-ingress.yaml
# /api/* → api-service
# / → frontend-service
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: path-routing
  annotations:
    # Strip /api prefix before forwarding to backend
    # (/|$)(.*) captures the rest of the path; $2 is forwarded
    nginx.ingress.kubernetes.io/rewrite-target: /$2
    nginx.ingress.kubernetes.io/use-regex: "true"
spec:
  ingressClassName: nginx                # Which Ingress controller handles this

  rules:
  - host: app.example.com               # Set this in /etc/hosts for local testing
    http:
      paths:
      - path: /api(/|$)(.*)             # Regex: matches /api and /api/anything
        pathType: ImplementationSpecific # Needed for regex paths
        backend:
          service:
            name: api-service
            port:
              number: 80

      - path: /(.*)                     # Catch-all for all other paths
        pathType: ImplementationSpecific
        backend:
          service:
            name: frontend-service
            port:
              number: 80
```

```bash
kubectl apply -f apps.yaml
kubectl apply -f path-based-ingress.yaml

# Get the ingress controller IP
INGRESS_IP=$(minikube ip)  # or kubectl get svc -n ingress-nginx...

# Test path-based routing
curl -H "Host: app.example.com" http://$INGRESS_IP/        # → Frontend
curl -H "Host: app.example.com" http://$INGRESS_IP/api     # → API
curl -H "Host: app.example.com" http://$INGRESS_IP/api/v1  # → API (prefix stripped)
```

---

## Example 4: Host-Based Routing Ingress

```yaml
# host-based-ingress.yaml
# api.example.com → api-service
# www.example.com → frontend-service
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: host-routing
spec:
  ingressClassName: nginx

  rules:
  # First hostname
  - host: api.example.com               # All requests to this hostname
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80

  # Second hostname
  - host: www.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
```

```bash
kubectl apply -f host-based-ingress.yaml

INGRESS_IP=$(minikube ip)

# Test host-based routing with different Host headers
curl -H "Host: api.example.com" http://$INGRESS_IP/   # → API
curl -H "Host: www.example.com" http://$INGRESS_IP/   # → Frontend

# Or add to /etc/hosts and use real URLs
echo "$INGRESS_IP api.example.com www.example.com" | sudo tee -a /etc/hosts
curl http://api.example.com/
curl http://www.example.com/
```

---

## Example 5: TLS with Self-Signed Certificate

```bash
# Generate a self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout tls.key \
  -out tls.crt \
  -subj "/CN=app.example.com/O=example"

# Create the TLS secret in Kubernetes
kubectl create secret tls app-tls-secret \
  --cert=tls.crt \
  --key=tls.key
```

```yaml
# tls-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tls-ingress
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"    # Force HTTP → HTTPS redirect
spec:
  ingressClassName: nginx

  tls:
  - hosts:
    - app.example.com                   # Must match the certificate's CN or SAN
    secretName: app-tls-secret          # The TLS secret we created above

  rules:
  - host: app.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80
```

```bash
kubectl apply -f tls-ingress.yaml

INGRESS_IP=$(minikube ip)

# Test HTTPS (use -k to ignore self-signed cert warning)
curl -k -H "Host: app.example.com" https://$INGRESS_IP/
curl -k -H "Host: app.example.com" https://$INGRESS_IP/api

# Test that HTTP redirects to HTTPS
curl -v -H "Host: app.example.com" http://$INGRESS_IP/
# Should see: 308 Permanent Redirect to https://...
```

---

## Example 6: TLS with cert-manager (Automatic Certificates)

```bash
# Install cert-manager first
helm repo add jetstack https://charts.jetstack.io && helm repo update

helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set installCRDs=true
```

```yaml
# letsencrypt-issuer.yaml
# ClusterIssuer — works across all namespaces
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com            # Receives cert expiry notifications
    privateKeySecretRef:
      name: letsencrypt-prod            # Where to store the ACME account key
    solvers:
    - http01:
        ingress:
          class: nginx                  # Use nginx to handle HTTP-01 challenges
---
# auto-tls-ingress.yaml
# cert-manager sees the annotation and creates the certificate automatically
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: auto-tls-ingress
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod   # Magic annotation
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: nginx

  tls:
  - hosts:
    - api.yourdomain.com               # Must be a real public domain for Let's Encrypt
    secretName: api-yourdomain-tls     # cert-manager creates this Secret automatically

  rules:
  - host: api.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80
```

```bash
kubectl apply -f letsencrypt-issuer.yaml
kubectl apply -f auto-tls-ingress.yaml

# Watch cert-manager create the certificate
kubectl get certificate -w
# api-yourdomain-tls   False   False   1m    (requesting...)
# api-yourdomain-tls   True    True    3m    (issued!)

# Check certificate details
kubectl describe certificate api-yourdomain-tls
```

---

## Navigation

| File | Description |
|------|-------------|
| [Theory.md](./Theory.md) | Ingress explained |
| [Cheatsheet.md](./Cheatsheet.md) | Quick reference commands |
| [Interview_QA.md](./Interview_QA.md) | Interview questions and answers |
| [Code_Example.md](./Code_Example.md) | You are here — working YAML examples |

**Previous:** [08_Namespaces](../08_Namespaces/Theory.md) |
**Next:** [10_Persistent_Volumes](../10_Persistent_Volumes/Theory.md)
