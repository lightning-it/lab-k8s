# Testing

This repository uses the Lightning IT shared test model.

## Test Profiles

- `yaml-structure`
- `kubernetes-manifest-validation`
- `smoke`

## Supported Matrix

Operating systems and runners:

- `ubuntu-latest`

Products and runtimes:

- `kubernetes`

## When Tests Run

- Normal pull requests run the declared test profiles relevant to changed files.
- Renovate and verified shared-assets or repository-quality synchronization pull requests target `develop` and may auto-merge only after required checks pass.
- `develop` to `main` promotion pull requests run the strongest validation profile for this repository.
- Trusted `main` release workflows build and publish artifacts only after validation succeeds.

## Local Commands

Run the managed repository-policy checks:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install PyYAML==6.0.3
.venv/bin/python scripts/lit-repository-quality.py
```

Run the repository-specific commands declared in
`.lit/push-ready.json` and the required CI workflow named in
`.lit/repository.yml`. Do not substitute unrelated toolchains.

Heavy Incus execution is not required for this repository. Do not report an Incus run as part of its acceptance evidence.

## Interpreting GitHub Actions

The GitHub Actions matrix is the primary dashboard. Job names should expose the repository class, OS/runtime where applicable, and profile, for example `repository / quality`.

Release evidence is generated during trusted release workflows and attached to or linked from GitHub Releases where the repository publishes release artifacts.

## OpenSSF Enrollment Promotion Evidence

The protected ancestry backmerge joins:

- reviewed `develop` source `5f0fbcc66c997fe4bfb73ef38069f4a3890553b3`, which records OpenSSF Best Practices project `13885`.
- protected `main` source `cc181724a4a2bb851de7f5b5bd65e0ee3bb47ae9`.

The resulting two-parent commit preserves the `develop` tree while making the
current protected `main` history an ancestor. Promotion must still pass the
repository-specific Kubernetes quality gate and current-revision Copilot review.
