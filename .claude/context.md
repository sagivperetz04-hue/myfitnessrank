# Project Context

## What This Project Is

**myfitnessrank-app** is a 3-tier fitness ranking web application.

Users log their lifts (exercise, weight, reps). The system calculates their One Rep Max (1RM),
compares it against a pre-seeded global distribution, and assigns a percentile rank tier
(Copper → Bronze → Silver → Gold → Platinum → Elite).

The app is the vehicle for a full DevOps pipeline — the primary goal is the infrastructure,
CI/CD, and observability around the application, not the application itself.

---

## MVP Feature Set

1. **Lift input** — form to enter exercise name, weight (kg), reps
2. **1RM calculation** — backend computes 1RM using Epley formula: `weight * (1 + reps/30)`
3. **Ranking** — classify 1RM into tier against `global_standards` table benchmarks
4. **Dashboard** — display rank per muscle group + overall weighted body rank
5. **Workout logs** — save sets under predefined templates (Push / Pull / Legs)

---

## Architecture

```
Browser
  └─► Frontend (React or plain HTML — port 80/443 via Ingress)
        └─► Backend API (Flask — port 5000)
              └─► PostgreSQL (StatefulSet — port 5432)
```

**Frontend** — serves the dashboard and lift input forms. Calls the backend API.
**Backend** — stateless Flask API. Handles 1RM calculation, ranking logic, DB queries.
**Database** — PostgreSQL StatefulSet. Persists users, workout logs, and global standards.

---

## Data Model (PostgreSQL)

```sql
-- Read-only benchmark table, seeded at deploy time
CREATE TABLE global_standards (
    exercise    TEXT NOT NULL,
    tier        TEXT NOT NULL,   -- copper, bronze, silver, gold, platinum, elite
    min_1rm_kg  NUMERIC NOT NULL,
    PRIMARY KEY (exercise, tier)
);

-- Users (for future auth — MVP can stub this)
CREATE TABLE users (
    id         SERIAL PRIMARY KEY,
    username   TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Workout log
CREATE TABLE workout_logs (
    id          SERIAL PRIMARY KEY,
    user_id     INT REFERENCES users(id),
    exercise    TEXT NOT NULL,
    weight_kg   NUMERIC NOT NULL,
    reps        INT NOT NULL,
    one_rm_kg   NUMERIC NOT NULL,
    tier        TEXT NOT NULL,
    logged_at   TIMESTAMPTZ DEFAULT NOW()
);
```

---

## API Endpoints (Backend)

| Method | Path | Description |
|---|---|---|
| GET | `/health` | K8s liveness/readiness probe |
| POST | `/api/rank` | Body: `{username, exercise, weight_kg, reps, bodyweight_kg, sex}` → returns `{one_rm_kg, weight_class_kg, competition: {percentile, tier}, world_avg: {percentile, tier}}` |
| GET | `/api/rank/history` | Returns recent logs for the user |
| POST | `/api/log` | Save a workout set |

---

## Tech Stack Decisions

| Layer | Choice | Reason |
|---|---|---|
| Backend | Python 3.11 + Flask | Familiar, simple, course uses Python |
| Frontend | React (Vite) or plain HTML | TBD |
| Database | PostgreSQL 15 | Standard relational, StatefulSet-friendly |
| Container registry | AWS ECR | Required by assignment |
| K8s cluster | AWS EKS | Required by assignment |
| IaC | Terraform + terraform-aws-modules | Required by assignment |
| GitOps | ArgoCD | Required by assignment |
| CI | GitHub Actions | Chosen over Jenkins |
| Monitoring | Prometheus + Grafana (kube-prometheus-stack) | Required by assignment |
| Logging | Elasticsearch + Kibana (or CloudWatch) | TBD |

---

## Repository Layout

```
myfitnessrank-app/         ← this repo
  backend/
    app.py
    requirements.txt
    Dockerfile
  frontend/
    (TBD)
    Dockerfile
  helm/
    backend/
    frontend/
    postgres/
  .github/
    workflows/
      ci.yml
      deploy-staging.yml
      deploy-production.yml
  CLAUDE.md
  .claude/
    standards.md
    context.md
    prompts/
```

Separate repositories:
- `myfitnessrank-gitops` — ArgoCD desired state per environment
- `myfitnessrank-infra` — Terraform modules
