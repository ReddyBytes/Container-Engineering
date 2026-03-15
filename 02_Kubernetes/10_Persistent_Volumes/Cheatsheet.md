# Persistent Volumes Cheatsheet

## Core Concepts Quick Reference

| Object | Namespaced? | Role |
|---|---|---|
| PersistentVolume (PV) | No | The actual storage resource |
| PersistentVolumeClaim (PVC) | Yes | A request to use storage |
| StorageClass | No | Template for dynamic provisioning |
| VolumeSnapshot | Yes | Point-in-time copy of a PVC |

---

## kubectl Commands

```bash
# --- PersistentVolumes ---

# List all PVs cluster-wide
kubectl get pv

# Describe a PV (see status, capacity, binding, reclaim policy)
kubectl describe pv <pv-name>

# List PVs sorted by capacity
kubectl get pv --sort-by=.spec.capacity.storage

# Delete a PV (only safe if reclaim policy is Retain and you have migrated data)
kubectl delete pv <pv-name>

# --- PersistentVolumeClaims ---

# List all PVCs in a namespace
kubectl get pvc -n <namespace>

# List all PVCs across all namespaces
kubectl get pvc -A

# Describe a PVC (see events, bound PV, storage class)
kubectl describe pvc <pvc-name> -n <namespace>

# Delete a PVC (caution: may trigger data deletion if reclaim policy is Delete)
kubectl delete pvc <pvc-name> -n <namespace>

# Watch PVC status (useful while waiting for binding)
kubectl get pvc <pvc-name> -n <namespace> -w

# --- StorageClasses ---

# List all storage classes
kubectl get storageclass
kubectl get sc

# Describe a storage class
kubectl describe sc <name>

# See the default storage class (marked with annotation)
kubectl get sc | grep default

# Set a storage class as default
kubectl patch storageclass <name> \
  -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'

# Remove default annotation from a storage class
kubectl patch storageclass <name> \
  -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"false"}}}'

# --- Debugging Storage Issues ---

# Why is my PVC pending? (check events at the bottom)
kubectl describe pvc <pvc-name> -n <namespace>

# Why is my pod stuck in ContainerCreating?
kubectl describe pod <pod-name> -n <namespace>
# Look for: Unable to attach or mount volumes

# Check which PV a PVC is bound to
kubectl get pvc <name> -n <namespace> -o jsonpath='{.spec.volumeName}'

# Check which PVC a PV is bound to
kubectl get pv <pv-name> -o jsonpath='{.spec.claimRef}'

# Check CSI driver pods are healthy
kubectl get pods -n kube-system | grep csi

# Check CSI node driver logs
kubectl logs -n kube-system <csi-node-pod-name> -c csi-driver

# --- VolumeSnapshots ---

# List all snapshots in a namespace
kubectl get volumesnapshot -n <namespace>

# Describe a snapshot
kubectl describe volumesnapshot <name> -n <namespace>

# Check if snapshot is ready
kubectl get volumesnapshot <name> -n <namespace> \
  -o jsonpath='{.status.readyToUse}'

# List VolumeSnapshotClasses
kubectl get volumesnapshotclass

# --- Resource Cleanup ---

# List released PVs (safe to investigate or delete)
kubectl get pv | grep Released

# Force-delete a stuck PVC (remove finalizer)
kubectl patch pvc <name> -n <namespace> \
  -p '{"metadata":{"finalizers":null}}'
```

---

## Access Modes Reference

| Mode | Code | Multiple pods? | Multiple nodes? | Common backends |
|---|---|---|---|---|
| ReadWriteOnce | RWO | Yes (same node) | No | EBS, GCE PD, Azure Disk, local |
| ReadOnlyMany | ROX | Yes | Yes | NFS, GCE PD |
| ReadWriteMany | RWX | Yes | Yes | NFS, Azure Files, EFS |
| ReadWriteOncePod | RWOP | One pod only | No | Any CSI driver (K8s 1.22+) |

---

## Reclaim Policy Reference

| Policy | Data fate on PVC delete | Use case |
|---|---|---|
| `Retain` | Preserved — admin must clean up | Production databases |
| `Delete` | Automatically deleted | Dev/test, ephemeral storage |
| `Recycle` | **Deprecated** — do not use | Legacy only |

---

## PVC YAML Reference

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: my-app-data
  namespace: production
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: fast-ssd     # omit to use default StorageClass
  resources:
    requests:
      storage: 10Gi
```

---

## PV YAML Reference (Static Provisioning)

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: nfs-pv-001
spec:
  capacity:
    storage: 100Gi
  accessModes:
    - ReadWriteMany
  reclaimPolicy: Retain
  storageClassName: nfs-storage
  nfs:
    server: 10.0.1.50
    path: /exports/data
```

---

## StorageClass YAML Reference

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
  annotations:
    storageclass.kubernetes.io/is-default-class: "false"
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  iops: "3000"
  throughput: "125"
  encrypted: "true"
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
```

---

## Pod Using a PVC

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-app
spec:
  containers:
    - name: app
      image: my-app:latest
      volumeMounts:
        - name: data
          mountPath: /var/data
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: my-app-data
```

---

## VolumeSnapshot YAML Reference

```yaml
# Take a snapshot
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: myapp-snapshot-20240115
  namespace: production
spec:
  volumeSnapshotClassName: csi-aws-vsc
  source:
    persistentVolumeClaimName: my-app-data

---
# Restore snapshot to new PVC
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: my-app-data-restored
  namespace: production
spec:
  dataSource:
    name: myapp-snapshot-20240115
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

---

## Common PVC Status Values and What They Mean

| Status | Meaning | Action |
|---|---|---|
| `Pending` | No matching PV found yet | Check StorageClass, CSI driver, capacity |
| `Bound` | PVC is bound to a PV — ready to use | None |
| `Lost` | The bound PV no longer exists | Data may be lost; create new PVC |
| `Terminating` | PVC is being deleted but has a finalizer | Check if pod still using it |

---

## 📂 Navigation

⬅️ **Prev:** [Ingress](../09_Ingress/Interview_QA.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [RBAC and Security](../11_RBAC/Theory.md)

| | Link |
|---|---|
| Theory | [Theory.md](./Theory.md) |
| Interview Q&A | [Interview_QA.md](./Interview_QA.md) |
| Module Home | [10_Persistent_Volumes](../) |
