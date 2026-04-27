# starter.py — Production K8s Cluster
#
# This project is primarily YAML-based. The Python files in src/ serve as
# a reference scaffold for thinking about the nine production components.
#
# Each section below contains a class stub. Fill in the docstring comments
# to describe what the corresponding Kubernetes YAML should do, then write
# the YAML files. See solution.py for the full YAML content embedded as strings.

# =============================================================================
# Component 1: Namespaces
# =============================================================================
# TODO: Describe which namespaces to create and what labels each needs.
NAMESPACES = {
    # namespace_name: {label_key: label_value}
}


# =============================================================================
# Component 2: RBAC
# =============================================================================
# TODO: Describe the three service accounts, their namespaces, and what
# roles they should have. Fill in the dicts.

RBAC_MODEL = {
    "developer-sa": {
        "namespace": None,         # TODO: which namespace?
        "can_deploy_to": [],       # TODO: list namespaces where deploy is allowed
        "read_only_in": [],        # TODO: list namespaces with only get/list/watch
        "cannot_access": [],       # TODO: list namespaces with no access
    },
    "ops-sa": {
        "namespace": None,
        "access": None,            # TODO: "full-cluster" or "namespace-scoped"?
    },
    "ci-sa": {
        "namespace": None,
        "verbs": [],               # TODO: only read verbs
    },
}


# =============================================================================
# Component 3: Resource Quotas
# =============================================================================
# TODO: Fill in the hard limits per namespace.

QUOTAS = {
    "dev": {
        "requests.cpu": None,      # e.g. "4"
        "requests.memory": None,   # e.g. "8Gi"
        "pods": None,
    },
    "staging": {},
    "production": {},
}


# =============================================================================
# Component 4: HPA
# =============================================================================
# TODO: Fill in the HPA spec fields.

HPA_SPEC = {
    "target_deployment": None,      # name of the Deployment to scale
    "namespace": None,
    "min_replicas": None,
    "max_replicas": None,
    "cpu_threshold_percent": None,  # scale up when average CPU exceeds this
    "scale_up_stabilization_seconds": None,
    "scale_down_stabilization_seconds": None,
}


# =============================================================================
# Component 5: NetworkPolicy rules (describe the allow paths)
# =============================================================================
# TODO: List the four policies and what each allows.

NETWORK_POLICIES = [
    # {
    #     "name": "deny-all-default",
    #     "podSelector": "all pods",
    #     "blocks": "all ingress and egress",
    # },
    # ... fill in the rest
]


# =============================================================================
# Component 6: ArgoCD Application
# =============================================================================
# TODO: Fill in the ArgoCD Application spec fields.

ARGOCD_APP = {
    "name": None,
    "namespace": "argocd",
    "repo_url": None,              # your git repo URL
    "target_revision": "main",
    "path": None,                  # path within the repo to K8s manifests
    "destination_namespace": "production",
    "prune": None,                 # True/False
    "self_heal": None,             # True/False
}
