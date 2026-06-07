# MyFitnessRank

**Know exactly where you stand.**

MyFitnessRank turns your gym lifts into a competitive rank. Log a set, get your One Rep Max calculated instantly, and see how you compare against global standards — from Copper all the way to Elite.

---

## What It Does

You enter an exercise, a weight, and how many reps you did. MyFitnessRank does the rest:

1. Calculates your **One Rep Max (1RM)** using the Epley formula
2. Compares it against a global benchmark table
3. Awards you a **tier** — Copper, Bronze, Silver, Gold, Platinum, or Elite
4. Tracks your history so you can see progression over time

No manual math. No guessing. Just your rank.

---

## Rank Tiers

| Tier | Description |
|---|---|
| Copper | Getting started |
| Bronze | Building consistency |
| Silver | Above average |
| Gold | Seriously strong |
| Platinum | Top percentile |
| Elite | World-class |

---

## Features

- **1RM Calculator** — Epley-formula based, works for any barbell lift
- **Lift Ranking** — ranked per exercise against global standards
- **Workout Logs** — save sets under Push / Pull / Legs templates
- **Dashboard** — overall body rank weighted across muscle groups
- **REST API** — clean JSON API, ready to integrate or extend

---

## API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/rank` | Submit a lift, get back 1RM + tier |
| `GET` | `/api/rank/history` | Your recent lift history |
| `POST` | `/api/log` | Save a workout set |

**Example request:**
```bash
curl -X POST http://localhost:5000/api/rank \
  -H "Content-Type: application/json" \
  -d '{"exercise": "bench_press", "weight_kg": 100, "reps": 5}'
```

**Example response:**
```json
{
  "exercise": "bench_press",
  "one_rm_kg": 116.67,
  "tier": "Gold"
}
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11 + Flask |
| Database | PostgreSQL 15 |
| Container Runtime | Docker |
| Orchestration | Kubernetes (AWS EKS) |
| Infrastructure | Terraform |
| GitOps | ArgoCD |
| CI/CD | GitHub Actions |
| Monitoring | Prometheus + Grafana |
| Registry | AWS ECR |

---

## Running Locally

**Prerequisites:** Docker, Python 3.11+, PostgreSQL

```bash
# Clone the repo
git clone https://github.com/sagivperetz04-hue/myfitnessrank.git
cd myfitnessrank-app

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=postgresql://user:password@localhost:5432/myfitnessrank
export FLASK_ENV=development

# Apply the schema
psql $DATABASE_URL < schema.sql

# Start the API
python app.py
```

API will be available at `http://localhost:5000`.

---

## Project Structure

```
myfitnessrank-app/
  backend/          # Flask API — 1RM logic, ranking, DB layer
  frontend/         # Web UI — dashboard + lift input forms
  helm/             # Helm charts (backend, frontend, postgres)
  .github/
    workflows/      # GitHub Actions CI/CD pipelines
```

---

## CI/CD Pipeline

| Trigger | Jobs |
|---|---|
| Feature branch push | Lint + build |
| Merge to `master` | Lint + build + push to ECR + deploy to staging |
| Git tag `vX.Y.Z` | Deploy to production |

---

## License

MIT
