# Engineering agent contract

This repository contains public Kubernetes laboratory manifests and runbooks. Treat
`.lit/repository.yml`, `RELEASE.md`, `TESTING.md`, `SECURITY.md`, and the accepted
Lightning IT Engineering ADRs as the governing repository contract.

- Work through a pull request into `develop`; promote reviewed `develop` to `main`.
- Never commit kubeconfigs, tokens, private keys, credentials, or production data.
- Validate YAML structure, Kubernetes manifests, and documented smoke tests.
- Keep external GitHub Actions pinned to full commit SHAs and permissions
  least-privilege.
- Preserve managed-file headers and change shared policy at
  `lightning-it/shared-assets-lit`.
- Run `python3 scripts/lit-push-ready.py push-ready` before pushing.
- Required remote checks and branch protection must not be bypassed.
- ADR 70 temporarily allows zero human/CODEOWNER approvals and separately
  documented protected-environment self-approval for immutable exact-SHA
  plan/apply evidence; it does not allow PR self-review or check bypass.
