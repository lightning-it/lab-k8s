# lab-k8s

A Kubernetes lab repo for PoCs, experiments, and reusable manifests.

## Structure

- `pocs/` – source code + container build context for PoCs
- `gitops/` – Argo CD / Kustomize-ready manifests (app-of-apps)

## Bootstrap with Argo CD (App-of-Apps)

1. Replace placeholders in Argo CD manifests:
   - `<YOUR_REPO_URL>` in `gitops/argocd/*`
   - `<YOUR_REGISTRY>/okms-secret-fetcher:<tag>` in overlay patches

2. Apply the project + root app:
   ```bash
   kubectl apply -f gitops/argocd/projects/lab-k8s.yaml
   kubectl apply -f gitops/argocd/app-of-apps/lab-k8s-root.yaml
   ```

3. Create the OKMS mTLS client cert secret **out-of-band** (do not commit private keys):
   ```bash
   kubectl -n okms create secret tls okms-client --cert <CERT_PEM> --key <KEY_PEM>
   ```

## OKMS Secret Fetcher PoC

- App source: `pocs/okms-secret-fetcher/app`
- GitOps manifests: `gitops/apps/okms-secret-fetcher`
