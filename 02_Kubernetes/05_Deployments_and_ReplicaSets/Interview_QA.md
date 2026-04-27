# Module 05 — Interview Q&A: Deployments and ReplicaSets

---

**Q1: What is the difference between a ReplicaSet and a Deployment?**

A **ReplicaSet** ensures a specified number of identical pod replicas are running at any time.
It has a label selector, a replica count, and a pod template. If pods crash or are deleted, it
creates replacements. However, ReplicaSets have no concept of update history — if you change the
pod template, existing pods are not updated.

A **Deployment** manages ReplicaSets and adds update and rollback capabilities. When you update
a Deployment's pod template, it creates a new ReplicaSet, scales it up, and scales down the old
one (rolling update). Old ReplicaSets are retained as history, enabling rollback. In practice,
you should almost always use Deployments rather than ReplicaSets directly.

---

**Q2: How does a rolling update work in Kubernetes?**

When a Deployment's pod template changes (e.g., image update), Kubernetes creates a new ReplicaSet
with the updated template. It then runs a rolling update loop:
1. Scale up the new ReplicaSet by 1 (or maxSurge)
2. Wait for the new pod to become Ready
3. Scale down the old ReplicaSet by 1 (or maxUnavailable)
4. Repeat until the new ReplicaSet is at full capacity and the old is at zero

The parameters `maxUnavailable` (how many old pods can be down) and `maxSurge` (how many extra
pods above desired count) control the pace and availability during the rollout.

---

**Q3: What are `maxUnavailable` and `maxSurge` in a Deployment?**

Both are defined under `spec.strategy.rollingUpdate` and can be absolute numbers or percentages
(of the desired replica count).

- **maxUnavailable**: the maximum number of pods that can be unavailable during the update.
  Setting this to 0 means the rollout never reduces capacity below the desired count.
- **maxSurge**: the maximum number of pods that can exceed the desired replica count during
  the update. Setting this to 0 means you stay at exactly `replicas` at all times.

You cannot set both to 0 simultaneously. Common production settings: `maxUnavailable: 0,
maxSurge: 1` (zero-downtime, one-at-a-time rollout) or `maxUnavailable: 25%, maxSurge: 25%`.

---

**Q4: How do you roll back a Deployment?**

```bash
kubectl rollout undo deployment/my-app               # go back one revision
kubectl rollout undo deployment/my-app --to-revision=3  # go back to revision 3
```

Kubernetes keeps old ReplicaSets as rollback history. The number retained is controlled by
`spec.revisionHistoryLimit` (default: 10). Rolling back simply sets the desired state to use
the previous ReplicaSet's pod template, which immediately triggers a rolling update in reverse.

---

**Q5: What does `kubectl rollout status` tell you?**

It shows whether a rollout is complete, in progress, or has failed. It blocks and streams
progress updates until the rollout completes or times out (controlled by `progressDeadlineSeconds`).
Example output:
- `Waiting for deployment rollout to finish: 1 out of 3 new replicas have been updated...`
- `deployment "my-app" successfully rolled out`
- `error: deployment "my-app" exceeded its progress deadline`

It is useful in CI/CD pipelines to block the pipeline until the deployment is confirmed healthy.

---

**Q6: What happens to pods when you delete a Deployment?**

By default, deleting a Deployment also deletes its ReplicaSets and all pods managed by those
ReplicaSets. This is called a "cascading delete." If you want to delete the Deployment but keep
the pods running (orphan them), you use `--cascade=orphan`. The pods then lose their owner
reference and become "standalone" pods that are no longer managed by any controller.

---

**Q7: How do labels and selectors work with Deployments?**

The `spec.selector.matchLabels` field defines which pods the Deployment considers "its own."
The `spec.template.metadata.labels` must include all labels defined in the selector. If you
accidentally create pods with the same labels outside the Deployment, the Deployment may adopt
or delete them depending on the replica count. The selector is immutable after creation — to
change it, you must delete and recreate the Deployment.

---

**Q8: What is the Recreate deployment strategy and when do you use it?**

With `strategy.type: Recreate`, Kubernetes deletes all existing pods before creating new ones.
This causes downtime but ensures only one version of the application runs at a time.

Use it when:
- Your application cannot run two versions simultaneously (e.g., it holds an exclusive database
  lock that only one instance can hold)
- Your application stores incompatible state in a shared volume
- You're managing a stateful app that handles schema migrations on startup

For most stateless services, RollingUpdate is the right choice.

---

**Q9: Can you update a Deployment without downtime?**

Yes, if you configure it correctly:
- Use `strategy.type: RollingUpdate` (the default)
- Set `maxUnavailable: 0` to ensure capacity never drops below desired
- Ensure your pods have readiness probes — Kubernetes only considers a new pod "available"
  once its readiness probe succeeds, preventing traffic from going to not-yet-ready containers
- Ensure your application handles graceful shutdown (responds to SIGTERM, finishes in-flight
  requests, then exits)

---

**Q10: What is `revisionHistoryLimit` and why does it matter?**

`spec.revisionHistoryLimit` controls how many old ReplicaSets Kubernetes keeps for rollback
(default: 10). Each old ReplicaSet has 0 replicas but still occupies API server storage (etcd).
In a busy cluster with frequent deployments, this can accumulate thousands of empty ReplicaSets.

Setting it too low (e.g., 1) means you can only roll back to the immediately previous version.
A value of 5–10 is typically a good balance.

---

**Q11: How do you pause a rollout and why would you?**

`kubectl rollout pause deployment/my-app` halts the rolling update mid-way or prevents one from
starting. Any changes made while paused are accumulated but not rolled out until you run
`kubectl rollout resume deployment/my-app`.

Use cases:
- Make multiple changes (image + resource limits + env vars) and roll them out together as
  one combined update rather than triggering three separate rollouts
- Verify partial rollout health on a subset of pods before proceeding

---

**Q12: How does a Deployment know which ReplicaSet is the "current" one?**

The Deployment controller uses the `deployment.kubernetes.io/revision` annotation on ReplicaSets
to track versions. The current ReplicaSet is the one with the highest revision number that has
the same pod template hash as the Deployment's current template. The Deployment stores its
current template hash in `spec.selector.matchLabels["pod-template-hash"]` and stamps every new
pod with the same label. This ensures pods are unambiguously assigned to the correct ReplicaSet.

---

## 📂 Navigation

| File | Description |
|------|-------------|
| [Theory.md](./Theory.md) | Deployments and ReplicaSets explained |
| [Cheatsheet.md](./Cheatsheet.md) | Quick reference commands |
| [Interview_QA.md](./Interview_QA.md) | You are here — interview questions |
| [Code_Example.md](./Code_Example.md) | Working YAML examples |

**Previous:** [04_Pods](../04_Pods/Interview_QA.md) |
**Next:** [06_Services](../06_Services/Theory.md)
