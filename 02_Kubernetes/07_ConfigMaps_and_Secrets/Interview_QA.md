# Module 07 — Interview Q&A: ConfigMaps and Secrets

---

**Q1: What is the difference between a ConfigMap and a Secret?**

Both store key-value configuration data that can be injected into pods. The differences:
- **ConfigMap**: designed for non-sensitive data (URLs, feature flags, config files, log levels).
  Values are stored as plain text.
- **Secret**: designed for sensitive data (passwords, tokens, TLS certificates). Values are
  stored as base64-encoded strings.

Functionally they are very similar, but Secrets have slightly stricter defaults (they can be
encrypted at rest, RBAC can differentiate between them, and `kubectl describe` doesn't show
Secret values). The main benefit is organizational — they signal intent and let you apply
different access controls.

---

**Q2: Is base64 encoding secure for Secrets?**

No. Base64 is an encoding scheme, not encryption. Anyone who can read the Secret object
via `kubectl get secret -o yaml` can decode the values with `base64 -d`. By default, Secrets
are stored unencrypted in etcd.

For real security:
- Enable **EncryptionConfiguration** in the API server to encrypt Secret data at rest in etcd
- Use **Sealed Secrets** (Bitnami) to encrypt secrets with a cluster key, safe for Git storage
- Use **External Secrets Operator** to fetch secrets from AWS Secrets Manager, HashiCorp Vault,
  or GCP Secret Manager at runtime — secret values never touch your Git repo

---

**Q3: What are the three ways to inject a ConfigMap into a pod?**

1. **Individual environment variable** (`env.valueFrom.configMapKeyRef`): map a specific key
   to a specific env var name in the container.
2. **envFrom** (`envFrom.configMapRef`): load ALL keys from the ConfigMap as environment
   variables in one declaration. The ConfigMap key becomes the env var name.
3. **Volume mount** (`volumes.configMap` + `volumeMounts`): mount the ConfigMap as a directory
   where each key becomes a file. The key name is the filename; the value is the file content.

All three work the same way for Secrets (using `secretKeyRef` and `secretRef`).

---

**Q4: What is the difference between environment variable injection and volume mount injection?**

The critical difference is **hot reload behavior**:

- **Environment variables** (methods 1 and 2) are set at pod startup. If you update the
  ConfigMap, running pods do NOT see the change. The pod must be restarted.
- **Volume mounts** (method 3) are updated automatically. When a ConfigMap is modified,
  Kubernetes updates the mounted files within ~1–2 minutes (via kubelet's sync loop).
  However, the application must be designed to re-read its config files — many frameworks
  support this (e.g., watching for file changes with inotify).

---

**Q5: What happens if a pod references a ConfigMap or Secret that doesn't exist?**

The pod fails to start and shows `CreateContainerConfigError` status. `kubectl describe pod`
will show an event like: "Error: configmap 'missing-config' not found".

You can make the reference optional using `optional: true`:
```yaml
envFrom:
- configMapRef:
    name: maybe-missing-config
    optional: true             # Pod starts even if this ConfigMap doesn't exist
```

---

**Q6: What is an imagePullSecret and how do you use it?**

An imagePullSecret is a Secret of type `kubernetes.io/dockerconfigjson` that contains
credentials for pulling container images from a private registry. Without it, pods fail with
`ImagePullBackOff` when trying to pull from private registries.

```yaml
# In pod spec:
spec:
  imagePullSecrets:
  - name: my-registry-secret   # Reference to the Docker config secret
  containers:
  - name: app
    image: registry.example.com/my-private-image:1.0
```

You can also attach an imagePullSecret to a ServiceAccount so all pods using that account
automatically get the pull credentials.

---

**Q7: What is an immutable ConfigMap and when should you use it?**

An immutable ConfigMap (or Secret) has `immutable: true` set. Once created, its data cannot
be changed — you must create a new object with a new name and update pod references.

Benefits:
- Prevents accidental modifications in production
- Performance improvement: Kubernetes stops watching immutable objects for changes, reducing
  API server load in clusters with many ConfigMaps
- Encourages versioned config objects (app-config-v2, app-config-v3) rather than mutating shared ones

---

**Q8: How do you rotate a Secret (update its value) without downtime?**

For secrets mounted as volumes: update the Secret; mounted files update automatically within
~1–2 minutes; the app must detect and apply the new value.

For secrets used as env vars: you must restart the pods. Rolling restart:
```bash
kubectl rollout restart deployment/my-app
```

For zero-downtime rotation of credentials:
1. Add the new credential alongside the old one in the Secret
2. Configure your app to try both (or use the new one)
3. Rolling restart pods to pick up the new env var
4. Remove the old credential once all pods are using the new one

---

**Q9: What is the `stringData` field in a Secret?**

`stringData` is a convenience field that lets you write plain text values in your Secret YAML.
Kubernetes automatically base64-encodes them before storing. It's write-only — you can't read
`stringData` back; it always appears under `data` in the stored object.

```yaml
stringData:
  PASSWORD: "mysecretpassword"   # Plain text — K8s encodes on write
```

is equivalent to:

```yaml
data:
  PASSWORD: bXlzZWNyZXRwYXNzd29yZA==  # Base64-encoded
```

---

**Q10: How do you prevent a Secret from being stored in Git?**

Several approaches:
1. **Never commit Secret YAML**: only commit ConfigMaps; store Secrets separately and apply
   manually or via CI with environment-specific credentials.
2. **Sealed Secrets**: commit `SealedSecret` objects (encrypted with cluster public key).
   Only the cluster can decrypt them. Safe to store in Git.
3. **External Secrets Operator**: commit `ExternalSecret` objects that describe *where* to
   find the secret (AWS Secrets Manager path, Vault path), not the value itself.
4. **SOPS** (Secrets OPerationS): encrypt secrets files with KMS or PGP before committing.

---

**Q11: What ConfigMap and Secret types exist for Secrets?**

Secret types signal how the Secret should be used and validate its keys:
- `Opaque`: generic — any key-value data (default)
- `kubernetes.io/tls`: TLS cert — requires `tls.crt` and `tls.key` keys
- `kubernetes.io/dockerconfigjson`: Docker registry auth — requires `.dockerconfigjson` key
- `kubernetes.io/service-account-token`: auto-created for ServiceAccounts
- `kubernetes.io/ssh-auth`: SSH private key — requires `ssh-privatekey` key
- `kubernetes.io/basic-auth`: username/password — requires `username` and `password` keys

---

**Q12: What is the maximum size of a ConfigMap or Secret?**

The maximum size is **1 MiB** per ConfigMap or Secret. This limit exists because etcd
stores all Kubernetes objects and is not designed for large data storage. If you need to
store large configuration files or binary data, consider using a PersistentVolume or
an object storage system (S3, GCS) and have your application fetch them at startup.

---

## 📂 Navigation

| File | Description |
|------|-------------|
| [Theory.md](./Theory.md) | ConfigMaps and Secrets explained |
| [Cheatsheet.md](./Cheatsheet.md) | Quick reference commands |
| [Interview_QA.md](./Interview_QA.md) | You are here — interview questions |
| [Code_Example.md](./Code_Example.md) | Working YAML examples |

---

⬅️ **Prev:** [RBAC](../06_RBAC_and_Security/Interview_QA.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Namespaces](../08_Namespaces/Theory.md)
