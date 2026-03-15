# Module 09 — Interview Q&A: Ingress

---

**Q1: What is the difference between an Ingress resource and an Ingress controller?**

An **Ingress resource** is a Kubernetes API object (kind: Ingress) where you declare routing
rules — which hostnames and paths map to which services. It is just configuration; by itself
it does nothing.

An **Ingress controller** is the actual software that reads Ingress resources and implements
the routing. It runs as pods in the cluster (typically with a LoadBalancer service in front of
it). Kubernetes does not ship with an Ingress controller — you must install one separately
(nginx-ingress, AWS ALB controller, Traefik, etc.). The Ingress controller watches the API
server for Ingress objects and programs its routing table accordingly.

---

**Q2: Why use Ingress instead of multiple LoadBalancer services?**

Each LoadBalancer service creates an external cloud load balancer, which costs money and
requires separate DNS records and TLS certificates per service. With 10 services, you have
10 external IPs to manage.

Ingress uses a single Ingress controller (with one LoadBalancer service and one external IP)
and routes traffic to all your services based on hostname and path rules. This is:
- Cheaper (one cloud LB instead of many)
- Easier to manage (one place for TLS certificates and routing rules)
- More flexible (path-based and host-based routing in one place)

---

**Q3: What is path-based vs host-based routing in Ingress?**

**Path-based routing**: routes requests to different services based on the URL path, all under
the same hostname. `example.com/api` goes to the API service; `example.com/` goes to the
frontend service.

**Host-based routing**: routes requests to different services based on the HTTP Host header.
`api.example.com` goes to the API service; `www.example.com` goes to the frontend service.
Both hostnames resolve to the same Ingress controller IP.

Both can be combined: different hostnames, each with different path rules.

---

**Q4: How does TLS termination work with Ingress?**

You specify a TLS section in the Ingress resource listing the hostnames and a reference to
a Kubernetes Secret containing the TLS certificate and private key. The Ingress controller
loads this certificate and terminates TLS connections — it decrypts incoming HTTPS traffic
and forwards plain HTTP to the backend services. The backend services don't need to handle
TLS at all.

The TLS Secret must be of type `kubernetes.io/tls` with two keys: `tls.crt` (certificate)
and `tls.key` (private key).

---

**Q5: What is cert-manager and how does it work with Ingress?**

cert-manager is a Kubernetes operator that automates TLS certificate provisioning and renewal.
You define an `Issuer` or `ClusterIssuer` that specifies how to obtain certificates
(e.g., Let's Encrypt via ACME). Then you add an annotation to your Ingress resource:

```yaml
cert-manager.io/cluster-issuer: letsencrypt-prod
```

cert-manager detects this annotation, creates a `Certificate` resource, performs the ACME
challenge (usually HTTP-01: cert-manager temporarily handles a specific URL path to prove
domain ownership), and creates a TLS Secret with the issued certificate. It also monitors
the certificate's expiry and renews it automatically (typically 30 days before expiry).

---

**Q6: What is an IngressClass?**

An IngressClass is a Kubernetes resource that maps a class name to a specific Ingress controller
implementation. The `spec.ingressClassName` field in an Ingress resource specifies which
controller should handle it. This allows running multiple Ingress controllers in the same
cluster (e.g., nginx for most services, AWS ALB for certain high-traffic services requiring
advanced AWS-specific features). You can set a default IngressClass so Ingress resources
without an explicit class are handled by the default controller.

---

**Q7: What is the `rewrite-target` annotation in nginx-ingress and when do you use it?**

When you route traffic based on a path prefix (e.g., `/api`), the backend service typically
expects requests without that prefix. The `rewrite-target` annotation strips the prefix before
forwarding:

```yaml
nginx.ingress.kubernetes.io/rewrite-target: /$2
```

With path `/api(/|$)(.*)`, this rewrites `/api/users` to `/users` before forwarding to the
backend. Without it, the backend would receive `/api/users` but might only handle `/users`.

---

**Q8: How do you expose multiple hostnames with TLS using a single Ingress?**

List multiple host entries in the `tls` section and multiple rules in the `rules` section:

```yaml
spec:
  tls:
  - hosts:
    - api.example.com
    secretName: api-tls
  - hosts:
    - www.example.com
    secretName: www-tls
  rules:
  - host: api.example.com
    http:
      paths: [...]
  - host: www.example.com
    http:
      paths: [...]
```

Each hostname can have a separate TLS secret, or you can use a wildcard certificate
(`*.example.com`) that covers all subdomains with a single secret.

---

**Q9: How do you test an Ingress before setting up DNS?**

Use curl with the `Host` header to simulate what DNS would do:

```bash
INGRESS_IP=$(kubectl get svc -n ingress-nginx ingress-nginx-controller \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

curl -H "Host: api.example.com" http://$INGRESS_IP/health
```

Alternatively, add entries to `/etc/hosts`:
```
<ingress-ip> api.example.com www.example.com
```

---

**Q10: What happens if two Ingress resources define rules for the same hostname?**

The behavior depends on the Ingress controller implementation. With nginx-ingress, if two
Ingress resources define rules for the same hostname, the controller merges them (if they're
in the same IngressClass). However, conflicts (two rules for the same path) result in
unpredictable behavior — one will win based on creation order or alphabetical sorting.

Best practice: use a single Ingress resource per hostname, or use tools like Helm or
Kustomize to ensure Ingress rules are managed as a unit.

---

**Q11: Can Ingress handle TCP or UDP traffic?**

Standard Kubernetes Ingress only handles HTTP/HTTPS traffic (Layer 7). For TCP or UDP
(Layer 4), nginx-ingress supports TCP/UDP port routing through ConfigMaps (not Ingress
resources). Other controllers like Traefik and HAProxy have native TCP routing support.

For general TCP load balancing, you'd typically use a LoadBalancer or NodePort Service instead
of an Ingress resource.

---

**Q12: What is the default backend in Ingress?**

The default backend handles requests that don't match any rule in any Ingress resource.
Without a default backend, unmatched requests return a 404. You can configure a default
backend as a catch-all service:

```yaml
spec:
  defaultBackend:
    service:
      name: default-404-service
      port:
        number: 80
```

The nginx-ingress controller ships with a built-in default backend that serves a simple
404 page.

---

## Navigation

| File | Description |
|------|-------------|
| [Theory.md](./Theory.md) | Ingress explained |
| [Cheatsheet.md](./Cheatsheet.md) | Quick reference commands |
| [Interview_QA.md](./Interview_QA.md) | You are here — interview questions |
| [Code_Example.md](./Code_Example.md) | Working YAML examples |

---

⬅️ **Prev:** [Namespaces](../08_Namespaces/Interview_QA.md) &nbsp;&nbsp;&nbsp; ➡️ **Next:** [Persistent Volumes](../10_Persistent_Volumes/Theory.md)
