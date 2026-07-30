# lab-k8s

Enterprise Kubernetes, Helm, and GitOps quality requirements are documented in
[KUBERNETES_QUALITY.md](KUBERNETES_QUALITY.md).

<!-- BEGIN LIT_SHARED_RELEASE_MODEL -->

## Release and Quality Model

This repository follows the Lightning IT shared release and quality model.

See [RELEASE.md](./RELEASE.md) for:

- branch and release flow
- required quality checks
- test matrix
- release evidence
- artifact publishing
- supported repository-specific release behavior

Repository classification: **Playbook/Runbook Repository**.
Required test profiles: `yaml-structure, kubernetes-manifest-validation, smoke`.
Publishing targets: `none`.

## Supported and Tested Platforms

| Platform / Product |                  Status | Validation    |
| ------------------ | ----------------------: | ------------- |
| ubuntu-latest      |               Supported | Repository CI |
| kubernetes         | Tested where applicable | Repository CI |

<!-- END LIT_SHARED_RELEASE_MODEL -->

<!-- BEGIN LIT_QUALITY_BADGES -->

[![CI](https://github.com/lightning-it/lab-k8s/actions/workflows/repository-quality.yml/badge.svg?branch=develop)](https://github.com/lightning-it/lab-k8s/actions/workflows/repository-quality.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/lightning-it/lab-k8s/badge)](https://scorecard.dev/viewer/?uri=github.com/lightning-it/lab-k8s)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/13885/badge)](https://www.bestpractices.dev/projects/13885)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

<!-- END LIT_QUALITY_BADGES -->

`lab-k8s` contains Lightning IT playbooks and runbooks for repeatable platform automation.

## Purpose

This repository provides repeatable automation workflows with sanitized documentation and shared release validation.

## Included Playbooks

Key playbooks and runbooks are documented in repository-specific sections below.

## Requirements

- Ansible or controller runtime compatible with the tested matrix.
- Access to required inventories, credentials, or private inputs only at runtime.

## Usage

Use the repository-specific examples below. Public examples must stay sanitized and must not expose private inventory values.

## Documentation

- [RELEASE.md](./RELEASE.md)
- [TESTING.md](./TESTING.md)
- [SECURITY.md](./SECURITY.md)

Kubernetes lab: PoCs, experiments, and reusable manifests.

## Lab Structure

- `pocs/` – source code and container build contexts for proofs of concept
- `gitops/` – Argo CD and Kustomize-ready app-of-apps manifests

## Bootstrap with Argo CD

1. Replace `<YOUR_REPO_URL>` and `<YOUR_TARGET_REVISION>` in
   `gitops/argocd/*`, and replace the
   `example.invalid/okms-secret-fetcher:dev` and
   `example.invalid/okms-secret-fetcher:prod` image placeholders in the
   corresponding overlay patches.
2. Apply the project and root application:

   ```bash
   kubectl apply -f gitops/argocd/projects/lab-k8s.yaml
   kubectl apply -f gitops/argocd/app-of-apps/lab-k8s-root.yaml
   ```

3. Create the OKMS mTLS client certificate secret out of band; never commit
   private keys:

   ```bash
   kubectl -n okms create secret tls okms-client \
     --cert=path/to/client.crt \
     --key=path/to/client.key
   ```

## OKMS Secret Fetcher PoC

- Application source: `pocs/okms-secret-fetcher/app`
- GitOps manifests: `gitops/apps/okms-secret-fetcher`

## Security

See [SECURITY.md](./SECURITY.md) for supported versions and vulnerability reporting.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for contribution and review expectations.

## License

See [LICENSE](./LICENSE).

<!-- BEGIN LIT_RELEASE_QUALITY_MODEL -->

## Release and Quality Model

This repository follows the Lightning IT shared release and quality model.
The README shows the current supported and tested matrix.
Exact per-version validation proof is stored with each GitHub Release as `release-evidence.md` and `release-evidence.json`.
Releases are created from the protected `main` branch after a reviewed `develop -> main` release promotion.
Runbook releases validate linting, syntax, sanitized examples, and integration scenarios where configured.

See:

- [RELEASE.md](./RELEASE.md)
- [TESTING.md](./TESTING.md)
- [GitHub Releases](../../releases)

Repository classification: **Playbook/Runbook Repository**.
Required test profiles: `yaml-structure, kubernetes-manifest-validation, smoke`.
Publishing targets: `none`.

<!-- END LIT_RELEASE_QUALITY_MODEL -->

<!-- BEGIN LIT_COMPATIBILITY_MATRIX -->

## Compatibility Matrix

| Platform / Product | Status | Validation |
|---|---:|---|
| ubuntu-latest | Supported | Repository CI |
| kubernetes | Tested where applicable | Repository CI |

Validation proof for each released version is stored in the corresponding GitHub Release evidence.

<!-- END LIT_COMPATIBILITY_MATRIX -->

## Release Evidence

This repository does not publish release artifacts by default; release evidence is recorded when artifact releases are enabled.
The evidence records:

- tested matrix combinations
- GitHub Actions run links
- artifact references
- publish status
- security scan status

See [GitHub Releases](../../releases), [RELEASE.md](./RELEASE.md), and [TESTING.md](./TESTING.md) for the release process and validation model.
