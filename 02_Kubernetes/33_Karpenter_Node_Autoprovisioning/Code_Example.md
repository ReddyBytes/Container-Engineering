# Karpenter — Code Examples

Prerequisites: EKS cluster with Karpenter v1.0 installed. See [Theory.md](./Theory.md) for installation steps.

---

## Example 1: NodePool for General Workloads (Spot + On-Demand Mix)

A NodePool suitable for stateless web applications and workers. Uses multiple instance families for Spot availability diversification.

```yaml
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: general-purpose
spec:
  template:
    metadata:
      labels:
        nodepool: general-purpose
        billing-team: platform
    spec:
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default-nodeclass
      requirements:
      # Allow both Spot and On-Demand; Karpenter prefers Spot (cheaper)
      - key: karpenter.sh/capacity-type
        operator: In
        values: ["spot", "on-demand"]
      # Wide range of instance families for Spot diversification
      # More families = better Spot availability, lower interruption rate
      - key: karpenter.k8s.aws/instance-family
        operator: In
        values:
        - m5
        - m5a
        - m6i
        - m6a
        - m7i
        - c5
        - c5a
        - c6i
        - c6a
        - c7i
        - r5
        - r6i
      # Only amd64 (x86); separate NodePool for arm64 if needed
      - key: kubernetes.io/arch
        operator: In
        values: ["amd64"]
      # Exclude tiny instances (not cost-effective for most workloads)
      - key: karpenter.k8s.aws/instance-size
        operator: NotIn
        values: ["nano", "micro", "small"]
      # Spread across availability zones for resilience
      - key: topology.kubernetes.io/zone
        operator: In
        values: ["us-east-1a", "us-east-1b", "us-east-1c"]
      # Expiry: nodes are replaced after 30 days (forces AMI updates, security patches)
      expireAfter: 720h         # 30 days

  # Hard cap on total resources from this NodePool
  limits:
    cpu: "1000"
    memory: 4000Gi

  # Proactive consolidation: bin-pack underutilized nodes
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 2m        # wait 2 min after underutilization before acting
    budgets:
    # Never consolidate more than 10% of nodes at once
    - nodes: "10%"
    # More aggressive during off-peak hours (saves money overnight)
    - schedule: "0 22 * * *"   # 10 PM every night
      duration: 8h
      nodes: "25%"
```

---

## Example 2: NodePool for GPU Workloads

A dedicated GPU NodePool with a taint so only GPU-aware pods land here. Uses p3, p4d, and g4dn instance families.

```yaml
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: gpu-workers
spec:
  template:
    metadata:
      labels:
        nodepool: gpu-workers
        workload-type: gpu
    spec:
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: gpu-nodeclass        # separate EC2NodeClass with GPU-optimized AMI
      # Taint: only pods that tolerate "gpu=true" will be scheduled here
      taints:
      - key: nvidia.com/gpu
        value: "true"
        effect: NoSchedule
      requirements:
      # GPU instances only (both Spot and On-Demand for flexibility)
      - key: karpenter.sh/capacity-type
        operator: In
        values: ["spot", "on-demand"]
      - key: karpenter.k8s.aws/instance-family
        operator: In
        values:
        - p3          # V100 GPUs — good for training
        - p4d         # A100 GPUs — best for large model training
        - g4dn        # T4 GPUs — cost-effective for inference
        - g5          # A10G GPUs — good for inference and training
      - key: kubernetes.io/arch
        operator: In
        values: ["amd64"]
      - key: karpenter.k8s.aws/instance-gpu-count
        operator: Gt
        values: ["0"]             # must have at least 1 GPU

  limits:
    cpu: "256"
    memory: 2000Gi
    # Limit GPUs to control cost
    nvidia.com/gpu: "32"

  disruption:
    # Conservative for GPU nodes — training jobs are expensive to restart
    consolidationPolicy: WhenEmpty
    consolidateAfter: 5m

---
# EC2NodeClass for GPU — uses GPU-optimized AMI
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: gpu-nodeclass
spec:
  amiFamily: AL2023
  role: KarpenterNodeRole
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  blockDeviceMappings:
  - deviceName: /dev/xvda
    ebs:
      volumeSize: 200Gi         # larger root volume for model weights
      volumeType: gp3
      iops: 6000
      throughput: 500           # MB/s
      encrypted: true
  tags:
    workload-type: gpu
    ManagedBy: karpenter

---
# Example GPU pod (must tolerate the GPU taint)
apiVersion: v1
kind: Pod
metadata:
  name: gpu-training-job
spec:
  tolerations:
  - key: nvidia.com/gpu
    value: "true"
    effect: NoSchedule
  nodeSelector:
    workload-type: gpu
  containers:
  - name: trainer
    image: nvcr.io/nvidia/pytorch:24.01-py3
    resources:
      requests:
        nvidia.com/gpu: "1"
        cpu: 8
        memory: 32Gi
      limits:
        nvidia.com/gpu: "1"
```

---

## Example 3: EC2NodeClass (Full Configuration)

A complete EC2NodeClass covering all common configuration options.

```yaml
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default-nodeclass
  annotations:
    # Document the last time this was reviewed
    last-reviewed: "2024-10-01"
spec:
  # AMI family — determines the base OS and bootstrapping method
  # AL2023 is recommended for EKS 1.30+
  # Options: AL2, AL2023, Bottlerocket, Windows2019, Windows2022, Custom
  amiFamily: AL2023

  # IAM instance role (the role name, not ARN)
  # Must have the AmazonEKSWorkerNodePolicy, AmazonEKS_CNI_Policy, etc.
  role: KarpenterNodeRole

  # Subnet selection by tag
  # Karpenter will use any subnet matching these tags
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
      kubernetes.io/role/internal-elb: "1"   # private subnets only

  # Security group selection by tag
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster

  # EBS volume configuration
  blockDeviceMappings:
  - deviceName: /dev/xvda     # root volume (AL2023/AL2)
    ebs:
      volumeSize: 100Gi
      volumeType: gp3
      iops: 3000              # gp3 baseline; up to 16000
      throughput: 125         # MB/s; up to 1000 for gp3
      encrypted: true
      deleteOnTermination: true

  # IMDSv2 (security best practice — prevents SSRF attacks)
  metadataOptions:
    httpEndpoint: enabled
    httpPutResponseHopLimit: 1   # 1 = only the instance itself; 2 would allow containers
    httpTokens: required         # require IMDSv2 tokens

  # User data — custom bootstrap script (AL2023 format)
  # Most clusters don't need this; use for custom node configuration
  userData: |
    #!/bin/bash
    # Enable kernel parameter for conntrack
    sysctl -w net.netfilter.nf_conntrack_max=524288

  # Tags applied to all EC2 instances launched by this NodeClass
  tags:
    Environment: production
    ManagedBy: karpenter
    ClusterName: my-cluster
    CostCenter: platform-engineering
    # Required for Cost Allocation in AWS
    aws:eks:cluster-name: my-cluster
```

---

## Example 4: PodDisruptionBudget to Protect from Karpenter Consolidation

These PDBs ensure Karpenter cannot disrupt your services below a safe threshold during consolidation.

```yaml
---
# Protect a stateless web API: always keep at least 2 pods
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api-pdb
  namespace: production
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: api-service

---
# Protect a database: never allow more than 0 simultaneous disruptions
# (i.e., always keep all pods)
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: postgres-pdb
  namespace: production
spec:
  maxUnavailable: 0            # no voluntary disruptions allowed
  selector:
    matchLabels:
      app: postgres

---
# Protect a Kafka cluster: allow at most 1 broker down at a time
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: kafka-pdb
  namespace: kafka
spec:
  maxUnavailable: 1
  selector:
    matchLabels:
      app.kubernetes.io/component: kafka-broker

---
# Deployment with PDB (complete example)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-service
  namespace: production
spec:
  replicas: 5
  selector:
    matchLabels:
      app: api-service
  template:
    metadata:
      labels:
        app: api-service
    spec:
      topologySpreadConstraints:
      # Spread across zones so consolidation of one zone doesn't break the PDB
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: api-service
      containers:
      - name: api
        image: myrepo/api:latest
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
```

---

## Example 5: Annotations to Control Karpenter Behavior Per Pod

```yaml
---
# Example 1: Long-running batch job — prevent consolidation eviction
apiVersion: batch/v1
kind: Job
metadata:
  name: weekly-data-pipeline
  namespace: batch
spec:
  template:
    metadata:
      annotations:
        # Tell Karpenter: do not evict this pod for consolidation
        karpenter.sh/do-not-disrupt: "true"
      labels:
        app: data-pipeline
    spec:
      restartPolicy: Never
      containers:
      - name: pipeline
        image: myrepo/data-pipeline:latest
        resources:
          requests:
            cpu: 4
            memory: 16Gi

---
# Example 2: Force a pod to use on-demand (not Spot) via nodeSelector
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stateful-service
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: stateful-service
  template:
    metadata:
      labels:
        app: stateful-service
    spec:
      nodeSelector:
        # Only schedule on on-demand nodes (Karpenter provisions accordingly)
        karpenter.sh/capacity-type: on-demand
      containers:
      - name: app
        image: myrepo/stateful-service:latest

---
# Example 3: Target a specific NodePool with nodeAffinity
apiVersion: apps/v1
kind: Deployment
metadata:
  name: memory-intensive-app
  namespace: production
spec:
  replicas: 2
  selector:
    matchLabels:
      app: memory-intensive
  template:
    metadata:
      labels:
        app: memory-intensive
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              # Only schedule on nodes from the 'memory-optimized' NodePool
              - key: nodepool
                operator: In
                values: ["memory-optimized"]
      containers:
      - name: app
        image: myrepo/memory-intensive:latest
        resources:
          requests:
            cpu: 2
            memory: 30Gi       # Karpenter will provision r5/r6i instances

---
# Example 4: Topology spread to prevent Karpenter from over-packing one zone
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-frontend
  namespace: production
spec:
  replicas: 6
  selector:
    matchLabels:
      app: web-frontend
  template:
    metadata:
      labels:
        app: web-frontend
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web-frontend
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname   # also spread across nodes
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: web-frontend
      containers:
      - name: frontend
        image: myrepo/frontend:latest
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
```

---

## 📂 Navigation

| | |
|---|---|
| Previous | [32_KEDA_Event_Driven_Autoscaling](../32_KEDA_Event_Driven_Autoscaling/) |
| Next | [34_eBPF_and_Cilium](../34_eBPF_and_Cilium/) |
| Up | [02_Kubernetes](../) |

**Files in this module:**
- [Theory.md](./Theory.md) — Concepts and architecture
- [Cheatsheet.md](./Cheatsheet.md) — Quick reference
- [Interview_QA.md](./Interview_QA.md) — Common interview questions
- [Code_Example.md](./Code_Example.md) — Working YAML examples
