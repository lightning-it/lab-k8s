# GitOps: okms-secret-fetcher

This folder is designed to be consumed by Argo CD.

- `base/` contains the base manifests.
- `overlays/dev|prod` patch only the initContainer image.

Requirements:
- Create the TLS secret `okms-client` in namespace `okms` manually (or via SealedSecrets/SOPS):
  ```bash
  kubectl -n okms create secret tls okms-client --cert <CERT_PEM> --key <KEY_PEM>
  ```
