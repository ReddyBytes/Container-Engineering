# Jobs and CronJobs Cheatsheet

## Key Parameters Quick Reference

| Parameter | Object | Default | Meaning |
|-----------|--------|---------|---------|
| `completions` | Job | 1 | Total successful pod completions needed |
| `parallelism` | Job | 1 | Max pods running simultaneously |
| `backoffLimit` | Job | 6 | Max pod failures before Job fails |
| `activeDeadlineSeconds` | Job | — | Kill Job if it runs longer than this |
| `ttlSecondsAfterFinished` | Job | — | Auto-delete completed Job after N seconds |
| `concurrencyPolicy` | CronJob | Allow | Allow/Forbid/Replace concurrent runs |
| `successfulJobsHistoryLimit` | CronJob | 3 | Keep last N successful Jobs |
| `failedJobsHistoryLimit` | CronJob | 1 | Keep last N failed Jobs |
| `startingDeadlineSeconds` | CronJob | — | Skip if can't start within N seconds of schedule |
| `suspend` | CronJob | false | Pause CronJob without deleting it |

---

## kubectl Commands

```bash
# --- Jobs ---

# List all Jobs
kubectl get jobs -n <namespace>
kubectl get jobs -A          # all namespaces

# Describe a Job (see parallelism, completions, status)
kubectl describe job <name> -n <namespace>

# Get Job status
kubectl get job <name> -n <namespace> \
  -o jsonpath='{.status}'

# View logs from a Job's pod(s)
kubectl logs job/<job-name> -n <namespace>

# View logs from a specific Job pod
kubectl logs <pod-name> -n <namespace>

# List pods created by a Job
kubectl get pods -n <namespace> --selector=job-name=<job-name>

# Create a Job from a CronJob spec (manual trigger)
kubectl create job <name> \
  --from=cronjob/<cronjob-name> \
  -n <namespace>

# Delete a Job (and its pods)
kubectl delete job <name> -n <namespace>

# Delete all completed Jobs (cleanup)
kubectl delete jobs -n <namespace> \
  --field-selector=status.successful=1

# Wait for a Job to complete
kubectl wait --for=condition=complete \
  job/<job-name> \
  -n <namespace> \
  --timeout=300s

# Wait for a Job to fail (useful in CI/CD)
kubectl wait --for=condition=failed \
  job/<job-name> \
  -n <namespace> \
  --timeout=300s

# --- CronJobs ---

# List all CronJobs
kubectl get cronjobs -n <namespace>
kubectl get cj -n <namespace>         # short form
kubectl get cj -A

# Describe a CronJob
kubectl describe cronjob <name> -n <namespace>

# View last schedule time and next schedule time
kubectl get cj <name> -n <namespace> \
  -o jsonpath='{.status.lastScheduleTime}'

# Suspend a CronJob (pause without deleting)
kubectl patch cronjob <name> -n <namespace> \
  -p '{"spec":{"suspend":true}}'

# Resume a CronJob
kubectl patch cronjob <name> -n <namespace> \
  -p '{"spec":{"suspend":false}}'

# Manually trigger a CronJob immediately
kubectl create job --from=cronjob/<name> \
  <name>-manual-$(date +%s) \
  -n <namespace>

# View Jobs created by a CronJob
kubectl get jobs -n <namespace> \
  --selector=batch.kubernetes.io/controller-uid=$(
    kubectl get cronjob <name> -n <namespace> \
    -o jsonpath='{.metadata.uid}')

# Delete a CronJob (keeps existing Jobs running)
kubectl delete cronjob <name> -n <namespace>

# --- Monitoring Job Progress ---

# Watch job pods in real time
kubectl get pods -n <namespace> \
  -l job-name=<job-name> -w

# Get Job completion events
kubectl get events -n <namespace> \
  --field-selector=involvedObject.name=<job-name>

# Check overall Job status in structured format
kubectl get job <name> -n <namespace> -o yaml | \
  grep -A 20 "^status:"
```

---

## Cron Schedule Quick Reference

```
Minute Hour DayOfMonth Month DayOfWeek

0 2 * * *       → Daily at 2:00 AM
*/5 * * * *     → Every 5 minutes
0 */6 * * *     → Every 6 hours
0 9 * * 1-5     → 9 AM every weekday
0 0 1 * *       → First day of every month at midnight
0 0 * * 0       → Every Sunday at midnight
@hourly         → 0 * * * *
@daily          → 0 0 * * *
@weekly         → 0 0 * * 0
@monthly        → 0 0 1 * *
```

---

## Job restartPolicy Rules

| restartPolicy | Behavior on failure |
|---|---|
| `Never` | Pod is left terminated; Job creates new pod to retry |
| `OnFailure` | Pod is restarted in place on the same node |
| `Always` | FORBIDDEN in Jobs (causes conflict with Job controller) |

---

## 📂 Navigation

| | Link |
|---|---|
| Theory | [Theory.md](./Theory.md) |
| Interview Q&A | [Interview_QA.md](./Interview_QA.md) |
| Code Example | [Code_Example.md](./Code_Example.md) |
| Module Home | [17_Jobs_and_CronJobs](../) |
