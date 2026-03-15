# Jobs and CronJobs — Interview Q&A

---

**Q1: What is the difference between a Job and a Deployment in Kubernetes?**

A Deployment is designed to keep pods running indefinitely — if a pod dies, it is replaced. It manages long-running stateless services. A Job is designed to run pods to completion — once the desired number of successful completions is reached, the Job is done. If a Job pod exits with code 0, that counts as a successful completion. Jobs are for finite batch work: migrations, reports, data processing. Using a Deployment for batch work causes infinite re-running because Kubernetes replaces exiting pods.

---

**Q2: What is `backoffLimit` and what happens when it is reached?**

`backoffLimit` (default: 6) is the maximum number of pod failures the Job will tolerate before marking the Job itself as failed. Each pod failure increments the failure counter. The backoff time between retries increases exponentially (10s, 20s, 40s... up to 6 minutes). When `backoffLimit` is reached, no more pods are created, the Job status is set to `Failed`, and a `BackoffLimitExceeded` event is generated. Existing pods are terminated. You must manually investigate and re-create the Job or fix the underlying issue.

---

**Q3: What is the difference between `completions` and `parallelism` in a Job?**

`completions` is the total number of successful pod completions required for the Job to succeed. `parallelism` is the maximum number of pods that can run concurrently at any point.

Example: `completions: 100, parallelism: 10` means "run 100 successful tasks, but no more than 10 at the same time." If you need to process 100 items and each pod processes one item, this configuration parallelizes the work 10-fold.

---

**Q4: What are the three CronJob concurrency policies?**

1. **Allow** (default): Create a new Job even if the previous one is still running. Risks: multiple concurrent runs, resource contention, potential data conflicts.
2. **Forbid**: Skip the new Job if the previous one is still running. Best for idempotent jobs where you want exactly one run at a time. If the schedule fires during an active run, that schedule slot is simply skipped.
3. **Replace**: Cancel the currently running Job and start a fresh one. Use when "latest is best" — for example, a report generator where you always want the most recent data, not a report from a run that started 50 minutes ago.

---

**Q5: What happens if a CronJob misses its schedule?**

If `startingDeadlineSeconds` is not set, Kubernetes allows a CronJob to start even if it is late (e.g., the scheduler was down). If `startingDeadlineSeconds` is set, the CronJob is skipped if it cannot start within that many seconds of its scheduled time. Additionally, if a CronJob misses more than 100 scheduled runs (e.g., because it was suspended or the cluster was down for a long time), Kubernetes will not try to catch up — it logs an error and starts fresh from the next scheduled time.

---

**Q6: What restartPolicy should a Job pod use?**

Job pods must use either `Never` or `OnFailure`. They must NOT use `Always` (the default for Deployment pods). With `Always`, the pod would restart on success, fighting with the Job controller which expects pods to exit cleanly. The difference between `Never` and `OnFailure` is where the retry happens: `Never` leaves the failed pod in place and creates a new pod (preserving logs); `OnFailure` restarts the container in the same pod.

---

**Q7: What is `ttlSecondsAfterFinished` and why would you use it?**

`ttlSecondsAfterFinished` is a Job field that causes the Job (and its pods) to be automatically deleted N seconds after the Job completes or fails. Without it, completed Jobs and their pods accumulate indefinitely, cluttering the cluster and consuming etcd storage. Setting `ttlSecondsAfterFinished: 3600` (1 hour) gives you time to inspect logs after completion before automatic cleanup. For high-frequency CronJobs, this is important — a CronJob running every minute creates 1,440 Jobs per day without cleanup.

---

**Q8: How do you manually trigger a CronJob without waiting for its schedule?**

```bash
kubectl create job <manual-name> \
  --from=cronjob/<cronjob-name> \
  -n <namespace>
```

This creates a Job using the CronJob's job template. The manually triggered Job runs immediately and is independent of the schedule. This is useful for testing, for running a missed run on demand, or for running a CronJob after a config change without waiting for the next schedule.

---

**Q9: What is the work queue pattern for Jobs?**

In the work queue pattern, `completions` is not set (or set to 1) and `parallelism` is set to N. Each pod pulls a work item from an external queue (RabbitMQ, SQS, Redis list, Kafka), processes it, and loops until the queue is empty — at which point the pod exits with code 0. The Job controller considers the overall Job complete when enough pods exit successfully (usually 1 in this pattern, since "the queue is empty" is a global state, not a per-pod count).

This pattern is useful when the total number of items to process is unknown at Job creation time.

---

**Q10: How does a CronJob relate to a Job — what is the ownership structure?**

A CronJob owns Jobs. At each scheduled time, the CronJob controller creates a new Job object based on the CronJob's `jobTemplate`. Each Job in turn owns the pods it creates. Deleting a CronJob does not immediately delete running Jobs it created (they continue to completion), but future scheduled runs are canceled. The CronJob tracks recent Jobs in its status (`status.active`, `status.lastScheduleTime`). `successfulJobsHistoryLimit` and `failedJobsHistoryLimit` control how many old Jobs the CronJob keeps in its history for inspection.

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Theory.md](./Theory.md) |
| Cheatsheet | [Cheatsheet.md](./Cheatsheet.md) |
| Code Example | [Code_Example.md](./Code_Example.md) |
| Module Home | [17_Jobs_and_CronJobs](../) |
