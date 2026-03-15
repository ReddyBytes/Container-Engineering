# Karpenter — Cheatsheet

## Installation (EKS)

```bash
# Set variables
export CLUSTER_NAME=my-cluster
export KARPENTER_VERSION=1.0.0
export KARPENTER_NAMESPACE=karpenter

# Install via Helm
helm upgrade --install karpenter \
  oci://public.ecr.aws/karpenter/karpenter \
  --version "${KARPENTER_VERSION}" \
  --namespace "${KARPENTER_NAMESPACE}" \
  --create-namespace \
  --set "settings.clusterName=${CLUSTER_NAME}" \
  --set "settings.interruptionQueue=${CLUSTER_NAME}" \
  --wait

# Verify
kubectl get pods -n karpenter
kubectl get crd | grep karpenter
```

---

## Core Resources

| Resource | Scope | Owner | Purpose |
|---|---|---|---|
| `NodePool` | Cluster | Platform team | Defines what nodes Karpenter can provision |
| `EC2NodeClass` | Cluster | Platform team | AWS-specific: AMI, subnets, security groups |
| `NodeClaim` | Cluster | Karpenter (auto) | Represents a specific node Karpenter launched |

---

## NodePool Template

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: general
spec:
  template:
    metadata:
      labels:
        nodepool: general
    spec:
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
      requirements:
      # Capacity type: spot, on-demand, or both
      - key: karpenter.sh/capacity-type
        operator: In
        values: ["spot", "on-demand"]
      # Instance families allowed
      - key: karpenter.k8s.aws/instance-family
        operator: In
        values: ["m5", "m6i", "m6a", "c5", "c6i", "r5"]
      # Architecture
      - key: kubernetes.io/arch
        operator: In
        values: ["amd64"]
      # Instance size constraints (optional)
      - key: karpenter.k8s.aws/instance-size
        operator: NotIn
        values: ["nano", "micro", "small"]
      # Topology / zones
      - key: topology.kubernetes.io/zone
        operator: In
        values: ["us-east-1a", "us-east-1b", "us-east-1c"]
      taints: []               # optional: taint all nodes from this pool
  limits:
    cpu: 500                   # max vCPUs across all nodes from this pool
    memory: 2000Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    budgets:
    - nodes: "10%"             # max 10% of nodes consolidated at once
```

---

## EC2NodeClass Template

```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default
spec:
  amiFamily: AL2023            # Amazon Linux 2023 (recommended EKS 1.30+)
  # amiFamily: Bottlerocket   # for security-focused clusters
  role: KarpenterNodeRole      # IAM instance role (not ARN, just name)
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster-name
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster-name
  # Optional: block device config
  blockDeviceMappings:
  - deviceName: /dev/xvda
    ebs:
      volumeSize: 100Gi
      volumeType: gp3
      encrypted: true
  # Optional: instance metadata
  metadataOptions:
    httpEndpoint: enabled
    httpPutResponseHopLimit: 1  # security: prevent SSRF attacks
    httpTokens: required        # IMDSv2 only
  tags:
    Environment: production
    ManagedBy: karpenter
    ClusterName: my-cluster
```

---

## Useful NodePool Requirements Keys

```yaml
# Capacity type
karpenter.sh/capacity-type: [spot, on-demand]

# Instance family
karpenter.k8s.aws/instance-family: [m5, m6i, c5, c6i, r5, r6i, t3]

# Instance size
karpenter.k8s.aws/instance-size: [medium, large, xlarge, 2xlarge, 4xlarge]

# Architecture
kubernetes.io/arch: [amd64, arm64]

# OS
kubernetes.io/os: [linux, windows]

# Zone
topology.kubernetes.io/zone: [us-east-1a, us-east-1b]

# GPU
karpenter.k8s.aws/instance-gpu-count: ["1", "4", "8"]
karpenter.k8s.aws/instance-accelerator-manufacturer: [nvidia, aws]
```

---

## Pod Annotations for Karpenter Control

```yaml
metadata:
  annotations:
    # Prevent this pod from being evicted during consolidation
    karpenter.sh/do-not-disrupt: "true"

    # Request a specific node pool
    karpenter.sh/nodepool: gpu-pool
```

---

## Consolidation Policies

```yaml
disruption:
  # Only remove completely empty nodes
  consolidationPolicy: WhenEmpty
  consolidateAfter: 30s

  # Evict and bin-pack underutilized nodes
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 1m

  # Control how many nodes can be consolidated at once
  budgets:
  - nodes: "10%"               # max 10% at any time (default)
  - nodes: "0"                 # block consolidation entirely (e.g., during deployments)
    schedule: "0 2 * * *"      # during scheduled maintenance window
    duration: 1h
```

---

## PodDisruptionBudget (Protect from Consolidation)

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: my-app-pdb
spec:
  minAvailable: 2              # always keep at least 2 pods
  # or: maxUnavailable: 1     # allow at most 1 pod down at once
  selector:
    matchLabels:
      app: my-app
```

Karpenter respects PDBs during consolidation. If evicting a pod would violate the PDB, Karpenter skips that node.

---

## kubectl Commands

```bash
# List all NodePools
kubectl get nodepools

# Describe a NodePool (see limits, disruption config, conditions)
kubectl describe nodepool general

# List NodeClaims (nodes Karpenter launched)
kubectl get nodeclaims

# Check which nodes are Karpenter-managed
kubectl get nodes -l karpenter.sh/nodepool

# Check node details (instance type, zone, capacity type)
kubectl get nodes -l karpenter.sh/nodepool \
  -o custom-columns='NAME:.metadata.name,TYPE:.metadata.labels.node\.kubernetes\.io/instance-type,ZONE:.metadata.labels.topology\.kubernetes\.io/zone,CAPACITY:.metadata.labels.karpenter\.sh/capacity-type'

# View Karpenter controller logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -f

# Force Karpenter to evaluate unschedulable pods
kubectl rollout restart deployment -n karpenter karpenter
```

---

## Common Karpenter Labels on Nodes

| Label | Example Value |
|---|---|
| `karpenter.sh/nodepool` | `general` |
| `karpenter.sh/capacity-type` | `spot` or `on-demand` |
| `node.kubernetes.io/instance-type` | `m6i.xlarge` |
| `topology.kubernetes.io/zone` | `us-east-1a` |
| `kubernetes.io/arch` | `amd64` or `arm64` |

---

## Karpenter vs Cluster Autoscaler Quick Ref

| | CA | Karpenter |
|---|---|---|
| Launch speed | 2-3 min | ~30s |
| Instance flexibility | 1 type per ASG | Hundreds evaluated dynamically |
| Spot support | Multi-ASG required | Native |
| Consolidation | Passive | Proactive |
| ARM/Graviton | Manual ASG | Native |

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
