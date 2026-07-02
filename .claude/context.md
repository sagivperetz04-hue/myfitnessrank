# Project Context

## What This Project Is

**myfitnessrank-app** is a fitness ranking web application built as microservices.

Users log their lifts (exercise, weight, reps). The system calculates their One Rep Max (1RM),
compares it against a pre-seeded global distribution, and assigns a percentile rank tier
(Copper → Bronze → Silver → Gold → Platinum → Elite). Signed-in users can submit lifts
to a global leaderboard.

The app is the vehicle for a full DevOps pipeline — the primary goal is the infrastructure,
CI/CD, and observability around the application, not the application itself.

---

## Architecture

Originally a 3-tier monolith; split into microservices in RND-002 (auth) and RND-003
(leaderboards). **Database-per-service** — each service owns its schema, no shared tables.
The frontend nginx is the single public entry point (Ingress) and reverse-proxies to
every service; the APIs are never exposed outside the cluster directly.

```
Browser
  └─► Frontend (React + unprivileged nginx :8080 — exposed via Ingress)
        ├─► /api/auth/*        → auth service (Flask :5000)          → postgres-auth
        ├─► /api/leaderboards* → leaderboards service (Flask :5000)  → postgres-leaderboards
        └─► /api/*             → backend service (Flask :5000)       → postgres (fitrank)
                                     └─► calls leaderboards internally for /api/leaderboard
```

| Service | Responsibility |
|---|---|
| **frontend** | Dashboard, lift input, login/signup, leaderboard page; nginx doubles as the API gateway (upstream URLs injected via env at container start) |
| **backend** | 1RM calculation (Epley), percentile ranking against `global_standards`, workout history/bests |
| **auth** | Accounts; Argon2 password hashing; JWT access tokens + refresh cookie path-scoped to `/api/auth` |
| **leaderboards** | Public leaderboard reads; JWT-verified lift submissions (verifies auth's tokens via shared signing key — no per-request call to auth); Fernet-encrypted lifter names |
| **postgres / postgres-auth / postgres-leaderboards** | Three PostgreSQL 15 StatefulSets, one per service |

Every service exposes `/health` (readiness, DB ping), `/health/live` (liveness, dependency-free),
and `/metrics` (Prometheus, gunicorn multiprocess-aware).

**Environments:** dev / staging / prod are namespaces on the single cluster
(`myfitnessrank-<env>`), each with its own Postgres trio and independently generated
secrets. Promotion: `dev` branch → dev, `master` → staging and prod (prod's image tags
are pinned in `deploy/envs/prod/`). Per-env config lives in `deploy/envs/<env>/` values
overlays; ArgoCD generates one Application per (env × service) from a single
ApplicationSet. Local access: `dev.localhost:8080`, `staging.localhost:8080`,
prod at `localhost:8080`.

---

## Data Model

The `schema.sql` in each service directory is the source of truth. Summary:

**backend** (`backend/schema.sql`, DB `fitrank`):
- `global_standards` — read-only benchmark distribution, seeded at deploy: `(lift, sex, weight_class_kg, percentile, track)` → `min_kg`; `track` is `competition` or `world_avg`
- `users` — `id`, unique `username`
- `workout_logs` — full lift record incl. `one_rm_kg`, `weight_class_kg`, and percentile+tier for both tracks; indexed for history and per-exercise-best queries

**auth** (`auth/schema.sql`, DB in `postgres-auth`):
- `accounts` — `email` (unique), `username` (unique case-insensitively via `LOWER(username)` index, stored as typed), `password_hash` (Argon2)

**leaderboards** (`leaderboards/schema.sql`, DB in `postgres-leaderboards`):
- `leaderboard_entries` — one row per lifter: `sex`, `source` (`seed` dataset row or `user`), encrypted name (`name_enc`), per-lift kg columns, generated `bw_ratio`; partial unique index `(sex, user_id) WHERE source = 'user'` is the upsert target for overwrite-when-better submissions

---

## API Endpoints

**backend**
| Method | Path | Description |
|---|---|---|
| POST | `/api/rank` | `{username, exercise, weight_kg, reps, bodyweight_kg, sex}` → `{one_rm_kg, weight_class_kg, competition: {percentile, tier}, world_avg: {percentile, tier}}`; validates reps ≤ 20, weight ≤ world record + 2 kg |
| GET | `/api/users/<username>/history` | Paginated logs (`limit` ≤ 100, `offset`, optional `exercise` filter) |
| GET | `/api/users/<username>/best` | Best 1RM per exercise |
| GET | `/api/leaderboard` | Proxies to the leaderboards service (`sex`, `weight_class`, `lift`) |

**auth** (all under `/api/auth/`)
| Method | Path | Description |
|---|---|---|
| GET | `/api/auth/username-available` | Live signup-form check |
| POST | `/api/auth/signup` | Email + username + password-strength validation |
| POST | `/api/auth/login` | Returns access JWT, sets `mfr_refresh` cookie |
| POST | `/api/auth/refresh` | New access token from the refresh cookie |
| POST | `/api/auth/logout` | Clears the refresh cookie |
| GET | `/api/auth/me` | Identity from a valid access token |

**leaderboards**
| Method | Path | Description |
|---|---|---|
| GET | `/api/leaderboards` | Top entries by sex / weight class / lift |
| POST | `/api/leaderboards/submit` | Requires `Bearer` access token; upserts the caller's entry when better |

---

## Tech Stack Decisions

| Layer | Choice | Status |
|---|---|---|
| Backend services | Python 3.11 + Flask + gunicorn | Done (backend, auth, leaderboards) |
| Frontend | React 18 + Vite, served by unprivileged nginx | Done |
| Database | PostgreSQL 15, StatefulSet per service | Done (local) |
| Container registry | AWS ECR | Pending (Terraform) |
| K8s cluster | AWS EKS | Pending (Terraform); kind locally |
| IaC | Terraform + terraform-aws-modules + Terragrunt | Pending |
| GitOps | ArgoCD, app-of-apps + ApplicationSet (env × service) | Done (local cluster) |
| Environments | dev/staging/prod namespaces on one cluster (cost: one control plane) | Done (local) |
| CI | GitHub Actions (SHA-pinned actions, OIDC to AWS) | Done; deploy workflows pending |
| Monitoring | Prometheus + Grafana via kube-prometheus-stack | Done (RND-005) |
| Logging | Elasticsearch + Kibana (or CloudWatch) | TBD |

---

## Repository Layout

```
myfitnessrank-app/         ← this repo
  backend/                 # ranking API (app, services/, tests/, schema.sql, Dockerfile)
  auth/                    # auth service (same shape)
  leaderboards/            # leaderboards service (same shape + seed scripts)
  frontend/                # React app + nginx.conf.template + Dockerfile
  helm/                    # one chart per service + per-DB postgres charts + monitoring
  deploy/
    kind/                  # local cluster config
    argocd/                # root app + AppProject + services ApplicationSet + monitoring apps
    envs/                  # per-environment values overlays (dev/staging/prod × service)
  .github/workflows/
    ci.yml                 # lint + test + build (+ ECR push on master)
                           # deploy-staging.yml / deploy-production.yml: planned
  start / shutdown         # idempotent local environment up/down
  PROJECT_MANIFEST.md      # detailed build log + roadmap templates
  CLAUDE.md  .claude/      # working rules, standards, this file
```

Separate repositories (planned):
- `myfitnessrank-gitops` — ArgoCD desired state per environment
- `myfitnessrank-infra` — Terraform modules + Terragrunt live tree
