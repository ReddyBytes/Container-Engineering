# Deployment Strategies — Interview Q&A

---

**Q1: What deployment strategies are available in Kubernetes and what are the trade-offs?**

Kubernetes natively supports two strategies in the Deployment spec:
1. **Recreate**: Terminates all old pods before starting new ones. Causes downtime but ensures only one version runs at a time. Good for environments where two versions cannot coexist.
2. **RollingUpdate** (default): Replaces pods gradually, controlled by `maxSurge` and `maxUnavailable`. No downtime with proper configuration. Both versions run simultaneously during the rollout.

Additional strategies implemented outside the Deployment spec:
3. **Blue/Green**: Two full environments, instant traffic cutover via Service selector change. Requires 2x resources but enables instant rollback.
4. **Canary**: Small percentage of traffic goes to the new version. Observe real traffic behavior before full rollout. Risk is contained to a fraction of users.
5. **A/B Testing**: Route specific user segments to specific versions based on request attributes (headers, cookies). Used for feature experiments, not infrastructure safety.

---

**Q2: What are `maxSurge` and `maxUnavailable` in a RollingUpdate deployment?**

`maxSurge` defines the maximum number of pods that can exist above the desired replica count during a rollout. Setting `maxSurge: 1` on a 10-replica deployment means up to 11 pods run during the rollout. Setting it to 0 means no extra pods are created — old pods are deleted first.

`maxUnavailable` defines the maximum number of pods that can be unavailable during a rollout. Setting `maxUnavailable: 0` means the rollout never removes an old pod until its replacement is healthy (readiness probe passing). This guarantees full capacity throughout the rollout at the cost of needing extra resources.

For zero-downtime deployments: `maxSurge: 1, maxUnavailable: 0`.

---

**Q3: How does a Blue/Green deployment work in Kubernetes?**

Blue/Green deployment maintains two full Deployments (blue = current version, green = new version) behind a single Service. The Service uses a label selector to route traffic. To deploy:
1. Deploy the green Deployment with the new image
2. Wait for all green pods to pass readiness probes
3. Change the Service selector from `version: blue` to `version: green`

Traffic instantly shifts to the new version. If something goes wrong, change the selector back to blue — instant rollback. Once the green deployment is confirmed stable, delete the blue Deployment.

In Kubernetes, this selector change is done with `kubectl patch service`.

---

**Q4: What is a canary deployment and how is it implemented in Kubernetes?**

A canary deployment sends a small fraction of traffic to the new version while the majority continues on the old version. In native Kubernetes, the simplest approach is two Deployments sharing the same Service label:
- `my-app-v1`: 9 replicas (old version)
- `my-app-v2`: 1 replica (canary)

Since the Service routes traffic proportionally to pod count, approximately 10% of requests go to the canary. Monitor error rates and latency. If healthy, gradually scale v2 up and v1 down. If issues appear, scale v2 to 0.

For precise traffic percentages independent of pod count, use Ingress-level traffic splitting or a service mesh like Istio.

---

**Q5: What is the difference between a canary deployment and A/B testing?**

Canary splits traffic randomly (by percentage) to detect issues before full rollout. It is a safety mechanism — a small random sample of real users hit the new version. A/B testing routes specific, deterministic user segments to specific versions based on request attributes like cookies, headers, or user IDs. It is an experiment designed to measure the impact of a change on a specific cohort.

Canary: random 10% of users → new version (safety).
A/B: users with cookie `beta=true` → new version (measurement).

---

**Q6: How do you pause and resume a rolling deployment in Kubernetes?**

```bash
kubectl rollout pause deployment/<name> -n <namespace>
kubectl rollout resume deployment/<name> -n <namespace>
```

Pausing is useful for implementing manual canary-style rollouts: update the image, which starts replacing pods. After some pods are replaced, pause. Monitor the new pods. If metrics look good, resume. This gives you manual control over rollout progress without needing Argo Rollouts.

---

**Q7: What is Argo Rollouts and when would you use it over native Kubernetes strategies?**

Argo Rollouts is a Kubernetes controller that extends Deployment with advanced rollout strategies including automated canary analysis and blue/green deployments. Key features:
- **Automated metric-based promotion**: if error rate on canary is below threshold, automatically promote; if above, automatically roll back
- **Step-based canary**: define a sequence of steps (10% → wait 5 minutes → 25% → analyze → 50% → 100%)
- **Integrations**: Prometheus, Datadog, Dynatrace, CloudWatch for metric gates
- **Argo CD integration**: native GitOps workflow support

Use native Kubernetes strategies for simpler applications. Use Argo Rollouts when you need automated progressive delivery with metric-based gates.

---

**Q8: Why is it important that both versions can coexist during a RollingUpdate?**

During a rolling update, both old and new pods handle production traffic simultaneously. This means:
- API responses must be compatible between versions (no breaking API changes)
- Database schema must be compatible with both versions (additive-only migrations during rollout)
- Session state must be shareable or sticky (a user might hit v1 for one request and v2 for the next)

This is why database migrations during rolling updates use the "expand and contract" pattern: first add the new column (v1 and v2 both work), then deploy v2, then remove the old column (once v1 is gone).

---

**Q9: How do you roll back a deployment and how quickly does it happen?**

Rolling back a Kubernetes Deployment:
```bash
kubectl rollout undo deployment/<name>              # roll back to previous
kubectl rollout undo deployment/<name> --to-revision=3  # specific revision
```

Rollback is another rolling update — it gradually replaces new pods with old pods at the same rate as the original rollout. It is NOT instant. For instant rollback, use Blue/Green deployment where you simply change the Service selector.

Kubernetes keeps rollout history (by default, 10 revisions) via `revisionHistoryLimit` in the Deployment spec.

---

**Q10: What happens if a rolling update gets stuck?**

A rolling update stalls if new pods never pass their readiness probe. The deployment controller stops removing old pods (to preserve service) and cannot make progress. Symptoms:
- `kubectl rollout status` hangs
- Some old pods, some new pods, new ones all show `0/1 Ready`

To investigate: `kubectl describe pod <new-pod>` (check events), `kubectl logs <new-pod>` (check application errors). To resolve: fix the underlying issue (wrong image, missing config, crashing app) and update the deployment again, or roll back with `kubectl rollout undo`.

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Theory.md](./Theory.md) |
| Cheatsheet | [Cheatsheet.md](./Cheatsheet.md) |
| Module Home | [15_Deployment_Strategies](../) |
