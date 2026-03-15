# Health Probes — Code Examples

## Example 1: HTTP Liveness and Readiness Probes for a Web App

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-api
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-api
  template:
    metadata:
      labels:
        app: web-api
    spec:
      containers:
        - name: web-api
          image: my-registry/web-api:2.1.0
          ports:
            - containerPort: 8080

          # LIVENESS PROBE — is the app still alive?
          # If this fails 3 times, Kubernetes restarts the container.
          # We use a conservative configuration: allow some slowness
          # before declaring the app dead.
          livenessProbe:
            httpGet:
              path: /healthz      # returns 200 if the server is alive
              port: 8080
            initialDelaySeconds: 30   # wait 30s before first check (app startup time)
            periodSeconds: 15         # check every 15 seconds
            timeoutSeconds: 5         # fail if no response within 5 seconds
            failureThreshold: 3       # restart after 3 consecutive failures (45s total)
            successThreshold: 1       # 1 success = healthy

          # READINESS PROBE — is the app ready to handle traffic?
          # If this fails, the pod is removed from the Service endpoints.
          # More sensitive than liveness — we want to remove from LB quickly.
          readinessProbe:
            httpGet:
              path: /ready        # returns 200 when cache is warm, DB connected
              port: 8080
            initialDelaySeconds: 5    # start checking sooner than liveness
            periodSeconds: 5          # check every 5 seconds
            timeoutSeconds: 3
            failureThreshold: 3       # remove from LB after 3 failures (15s)
            successThreshold: 2       # require 2 consecutive successes to re-add (anti-flap)

          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
```

---

## Example 2: Startup Probe for a Slow Java Application

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payments-service
  namespace: production
spec:
  replicas: 2
  selector:
    matchLabels:
      app: payments-service
  template:
    metadata:
      labels:
        app: payments-service
    spec:
      containers:
        - name: payments-service
          image: my-registry/payments-service:3.0.0
          ports:
            - containerPort: 8080

          # STARTUP PROBE — wait for the JVM to warm up and Spring Boot to start
          # While startup probe is running, liveness is DISABLED.
          # failureThreshold * periodSeconds = max startup time allowed
          # 36 * 5 = 180 seconds (3 minutes) of startup runway
          startupProbe:
            httpGet:
              path: /actuator/health/liveness  # Spring Boot Actuator endpoint
              port: 8080
            initialDelaySeconds: 10   # don't even try for the first 10s
            periodSeconds: 5          # try every 5 seconds after that
            failureThreshold: 36      # give up to 3 minutes for startup
            timeoutSeconds: 3

          # LIVENESS PROBE — only activates after startup probe succeeds
          # Conservative: only restart if truly broken
          livenessProbe:
            httpGet:
              path: /actuator/health/liveness
              port: 8080
            periodSeconds: 20
            timeoutSeconds: 5
            failureThreshold: 3

          # READINESS PROBE — checks DB connection, queue connection, etc.
          readinessProbe:
            httpGet:
              path: /actuator/health/readiness  # checks all downstream deps
              port: 8080
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
            successThreshold: 1

          # JVM tuning for containers
          env:
            - name: JAVA_OPTS
              value: >-
                -XX:+UseContainerSupport
                -XX:MaxRAMPercentage=75.0
                -Xss512k

          resources:
            requests:
              cpu: 500m
              memory: 1Gi
            limits:
              cpu: 2000m
              memory: 2Gi
```

---

## Example 3: Exec Probe for a Database

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres-standalone
  namespace: data
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres-standalone
  template:
    metadata:
      labels:
        app: postgres-standalone
    spec:
      containers:
        - name: postgres
          image: postgres:15
          ports:
            - containerPort: 5432

          env:
            - name: POSTGRES_DB
              value: mydb
            - name: POSTGRES_USER
              value: appuser
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: password

          # LIVENESS PROBE — use pg_isready CLI tool (exec probe)
          # pg_isready checks if PostgreSQL is accepting connections
          # Exit code 0 = accepting connections; non-zero = not ready
          livenessProbe:
            exec:
              command:
                - /bin/sh
                - -c
                - pg_isready -U appuser -d mydb -h 127.0.0.1
            initialDelaySeconds: 30   # PostgreSQL takes time to initialize
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 5       # allow 5 failures before restart

          # READINESS PROBE — also use pg_isready
          # Same command but checked more frequently
          readinessProbe:
            exec:
              command:
                - /bin/sh
                - -c
                - pg_isready -U appuser -d mydb -h 127.0.0.1
            initialDelaySeconds: 10
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 3

          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data

          resources:
            requests:
              cpu: 250m
              memory: 512Mi
            limits:
              cpu: 1000m
              memory: 2Gi

      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: postgres-data-pvc
```

---

## Example 4: gRPC Health Probe

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grpc-service
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: grpc-service
  template:
    metadata:
      labels:
        app: grpc-service
    spec:
      containers:
        - name: grpc-service
          image: my-registry/grpc-service:1.0.0
          ports:
            - containerPort: 50051
              name: grpc

          # gRPC liveness probe — calls the standard gRPC health protocol
          # The app must implement grpc.health.v1.Health/Check
          # Available from Kubernetes 1.24+
          livenessProbe:
            grpc:
              port: 50051
              service: ""      # "" checks overall server health
                               # "mypackage.MyService" checks a specific service
            initialDelaySeconds: 10
            periodSeconds: 15
            failureThreshold: 3
            timeoutSeconds: 3

          readinessProbe:
            grpc:
              port: 50051
              service: ""
            initialDelaySeconds: 5
            periodSeconds: 5
            failureThreshold: 3

          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 256Mi
```

---

## Example 5: Redis with TCP Socket Probe

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: cache
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
        - name: redis
          image: redis:7.2-alpine
          ports:
            - containerPort: 6379

          # LIVENESS — TCP socket check: can we connect to port 6379?
          livenessProbe:
            tcpSocket:
              port: 6379            # attempt TCP connection to Redis port
            initialDelaySeconds: 15
            periodSeconds: 10
            failureThreshold: 3

          # READINESS — exec probe using redis-cli ping for richer check
          readinessProbe:
            exec:
              command:
                - redis-cli
                - ping            # returns PONG if Redis is responsive
            initialDelaySeconds: 5
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 3

          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi

          volumeMounts:
            - name: data
              mountPath: /data

      volumes:
        - name: data
          emptyDir: {}              # use PVC for persistent Redis
```

---

## Verifying Probe Behavior

```bash
# Watch pod status changes in real time (see READY column flap)
kubectl get pods -n production -w

# See readiness affecting endpoints (NotReadyAddresses means probe is failing)
kubectl describe endpoints web-api -n production

# Check events for probe failure messages
kubectl get events -n production --sort-by='.lastTimestamp' | grep -i probe

# Port-forward and manually test health endpoints
kubectl port-forward deployment/web-api 8080:8080 -n production &
curl -v http://localhost:8080/healthz
curl -v http://localhost:8080/ready

# Exec into a pod to test the endpoint from inside
kubectl exec -it deployment/web-api -n production -- \
  wget -qO- http://localhost:8080/healthz

# See how many restarts a container has had (liveness failures)
kubectl get pods -n production -o custom-columns=\
NAME:.metadata.name,RESTARTS:.status.containerStatuses[0].restartCount
```

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Theory.md](./Theory.md) |
| Cheatsheet | [Cheatsheet.md](./Cheatsheet.md) |
| Interview Q&A | [Interview_QA.md](./Interview_QA.md) |
| Module Home | [14_Health_Probes](../) |
