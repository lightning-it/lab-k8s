# lab-k8s

<!-- BEGIN LIT_QUALITY_BADGES -->

[![CI](https://github.com/lightning-it/lab-k8s/actions/workflows/repository-quality.yml/badge.svg?branch=develop)](https://github.com/lightning-it/lab-k8s/actions/workflows/repository-quality.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/lightning-it/lab-k8s/badge)](https://scorecard.dev/viewer/?uri=github.com/lightning-it/lab-k8s)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

<!-- END LIT_QUALITY_BADGES -->

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

| Platform / Product | Status | Validation |
|---|---:|---|
| ubuntu-latest | Supported | Repository CI |
| kubernetes | Tested where applicable | Repository CI |

<!-- END LIT_SHARED_RELEASE_MODEL -->
Kubernetes lab: PoCs, experiments, and reusable manifests.
