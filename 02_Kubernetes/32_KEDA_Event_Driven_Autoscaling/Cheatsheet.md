# KEDA — Cheatsheet

## Installation

```bash
helm repo add kedacore https://kedacore.github.io/charts
helm repo update
helm install keda kedacore/keda \
  --namespace keda \
  --create-namespace \
  --version 2.16.0

# Verify
kubectl get pods -n keda
kubectl get crd | grep keda
```

---

## Core Resources

| Resource | Purpose |
|---|---|
| `ScaledObject` | Scale a Deployment/StatefulSet based on external metrics |
| `ScaledJob` | Create K8s Jobs based on queue depth (1 pod per batch) |
| `TriggerAuthentication` | Store scaler credentials (refs to Secrets) |
| `ClusterTriggerAuthentication` | Cluster-scoped version of TriggerAuthentication |

---

## ScaledObject Template

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: my-scaler
  namespace: production
spec:
  scaleTargetRef:
    name: my-deployment        # Deployment to scale
    # kind: StatefulSet        # optional, default is Deployment
  minReplicaCount: 0           # 0 = scale to zero
  maxReplicaCount: 100
  pollingInterval: 30          # seconds between checks
  cooldownPeriod: 300          # seconds idle before scale to zero
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 60
  triggers:
  - type: <scaler-type>
    metadata:
      <scaler-specific-config>
    authenticationRef:
      name: my-trigger-auth    # optional
```

---

## Common Scalers

### AWS SQS

```yaml
triggers:
- type: aws-sqs-queue
  metadata:
    queueURL: https://sqs.us-east-1.amazonaws.com/123456789/my-queue
    queueLength: "5"           # target messages per pod
    awsRegion: us-east-1
  authenticationRef:
    name: aws-auth
```

### Kafka Consumer Lag

```yaml
triggers:
- type: kafka
  metadata:
    bootstrapServers: kafka.svc:9092
    consumerGroup: my-consumer-group
    topic: my-topic
    lagThreshold: "50"         # target lag per pod
    offsetResetPolicy: latest
```

### Prometheus

```yaml
triggers:
- type: prometheus
  metadata:
    serverAddress: http://prometheus.monitoring:9090
    metricName: http_requests
    threshold: "100"           # target value per pod
    query: sum(rate(http_requests_total{service="my-app"}[1m]))
```

### Cron (business hours scaling)

```yaml
triggers:
- type: cron
  metadata:
    timezone: America/New_York
    start: "0 8 * * 1-5"      # 8 AM Mon-Fri
    end: "0 18 * * 1-5"       # 6 PM Mon-Fri
    desiredReplicas: "10"      # scale to 10 during business hours
```

### Redis (list length)

```yaml
triggers:
- type: redis
  metadata:
    address: redis.svc:6379
    listName: job-queue
    listLength: "10"           # target: 10 items per pod
  authenticationRef:
    name: redis-auth
```

### RabbitMQ

```yaml
triggers:
- type: rabbitmq
  metadata:
    host: amqp://rabbitmq.svc:5672
    queueName: my-queue
    mode: QueueLength           # or MessageRate
    value: "20"
```

---

## TriggerAuthentication

```yaml
# Create a Secret with credentials
kubectl create secret generic aws-credentials \
  --from-literal=AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE \
  --from-literal=AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG

# TriggerAuthentication references the Secret
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: aws-auth
  namespace: production
spec:
  secretTargetRef:
  - parameter: awsAccessKeyID
    name: aws-credentials
    key: AWS_ACCESS_KEY_ID
  - parameter: awsSecretAccessKey
    name: aws-credentials
    key: AWS_SECRET_ACCESS_KEY
```

For EKS with IRSA (recommended):

```yaml
# Annotate the service account, no static credentials needed
apiVersion: v1
kind: ServiceAccount
metadata:
  name: keda-worker
  namespace: production
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789:role/keda-sqs-role
```

---

## ScaledJob Template

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledJob
metadata:
  name: batch-job-scaler
  namespace: production
spec:
  jobTargetRef:
    parallelism: 1
    completions: 1
    template:
      spec:
        restartPolicy: Never
        containers:
        - name: processor
          image: myrepo/processor:latest
  pollingInterval: 30
  maxReplicaCount: 50
  successfulJobsHistoryLimit: 5
  failedJobsHistoryLimit: 5
  scalingStrategy:
    strategy: default           # or accurate, eager
  triggers:
  - type: aws-sqs-queue
    metadata:
      queueURL: https://sqs.us-east-1.amazonaws.com/123456789/batch-q
      queueLength: "1"          # 1 job per message
      awsRegion: us-east-1
```

---

## kubectl Commands

```bash
# List all ScaledObjects
kubectl get scaledobjects -A

# Describe a ScaledObject (see status, triggers, HPA reference)
kubectl describe scaledobject my-scaler -n production

# List ScaledJobs
kubectl get scaledjobs -A

# Check the HPA that KEDA created
kubectl get hpa -n production
# NAME                 REFERENCE            TARGETS          MINPODS   MAXPODS
# keda-hpa-my-scaler   Deployment/workers   5000m/5000m (4)  1         100

# Check KEDA operator logs
kubectl logs -n keda -l app=keda-operator --tail=50

# Check metrics adapter logs
kubectl logs -n keda -l app=keda-operator-metrics-apiserver --tail=50

# Force scale to zero (for testing)
kubectl scale deployment my-deployment --replicas=0 -n production
```

---

## Scale to Zero Behavior

| State | Pods | Managed by |
|---|---|---|
| Queue empty > cooldownPeriod | 0 | KEDA Operator (bypasses HPA) |
| Queue has 1+ messages | 1 | KEDA Operator (activates) |
| Growing queue | 1 → N | HPA (KEDA manages metrics) |

```yaml
# Keep at least 1 pod (no cold start penalty)
spec:
  minReplicaCount: 1

# Allow full scale to zero (cold start ~10-30s)
spec:
  minReplicaCount: 0
  cooldownPeriod: 300   # wait 5 min before scaling to zero
```

---

## HPA vs KEDA Decision Guide

```
Is your workload queue/event-driven?          → KEDA
Do you need scale-to-zero?                    → KEDA
Do you need to scale on Prometheus metrics?   → KEDA
Do you need to scale on a cron schedule?      → KEDA
Simple CPU/memory scaling only?               → HPA (or KEDA with Prometheus)
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
