# Persistent Volumes — Interview Q&A

---

## Beginner

---

**Q1: What is a PersistentVolume in Kubernetes?**

A PersistentVolume (PV) is a piece of storage that has been provisioned in the cluster — either manually by an administrator (static provisioning) or automatically by a StorageClass (dynamic provisioning). It is a cluster-level resource, meaning it is not namespaced. Think of it as the actual storage locker: it exists independently of any pod, and its data survives even if every pod in the cluster is deleted.

A PV describes how much storage is available, what access mode is allowed, and what should happen to the data when the volume is no longer needed (the reclaim policy).

---

**Q2: What is a PersistentVolumeClaim and how is it different from a PersistentVolume?**

A PersistentVolumeClaim (PVC) is a request for storage made by a pod or application. It is namespaced — it belongs to a specific namespace. While a PV is the actual storage resource, the PVC is the application's way of saying "I need 5Gi of ReadWriteOnce storage, please."

The key difference: the PV is the supply side (the locker), and the PVC is the demand side (the reservation). Kubernetes automatically binds a PVC to a suitable PV that matches its requirements — correct size, access mode, and StorageClass. Once bound, the pod uses the PVC by name, without needing to know anything about the underlying storage.

---

**Q3: What is a StorageClass and why does it exist?**

A StorageClass is a template that tells Kubernetes how to dynamically create a PersistentVolume when a PVC requests one. Without StorageClasses, an administrator would need to manually pre-create every PV before any application could use storage. With StorageClasses, storage is created on demand.

A StorageClass defines the provisioner (which CSI driver or built-in driver to use), parameters (e.g., disk type, IOPS, encryption), and the reclaim policy. For example, you might have a `fast-ssd` StorageClass that provisions AWS EBS gp3 volumes, and a `slow-archive` StorageClass that provisions cheaper magnetic storage. Developers just reference the StorageClass name in their PVC — the infrastructure details are abstracted away.

---

**Q4: What are the access modes for a PersistentVolume?**

Access modes describe how a volume can be mounted across nodes:

- **ReadWriteOnce (RWO)**: Can be mounted as read-write by a single node. Multiple pods on the same node can use it. This is the most common mode — used by most databases.
- **ReadOnlyMany (ROX)**: Can be mounted as read-only by many nodes simultaneously. Good for shared static assets.
- **ReadWriteMany (RWX)**: Can be mounted as read-write by many nodes simultaneously. Required for applications where multiple pods on different nodes write to the same storage (e.g., shared file storage).
- **ReadWriteOncePod (RWOP)**: Can only be mounted by a single specific pod. Even stricter than RWO.

Not all storage backends support all modes. AWS EBS only supports RWO. NFS supports all three.

---

**Q5: How do you use a PersistentVolumeClaim in a pod?**

You reference the PVC by name in the pod's `volumes` section and mount it into the container:

```yaml
spec:
  containers:
    - name: app
      volumeMounts:
        - name: data-volume
          mountPath: /var/data
  volumes:
    - name: data-volume
      persistentVolumeClaim:
        claimName: my-app-pvc
```

The pod does not interact with the PV directly — only with the PVC. This means you can change the underlying storage (migrate from one PV to another) without changing the pod spec, as long as the PVC name stays the same.

---

## Intermediate

---

**Q6: What are the three reclaim policies and when would you use each?**

Reclaim policies control what happens to a PV (and its data) when the bound PVC is deleted:

- **Retain**: The PV moves to a `Released` state. The data is preserved on the underlying storage. An administrator must manually decide what to do — clean it up, reuse it, or archive it. This is the safest policy and should be used for any production database or critical data.

- **Delete**: The PV object and the underlying storage (e.g., the AWS EBS volume) are automatically deleted. Use this for development environments or scratch storage where data loss is acceptable.

- **Recycle**: Deprecated. Used to wipe the volume (`rm -rf`) and make the PV `Available` again. Do not use this in new clusters.

In practice: default to `Retain` for anything important. Use `Delete` for test environments managed by automation where you want resources cleaned up automatically.

---

**Q7: What is the difference between static and dynamic provisioning?**

**Static provisioning**: A cluster administrator manually creates PersistentVolume objects before any application requests them. The PVC then searches for a matching pre-existing PV. This requires the admin to predict storage needs in advance. It is common in on-premises environments with fixed infrastructure.

**Dynamic provisioning**: When a PVC is created, Kubernetes automatically provisions a new PV using the StorageClass's provisioner. No pre-created PVs are needed. This is the standard in cloud environments where storage can be created programmatically on demand (AWS EBS, GCE PD, Azure Disk). The developer just creates a PVC with a StorageClass name and the infrastructure takes care of the rest.

---

**Q8: What is `volumeBindingMode: WaitForFirstConsumer` and why is it important?**

By default (`Immediate` mode), a PV is provisioned and bound to a PVC as soon as the PVC is created — before any pod has been scheduled. In cloud environments where storage is zone-specific (like AWS EBS), this can create a problem: the volume might be provisioned in zone `us-east-1a`, but the pod ends up scheduled on a node in zone `us-east-1b`. The pod cannot attach the volume because it is in the wrong zone.

`WaitForFirstConsumer` delays volume provisioning until a pod that uses the PVC is scheduled. At that point, Kubernetes knows which node (and which availability zone) the pod will run on, and provisions the volume in the correct zone. This is the recommended binding mode for cloud block storage.

---

**Q9: A PVC is stuck in `Pending` state. How do you debug it?**

Run `kubectl describe pvc <name> -n <namespace>` and look at the Events section at the bottom. Common causes:

1. **No matching PV** (static provisioning): No PV exists that matches the PVC's size, access mode, and StorageClass. Create a matching PV.
2. **Wrong StorageClass name**: The PVC references a StorageClass that does not exist. Check `kubectl get sc`.
3. **CSI driver not running**: The provisioner cannot create the volume. Check `kubectl get pods -n kube-system | grep csi`.
4. **Insufficient quota**: A ResourceQuota in the namespace blocks PVC creation.
5. **`WaitForFirstConsumer`**: The PVC is intentionally pending until a pod is scheduled — this is expected behavior.

---

## Advanced

---

**Q10: What are CSI drivers and why were they introduced?**

CSI stands for Container Storage Interface. It is a standardized API that allows storage vendors to build plugins that work with Kubernetes (and other container orchestrators) without their code being merged into the Kubernetes core.

Before CSI, storage drivers were "in-tree" — built directly into the Kubernetes source code. This meant that adding a new storage backend required a Kubernetes release, and bugs in storage drivers could affect the entire control plane. CSI moved storage drivers out of Kubernetes into separate plugins that can be installed, updated, and versioned independently.

A CSI driver has two components: the **controller plugin** (runs as a Deployment, handles volume provisioning and snapshots) and the **node plugin** (runs as a DaemonSet on every node, handles mounting volumes into pods). All major cloud providers (AWS, GCP, Azure) and storage vendors (NetApp, Pure Storage, Rook/Ceph) now provide CSI drivers.

---

**Q11: How do VolumeSnapshots work in Kubernetes?**

VolumeSnapshots are a Kubernetes API for taking point-in-time copies of PersistentVolumeClaims. They follow the same supply/demand pattern as PVs and PVCs:

- **VolumeSnapshotClass**: Defines which CSI driver to use for snapshots and any driver-specific parameters. Like StorageClass but for snapshots.
- **VolumeSnapshot**: A request to take a snapshot of a specific PVC. Created by a developer or automated backup job.
- **VolumeSnapshotContent**: The actual snapshot resource created by the CSI driver. Automatically created when a VolumeSnapshot is requested.

Once a VolumeSnapshot is ready (`status.readyToUse: true`), you can create a new PVC that uses it as a `dataSource`. The new PVC is pre-populated with all the data from the snapshot. This is how you restore backups, clone databases for testing, or promote a staging database to production.

VolumeSnapshots require a CSI driver that supports the snapshot capability — not all drivers do.

---

**Q12: How do you migrate data from one StorageClass to another?**

There is no built-in "move" command for PVC data. The migration process depends on the workload, but a common approach is:

1. **Scale down the workload** that uses the PVC (stop all writes).
2. **Take a VolumeSnapshot** of the existing PVC as a backup.
3. **Create a new PVC** with the target StorageClass and the same or larger size.
4. **Copy the data** — use a temporary pod that mounts both PVCs and runs `rsync`, `cp -a`, or `tar`. For databases, use a dump/restore approach (`pg_dump`, `mysqldump`) to preserve consistency.
5. **Update the pod spec** to reference the new PVC name (or rename using a PV-rebinding trick).
6. **Scale the workload back up** and verify the data.
7. **Delete the old PVC** (after verifying, and depending on the reclaim policy).

For zero-downtime migrations on critical workloads, tools like Velero (for backup/restore) or the CSI volume cloning feature (if the driver supports it) can streamline the process.

---

**Q13: What is PVC volume expansion and how does it work?**

If the StorageClass has `allowVolumeExpansion: true`, you can resize a PVC after it has been created by editing the PVC's `spec.resources.requests.storage` to a larger value. You can only expand, not shrink.

```bash
kubectl patch pvc my-app-data -n production \
  -p '{"spec":{"resources":{"requests":{"storage":"20Gi"}}}}'
```

Kubernetes then triggers the CSI driver to resize the underlying volume. Depending on the driver and filesystem, this may happen online (without pod restart) or may require a pod restart for the filesystem to pick up the new size. Check the PVC's `status.conditions` for the resize progress. Not all storage backends support online resizing.

---

## 📂 Navigation

⬅️ **Prev:** [Ingress](../09_Ingress/Interview_QA.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [RBAC and Security](../11_RBAC/Theory.md)

| | Link |
|---|---|
| Theory | [Theory.md](./Theory.md) |
| Cheatsheet | [Cheatsheet.md](./Cheatsheet.md) |
| Module Home | [10_Persistent_Volumes](../) |
