# Module 10 — Code Examples: Persistent Volumes

## Example 1: Manual PV + PVC (Static Provisioning)

```yaml
# manual-pv.yaml
# Admin creates this ahead of time — the actual storage resource
apiVersion: v1
kind: PersistentVolume
metadata:
  name: local-pv-001                       # Name of the PV (cluster-scoped, not namespaced)
  labels:
    type: local                             # Labels for PVC selector matching
spec:
  capacity:
    storage: 5Gi                           # Total storage this PV provides
  accessModes:
  - ReadWriteOnce                          # One node can mount read+write
  reclaimPolicy: Retain                    # Data survives PVC deletion (admin must clean up)
  storageClassName: manual                 # Must match PVC's storageClassName
  hostPath:                                # For local testing only — not for production
    path: /mnt/data/pv001                  # Actual path on the node
    type: DirectoryOrCreate                # Create the directory if it doesn't exist
---
# manual-pvc.yaml
# Developer creates this — requesting storage from the cluster
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: my-app-data                        # PVC name (namespaced)
  namespace: default
spec:
  accessModes:
  - ReadWriteOnce                          # Must match PV's access modes
  resources:
    requests:
      storage: 3Gi                         # Request 3Gi — PV must have at least this
  storageClassName: manual                 # Must match PV's storageClassName
  selector:                                # Optional: further filter PVs by labels
    matchLabels:
      type: local
```

```bash
kubectl apply -f manual-pv.yaml
kubectl apply -f manual-pvc.yaml

# Check the PV is Available
kubectl get pv
# NAME           CAPACITY   ACCESS MODES   RECLAIM POLICY   STATUS      STORAGECLASS
# local-pv-001   5Gi        RWO            Retain           Available   manual

# Check the PVC is Bound
kubectl get pvc
# NAME          STATUS   VOLUME         CAPACITY   ACCESS MODES   STORAGECLASS
# my-app-data   Bound    local-pv-001   5Gi        RWO            manual

# Once bound, the PV shows as Bound
kubectl get pv
# local-pv-001   5Gi   RWO   Retain   Bound   default/my-app-data   manual
```

---

## Example 2: StorageClass with Dynamic Provisioning

```yaml
# storageclass-ssd.yaml
# Define a storage class — cloud admin creates this once
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
  annotations:
    storageclass.kubernetes.io/is-default-class: "false"  # Not the default
provisioner: ebs.csi.aws.com                # AWS EBS CSI driver (install separately)
parameters:
  type: gp3                                 # AWS EBS volume type
  iops: "3000"                              # Provisioned IOPS
  throughput: "125"                         # MB/s throughput
  encrypted: "true"                         # Encrypt the volume
reclaimPolicy: Delete                       # Delete EBS volume when PVC is deleted
volumeBindingMode: WaitForFirstConsumer     # Wait until pod is scheduled (zone-aware)
allowVolumeExpansion: true                  # Allow PVC to be resized later
---
# dynamic-pvc.yaml
# Developer creates a PVC — storage is created automatically by the StorageClass
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: database-storage
  namespace: production
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: fast-ssd               # Reference the StorageClass
  resources:
    requests:
      storage: 20Gi                        # EBS volume will be 20Gi
```

```bash
kubectl apply -f storageclass-ssd.yaml
kubectl apply -f dynamic-pvc.yaml

# PVC starts Pending (WaitForFirstConsumer mode — waiting for pod)
kubectl get pvc -n production
# NAME               STATUS    VOLUME  CAPACITY  STORAGECLASS
# database-storage   Pending                     fast-ssd

# Once a pod using this PVC is scheduled, the EBS volume is created and PVC binds
kubectl get pvc -n production
# database-storage   Bound   pvc-abc123   20Gi   RWO   fast-ssd

# For minikube testing (uses standard storage class, not EBS)
# Change storageClassName to "standard" (minikube's built-in StorageClass)
kubectl get storageclass  # shows available classes
```

---

## Example 3: Pod Using a PVC

```yaml
# app-with-storage.yaml
# A pod that reads and writes to persistent storage
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: app-data-pvc
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
  storageClassName: standard               # Use minikube's default StorageClass
---
apiVersion: v1
kind: Pod
metadata:
  name: data-writer
spec:
  containers:
  - name: writer
    image: busybox:1.36
    command: ["/bin/sh", "-c"]
    args:
    - |
      echo "Writing data..."
      echo "Hello from pod at $(date)" >> /data/log.txt
      echo "Pod name: $POD_NAME" >> /data/log.txt
      cat /data/log.txt
      sleep 3600
    env:
    - name: POD_NAME
      valueFrom:
        fieldRef:
          fieldPath: metadata.name        # Inject the pod's own name
    volumeMounts:
    - name: app-storage                    # Must match volumes[].name below
      mountPath: /data                     # Where to mount inside the container
  volumes:
  - name: app-storage
    persistentVolumeClaim:
      claimName: app-data-pvc             # Reference the PVC by name
```

```bash
kubectl apply -f app-with-storage.yaml

# Verify the pod is running and PVC is bound
kubectl get pod data-writer
kubectl get pvc app-data-pvc

# Check what was written
kubectl exec data-writer -- cat /data/log.txt

# Delete the pod and recreate it — the data persists!
kubectl delete pod data-writer
kubectl apply -f app-with-storage.yaml   # reapply just the pod part

kubectl exec data-writer -- cat /data/log.txt
# Should show BOTH the old entry AND a new entry — data survived pod deletion
```

---

## Example 4: PostgreSQL StatefulSet with PVC Template

```yaml
# postgres-statefulset.yaml
# StatefulSet with automatically created PVCs for each replica
apiVersion: v1
kind: Service
metadata:
  name: postgres                           # Headless service for StatefulSet DNS
spec:
  clusterIP: None                          # Headless: direct pod DNS names
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
spec:
  serviceName: postgres                    # MUST match the headless service name
  replicas: 1                              # Start with 1 replica (primary)
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
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_USER
          value: "myuser"
        - name: POSTGRES_PASSWORD
          value: "mypassword"              # Use a Secret in production!
        - name: POSTGRES_DB
          value: "mydb"
        - name: PGDATA
          value: /var/lib/postgresql/data/pgdata  # Data directory inside mount
        volumeMounts:
        - name: postgres-data              # Must match volumeClaimTemplates[].metadata.name
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        readinessProbe:
          exec:
            command: ["pg_isready", "-U", "myuser", "-d", "mydb"]
          initialDelaySeconds: 10
          periodSeconds: 5

  # volumeClaimTemplates: creates a unique PVC for each pod replica
  # postgres-data-postgres-0, postgres-data-postgres-1, etc.
  volumeClaimTemplates:
  - metadata:
      name: postgres-data                  # PVC name prefix
    spec:
      accessModes:
      - ReadWriteOnce                      # One pod at a time (correct for Postgres)
      storageClassName: standard           # Use your cluster's StorageClass
      resources:
        requests:
          storage: 10Gi                    # Each pod gets its own 10Gi volume
```

```bash
kubectl apply -f postgres-statefulset.yaml

# Watch the StatefulSet create pods and PVCs
kubectl get pods --watch
# NAME         READY   STATUS    RESTARTS   AGE
# postgres-0   0/1     Pending   0          5s
# postgres-0   0/1     ContainerCreating   0   10s
# postgres-0   1/1     Running   0          20s

# Check PVCs were created (one per pod)
kubectl get pvc
# NAME                     STATUS   VOLUME         CAPACITY   STORAGECLASS
# postgres-data-postgres-0 Bound    pvc-abc12345   10Gi       standard

# Connect to Postgres and create a table
kubectl exec -it postgres-0 -- psql -U myuser -d mydb -c "
  CREATE TABLE users (id SERIAL PRIMARY KEY, name TEXT);
  INSERT INTO users (name) VALUES ('Alice'), ('Bob');
  SELECT * FROM users;
"

# Delete the pod (simulates crash/restart)
kubectl delete pod postgres-0

# Watch it restart
kubectl get pods --watch

# After restart, verify data is still there
kubectl exec -it postgres-0 -- psql -U myuser -d mydb -c "SELECT * FROM users;"
# Should show Alice and Bob — data persisted through pod deletion!
```

---

## Example 5: Volume Expansion

```yaml
# First, make sure the StorageClass allows expansion:
# storageClassName.allowVolumeExpansion: true

# Current PVC requesting 10Gi:
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: growing-pvc
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: standard
  resources:
    requests:
      storage: 10Gi
```

```bash
kubectl apply -f growing-pvc.yaml

# Check current size
kubectl get pvc growing-pvc
# NAME         STATUS   VOLUME    CAPACITY   ACCESS MODES   STORAGECLASS
# growing-pvc  Bound    pvc-xyz   10Gi       RWO            standard

# Expand to 20Gi (patch the PVC)
kubectl patch pvc growing-pvc \
  -p '{"spec":{"resources":{"requests":{"storage":"20Gi"}}}}'

# Watch the resize progress
kubectl describe pvc growing-pvc
# Conditions:
#   Type: Resizing   Status: True   (in progress)
#   Type: FileSystemResizePending (filesystem resize needed after pod restart)

# After resize completes
kubectl get pvc growing-pvc
# CAPACITY is now 20Gi

# NOTE: you can only increase, never decrease the size
# NOTE: if the pod needs a restart to see new filesystem size, rolling restart works:
kubectl rollout restart statefulset/postgres
```

---

## Navigation

| File | Description |
|------|-------------|
| [Theory.md](./Theory.md) | Persistent Volumes explained |
| [Cheatsheet.md](./Cheatsheet.md) | Quick reference commands |
| [Interview_QA.md](./Interview_QA.md) | Interview questions and answers |
| [Code_Example.md](./Code_Example.md) | You are here — working YAML examples |

**Previous:** [09_Ingress](../09_Ingress/Code_Example.md) |
**Next:** [11_RBAC](../11_RBAC/Theory.md)
