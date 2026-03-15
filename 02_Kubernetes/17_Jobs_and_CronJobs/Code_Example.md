# Jobs and CronJobs — Code Examples

## Example 1: Simple Job (Database Migration)

```yaml
# Run a database migration as a one-shot Job.
# This Job runs once, completes, and retains its pods for log inspection.
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migration-v2-1-0
  namespace: production
  labels:
    app: my-app
    migration-version: "2.1.0"
spec:
  # Only run once
  completions: 1
  parallelism: 1

  # Fail after 3 pod failures (not 6 — migrations are sensitive)
  backoffLimit: 3

  # Kill the job if it takes more than 10 minutes
  activeDeadlineSeconds: 600

  # Auto-delete 1 hour after completion (keep logs for debugging)
  ttlSecondsAfterFinished: 3600

  template:
    metadata:
      labels:
        app: my-app
        job-type: migration
    spec:
      # NEVER use restartPolicy: Always in a Job
      restartPolicy: Never

      containers:
        - name: migrator
          image: my-registry/my-app:2.1.0
          command: ["python", "manage.py", "migrate", "--noinput"]

          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: db-credentials
                  key: url

          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
```

---

## Example 2: Parallel Job (Process N Items)

```yaml
# Process 20 image thumbnails, 4 at a time.
# Each pod processes one image from a pre-determined list.
# Index-based job: each pod gets its ordinal via JOB_COMPLETION_INDEX (K8s 1.21+)

apiVersion: batch/v1
kind: Job
metadata:
  name: thumbnail-generator
  namespace: media
spec:
  completions: 20              # 20 total items to process
  parallelism: 4               # run 4 pods at a time
  completionMode: Indexed      # each pod gets a unique index (0-19)

  backoffLimit: 5              # allow some failures (network errors, etc.)
  activeDeadlineSeconds: 1800  # kill after 30 minutes

  ttlSecondsAfterFinished: 600

  template:
    metadata:
      labels:
        app: thumbnail-generator
    spec:
      restartPolicy: OnFailure  # retry same pod on failure (faster than Never)

      containers:
        - name: generator
          image: my-registry/thumbnail-generator:1.0.0

          env:
            # K8s automatically sets JOB_COMPLETION_INDEX to the pod's index
            # Pod 0 processes item 0, pod 1 processes item 1, etc.
            - name: ITEM_INDEX
              valueFrom:
                fieldRef:
                  fieldPath: metadata.annotations['batch.kubernetes.io/job-completion-index']

            - name: S3_BUCKET
              value: "my-media-bucket"

            - name: AWS_REGION
              value: "us-east-1"

          resources:
            requests:
              cpu: 200m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 256Mi
```

---

## Example 3: Work Queue Job (Pull from Queue Until Empty)

```yaml
# Each pod pulls from a Redis work queue and processes items.
# When the queue is empty, pods exit 0.
# Job succeeds when at least 1 pod exits successfully.

apiVersion: batch/v1
kind: Job
metadata:
  name: report-processor
  namespace: analytics
spec:
  # Don't set completions — let pods self-terminate when queue is empty
  parallelism: 5               # 5 workers consume the queue simultaneously
  backoffLimit: 10

  activeDeadlineSeconds: 3600  # kill after 1 hour regardless

  template:
    spec:
      restartPolicy: Never

      containers:
        - name: worker
          image: my-registry/queue-worker:1.0.0
          command:
            - python
            - worker.py
            # The worker script:
            # 1. Connects to Redis
            # 2. BLPOPs from the queue
            # 3. Processes each item
            # 4. Exits with 0 when queue is empty or after N seconds of no work

          env:
            - name: REDIS_URL
              valueFrom:
                secretKeyRef:
                  name: redis-credentials
                  key: url
            - name: QUEUE_NAME
              value: "reports-to-generate"
            - name: IDLE_TIMEOUT_SECONDS
              value: "30"        # exit if queue is empty for 30 seconds

          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              cpu: 2000m
              memory: 2Gi
```

---

## Example 4: CronJob (Nightly Report)

```yaml
# Generate a nightly business report at 2:00 AM every day.
# Use Forbid concurrency to prevent overlapping runs.

apiVersion: batch/v1
kind: CronJob
metadata:
  name: nightly-report
  namespace: analytics
spec:
  schedule: "0 2 * * *"         # at 02:00 AM every day

  # Skip if previous run is still active
  concurrencyPolicy: Forbid

  # If we can't start within 60 seconds of scheduled time, skip this run
  startingDeadlineSeconds: 60

  # Keep last 3 successful Jobs for inspection
  successfulJobsHistoryLimit: 3

  # Keep last 3 failed Jobs for debugging
  failedJobsHistoryLimit: 3

  # Set to true to pause without deleting
  # suspend: false

  jobTemplate:
    spec:
      backoffLimit: 2             # retry twice on failure
      activeDeadlineSeconds: 3600 # kill after 1 hour

      ttlSecondsAfterFinished: 86400  # clean up after 24 hours

      template:
        metadata:
          labels:
            app: nightly-report
            job-type: scheduled-report
        spec:
          restartPolicy: Never

          serviceAccountName: report-generator-sa

          containers:
            - name: report-generator
              image: my-registry/report-generator:3.2.0
              command: ["python", "generate_report.py", "--date", "yesterday"]

              env:
                - name: DATABASE_URL
                  valueFrom:
                    secretKeyRef:
                      name: analytics-db-credentials
                      key: url
                - name: SMTP_HOST
                  value: "smtp.mycompany.com"
                - name: REPORT_RECIPIENTS
                  value: "analytics-team@mycompany.com"
                - name: OUTPUT_BUCKET
                  value: "reports-archive"

              resources:
                requests:
                  cpu: 500m
                  memory: 1Gi
                limits:
                  cpu: 2000m
                  memory: 4Gi
```

---

## Example 5: CronJob with Retries (Cleanup Task)

```yaml
# Clean up expired sessions from the database.
# Runs every hour. Allows retries. Uses Replace policy
# so if a cleanup is slow and the next hour arrives,
# the old one is cancelled and a fresh run starts.

apiVersion: batch/v1
kind: CronJob
metadata:
  name: session-cleanup
  namespace: production
spec:
  schedule: "0 * * * *"          # every hour on the hour

  concurrencyPolicy: Replace      # cancel old run, start fresh

  successfulJobsHistoryLimit: 2
  failedJobsHistoryLimit: 2

  jobTemplate:
    spec:
      backoffLimit: 5
      activeDeadlineSeconds: 1800   # kill if takes more than 30 minutes

      template:
        spec:
          restartPolicy: OnFailure

          containers:
            - name: cleanup
              image: postgres:15
              command:
                - psql
                - $(DATABASE_URL)
                - -c
                - >
                  DELETE FROM sessions
                  WHERE expires_at < NOW() - INTERVAL '1 hour';

              env:
                - name: DATABASE_URL
                  valueFrom:
                    secretKeyRef:
                      name: app-db-secret
                      key: url

              resources:
                requests:
                  cpu: 50m
                  memory: 64Mi
                limits:
                  cpu: 200m
                  memory: 128Mi
```

---

## Monitoring and Debugging

```bash
# Watch all jobs complete in real time
kubectl get jobs -n production -w

# Get logs from the most recent Job pod
kubectl logs -n production \
  $(kubectl get pods -n production -l job-name=db-migration-v2-1-0 \
    --sort-by=.metadata.creationTimestamp \
    -o jsonpath='{.items[-1].metadata.name}')

# Check why a Job failed
kubectl describe job db-migration-v2-1-0 -n production
kubectl get events -n production | grep db-migration

# Manually trigger a CronJob for immediate testing
kubectl create job nightly-report-test \
  --from=cronjob/nightly-report \
  -n analytics

# Check CronJob last run and next scheduled time
kubectl get cronjob nightly-report -n analytics
# LAST SCHEDULE column shows when it last ran
```

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Theory.md](./Theory.md) |
| Cheatsheet | [Cheatsheet.md](./Cheatsheet.md) |
| Interview Q&A | [Interview_QA.md](./Interview_QA.md) |
| Module Home | [17_Jobs_and_CronJobs](../) |
