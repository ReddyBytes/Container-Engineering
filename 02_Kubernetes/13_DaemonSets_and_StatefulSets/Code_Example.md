# DaemonSets and StatefulSets — Code Examples

## Example 1: DaemonSet for Log Collection (Fluent Bit)

```yaml
# Fluent Bit log collector DaemonSet
# Runs on every node, reads container logs from the host filesystem,
# and ships them to a logging backend (e.g., Elasticsearch, Loki).

apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluent-bit
  namespace: logging
  labels:
    app: fluent-bit
    version: v2.2.0
spec:
  selector:
    matchLabels:
      app: fluent-bit

  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1      # update one node at a time

  template:
    metadata:
      labels:
        app: fluent-bit
    spec:
      # Run on control-plane nodes too (they also have logs)
      tolerations:
        - key: node-role.kubernetes.io/control-plane
          operator: Exists
          effect: NoSchedule
        - key: node-role.kubernetes.io/master
          operator: Exists
          effect: NoSchedule

      serviceAccountName: fluent-bit

      # Host mounts: access container logs from the node filesystem
      volumes:
        - name: varlog
          hostPath:
            path: /var/log             # main log directory
        - name: varlibdockercontainers
          hostPath:
            path: /var/lib/docker/containers   # container log files
        - name: config
          configMap:
            name: fluent-bit-config    # Fluent Bit configuration

      containers:
        - name: fluent-bit
          image: fluent/fluent-bit:2.2.0
          imagePullPolicy: IfNotPresent

          resources:
            requests:
              cpu: 50m
              memory: 64Mi
            limits:
              cpu: 200m
              memory: 256Mi

          # Mount host log directories (read-only — never write to host)
          volumeMounts:
            - name: varlog
              mountPath: /var/log
              readOnly: true
            - name: varlibdockercontainers
              mountPath: /var/lib/docker/containers
              readOnly: true
            - name: config
              mountPath: /fluent-bit/etc/

          # Environment variables for destination
          env:
            - name: FLUENT_ELASTICSEARCH_HOST
              value: "elasticsearch.logging.svc.cluster.local"
            - name: FLUENT_ELASTICSEARCH_PORT
              value: "9200"
            - name: NODE_NAME
              valueFrom:
                fieldRef:
                  fieldPath: spec.nodeName   # inject node name into logs
```

---

## Example 2: DaemonSet Only on Specific Nodes (GPU Monitoring)

```yaml
# This DaemonSet only runs on nodes labeled gpu=true
# Use case: NVIDIA GPU metrics collector

apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: nvidia-gpu-exporter
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: nvidia-gpu-exporter
  template:
    metadata:
      labels:
        app: nvidia-gpu-exporter
    spec:
      nodeSelector:
        gpu: "true"                # only schedule on GPU nodes

      tolerations:
        - key: nvidia.com/gpu      # tolerate GPU taint if present
          operator: Exists
          effect: NoSchedule

      containers:
        - name: gpu-exporter
          image: utkuozdemir/nvidia_gpu_exporter:1.2.0
          ports:
            - containerPort: 9835
              name: metrics
          resources:
            limits:
              nvidia.com/gpu: 1   # request access to one GPU
```

---

## Example 3: StatefulSet for PostgreSQL with PVC Template

```yaml
# Headless service MUST be created before the StatefulSet
apiVersion: v1
kind: Service
metadata:
  name: postgres                    # this name is used in pod DNS
  namespace: data
  labels:
    app: postgres
spec:
  clusterIP: None                   # headless: no virtual IP
  selector:
    app: postgres
  ports:
    - name: postgres
      port: 5432
      targetPort: 5432
---
# Regular service for application connections (load-balanced)
apiVersion: v1
kind: Service
metadata:
  name: postgres-read
  namespace: data
spec:
  selector:
    app: postgres
  ports:
    - port: 5432
      targetPort: 5432
  type: ClusterIP
---
# The StatefulSet
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: data
spec:
  serviceName: postgres             # must match the headless service name
  replicas: 3                       # creates postgres-0, postgres-1, postgres-2

  selector:
    matchLabels:
      app: postgres

  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      partition: 0                  # update all pods (set to 2 for canary)

  # podManagementPolicy: OrderedReady  # default: start 0 → 1 → 2 in order
  # podManagementPolicy: Parallel       # start all at once (faster, no ordering)

  template:
    metadata:
      labels:
        app: postgres
    spec:
      # Terminate gracefully — give PostgreSQL time to finish transactions
      terminationGracePeriodSeconds: 60

      initContainers:
        # Check if this is the primary (ordinal-0) or a replica
        - name: init-postgres
          image: postgres:15
          command:
            - bash
            - -c
            - |
              # Extract ordinal from hostname (postgres-0 → 0)
              ORDINAL=$(hostname | awk -F'-' '{print $NF}')
              if [ "$ORDINAL" = "0" ]; then
                echo "primary" > /etc/postgres/role
              else
                echo "replica" > /etc/postgres/role
              fi
          volumeMounts:
            - name: config
              mountPath: /etc/postgres

      containers:
        - name: postgres
          image: postgres:15
          ports:
            - containerPort: 5432
              name: postgres

          env:
            - name: POSTGRES_DB
              value: myapp
            - name: POSTGRES_USER
              value: appuser
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: password
            - name: PGDATA
              value: /var/lib/postgresql/data/pgdata   # avoid lost+found issue

          resources:
            requests:
              cpu: 250m
              memory: 512Mi
            limits:
              cpu: 1000m
              memory: 2Gi

          volumeMounts:
            - name: data             # mounts the per-pod PVC
              mountPath: /var/lib/postgresql/data
            - name: config
              mountPath: /etc/postgres

          # Readiness: only mark ready when postgres accepts connections
          readinessProbe:
            exec:
              command:
                - pg_isready
                - -U
                - appuser
                - -d
                - myapp
            initialDelaySeconds: 10
            periodSeconds: 5
            failureThreshold: 3

          # Liveness: restart if postgres stops responding
          livenessProbe:
            exec:
              command:
                - pg_isready
                - -U
                - appuser
            initialDelaySeconds: 30
            periodSeconds: 10
            failureThreshold: 5

      volumes:
        - name: config
          emptyDir: {}

  # VolumeClaimTemplates: each pod gets its own PVC
  # PVC name: data-postgres-0, data-postgres-1, data-postgres-2
  volumeClaimTemplates:
    - metadata:
        name: data                  # mounted as volumeMounts[name: data]
      spec:
        accessModes: ["ReadWriteOnce"]    # one node at a time (database)
        storageClassName: fast-ssd        # use fast SSD for database
        resources:
          requests:
            storage: 50Gi
```

---

## Example 4: Secret for PostgreSQL Password

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: postgres-secret
  namespace: data
type: Opaque
stringData:
  password: "change-me-in-production"   # use sealed-secrets or external-secrets in prod
```

---

## Connecting to Specific StatefulSet Pods

```bash
# Connect to postgres-0 (primary) for writes:
# postgres-0.postgres.data.svc.cluster.local:5432

# Connect to postgres-1 (replica) for reads:
# postgres-1.postgres.data.svc.cluster.local:5432

# From another pod in the same namespace:
psql -h postgres-0.postgres -U appuser -d myapp

# Exec directly into a specific pod:
kubectl exec -it postgres-0 -n data -- psql -U appuser -d myapp

# Check which pods exist and their ordinals:
kubectl get pods -n data -l app=postgres --sort-by=.metadata.name

# Check PVCs created by the StatefulSet:
kubectl get pvc -n data -l app=postgres
```

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Theory.md](./Theory.md) |
| Cheatsheet | [Cheatsheet.md](./Cheatsheet.md) |
| Interview Q&A | [Interview_QA.md](./Interview_QA.md) |
| Module Home | [13_DaemonSets_and_StatefulSets](../) |
