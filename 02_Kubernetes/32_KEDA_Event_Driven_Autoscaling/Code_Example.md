# KEDA — Code Examples

Install KEDA before applying these examples:

```bash
helm repo add kedacore https://kedacore.github.io/charts
helm repo update
helm install keda kedacore/keda --namespace keda --create-namespace
```

---

## Example 1: ScaledObject for AWS SQS Queue

Scale image processing workers based on the number of messages in an SQS queue. Target 1 pod per 10 messages in the queue. Scale to zero when queue is empty.

```yaml
---
# IAM-based credentials (use IRSA in production — see note below)
apiVersion: v1
kind: Secret
metadata:
  name: aws-credentials
  namespace: production
type: Opaque
stringData:
  AWS_ACCESS_KEY_ID: "AKIAIOSFODNN7EXAMPLE"
  AWS_SECRET_ACCESS_KEY: "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

---
# TriggerAuthentication: keeps credentials separate from scaling logic
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: aws-sqs-auth
  namespace: production
spec:
  secretTargetRef:
  - parameter: awsAccessKeyID
    name: aws-credentials
    key: AWS_ACCESS_KEY_ID
  - parameter: awsSecretAccessKey
    name: aws-credentials
    key: AWS_SECRET_ACCESS_KEY

---
# The Deployment being scaled
apiVersion: apps/v1
kind: Deployment
metadata:
  name: image-worker
  namespace: production
spec:
  replicas: 0                  # KEDA will manage this
  selector:
    matchLabels:
      app: image-worker
  template:
    metadata:
      labels:
        app: image-worker
    spec:
      containers:
      - name: worker
        image: myrepo/image-worker:latest
        env:
        - name: SQS_QUEUE_URL
          value: https://sqs.us-east-1.amazonaws.com/123456789/image-jobs
        - name: AWS_REGION
          value: us-east-1
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 2000m
            memory: 2Gi

---
# ScaledObject: the core KEDA resource
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: image-worker-scaler
  namespace: production
spec:
  scaleTargetRef:
    name: image-worker
  minReplicaCount: 0           # scale to zero when queue is empty
  maxReplicaCount: 50          # never exceed 50 workers
  pollingInterval: 15          # check queue every 15 seconds
  cooldownPeriod: 300          # wait 5 min after empty before scaling to 0
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 60    # don't scale down too fast
          policies:
          - type: Percent
            value: 25
            periodSeconds: 60              # remove at most 25% of pods per minute
  triggers:
  - type: aws-sqs-queue
    authenticationRef:
      name: aws-sqs-auth
    metadata:
      queueURL: https://sqs.us-east-1.amazonaws.com/123456789/image-jobs
      queueLength: "10"         # target: 10 messages per active pod
      awsRegion: us-east-1
      scaleOnInFlight: "true"   # count in-flight messages too
```

**Note on IRSA (recommended for EKS):** Instead of static credentials, annotate the worker's ServiceAccount with an IAM Role ARN. KEDA will automatically use the pod's projected service account token:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: image-worker-sa
  namespace: production
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789:role/image-worker-keda-role
---
# In the ScaledObject, use pod identity instead of credentials
triggers:
- type: aws-sqs-queue
  metadata:
    queueURL: https://sqs.us-east-1.amazonaws.com/123456789/image-jobs
    queueLength: "10"
    awsRegion: us-east-1
    identityOwner: pod          # use the pod's IRSA identity
```

---

## Example 2: ScaledObject for Kafka Consumer Lag

Scale a Kafka consumer deployment based on consumer group lag. Target 1 pod per 50 messages of lag.

```yaml
---
apiVersion: v1
kind: Secret
metadata:
  name: kafka-credentials
  namespace: streaming
type: Opaque
stringData:
  username: "kafka-user"
  password: "kafka-password"

---
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: kafka-auth
  namespace: streaming
spec:
  secretTargetRef:
  - parameter: username
    name: kafka-credentials
    key: username
  - parameter: password
    name: kafka-credentials
    key: password

---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: order-consumer-scaler
  namespace: streaming
spec:
  scaleTargetRef:
    name: order-consumer
  minReplicaCount: 1           # keep at least 1 pod (no cold start)
  maxReplicaCount: 30
  pollingInterval: 10
  cooldownPeriod: 120
  triggers:
  - type: kafka
    authenticationRef:
      name: kafka-auth
    metadata:
      bootstrapServers: kafka.kafka.svc.cluster.local:9092
      consumerGroup: order-processor-group
      topic: orders
      lagThreshold: "50"       # target: 50 messages of lag per pod
      offsetResetPolicy: latest
      # SASL authentication
      sasl: plaintext
      # For TLS: tls: enable, tlsInsecureSkipTlsVerify: false
```

Verify lag is being measured:

```bash
# Check the HPA KEDA created
kubectl get hpa -n streaming
# NAME                              REFERENCE                   TARGETS
# keda-hpa-order-consumer-scaler   Deployment/order-consumer   500m/50 (10 avg)

# Check ScaledObject status
kubectl describe scaledobject order-consumer-scaler -n streaming
```

---

## Example 3: ScaledObject with Prometheus Metrics

Scale a web API based on HTTP request rate per second, measured by Prometheus.

```yaml
---
# No authentication needed for in-cluster Prometheus
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: api-request-scaler
  namespace: production
spec:
  scaleTargetRef:
    name: api-deployment
  minReplicaCount: 2           # always keep 2 for HA
  maxReplicaCount: 100
  pollingInterval: 15
  triggers:
  # Trigger 1: scale on request rate
  # Target: 100 requests/second per pod
  - type: prometheus
    metadata:
      serverAddress: http://prometheus.monitoring.svc.cluster.local:9090
      metricName: http_rps         # name for this metric (used internally)
      threshold: "100"             # target value per pod
      query: |
        sum(rate(http_requests_total{
          service="api-deployment",
          code!~"5.."
        }[1m]))
  # Trigger 2: also scale on p99 latency
  # If p99 latency > 500ms, force scale up (threshold: 1 means "1 pod per 1 unit")
  - type: prometheus
    metadata:
      serverAddress: http://prometheus.monitoring.svc.cluster.local:9090
      metricName: p99_latency_violation
      threshold: "1"
      query: |
        scalar(
          histogram_quantile(0.99,
            sum(rate(http_request_duration_seconds_bucket{service="api-deployment"}[5m]))
            by (le)
          ) > bool 0.5
        ) * 50
      # Returns 50 when p99 > 500ms (forcing 50 pods minimum), 0 otherwise
      ignoreNullValues: "false"
```

This example uses two Prometheus triggers together. KEDA scales to the maximum recommended by either trigger — if request rate is low but latency is high, the latency trigger forces scale-up anyway.

---

## Example 4: ScaledObject with Cron Schedule (Business Hours)

Run reporting workers only during business hours. Zero pods overnight and on weekends.

```yaml
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: report-worker
  namespace: operations
spec:
  replicas: 0                  # KEDA starts at 0
  selector:
    matchLabels:
      app: report-worker
  template:
    metadata:
      labels:
        app: report-worker
    spec:
      containers:
      - name: worker
        image: myrepo/report-worker:latest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url

---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: report-worker-scaler
  namespace: operations
spec:
  scaleTargetRef:
    name: report-worker
  minReplicaCount: 0
  maxReplicaCount: 20
  triggers:
  # Scale to 5 during Eastern business hours, Mon-Fri
  - type: cron
    metadata:
      timezone: America/New_York
      start: "0 8 * * 1-5"      # 8:00 AM Mon-Fri
      end: "0 18 * * 1-5"       # 6:00 PM Mon-Fri
      desiredReplicas: "5"
  # Also scale on report queue depth (queue may build up during business hours)
  # KEDA will use max(cron=5, sqs=N) — whichever is higher
  - type: aws-sqs-queue
    authenticationRef:
      name: aws-sqs-auth
    metadata:
      queueURL: https://sqs.us-east-1.amazonaws.com/123456789/reports
      queueLength: "2"           # 2 queue messages per pod
      awsRegion: us-east-1
```

Behavior:
- Weeknights after 6 PM: cron trigger returns 0, SQS is empty → scale to 0 pods
- 8 AM Monday: cron trigger returns 5 → scale to 5 pods
- Monday 10 AM, queue has 30 messages: SQS trigger returns 15 → scale to max(5, 15) = 15 pods
- Monday 6 PM: cron trigger returns 0, queue drains → scale to 0 after cooldown

---

## Example 5: ScaledJob for Batch Processing (One Pod Per Job)

Process items from an SQS queue where each item requires its own isolated job pod. Use ScaledJob instead of ScaledObject.

```yaml
---
# The Job template — KEDA creates one of these per batch
apiVersion: keda.sh/v1alpha1
kind: ScaledJob
metadata:
  name: video-transcoder
  namespace: media
spec:
  # Template for each Job that KEDA creates
  jobTargetRef:
    parallelism: 1              # each job runs 1 pod
    completions: 1
    activeDeadlineSeconds: 3600 # jobs must finish within 1 hour
    backoffLimit: 2             # retry twice on failure
    template:
      metadata:
        labels:
          app: video-transcoder
          workload-type: batch
      spec:
        restartPolicy: Never    # required for Jobs
        serviceAccountName: media-processor-sa
        containers:
        - name: transcoder
          image: myrepo/video-transcoder:v2.1.0
          env:
          - name: SQS_QUEUE_URL
            value: https://sqs.us-east-1.amazonaws.com/123456789/video-jobs
          - name: AWS_REGION
            value: us-east-1
          - name: OUTPUT_BUCKET
            value: processed-videos-bucket
          resources:
            requests:
              cpu: 2000m        # video transcoding is CPU-intensive
              memory: 4Gi
            limits:
              cpu: 4000m
              memory: 8Gi
        nodeSelector:
          node-type: compute-optimized   # use c5/c6i instances

  # Scaling configuration
  pollingInterval: 30
  maxReplicaCount: 20           # never run more than 20 simultaneous jobs
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 5

  scalingStrategy:
    strategy: accurate          # count pending messages accurately
    customScalingRunningJobPercentage: "0.5"  # create new jobs when 50% are running

  triggers:
  - type: aws-sqs-queue
    authenticationRef:
      name: aws-sqs-auth
    metadata:
      queueURL: https://sqs.us-east-1.amazonaws.com/123456789/video-jobs
      queueLength: "1"          # 1 job per 1 message
      awsRegion: us-east-1
```

Monitor ScaledJob:

```bash
# Check pending vs running jobs
kubectl get jobs -n media -l app=video-transcoder

# Check ScaledJob status
kubectl describe scaledjob video-transcoder -n media

# Watch jobs complete
kubectl get pods -n media -l app=video-transcoder -w
```

---

## 📂 Navigation

| | |
|---|---|
| Previous | [31_Gateway_API](../31_Gateway_API/) |
| Next | [33_Karpenter_Node_Autoprovisioning](../33_Karpenter_Node_Autoprovisioning/) |
| Up | [02_Kubernetes](../) |

**Files in this module:**
- [Theory.md](./Theory.md) — Concepts and architecture
- [Cheatsheet.md](./Cheatsheet.md) — Quick reference
- [Interview_QA.md](./Interview_QA.md) — Common interview questions
- [Code_Example.md](./Code_Example.md) — Working YAML examples
