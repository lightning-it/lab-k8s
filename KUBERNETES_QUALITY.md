# Kubernetes, Helm, and GitOps Quality Contract

This repository contains laboratory GitOps manifests, Kubernetes proof-of-concept
resources, and an inherited snapshot of Helm charts. All of them are treated as
executable software and must pass the `kubernetes / quality` gate before merge
or promotion.

The governing Lightning IT decisions and standards are:

- [Repository Topology and Shared Engineering Assets][topology-adr]
- [Branching, Review and Release Governance][branch-adr]
- [Mandatory CI Quality and Artifact Assurance][ci-adr]
- [Repository and Secure SDLC Standard][sdlc-standard]
- [Quality Gates and Definition of Done][quality-standard]
- [OpenSSF and Software Supply Chain Assurance][supply-chain-standard]

The implementation also directly follows:

- [OpenSSF OSPS Baseline][osps-baseline]
- [Kubernetes Pod Security Standards][pod-security]
- [Kubernetes RBAC good practices][rbac]
- [Kubernetes resource-management guidance][resources]
- [Kubernetes probe guidance][probes]
- [Helm schema files][helm-schema]
- [Argo CD tracking strategies][argocd-tracking]

## Enforced Gate

`.github/workflows/kubernetes-quality.yml` uses read-only workflow permissions
and full-SHA-pinned actions. It performs:

1. deterministic `values.schema.json` verification for every embedded product
   chart;
2. `helm lint` and `helm template` for every embedded product chart;
3. unit tests proving that unsafe examples fail closed;
4. offline builds of every GitOps Kustomize overlay;
5. policy evaluation of all rendered Helm, Kustomize, Argo CD, and PoC
   resources.

The manifest policy rejects mutable images, literal secret payloads, wildcard
RBAC, missing non-root/seccomp/capability hardening, missing CPU or memory
requests and limits, missing probes for long-running workloads, unnecessary
service-account tokens, and mutable Argo CD revisions.

Public examples use deliberately non-deployable placeholders. An example image
must still use digest syntax, and the placeholder digest must be replaced by the
digest produced by the real build before deployment. Argo CD applications must
use an exact 40-character Git commit. The literal
`<YOUR_TARGET_REVISION>` value is accepted only because it cannot resolve and
therefore cannot silently deploy a mutable revision.

## Helm Ownership and Migration

Reusable charts are owned by the canonical
[`lightning-it/helm-charts` repository][canonical-helm]. The embedded
`helm-charts/` tree predates that topology and remains repository-owned until a
separate reviewed migration removes it. While it exists, it receives the same
schema, lint, render, security, dependency, and waiver enforcement as any other
executable artifact. New reusable chart development belongs in the canonical
repository; this repository must not create another reusable chart fork.

## Waivers

Temporary exceptions live in `.lit/kubernetes-policy-waivers.yml`. Every waiver
is bound to one exact rendered finding and requires an owner, rationale,
compensating control, and expiry. Expired, duplicate, malformed, or stale
waivers fail CI. The current Rook exceptions cover limitations of the pinned
vendored chart contract and expire on 2026-10-31; renewal requires a new
reviewed decision.

## GitOps Promotion, Drift, and Rollback

- Changes enter through `develop` and move to `main` only through the protected
  promotion pull request.
- Production Argo CD applications pin an exact Git commit; floating branches
  and `HEAD` are rejected.
- Argo CD reconciliation state and diff are the drift evidence.
- Rollback is a reviewed repin or revert to the last accepted commit.
- Preserve the pull request, exact Git commit, image digest, reconciliation
  result, and workload health as deployment or rollback evidence.

The enterprise alignment is tracked in
[Engineering ADR issue #51][alignment-issue].

[alignment-issue]: https://github.com/lightning-it/lab-k8s/issues/51
[argocd-tracking]: https://argo-cd.readthedocs.io/en/stable/user-guide/tracking_strategies/
[branch-adr]: https://lit.atlassian.net/wiki/spaces/LIT/pages/2878603438
[canonical-helm]: https://github.com/lightning-it/helm-charts
[ci-adr]: https://lit.atlassian.net/wiki/spaces/LIT/pages/2878636340
[helm-schema]: https://helm.sh/docs/topics/charts/#schema-files
[osps-baseline]: https://baseline.openssf.org/
[pod-security]: https://kubernetes.io/docs/concepts/security/pod-security-standards/
[probes]: https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/
[quality-standard]: https://lit.atlassian.net/wiki/spaces/LIT/pages/2887123058
[rbac]: https://kubernetes.io/docs/concepts/security/rbac-good-practices/
[resources]: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/
[sdlc-standard]: https://lit.atlassian.net/wiki/spaces/LIT/pages/2887778335
[supply-chain-standard]: https://lit.atlassian.net/wiki/spaces/LIT/pages/2887024876
[topology-adr]: https://lit.atlassian.net/wiki/spaces/LIT/pages/2878636297
