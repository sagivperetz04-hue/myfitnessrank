# MyFitnessRank — Project Manifest

> Snapshot of everything built so far, section by section, plus the roadmap templates
> for what remains (EKS, Terraform, Terragrunt, deploy pipelines, logging).
> Last updated: 2026-07-09, DB backups to S3 (RND-015) in the postgres charts + prod overlays.

---

## 1. Architecture Overview

The app started as a 3-tier monolith and was split into microservices (RND-002/003).
Current shape:

```
Browser
  └─► Frontend (React + nginx, port 8080) — the single public entry point (Ingress)
        ├─► /api/auth/*        → auth service (Flask, port 5000)      → postgres-auth
        ├─► /api/leaderboards* → leaderboards service (Flask, 5000)   → postgres-leaderboards
        └─► /api/*             → backend service (Flask, 5000)        → postgres (fitrank)
                                     └─► calls leaderboards internally for /api/leaderboard
Prometheus ──scrapes /metrics──► backend, auth, leaderboards
Grafana ◄── dashboards ── kube-prometheus-stack (monitoring namespace)
ArgoCD ──watches master──► deploys everything (app-of-apps)
```

Key decisions:
- **Environments as namespaces** — dev/staging/prod are namespaces (`myfitnessrank-<env>`) on the single cluster (one EKS control plane later, not three). Each env has its own Postgres trio and independently generated secrets. Promotion: dev tracks the `dev` branch, staging tracks `master`, prod tracks `master` with image tags pinned in its values overlay. Local access: `dev.localhost:8080`, `staging.localhost:8080`, prod at `localhost:8080` (catch-all).
- **Database-per-service** — each service owns its schema; no shared tables.
- **JWT between services** — auth issues tokens; leaderboards verifies them independently.
- **Frontend nginx is the API gateway** — no service is exposed outside the cluster directly.
- **GitOps** — nothing is `helm install`ed by hand; ArgoCD syncs `deploy/argocd/apps/` from `master`.

---

## 2. Backend Service (`backend/`)

Core ranking API. Python 3.11 + Flask 3.0.3, served by gunicorn (2 workers).

### Application code
| File | What it does |
|---|---|
| `app.py` | Flask app, all routes, request validation, Prometheus metrics wiring |
| `db.py` | psycopg2 connection pool; credentials from env vars (never hardcoded) |
| `services/ranking.py` | Epley 1RM formula (`weight * (1 + reps/30)`), weight-class assignment, percentile lookup against `global_standards`, tier assignment (Copper → Elite) |
| `services/leaderboard.py` | HTTP clients: `get_top_lifters` (external rankings API) and `submit_bests` (RND-008 — forwards a signed-in user's best 1RMs to the leaderboards service, `LEADERBOARDS_URL`, default `http://leaderboards:5000`) |
| `services/tokens.py` | RND-011: verify-only JWT decode (PyJWT, shared `JWT_SIGNING_KEY` + issuer with auth). `/api/rank` uses it to take a signed-in lifter's identity from the token, never a spoofable body field |
| `gunicorn.conf.py` | Creates `PROMETHEUS_MULTIPROC_DIR` at startup so multi-worker metric counters aggregate correctly |
| `schema.sql` | `users`, `workout_logs`, `global_standards` tables |
| `scripts/generate_global_standards.py` + `seed_global_standards.sql` | Generates and seeds the benchmark distribution the percentile ranking compares against |

### Endpoints
| Method | Path | Notes |
|---|---|---|
| GET | `/health/live` | Liveness — deliberately **never** touches the DB (a DB outage should fail readiness, not restart pods) |
| GET | `/health` | Readiness — `SELECT 1` DB ping, 503 when DB unreachable |
| POST | `/api/rank` | Validates username/exercise/sex/weight/reps (reps ≤ 20 for Epley reliability, weight capped at world record + 2 kg), computes 1RM, persists the log, returns competition + world-average percentile/tier. RND-011: when a Bearer token is present it is verified and the log is recorded under the token's username (a present-but-invalid token → 401; no token = guest mode, body username trusted) — closes the hole where any signed-in user could write history under another username. RND-008: if the request carries a Bearer token, forwards the user's best squat/bench/deadlift 1RMs to the leaderboards `/submit` (best-effort — a leaderboards outage never fails the rank; skipped until all three lifts have been logged; the leaderboards service dedups one row per user per sex via keep-the-best upsert). No lift verification yet — planned |
| GET | `/api/users/<username>/history` | Paginated (limit ≤ 100), optional exercise filter |
| GET | `/api/users/<username>/best` | Best 1RM per exercise (`DISTINCT ON`) |
| GET | `/api/leaderboard` | Proxies to the leaderboards service; 502 if upstream down |
| GET | `/metrics` | Prometheus (prometheus-flask-exporter, multiprocess-aware) |

### Input validation & safety
- All SQL is parameterized (no string interpolation).
- Structured logging via stdlib `logging` (timestamp, level, message) to stdout.
- DB connections returned to the pool per-request via `teardown_appcontext`; rolled back on error.

### Tests (`backend/tests/`)
- `test_ranking.py` — pure-function unit tests (1RM, tiers, weight classes).
- `test_api.py` — endpoint tests against a real Postgres (`conftest.py` spins fixtures; CI provides a `postgres:15.6-alpine` service container on port 5433).

---

## 3. Auth Service (`auth/`) — RND-002

Online-accounts microservice: signup, login, session management. Same Flask/gunicorn skeleton as backend.

### Application code
| File | What it does |
|---|---|
| `app.py` | Routes + refresh-cookie handling |
| `services/security.py` | **Argon2** password hashing (argon2-cffi), email/username/password validation rules |
| `services/tokens.py` | JWT issue/decode (PyJWT): short-lived access tokens + refresh tokens with TTL |
| `db.py` / `schema.sql` | Own Postgres (`postgres-auth`), users table with case-insensitive-unique usernames + `last_login_at` (idempotent ALTER for pre-existing DBs) |

### Endpoints
| Method | Path | Notes |
|---|---|---|
| GET | `/health/live`, `/health` | Same liveness/readiness split as backend |
| GET | `/api/auth/username-available` | Live availability check for the signup form |
| POST | `/api/auth/signup` | Validates email + username + password strength; Argon2-hashes; `first_login: true` |
| POST | `/api/auth/login` | Issues JWT access token + sets refresh cookie; returns `first_login` (from `last_login_at`, stamped on success) |
| POST | `/api/auth/refresh` | Rotates the access token from the refresh cookie |
| POST | `/api/auth/logout` | Clears the refresh cookie |
| GET | `/api/auth/me` | Returns identity from a valid access token |
| GET | `/metrics` | Prometheus |

### Security decisions
- Refresh cookie (`mfr_refresh`) is `HttpOnly`, `Secure` by default, and **path-scoped to `/api/auth`** — it is never sent to the other services.
- `JWT_SIGNING_KEY` comes from a Kubernetes Secret (env var), never from values or code.
- Tests: `test_security.py` (hashing/validation), `test_tokens.py` (issue/decode/expiry).

---

## 4. Leaderboards Service (`leaderboards/`) — RND-003

Public leaderboards + authenticated lift submission. Own Postgres, seeded with a realistic lifter pool.

### Application code
| File | What it does |
|---|---|
| `app.py` | Routes; extracts `Bearer` tokens and verifies them |
| `services/board.py` | `top_entries` (read leaderboard), `submit_lift` (write, upsert-best, returns rank + notify meta), `mark_notified` (stamps `notified_at` after the top-200 mail) |
| `services/mailer.py` | RND-009: top-200 congratulations/verification mail via stdlib `smtplib`. Env: `SMTP_HOST` (unset = mail is logged, not sent — local/dev default), `SMTP_PORT`, `SMTP_STARTTLS`, `MAIL_FROM`, `SMTP_USER`/`SMTP_PASSWORD` from an optional secret. Recipient email comes from the JWT claims. Sent once per entry: only when rank ≤ 200 and `notified_at IS NULL`; stamped only after a successful send so failures retry on the next submit. Asks for lift video + bodyweight photo within 7 days (manual verification for now) |
| `services/tokens.py` | Verifies the auth service's JWTs (shared signing key — no call to auth needed per request) |
| `services/crypto.py` | Crypto helpers (cryptography lib) |
| `scripts/seed_pool.csv` + `extract_seed.py` + `load_seed.py` | Seed dataset of lifters loaded into the DB by a Helm **seed Job** |

### Endpoints
| Method | Path | Notes |
|---|---|---|
| GET | `/health/live`, `/health` | Standard split |
| GET | `/api/leaderboards` | Top entries filtered by sex / weight class / lift |
| POST | `/api/leaderboards/submit` | Requires valid JWT; positive-number validation on all lift fields **plus a per-lift world-record+2 kg ceiling enforced here** (RND-011 — the board is proxy-reachable, so it can't trust the backend to be the only caller; a direct POST can no longer manufacture a #1 entry); first time an entry ranks ≤ 200 it triggers the verification mail (RND-009) |
| GET | `/metrics` | Prometheus |

Tests: `test_board.py`, `test_crypto.py`, `test_extract.py`.

---

## 5. Frontend (`frontend/`) — RND-004 included

React 18 + Vite, served by **unprivileged nginx** which doubles as the API gateway.

**Visual design (RND-007, chart 0.2.0):** "meet day" system — chalk-white background, ink woodtype (Big Shoulders Display + Barlow via Google Fonts `<link>`), IPF competition plate colors (red/blue/yellow/green) as the only accents, judges'-lights reveal on the result scorecard, loaded-bar header rule. Tokens live in `src/App.css` `:root`; tier text colors in `src/tiers.js`. Respects `prefers-reduced-motion`.

### Application code
| File | What it does |
|---|---|
| `src/App.jsx` | Dashboard: lift input form, rank results, history, leaderboard page; client-side world-record sanity check (UX only — backend is the real gate); intro overlay shows a first-visit greeting vs. "welcome back" (online: `first_login` from auth; guest: per-username `mfr_greeted_*` localStorage flag) |
| `src/LoginPage.jsx` + `src/auth.js` | Signup/login UI, access-token handling, silent refresh |
| `src/RankBadge.jsx` / `.css` + `src/tiers.js` | Tier badge rendering (Copper → Elite) |
| `src/ErrorBoundary.jsx` | Catches render errors instead of white-screening |
| `src/App.test.jsx` + `src/test-setup.js` | Vitest + Testing Library suite |
| `eslint.config.js`, `vite.config.js` | Lint + build config |

### nginx (`nginx.conf.template`)
- Templated at container start via the stock envsubst entrypoint (`BACKEND_URL`, `AUTH_URL`, `LEADERBOARDS_URL` injected from Helm values → no rebuilds to repoint).
- Routing: `/assets/` (long-cache immutable), `/index.html` (no-cache), `/api/auth/` → auth, `/api/leaderboards` → leaderboards, `/api/` → backend, `/` → SPA fallback.
- Security headers set at server level (repeated in locations because `add_header` in a location drops server-level ones).

---

## 6. Containers (all `Dockerfile`s)

Shared standards across backend / auth / leaderboards:
- **Multi-stage build**: builder stage creates a venv, runner copies only the venv + app code (small final image, no pip/build tools in prod).
- **Non-root**: `USER 1000:1000` — numeric so K8s `runAsNonRoot` can actually verify it.
- **Pinned bases**: `python:3.11-slim`, deps pinned exactly in `requirements.txt`.
- `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1` (logs flush to stdout immediately).
- `PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_multiproc` — lives on a writable emptyDir because the root filesystem is read-only.

Frontend:
- Stage 1 `node:22-alpine` builds the Vite bundle; stage 2 `nginxinc/nginx-unprivileged:1.27-alpine` (runs as uid 101, listens on **8080**, not 80).
- `npm ci --ignore-scripts` (no arbitrary postinstall execution).

---

## 7. Kubernetes / Helm (`helm/`)

Charts: `core` (umbrella: auth + backend), `web-service` (generic, instantiated by core), `leaderboards`, `frontend`, plus three Postgres charts (`postgres`, `postgres-auth`, `postgres-leaderboards`).

### Umbrella + generic chart (RND-012 restructure)
The old `helm/auth` and `helm/backend` charts were ~95% identical, so they were replaced by:
- **`helm/web-service/`** — one generic chart (deployment/service/ingress/hpa/helpers) parameterized by `component`, `image`, `db`, `ingress.host`, and an `extraEnv` list (auth: `COOKIE_SECURE`; backend: `LEADERBOARDS_URL`). Its `fullname` defaults to the **component name**, not the release name, so cross-service DNS (`auth`, `backend`) survives any release naming. The `version` label comes from `image.tag` (not `appVersion`) so prod's pinned tags label truthfully.
- **`helm/core/`** — umbrella chart declaring `web-service` twice as `file://../web-service` dependencies with aliases `auth` and `backend`; per-service identity lives under those alias keys in its `values.yaml`. `Chart.lock` is committed; the vendored `charts/*.tgz` is gitignored (ArgoCD rebuilds file:// deps itself; locally run `helm dependency build helm/core` before `helm template`).
- Rendered-manifest parity with the old charts was verified per env (canonicalized diff); only intended deltas: backend env-var order, and prod `version` labels now matching the pinned tags.

### App charts (web-service instances / leaderboards / frontend)
Every chart contains `Chart.yaml`, `values.yaml`, `deployment.yaml`, `service.yaml`, `ingress.yaml`, `_helpers.tpl`, `NOTES.txt`. Common hardening baked into all of them:

| Concern | Setting |
|---|---|
| Replicas | 2 (frontend/backend) for basic HA |
| Image tags | Pinned versions (`0.1.x`), **never `latest`**; `pullPolicy: IfNotPresent` |
| Pod security | `runAsNonRoot: true`, `runAsUser/Group: 1000` |
| Container security | `allowPrivilegeEscalation: false`, `readOnlyRootFilesystem: true`, `capabilities.drop: [ALL]` |
| Resources | requests + limits on every container (e.g. backend 100m/128Mi → 500m/256Mi) |
| Probes | readiness → `/health` (DB-aware), liveness → `/health/live` (dependency-free) |
| Secrets | `existingSecret` pattern (`fitrank-db-credentials` etc.) — created out-of-band, never in git |
| Exposure | Backend/auth/leaderboards ingress **disabled** — only the frontend has an Ingress; nginx proxies the rest |
| Labels | Shared `app: myfitnessrank` + per-service `component:` label (drives monitoring selection) |

Leaderboards chart additionally has `seed-job.yaml` — a Job that loads the seed lifter pool.

Charts hold the defaults; per-environment differences live in small values overlays under
`deploy/envs/<env>/<service>.yaml` — replicas/resources (dev/staging run lighter), the
frontend ingress host per env, and prod's pinned image tags (the promotion gate).
auth + backend overlays are one `core.yaml` per env with the settings nested under the
`auth:`/`backend:` alias keys (dev's also enables the backend HPA).
Current prod pins: auth 0.1.0, backend 0.1.2, leaderboards 0.1.1, frontend 0.2.1
(RND-008 leaderboard sync + RND-009 top-200 mail promoted 2026-07-05).
Prod's leaderboards overlay also carries the only real SMTP config (Gmail relay,
`leaderboards-smtp-credentials` secret created out-of-band); staging/dev stay log-only.

### Postgres charts (x3, one per service DB) — 0.2.0
- StatefulSet + headless Service, `postgres:15.18-alpine` pinned.
- `configmap-initdb.yaml` mounts `files/initdb/*.sql` → schema (and seed data for the main DB) applied automatically on first boot.
- Credentials from pre-created Secrets; PVC-backed storage survives pod restarts.
- `backup-cronjob.yaml` (RND-015, after the 2026-07-08 EKS teardown wiped real prod signups): 4-hourly `pg_dump -Fc` → S3, off by default, enabled per env by the prod overlays (`deploy/envs/prod/postgres*.yaml`, bucket `myfitnessrank-db-backups-809379394639`, prefix `<service>/prod`). initContainer dumps with the server's own image; an `aws-cli` container (pinned `2.35.19`) uploads. Credentials via EKS pod identity bound to the `<service>-backup` ServiceAccount — no keys in-cluster, so the job only works on EKS (infra repo: `live/global/db-backups-bucket` survives stopinfra + `live/us-east-1/db-backups` IAM, upload-only). Restore: `pg_restore -d <db> <file>.dump`.

---

## 8. GitOps — ArgoCD (`deploy/argocd/`)

App-of-apps pattern, one app-of-apps **per cluster** (RND-013):
`deploy/argocd/local/` (kind — dev only, root applied by `./start`) and
`deploy/argocd/aws/` (EKS — staging + prod, root planted by the infra repo's
`argocd` Terraform unit). Each copy scopes its AppProject destinations and the
monitoring chart's `appNamespaces` to its own environments. EKS overlays pull
images from ECR (`809379394639.dkr.ecr.us-east-1.amazonaws.com/myfitnessrank/*`);
`root-app.yaml` is the **only** manifest ever applied by hand (kind).

| File | Purpose |
|---|---|
| `root-app.yaml` | Root Application → syncs `deploy/argocd/apps/` from `master` |
| `apps/appproject.yaml` | `myfitnessrank` AppProject — scopes what the child apps may deploy (least privilege vs. `default`) |
| `apps/services.yaml` | ApplicationSet: matrix generator (3 envs × 6 services, `core` covering auth+backend) → 18 Applications named `<service>-<env>`, each multi-source (chart + `$values` ref to `deploy/envs/<env>/<service>.yaml`), destination `myfitnessrank-<env>`; dev apps track the `dev` branch, staging/prod track `master`. `helm.releaseName` is pinned to the bare service name — without it ArgoCD uses the Application name (`<service>-<env>`) as the release name, suffixing every K8s resource and breaking cross-service DNS (`postgres`, …); auth/backend names are additionally safe because web-service's fullname defaults to the component name |
| `apps/prometheus-adapter.yaml` | prometheus-adapter chart (custom.metrics.k8s.io for the backend HPA, see §10) |
| `apps/kube-prometheus-stack.yaml` | Upstream chart from the prometheus-community Helm repo (see §10) |
| `apps/monitoring.yaml` | Our `helm/monitoring` chart (ServiceMonitor + dashboard) |

Conventions used:
- `automated: { prune: true, selfHeal: true }` everywhere — git is the single source of truth; manual drift is reverted.
- **Sync waves** order dependencies (kube-prometheus-stack CRDs at wave 1 before the ServiceMonitor at wave 2).
- `ServerSideApply=true` where CRDs exceed the client-side annotation size limit.
- `ignoreDifferences` on the admission webhook `caBundle` (the chart patches itself in-cluster; without this ArgoCD reports permanent OutOfSync).
- Promotion model: `dev` branch → dev namespace (sandbox), `master` → staging and prod (prod's image tags are pinned in its overlay and only move on release). Feature branches never deploy.
- The AppProject also permits `kube-system` — kube-prometheus-stack places control-plane scrape Services there, and a sync containing any forbidden resource fails as a whole.

---

## 9. Local Environment (`deploy/kind/`, `./start`, `./shutdown`)

Local stand-in for EKS so the whole GitOps loop runs on one machine.

### `./start` (idempotent — safe to re-run after reboot)
1. Verifies docker/kind/kubectl/openssl exist and the daemon is up.
2. Creates (or restarts) the `myfitnessrank` kind cluster from `deploy/kind/kind-config.yaml`.
3. Installs ingress-nginx (kind provider manifest, pinned version) and ArgoCD (pinned version, server-side apply).
4. Owns the ArgoCD admin password across reinstalls — stored in `~/.config/myfitnessrank/` (outside the repo so it can never be committed).
5. Creates the three env namespaces and, per env, independently generated out-of-band Secrets (DB credentials ×3, JWT signing key, Fernet key), plus `grafana-admin` in `monitoring`.
6. Builds app images (`REBUILD=1` to force) and `kind load`s them into the node; tags are **sourced from Helm values** so git stays authoritative.
7. Applies `root-app.yaml`; ArgoCD does the rest.
8. Reconciles `global_standards` seed data in every env on every run.
9. Reconciles the leaderboards schema in every env (`ADD COLUMN IF NOT EXISTS notified_at` — initdb only runs on fresh volumes).
9. Auto-manages detached port-forwards: ArgoCD UI :8081, Grafana :3000; apps via ingress at `dev.localhost:8080`, `staging.localhost:8080`, and `localhost:8080` (prod).

### `./shutdown`
- Default: gracefully stops the node container — cluster + DB data preserved (pairs with `./start`).
- Kills orphan port-forward processes.
- `DESTROY=1` deletes the cluster entirely; `GRACE=n` tunes the stop grace period.

---

## 10. Monitoring (`helm/monitoring/` + ArgoCD apps) — RND-005, extended by RND-012

### Stack
- **kube-prometheus-stack 87.3.0** (Prometheus Operator + Prometheus + Grafana + Alertmanager + node-exporter + kube-state-metrics) installed via ArgoCD from the upstream chart repo into the `monitoring` namespace.
- Values hardening: 2d retention + resource requests (kind-friendly), Grafana admin from the pre-created `grafana-admin` Secret (never in values), `*SelectorNilUsesHelmValues: false` so it discovers ServiceMonitors cluster-wide.

### Our chart (`helm/monitoring/`, version 0.2.0)
- `servicemonitor.yaml` — one ServiceMonitor selecting `app: myfitnessrank` Services across all three env namespaces (`appNamespaces` in values) on the `http` port at `/metrics`, 30s interval → 9 targets (3 services × 3 envs). Frontend is excluded via `component NotIn (frontend)` (nginx 404s on /metrics → would be a permanently-down target); Postgres is naturally excluded (no `http`-named port).
- `dashboard-configmap.yaml` + `dashboards/myfitnessrank.json` — Grafana dashboard auto-imported by the sidecar via the `grafana_dashboard` label; a `namespace` template variable filters panels per environment, legends read `namespace/service`. RND-012 added six custom-metric panels: ranks by exercise, tier distribution (24h pie), p95 estimated 1RM, signup/login outcomes, leaderboard size, leaderboard-sync + top-200-mail outcomes.
- `prometheusrule.yaml` (RND-012) — alert rules discovered by the operator (`ruleSelectorNilUsesHelmValues: false`): `ServiceDown` (`up == 0` in app namespaces, 5m, critical), `HighErrorRate` (5xx ratio > 5% for 10m, warning), `HighLatency` (p95 > 0.5s for 10m, warning). Thresholds/durations in `values.yaml` under `alerts:`.
- Control-plane scrape components that bind to 127.0.0.1 on kind (controller-manager, scheduler, etcd, kube-proxy) are disabled in the kube-prometheus-stack values — unreachable targets would show permanently down. CoreDNS stays enabled.

### App instrumentation
- All three Flask services expose `/metrics` via `prometheus-flask-exporter` with **gunicorn multiprocess mode** (per-worker counters aggregated through `PROMETHEUS_MULTIPROC_DIR`) — without this, scrapes would return only one random worker's numbers.
- **RND-012 fix:** the services previously used `GunicornPrometheusMetrics`, which registers **no** `/metrics` route (it expects a separate metrics server started from a gunicorn `when_ready` hook that was never configured) — under gunicorn, in-cluster `/metrics` was a 404 and every ServiceMonitor target was down. Switched to `GunicornInternalPrometheusMetrics`, which serves `/metrics` on the app port itself. Caught by a gunicorn-mode smoke test; explains why the §13 "verify 9 targets up" follow-up never passed.
- **Custom business metrics (RND-012)**, all `fitrank_*`-prefixed, defined next to the exporter init in each service's `app.py` (`prometheus-client` now pinned directly in each `requirements.txt`):
  - backend: `fitrank_ranks_total{exercise,sex,tier}` counter, `fitrank_one_rm_kg{exercise}` histogram (buckets 40–1000 kg), `fitrank_leaderboard_sync_total{outcome=synced|incomplete|failed}` counter.
  - auth: `fitrank_signups_total{outcome=created|rejected|conflict}`, `fitrank_logins_total{outcome=success|rejected}` counters.
  - leaderboards: `fitrank_board_submissions_total{sex}` counter, `fitrank_board_size{sex}` gauge (DB count, `multiprocess_mode="livemostrecent"` so workers don't sum a global truth), `fitrank_top200_mails_total{outcome=sent|failed}` counter.

### HPA on a custom metric (RND-012)
- `deploy/argocd/apps/prometheus-adapter.yaml` — prometheus-adapter 5.3.0 (wave 2, `monitoring` ns) serves `custom.metrics.k8s.io` from Prometheus; `rules.default: false`, single custom rule exposing `flask_http_request_total` as per-pod `flask_http_requests_per_second` (2m rate).
- `helm/web-service/templates/hpa.yaml` — autoscaling/v2 HPA on that Pods metric, gated by `autoscaling.enabled` (default **off**; target 5 req/s per pod). When enabled the Deployment omits `replicas` so ArgoCD selfHeal doesn't fight the autoscaler. Enabled for the **backend in dev only** (`deploy/envs/dev/core.yaml`, min 1 / max 3); staging/prod keep fixed replicas.

Status: RND-005 merged to master (PR #4, 2026-07-02); first live sync exposed an AppProject gap — the stack's `kube-system` scrape Services were forbidden, failing the whole sync — fixed alongside the environments work (RND-006). RND-012 (custom metrics + alerts + HPA + auth/backend umbrella restructure, §7) on `feature/RND-012-custom-metrics`; chart state: monitoring 0.2.0, core 0.1.0 + web-service 0.1.0 (backend image 0.1.4, auth image 0.1.1), leaderboards 0.1.3 (image 0.1.3).

---

## 11. CI — GitHub Actions (`.github/workflows/ci.yml`)

Runs on every branch push and PRs to master.

| Job | What it does |
|---|---|
| `lint` | ruff check + ruff format check over backend/auth/leaderboards (pinned ruff 0.6.9) |
| `test` | Backend pytest against a real `postgres:15.6-alpine` service container (health-checked) |
| `test-auth` | Auth pytest (test-only `JWT_SIGNING_KEY` env, clearly marked not-for-prod) |
| `test-leaderboards` | Leaderboards pytest |
| `frontend` | npm ci (`--ignore-scripts`) → lint → vitest → production build |
| `build` | Needs all test jobs; docker-builds all three service images; on `master` only, checks AWS secrets, assumes role via **OIDC** (`id-token: write`, no long-lived keys), logs into ECR, pushes |

Standards enforced:
- **Every `uses:` is pinned to a full commit SHA** with the version as a trailing comment — resolved live from the GitHub API, never from memory.
- Pip/npm caches keyed on lockfiles; Python 3.11 / Node 22 pinned.
- Secrets never referenced in `if:` expressions directly (exposed via step output instead).

The build job docker-builds all four images and, on `master`, pushes each to its own ECR repository (`myfitnessrank/<service>`), matching the repositories Terraform will create (§14.3).

---

## 12. Repo Governance (`.claude/`, `CLAUDE.md`, branching)

- **GitHub Flow**: `master` protected + always deployable; all work on `feature/RND-NNN-*`; merge via PR with passing CI; `vX.Y.Z` tags will trigger production deploys.
- Conventional-ish commits (`feat:`/`fix:`/`chore:`/`ci:`/`infra:`/`docs:`/`test:`), no AI attribution trailers.
- `.claude/standards.md` — Docker/K8s/Terraform/CI/Python quality rules (source of truth).
- `.claude/context.md` — architecture + MVP scope (note: predates the microservice split; describes the original 3-tier shape).
- `.claude/prompts/` — feature-implementation and code-review templates.
- Merged PRs so far: #1 leaderboards service, #2 ArgoCD→master tracking, #3 leaderboard frontend.

---
---

# ROADMAP — Remaining Work (templates)

Everything below is **not built yet**. Each section is a checklist template with the
practices we intend to follow, so a section can be lifted straight into an RND ticket.

## 13. Immediate follow-ups (this repo)

- [x] Merge `feature/RND-005-monitoring` → master (PR #4).
- [ ] Run `./start` end-to-end after the RND-006 merge; verify Prometheus targets (9 up: 3 services × 3 envs) and the Grafana dashboard.
- [x] Update `.claude/context.md` to reflect the microservice architecture.
- [x] CI: build the frontend image and push **all four images** to per-service ECR repositories (`myfitnessrank/<service>`).

## 14. Terraform — infra repo (`myfitnessrank-infra`)

Principles: terraform-aws-modules over hand-rolled resources; remote state from day one;
no resource created by hand in the console; least-privilege IAM; everything tagged
(`Project`, `Environment`, `ManagedBy=terraform`).

### 14.1 Bootstrap (one-time, its own state)
- [ ] S3 state bucket — versioning on, SSE (SSE-S3 or KMS), public access blocked, `use_lockfile = true` for S3-native state locking (TF ≥ 1.10; no DynamoDB table needed).
- [ ] GitHub OIDC identity provider in IAM + CI deploy role — trust policy scoped to `repo:<org>/myfitnessrank:*` (and `ref:refs/heads/master` / `refs/tags/v*` for deploys); permissions limited to ECR push + EKS describe. Fills the `AWS_ROLE_ARN` secret CI already expects.

### 14.2 Network (module: `terraform-aws-modules/vpc/aws`)
- [ ] VPC `/16`, 3 AZs; private subnets for nodes, public for load balancers.
- [ ] Subnet tags EKS requires: `kubernetes.io/role/elb=1` (public), `kubernetes.io/role/internal-elb=1` (private).
- [ ] Single NAT gateway for staging (cost), one-per-AZ documented as the prod option.
- [ ] VPC endpoints (ECR api+dkr, S3) to keep image pulls off the NAT — cost + security.

### 14.3 ECR (module: `terraform-aws-modules/ecr/aws`)
- [ ] One repository per service: `myfitnessrank/backend`, `/auth`, `/leaderboards`, `/frontend`.
- [ ] `image_tag_mutability = IMMUTABLE` (a tag can never be silently repointed).
- [ ] Scan on push enabled.
- [ ] Lifecycle policy: keep last N tagged images, expire untagged after 14 days.

### 14.4 EKS (module: `terraform-aws-modules/eks/aws`)
- [ ] Supported K8s version pinned explicitly (never default); upgrade path documented.
- [ ] Managed node group in private subnets; instance type + min/max/desired per env.
- [ ] Authentication via **EKS access entries** (`authentication_mode = API`), not the legacy `aws-auth` ConfigMap.
- [ ] **EKS Pod Identity** (or IRSA) for any pod needing AWS APIs — no node-role credentials for workloads.
- [ ] Core add-ons pinned: vpc-cni, coredns, kube-proxy, **aws-ebs-csi-driver** (needed by the Postgres and Prometheus PVCs) with its own pod identity/IRSA role.
- [ ] Control-plane logging enabled (api, audit, authenticator).
- [ ] Cluster add-ons via Helm (ArgoCD-managed where possible): **AWS Load Balancer Controller** (replaces the kind ingress path), ExternalDNS (optional), Cluster Autoscaler *or* Karpenter — pick one, document why.
- [ ] Endpoint access: public+private for the course setup; note prod-hardened option (private only + bastion/SSM).

### 14.5 Module layout (infra repo)
```
myfitnessrank-infra/
  modules/            # only if we need thin wrappers over terraform-aws-modules
  bootstrap/          # state bucket + OIDC (applied once, local state then migrated)
  vpc/  ecr/  eks/    # one component per directory, composed by Terragrunt (§15)
```

## 15. Terragrunt — environment layering

Principles: DRY backend/provider config generated by the root `root.hcl`; one
`terragrunt.hcl` per component per environment ("unit"); explicit `dependency` blocks
so `vpc → eks` ordering is enforced and outputs flow without manual copying.

- [ ] Live layout:
```
live/
  root.hcl                    # remote_state + provider generation, common inputs/tags
  staging/
    env.hcl                   # environment-wide inputs (cidr, instance sizes, cluster name)
    vpc/terragrunt.hcl
    ecr/terragrunt.hcl        # or place ECR under a shared/ account-level tree — decide once
    eks/terragrunt.hcl        # dependency: vpc
  production/
    env.hcl
    vpc/  eks/
```
- [ ] State key derived from `path_relative_to_include()` — one state object per unit, no collisions.
- [ ] `mock_outputs` on dependencies so `terragrunt plan --all` works before first apply.
- [ ] Version-pin terraform, terragrunt, and every module source (`?ref=vX.Y.Z`).
- [ ] Document the run order: `bootstrap` → `vpc` → `ecr` → `eks` (or `terragrunt apply --all` from `live/staging`).
- [ ] **Never auto-applied by Claude/CI without a human gate** — plan output reviewed first (matches the repo's destructive-actions policy).

## 16. Deploy pipelines (GitHub Actions)

- [ ] `deploy-staging.yml` — on merge to master: build → push all images to ECR (immutable `github.sha` tags) → **bump image tags in `deploy/envs/` via PR/commit** (GitOps: CI never runs `helm upgrade` or `kubectl apply` against the cluster).
- [ ] `deploy-production.yml` — on `v*.*.*` tag: retag/promote the already-tested staging digest (build once, promote many — no rebuild for prod), bump the prod overlay in `deploy/envs/`.
- [ ] OIDC role assumption in both (no static AWS keys anywhere).
- [ ] All new actions SHA-pinned via the live-API resolution process in CLAUDE.md.
- [ ] Concurrency group per environment so overlapping deploys queue instead of racing.

## 17. GitOps state (this repo — no separate gitops repo)

**Decision (2026-07-05):** GitOps desired state stays in this repo (`deploy/argocd/` + `deploy/envs/`) instead of a separate `myfitnessrank-gitops` repo. One repo keeps chart, overlay, and app changes atomic in a single PR; the mono-repo is small enough that the separation buys nothing yet.

- [x] Per-environment desired state: `deploy/envs/<env>/<service>.yaml` — values overlays per service (image tag, replicas, resources, ingress hosts).
- [x] ArgoCD **ApplicationSet** generating one Application per (service × environment) (`deploy/argocd/apps/services.yaml`).
- [ ] Root/bootstrap app per cluster; ArgoCD itself installed by Terraform/Helm on EKS and pointed at this repo's `deploy/argocd/apps/`.
- [ ] Secrets strategy for EKS (choose one, document): External Secrets Operator + AWS Secrets Manager (preferred — keeps the "no secrets in git" rule) vs. Sealed Secrets.

## 18. Production data layer

- [ ] Decide: keep in-cluster Postgres StatefulSets (EBS-backed via the CSI driver, matches coursework) vs. RDS (managed, the real-world default). Document the trade-off.
- [ ] If in-cluster: StorageClass (gp3), PVC sizing, scheduled `pg_dump` backups to S3 (CronJob), restore runbook.
- [ ] If RDS: terraform-aws-modules/rds, private subnets, credentials in Secrets Manager → External Secrets.

## 19. Monitoring & alerting (beyond RND-005)

- [ ] Prometheus/Grafana **persistence** on EKS (PVCs) + realistic retention (kind uses 2d).
- [x] PrometheusRule alerts: service down (`up == 0`), 5xx rate, p95 latency (RND-012, §10). Still open: pod restart loops, PVC near-full, CPU/memory vs. limits.
- [ ] Alertmanager receiver (email or Slack webhook via Secret) — rules fire but route nowhere useful yet.
- [x] Grafana: RED + business-metric panels building on the existing dashboard JSON (RND-012, §10).
- [ ] Ingress/ALB metrics once the AWS Load Balancer Controller is in.

## 20. Logging (assignment: Elasticsearch + Kibana, or CloudWatch)

- [ ] Decide stack: EFK (Elasticsearch/Fluent Bit/Kibana in-cluster) vs. Fluent Bit → CloudWatch Logs (simpler on EKS). Document why.
- [ ] Fluent Bit DaemonSet ships container stdout/stderr — apps already log structured lines to stdout, so no app changes needed.
- [ ] Retention policy + index lifecycle (or CloudWatch retention days) — logs are the easiest bill to bloat.

## 21. Hardening backlog (nice-to-have, note-worthy for review)

- [ ] NetworkPolicies: default-deny in `myfitnessrank` namespace; allow frontend→services, services→own DB, Prometheus→/metrics only.
- [ ] PodDisruptionBudgets for the 2-replica services.
- [ ] HPA for backend/leaderboards once resource metrics are validated.
- [ ] Image scanning gate in CI (ECR scan findings or trivy) before push.
- [ ] Helm chart testing in CI (`helm lint` + `helm template` render check).
- [ ] Renovate/Dependabot for pinned actions, base images, and chart versions.
