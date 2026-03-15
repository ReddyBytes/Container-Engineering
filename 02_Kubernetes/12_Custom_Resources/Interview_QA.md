# Custom Resources — Interview Q&A

---

**Q1: What is a CRD and what does it enable?**

A CRD (CustomResourceDefinition) is a Kubernetes object that registers a new resource type with the API server. Once a CRD is installed, users can create, list, update, and delete instances of the new type (Custom Resources) using kubectl and the Kubernetes API — exactly like built-in resources. CRDs enable extending Kubernetes to understand domain-specific concepts like `PostgresCluster`, `Certificate`, or `Kafka`.

---

**Q2: What is the difference between a CRD and a Custom Resource?**

A CRD is the schema or type definition — it defines the structure, validation rules, and metadata for a new resource type. A Custom Resource (CR) is an instance of a CRD — actual data stored in etcd representing a specific desired state. The relationship is like a class (CRD) and an object (CR) in object-oriented programming.

---

**Q3: What is the Operator pattern?**

The Operator pattern combines a CRD with a custom controller to automate the lifecycle of complex, stateful applications. The CRD defines what the user wants (desired state). The custom controller (operator) watches for changes to CRs and reconciles the cluster's actual state to match. Operators encode operational knowledge — backup procedures, failover logic, configuration management — that previously required manual human intervention.

---

**Q4: What is a reconcile loop?**

A reconcile loop is the core pattern of a Kubernetes controller. When a resource changes (created, updated, or deleted), or periodically on a timer, the reconcile function is called. It:
1. Reads the current desired state from the CR spec
2. Observes the current actual state of cluster resources
3. Calculates the difference (delta)
4. Takes action to bring actual state in line with desired state
5. Updates the CR's status subresource to reflect what was observed

The loop is designed to be idempotent — running it many times should produce the same result.

---

**Q5: Can you name three real-world operators and what they manage?**

1. **cert-manager**: Manages TLS certificates. Users create `Certificate` CRs specifying domain names; cert-manager automatically requests certificates from Let's Encrypt (or other ACME issuers), stores them in Secrets, and renews them before expiry.

2. **Strimzi**: Manages Apache Kafka clusters. Users create a `Kafka` CR; Strimzi provisions ZooKeeper (or KRaft), Kafka brokers, and services. It handles rolling upgrades, topic management via `KafkaTopic` CRs, and user access via `KafkaUser` CRs.

3. **CloudNativePG**: Manages PostgreSQL HA clusters. Users define a `Cluster` CR; the operator manages primary/replica topology, automatic failover, scheduled backups, and connection pooling.

---

**Q6: When should you use an Operator instead of Helm?**

Use Helm for stateless applications or for one-time installations where "apply manifests, done" is sufficient. Use an Operator when:
- The application is stateful and requires ongoing lifecycle management (backups, failover)
- Operations need to react to runtime events (a pod dies, trigger failover)
- Day-2 operations (upgrades, scaling, recovery) are complex and error-prone manually
- The application has internal state that Kubernetes does not natively understand

Many operators actually use Helm internally for the initial install (Level 1), then provide additional reconciliation logic for higher maturity operations.

---

**Q7: What is the status subresource in a Custom Resource?**

The status subresource is the portion of a CR that the operator writes to report current observed state back to users. It is separate from the spec (which the user writes). This separation is important: kubectl apply and user edits target the spec, while the operator exclusively manages status. Common status fields include phase (Running, Failed, Pending), ready replica counts, and Kubernetes-style Condition objects with type, status, and lastTransitionTime.

---

**Q8: What happens to Custom Resource instances when you delete a CRD?**

All Custom Resource instances are deleted along with the CRD. This is a destructive operation. If you have a production `PostgresCluster` CR representing a running database, deleting the CRD will delete that CR, and a well-written operator will then interpret that as a deletion request and may attempt to deprovision the database. CRDs should only be deleted intentionally and with care.

---

**Q9: What is CRD versioning and why does it matter?**

CRDs support multiple API versions (e.g., `v1alpha1`, `v1beta1`, `v1`) within the same resource type. This matters because as an operator matures, the schema evolves. Versioning lets you:
- Introduce new fields without breaking existing users
- Deprecate old fields gradually (mark `served: false` for old versions)
- Use conversion webhooks to automatically translate between versions
- Only one version can be the storage version (what is written to etcd)

---

**Q10: What tools exist for building operators?**

- **Kubebuilder** (Go): The most widely used framework. Generates scaffolding, CRD manifests from Go struct annotations, and controller boilerplate.
- **Operator SDK** (Go, Ansible, Helm): Red Hat's framework, wraps controller-runtime. Supports non-Go operators via Ansible playbooks or Helm charts.
- **kopf** (Python): Lightweight Python framework. Good for simple operators without Go expertise.
- **Java Operator SDK**: For Java/JVM teams.
- **shell-operator**: Triggers shell scripts on K8s events — minimal code, quick prototyping.

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Theory.md](./Theory.md) |
| Cheatsheet | [Cheatsheet.md](./Cheatsheet.md) |
| Module Home | [12_Custom_Resources](../) |
