# Local GitOps Environment

Local kind cluster + ArgoCD setup that mirrors the production GitOps flow
(EKS + ArgoCD syncing from git).

## Bootstrap

```bash
# 1. Cluster with ingress ports mapped to localhost:8080/8443
kind create cluster --config deploy/kind/kind-config.yaml

# 2. Ingress controller (kind provider manifest, pinned version)
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.15.1/deploy/static/provider/kind/deploy.yaml

# 3. ArgoCD (server-side apply — the ApplicationSet CRD exceeds the
#    client-side annotation size limit)
kubectl create namespace argocd
kubectl apply --server-side -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.4.3/manifests/install.yaml

# 4. App images (built locally, loaded into the kind node)
docker build -t myfitnessrank-backend:0.1.0 backend/
docker build -t myfitnessrank-frontend:0.1.0 frontend/
docker build -t myfitnessrank-leaderboards:0.1.0 leaderboards/
kind load docker-image myfitnessrank-backend:0.1.0 myfitnessrank-frontend:0.1.0 \
  myfitnessrank-leaderboards:0.1.0 --name myfitnessrank

# 5. DB credentials — never committed to git
kubectl create namespace myfitnessrank
kubectl -n myfitnessrank create secret generic fitrank-db-credentials \
  --from-literal=username=fitrank \
  --from-literal=password="$(openssl rand -hex 16)" \
  --from-literal=database=fitrank

# 5b. Leaderboards service — own DB + Fernet key for encrypting lifter names.
#     The shared jwt-signing-key secret (created with the auth service) is reused.
kubectl -n myfitnessrank create secret generic leaderboards-db-credentials \
  --from-literal=username=leaderboards \
  --from-literal=password="$(openssl rand -hex 16)" \
  --from-literal=database=leaderboards
kubectl -n myfitnessrank create secret generic leaderboards-enc-key \
  --from-literal=fernet-key="$(python -c 'from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())')"

# 6. The only manual Application — everything else syncs from git
kubectl apply -f deploy/argocd/root-app.yaml
```

## Access

- App: http://localhost:8080
- ArgoCD UI: `kubectl -n argocd port-forward svc/argocd-server 8081:443` → https://localhost:8081
  (user `admin`, password: `kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d`)

## Layout

```
deploy/
  kind/kind-config.yaml     # cluster definition (ingress-ready node, port mappings)
  argocd/root-app.yaml      # app-of-apps — points at deploy/argocd/apps/
  argocd/apps/*.yaml        # one ArgoCD Application per helm chart
```

In production ArgoCD on EKS syncs these same manifests from this repo (`master`);
`targetRevision` here points at the feature branch for local iteration.
