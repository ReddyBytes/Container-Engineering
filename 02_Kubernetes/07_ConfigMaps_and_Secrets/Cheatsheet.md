# Module 07 — ConfigMaps and Secrets Cheatsheet

## ConfigMap Commands

```bash
# List configmaps
kubectl get configmaps
kubectl get cm              # short form

# Describe a configmap (shows keys and values)
kubectl describe cm my-config

# Get as YAML
kubectl get cm my-config -o yaml

# Create a configmap from literal values
kubectl create configmap my-config \
  --from-literal=LOG_LEVEL=info \
  --from-literal=DB_HOST=postgres

# Create from a file (key = filename, value = file content)
kubectl create configmap my-config --from-file=app.properties

# Create from a file with a custom key name
kubectl create configmap my-config --from-file=config=./app.properties

# Create from all files in a directory
kubectl create configmap my-config --from-file=./configs/

# Create from YAML
kubectl apply -f configmap.yaml

# Edit a configmap in place
kubectl edit configmap my-config

# Delete a configmap
kubectl delete configmap my-config

# Show just the data section
kubectl get cm my-config -o jsonpath='{.data}'
```

## Secret Commands

```bash
# List secrets
kubectl get secrets

# Describe a secret (shows keys but NOT values)
kubectl describe secret my-secret

# Get secret YAML (values are base64-encoded)
kubectl get secret my-secret -o yaml

# Decode a specific secret value
kubectl get secret my-secret -o jsonpath='{.data.PASSWORD}' | base64 -d
kubectl get secret my-secret -o jsonpath='{.data.PASSWORD}' | base64 --decode

# Create a generic (Opaque) secret from literal values
kubectl create secret generic db-creds \
  --from-literal=DB_PASSWORD=mysecretpassword \
  --from-literal=API_KEY=myapikey123

# Create a secret from a file
kubectl create secret generic app-certs \
  --from-file=tls.crt=./server.crt \
  --from-file=tls.key=./server.key

# Create a TLS secret (used by Ingress for HTTPS)
kubectl create secret tls my-tls \
  --cert=./tls.crt \
  --key=./tls.key

# Create a Docker registry secret (for pulling private images)
kubectl create secret docker-registry my-registry-cred \
  --docker-server=registry.example.com \
  --docker-username=myuser \
  --docker-password=mypassword \
  --docker-email=me@example.com

# Delete a secret
kubectl delete secret my-secret

# Edit a secret (opens editor with base64-encoded values)
kubectl edit secret my-secret
```

## Encoding/Decoding Secrets Manually

```bash
# Encode a value to base64 (for use in Secret YAML)
echo -n "mysecretpassword" | base64
# -n flag prevents newline from being encoded — IMPORTANT

# Decode a base64 value
echo "bXlzZWNyZXRwYXNzd29yZA==" | base64 -d

# Encode a file
base64 -w 0 ./server.crt   # -w 0 disables line wrapping
```

## Consuming ConfigMaps and Secrets in Pods

```yaml
# Pattern 1: individual env var from ConfigMap
env:
- name: LOG_LEVEL
  valueFrom:
    configMapKeyRef:
      name: app-config
      key: LOG_LEVEL

# Pattern 2: individual env var from Secret
env:
- name: DB_PASSWORD
  valueFrom:
    secretKeyRef:
      name: db-creds
      key: DB_PASSWORD

# Pattern 3: ALL keys from ConfigMap as env vars
envFrom:
- configMapRef:
    name: app-config

# Pattern 4: ALL keys from Secret as env vars
envFrom:
- secretRef:
    name: db-creds

# Pattern 5: ConfigMap as mounted files
volumes:
- name: config-vol
  configMap:
    name: app-config
containers:
- name: app
  volumeMounts:
  - name: config-vol
    mountPath: /etc/config

# Pattern 6: Single key from ConfigMap as a specific file
volumes:
- name: config-vol
  configMap:
    name: app-config
    items:
    - key: app.properties        # Only mount this key
      path: application.properties  # As this filename
```

## Troubleshooting

```bash
# Pod stuck in CreateContainerConfigError?
# Usually means ConfigMap or Secret referenced doesn't exist
kubectl describe pod <pod-name>  # Look at Events section

# Check if a ConfigMap or Secret exists
kubectl get cm my-config         # Expected: shows the CM
kubectl get secret my-secret     # Expected: shows the Secret

# Verify the key exists in the ConfigMap
kubectl get cm my-config -o jsonpath='{.data}'

# Check pod has correct env vars
kubectl exec <pod-name> -- env | grep MY_VAR

# Check mounted files
kubectl exec <pod-name> -- ls /etc/config
kubectl exec <pod-name> -- cat /etc/config/app.properties
```

---

## 📂 Navigation

| File | Description |
|------|-------------|
| [Theory.md](./Theory.md) | ConfigMaps and Secrets explained |
| [Cheatsheet.md](./Cheatsheet.md) | You are here — quick reference |
| [Interview_QA.md](./Interview_QA.md) | Interview questions and answers |
| [Code_Example.md](./Code_Example.md) | Working YAML examples |

**Previous:** [06_Services](../06_Services/Cheatsheet.md) |
**Next:** [08_Namespaces](../08_Namespaces/Theory.md)
