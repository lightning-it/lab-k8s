# PoC: OKMS Secret Fetcher

Minimal container that reads a secret from OVHcloud OKMS Secret Manager using mTLS (access certificate)
and writes the value of a configured key to a protected file. Secret values are never written to stdout.

## Build

```bash
docker build -t <YOUR_REGISTRY>/okms-secret-fetcher:dev ./pocs/okms-secret-fetcher/app
docker push <YOUR_REGISTRY>/okms-secret-fetcher:dev
```

## Run in Kubernetes

Use GitOps manifests in `gitops/apps/okms-secret-fetcher`.
Create the TLS secret `okms-client` in namespace `okms`:
```bash
kubectl -n okms create secret tls okms-client --cert <CERT_PEM> --key <KEY_PEM>
```

The initContainer writes the secret value to:
- `/work/shared-key.txt` (required and configured by env `SECRET_OUT_FILE`)

Then your app container can read that file.
