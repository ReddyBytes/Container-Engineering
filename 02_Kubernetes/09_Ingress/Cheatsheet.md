# Module 09 — Ingress Cheatsheet

## Installing nginx-ingress Controller

```bash
# Install nginx-ingress via Helm (recommended)
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.replicaCount=2

# Verify the controller is running
kubectl get pods -n ingress-nginx
kubectl get svc -n ingress-nginx      # Shows the external IP / LoadBalancer

# In minikube, enable the built-in addon instead
minikube addons enable ingress
kubectl get pods -n ingress-nginx
```

## Managing Ingress Resources

```bash
# List ingress resources
kubectl get ingress
kubectl get ing          # short form

# List across all namespaces
kubectl get ingress -A

# Detailed info (shows rules, backend services, TLS)
kubectl describe ingress my-ingress

# Get as YAML
kubectl get ingress my-ingress -o yaml

# Apply from file
kubectl apply -f ingress.yaml

# Delete
kubectl delete ingress my-ingress
```

## Testing Ingress

```bash
# Get the Ingress controller's external IP
kubectl get svc -n ingress-nginx ingress-nginx-controller
# Look at EXTERNAL-IP column

# Test with curl using Host header (when DNS isn't set up)
INGRESS_IP=$(kubectl get svc -n ingress-nginx ingress-nginx-controller \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

curl -H "Host: api.example.com" http://$INGRESS_IP/v1/health
curl -H "Host: www.example.com" http://$INGRESS_IP/

# For minikube
INGRESS_IP=$(minikube ip)
curl -H "Host: api.example.com" http://$INGRESS_IP/health

# Test HTTPS (with -k to ignore self-signed cert)
curl -k -H "Host: api.example.com" https://$INGRESS_IP/

# Add local hosts entry to test by hostname
echo "$INGRESS_IP api.example.com www.example.com" | sudo tee -a /etc/hosts
curl http://api.example.com/v1/health
```

## Creating TLS Secrets

```bash
# Create a TLS secret manually
kubectl create secret tls my-tls-secret \
  --cert=path/to/tls.crt \
  --key=path/to/tls.key

# Generate a self-signed cert for testing
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout tls.key -out tls.crt \
  -subj "/CN=*.example.com/O=my-company"

kubectl create secret tls example-tls \
  --cert=tls.crt \
  --key=tls.key

# Verify the TLS secret
kubectl describe secret example-tls
```

## cert-manager (Automated TLS)

```bash
# Install cert-manager via Helm
helm repo add jetstack https://charts.jetstack.io
helm repo update

helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set installCRDs=true

# Verify
kubectl get pods -n cert-manager

# Create a ClusterIssuer for Let's Encrypt (staging first, then prod)
kubectl apply -f - <<'EOF'
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF

# Check certificate status
kubectl get certificates -A
kubectl describe certificate my-cert

# Check certificate requests
kubectl get certificaterequests -A
```

## Common nginx-ingress Annotations Reference

```yaml
# Annotations go in Ingress metadata.annotations
metadata:
  annotations:
    # Redirect HTTP to HTTPS
    nginx.ingress.kubernetes.io/ssl-redirect: "true"

    # Strip path prefix before forwarding to backend
    nginx.ingress.kubernetes.io/rewrite-target: /$2

    # Increase body size for file uploads (default 1m)
    nginx.ingress.kubernetes.io/proxy-body-size: "100m"

    # Timeouts (in seconds)
    nginx.ingress.kubernetes.io/proxy-connect-timeout: "30"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "60"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "60"

    # Enable CORS
    nginx.ingress.kubernetes.io/enable-cors: "true"
    nginx.ingress.kubernetes.io/cors-allow-origin: "*"

    # IP allowlist
    nginx.ingress.kubernetes.io/whitelist-source-range: "10.0.0.0/8,192.168.0.0/16"

    # Basic auth
    nginx.ingress.kubernetes.io/auth-type: basic
    nginx.ingress.kubernetes.io/auth-secret: basic-auth-secret
    nginx.ingress.kubernetes.io/auth-realm: "Authentication Required"

    # Rate limiting
    nginx.ingress.kubernetes.io/limit-rps: "10"
```

## Troubleshooting Ingress

```bash
# Check if Ingress has an address assigned
kubectl get ingress my-ingress
# ADDRESS column should show an IP

# If no address: Ingress controller may not be running
kubectl get pods -n ingress-nginx

# Check Ingress controller logs for routing errors
kubectl logs -n ingress-nginx \
  -l app.kubernetes.io/name=ingress-nginx \
  --tail=100

# Check if backend service exists and has endpoints
kubectl get svc my-backend-service
kubectl get endpoints my-backend-service

# Test from inside the cluster (bypasses Ingress, tests service directly)
kubectl run test --image=curlimages/curl --rm -it --restart=Never -- \
  curl http://my-backend-service:8080/health
```

---

## Navigation

| File | Description |
|------|-------------|
| [Theory.md](./Theory.md) | Ingress explained |
| [Cheatsheet.md](./Cheatsheet.md) | You are here — quick reference |
| [Interview_QA.md](./Interview_QA.md) | Interview questions and answers |
| [Code_Example.md](./Code_Example.md) | Working YAML examples |

---

⬅️ **Prev:** [Namespaces](../08_Namespaces/Cheatsheet.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Persistent Volumes](../10_Persistent_Volumes/Theory.md)
