# Project Standards

Source of truth for code quality in myfitnessrank-app.
Claude must follow these rules when generating or reviewing any code.

---

## 1. Docker Standards

All Dockerfiles must:
- Pin base image to a specific version tag (e.g. `python:3.11-slim`, never `python:latest`)
- Use multi-stage builds — builder stage installs deps, runner stage runs the app
- Run as a non-root user in the final stage
- Set `PYTHONDONTWRITEBYTECODE=1` and `PYTHONUNBUFFERED=1` for Python images
- Use a virtual environment (`venv`) in the builder stage, copy it to runner
- `EXPOSE` the correct port
- Use `COPY --chown=<user>:<user>` for app files

Anti-patterns — never do these:
- `FROM python:latest`
- `RUN pip install ...` without `--no-cache-dir`
- Running the container as root
- Copying the entire repo into the image (`COPY . .` before installing deps — defeats layer cache)

---

## 2. Kubernetes Standards

All K8s manifests must:
- Use a dedicated namespace (never `namespace: default`)
- Set resource `requests` and `limits` on every container
- Never use `:latest` image tag — always pin to a digest or version tag
- Include standard labels: `app`, `version`, `component`
- Use `readinessProbe` and `livenessProbe` on all Deployments
- Use `RollingUpdate` strategy with `maxSurge` and `maxUnavailable` set

Anti-patterns:
- `namespace: default`
- Missing resource limits (pods become unschedulable or starve other workloads)
- `image: myapp:latest` in production
- No health probes (K8s can't know when the pod is actually ready)

---

## 3. Helm Standards

All Helm charts must:
- Live under `helm/<service-name>/` in this repo
- Use `values.yaml` for all environment-specific config — no hardcoded values in templates
- Set `imagePullSecrets` to support ECR authentication
- Enable `ingress` and `service` by default (can be toggled via values)
- Include resource limits and requests in the deployment template
- Include `NOTES.txt` with post-install instructions
- Bump `Chart.yaml` version on every change

---

## 4. Terraform Standards

All Terraform code must:
- Use typed variables with descriptions and defaults where safe
- Never hardcode AWS account IDs, region, or any credentials
- Use `terraform-aws-modules` where available (VPC, EKS, ECR, etc.)
- Store state in S3 with DynamoDB locking
- Define outputs for every resource consumed by another module
- Follow module structure: `main.tf`, `variables.tf`, `outputs.tf`

Anti-patterns:
- Inline provider credentials
- Hardcoded values that differ per environment
- Modules that do too much (one module = one responsibility)
- Missing `description` on variables

---

## 5. GitHub Actions CI/CD Standards

All workflows must:
- Separate `build` and `deploy` jobs — never mix them
- Never print secrets in logs (`echo $SECRET` is forbidden)
- Use least-privilege IAM for ECR pushes (OIDC, not long-lived keys where possible)
- Use `actions/checkout@v4` (pinned major version minimum)
- Cache dependencies where possible (`pip cache`, etc.)
- Fail fast on lint errors before attempting build

Naming:
- `ci.yml` — lint + build (runs on feature branch push and PR)
- `deploy-staging.yml` — triggered on master merge
- `deploy-production.yml` — triggered on version tag

---

## 6. Python / Flask Standards

- Use `Flask` with `jsonify` for all API responses
- Structure responses consistently: `{"status": "success"|"error", "data": ...}`
- Keep business logic out of route handlers — put it in service modules
- Use environment variables for all config (DB URL, port, etc.) — never hardcode
- Include a `/health` endpoint returning `200 OK` for K8s probes
- Pin all dependencies in `requirements.txt` with exact versions

---

## 7. Security Standards

Non-negotiable:
- No real credentials anywhere in the repo (not even in `.gitignore`d files)
- No `latest` tags in production K8s manifests or Helm default values
- No containers running as root in production
- All secrets injected via environment variables or K8s Secrets
- IAM roles follow least privilege

---

## 8. Non-Negotiable Rules

- No dumping files outside the defined directory structure
- No hardcoded secrets
- No `latest` image tags in production contexts
- No running containers as root
- No skipping resource limits on K8s workloads
