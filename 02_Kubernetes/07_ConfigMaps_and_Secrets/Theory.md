# Module 07 — ConfigMaps and Secrets

## Separate Config from Code

The Twelve-Factor App methodology has a rule: "Store config in the environment." The reason is
simple: your container image is immutable (it's the same binary in dev, staging, and prod), but
the *configuration* of that app changes between environments — database URLs, feature flags,
API keys, log levels.

If you bake the configuration into the image, you need a different image for each environment.
That defeats the purpose of containers. Instead, you inject configuration at runtime.

Kubernetes provides two objects for this:
- **ConfigMap**: for non-sensitive configuration (URLs, hostnames, feature flags, log levels)
- **Secret**: for sensitive data (passwords, API keys, TLS certificates, tokens)

> **🐳 Coming from Docker?**
>
> In Docker, you pass config via `-e DATABASE_URL=postgres://...` or `--env-file .env`. That works for one container on one machine. In Kubernetes, ConfigMaps and Secrets let you define config once and inject it into dozens of pods across multiple nodes — without touching the pod spec. You can update a ConfigMap and have pods pick up the new value without redeployment. Secrets are the same idea, but Kubernetes keeps them base64-encoded and you can integrate with external vaults for proper encryption at rest.

---

## 📌 Learning Priority

**Must Learn** — core concepts, needed to understand the rest of this file:
[ConfigMap Basics](#configmap-non-sensitive-configuration) · [Secret Basics](#secret-sensitive-data) · [Consumption Methods](#three-ways-to-consume-configmaps-and-secrets)

**Should Learn** — important for real projects and interviews:
[Config Injection Flows](#config-injection-flows) · [Secret Types](#secret-types)

**Good to Know** — useful in specific situations, not needed daily:
[Real Encryption](#real-encryption-sealed-secrets-and-external-secrets) · [Immutable ConfigMaps](#immutable-configmaps-and-secrets)

**Reference** — skim once, look up when needed:
[envFrom Warning](#method-2-envfrom-all-keys-at-once)

---

## ConfigMap: Non-Sensitive Configuration

A ConfigMap stores key-value pairs. Keys are string names; values can be simple strings or
multi-line content (like an entire config file).

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  # Simple key-value pairs
  DATABASE_HOST: "postgres.production.svc.cluster.local"
  DATABASE_PORT: "5432"
  LOG_LEVEL: "info"
  CACHE_TTL: "300"
  FEATURE_NEW_DASHBOARD: "true"

  # Multi-line value (entire file content)
  app.properties: |
    server.port=8080
    spring.datasource.url=jdbc:postgresql://postgres:5432/mydb
    logging.level.root=INFO
    cache.ttl.seconds=300

  nginx.conf: |
    server {
      listen 80;
      location / {
        proxy_pass http://backend:8080;
      }
    }
```

---

## Secret: Sensitive Data

A Secret looks identical to a ConfigMap in structure, but values are **base64-encoded** by default.

**IMPORTANT**: base64 is NOT encryption. It's just encoding. Anyone who can read the Secret
object (via `kubectl get secret`) can decode the values trivially. Secrets provide:
1. A logical separation between config and credentials (so devs know where sensitive data lives)
2. Controlled RBAC access (you can give a service account access to read pods but not secrets)
3. Optional encryption at rest (if enabled via EncryptionConfiguration in the API server)

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
type: Opaque                               # Generic key-value secret

data:
  # Values MUST be base64-encoded in YAML
  # echo -n "mysecretpassword" | base64 → bXlzZWNyZXRwYXNzd29yZA==
  DB_PASSWORD: bXlzZWNyZXRwYXNzd29yZA==
  API_KEY: c2VjcmV0LWFwaS1rZXktMTIz

stringData:                                # Alternative: write plain text, K8s encodes it
  ANOTHER_KEY: "plain-text-value"          # More readable, K8s will base64-encode this
```

```bash
# Create a secret from literal values (base64 encoding is automatic)
kubectl create secret generic db-creds \
  --from-literal=DB_PASSWORD=mysecretpassword \
  --from-literal=API_KEY=myapikey123

# Create a secret from a file (e.g., TLS certificate)
kubectl create secret generic tls-certs \
  --from-file=tls.crt=./server.crt \
  --from-file=tls.key=./server.key

# Create a TLS secret (special type for HTTPS)
kubectl create secret tls my-tls-secret \
  --cert=./server.crt \
  --key=./server.key

# Decode a secret to see its value
kubectl get secret db-creds -o jsonpath='{.data.DB_PASSWORD}' | base64 -d
```

---

## Three Ways to Consume ConfigMaps and Secrets

### Method 1: Individual Environment Variables

```yaml
env:
- name: DB_HOST
  valueFrom:
    configMapKeyRef:
      name: app-config
      key: DATABASE_HOST
- name: DB_PASSWORD
  valueFrom:
    secretKeyRef:
      name: db-credentials
      key: DB_PASSWORD
```

Use when: you want specific keys, need to rename them, or want to be explicit.

### Method 2: envFrom (All Keys at Once)

```yaml
envFrom:
- configMapRef:
    name: app-config          # ALL keys become env vars
- secretRef:
    name: db-credentials      # ALL secret keys become env vars too
```

Use when: you have many keys and want all of them, with the same names.

**Warning**: if ConfigMap and Secret have overlapping key names, the later one wins. Also,
if a ConfigMap changes (is updated), pods do NOT see the new values until they restart.
Env vars are baked in at pod startup.

### Method 3: Volume Mount (Config Files)

```yaml
volumes:
- name: config-files
  configMap:
    name: app-config           # Mount ConfigMap as a directory of files

containers:
- name: app
  volumeMounts:
  - name: config-files
    mountPath: /etc/app-config  # Each key becomes a file at this path
```

The file `/etc/app-config/DATABASE_HOST` contains the value of the `DATABASE_HOST` key.
The file `/etc/app-config/app.properties` contains the multi-line properties file.

**Hot Reload**: when the ConfigMap is updated, the mounted files are automatically updated
within ~1–2 minutes. The application must re-read the files on its own (inotify watchers or
periodic config reload). Environment variables (methods 1 and 2) do NOT update — pod must restart.

---

## Config Injection Flows

```mermaid
graph TB
    subgraph "Configuration Sources"
        CM[ConfigMap<br/>app-config]
        SEC[Secret<br/>db-credentials]
    end

    subgraph "Consumption Methods"
        ENV1[env.valueFrom<br/>individual keys]
        ENV2[envFrom<br/>all keys at once]
        VOL[Volume Mount<br/>files on disk]
    end

    subgraph "Pod"
        APP[Application Container]
        FS[/etc/config/<br/>mounted files]
        ENVVARS[Environment Variables<br/>in process]
    end

    CM --> ENV1
    CM --> ENV2
    CM --> VOL
    SEC --> ENV1
    SEC --> ENV2
    SEC --> VOL

    ENV1 --> ENVVARS
    ENV2 --> ENVVARS
    VOL --> FS

    ENVVARS --> APP
    FS --> APP

    note1["Env vars: set at pod start,<br/>do NOT update on ConfigMap change"]
    note2["Volume files: update automatically<br/>within ~1-2 minutes"]
```

---

## Real Encryption: Sealed Secrets and External Secrets

For production, base64-encoded Secrets in Git are a security risk. Two popular solutions:

### Sealed Secrets (Bitnami)
Encrypt Kubernetes Secrets with a cluster-specific public key. Encrypted SealedSecret objects
can be safely stored in Git. The Sealed Secrets controller running in the cluster decrypts them.

```bash
# Install sealed-secrets controller (via Helm)
helm install sealed-secrets \
  oci://registry-1.docker.io/bitnamicharts/sealed-secrets \
  -n kube-system

# Seal a secret
kubeseal < secret.yaml > sealed-secret.yaml
# sealed-secret.yaml is safe to commit to Git
```

### External Secrets Operator
Fetches secrets from external secret managers (AWS Secrets Manager, HashiCorp Vault, GCP
Secret Manager, Azure Key Vault) and creates Kubernetes Secrets automatically. The actual
secret values never touch your Git repo.

---

## Immutable ConfigMaps and Secrets

Setting `immutable: true` prevents modifications after creation. Benefits:
- Protects against accidental changes
- Kubernetes stops watching immutable objects (performance improvement with many objects)
- To update, you create a new ConfigMap with a new name and update pod references

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config-v2
immutable: true         # Cannot be changed; must create new ConfigMap to update
data:
  LOG_LEVEL: "debug"
```

---

## Secret Types

| Type | Used For |
|------|---------|
| `Opaque` | Generic key-value secrets (default) |
| `kubernetes.io/tls` | TLS certificates (tls.crt and tls.key keys) |
| `kubernetes.io/dockerconfigjson` | Image pull credentials for private registries |
| `kubernetes.io/service-account-token` | Service account tokens (auto-created) |
| `kubernetes.io/ssh-auth` | SSH private keys |
| `kubernetes.io/basic-auth` | Username/password pairs |


---

## 📝 Practice Questions

- 📝 [Q18 · configmaps](../kubernetes_practice_questions_100.md#q18--normal--configmaps)
- 📝 [Q19 · secrets](../kubernetes_practice_questions_100.md#q19--normal--secrets)
- 📝 [Q20 · env-from-config](../kubernetes_practice_questions_100.md#q20--debug--env-from-config)
- 📝 [Q79 · compare-configmap-secret](../kubernetes_practice_questions_100.md#q79--interview--compare-configmap-secret)
- 📝 [Q88 · scenario-secret-rotation](../kubernetes_practice_questions_100.md#q88--design--scenario-secret-rotation)


---

## 📂 Navigation

| File | Description |
|------|-------------|
| [Theory.md](./Theory.md) | You are here — ConfigMaps and Secrets |
| [Cheatsheet.md](./Cheatsheet.md) | Quick reference commands |
| [Interview_QA.md](./Interview_QA.md) | Interview questions and answers |
| [Code_Example.md](./Code_Example.md) | Working YAML examples |

**Previous:** [06_Services](../06_Services/Theory.md) |
**Next:** [08_Namespaces](../08_Namespaces/Theory.md)
