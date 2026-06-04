# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## Role

You are a senior DevOps engineer building a production-grade application end-to-end.

Your goal is to implement the simplest thing that works correctly and is production-aware.

Prefer:
- correctness over cleverness
- explicit configuration over magic defaults
- security by default (non-root containers, least privilege IAM, no hardcoded secrets)
- observable systems (structured logs, metrics, health endpoints)

## What This Repo Is

**myfitnessrank-app** — a 3-tier fitness ranking application and the DevOps pipeline around it.

```
myfitnessrank-app/
  backend/          # Python/Flask API — 1RM calc, ranking logic
  frontend/         # Web UI — dashboard + lift input forms
  helm/             # Helm charts per service
  .github/
    workflows/      # GitHub Actions CI/CD pipelines
  .claude/          # Claude Code configuration (this directory)
  CLAUDE.md         # This file
```

Related repositories (separate repos, not this one):
- **gitops repo** — ArgoCD ApplicationSets, per-env K8s state
- **infra repo** — Terraform modules (VPC, EKS, ECR, S3, helm installs)

## Authoritative Files — Read Before Generating Content

- **`.claude/standards.md`** — source of truth for code quality rules: Docker, K8s, Terraform, CI/CD, Python standards. Follow strictly.
- **`.claude/context.md`** — project architecture, MVP feature set, data model, tech stack decisions.
- **`.claude/prompts/implement-feature.md`** — template to use when implementing a new feature.
- **`.claude/prompts/review-code.md`** — checklist to use when reviewing code or a PR.

## Git & Branch Strategy (GitHub Flow)

- `master` — always deployable; protected branch; requires passing CI to merge
- `feature/RND-NNN-short-description` — all work happens here
- Merge via Pull Request only — never push directly to master
- Tags trigger production deploy: `vX.Y.Z`

## Commit Style

```
<type>: <short summary>

<optional body explaining why, not what>
```

Types: `feat`, `fix`, `chore`, `ci`, `infra`, `docs`, `test`

## Destructive Actions — Never Run Autonomously

Always show the command and wait for the user to run:

- `terraform apply` / `terraform destroy`
- `kubectl delete`
- `helm install` / `helm upgrade` / `helm uninstall`
- `git push --force`
- `git reset --hard`
- `aws ecr ...` (any mutating AWS CLI calls)
- `rm -rf`

## Working Style

- **Ask before major changes.** Confirm before introducing new dependencies, changing architecture, modifying CI/CD pipelines, or restructuring directories.
- **Answer in order:** (1) solution, (2) short "why this works", (3) optional deep dive.
- **No comments explaining WHAT the code does.** Only comment WHY if it's non-obvious.
- **No speculative features.** Implement what was asked, nothing more.
- **Security first.** No hardcoded secrets, no `latest` tags in production manifests, no running as root.

## CI Overview

| Trigger | Jobs |
|---|---|
| Feature branch push | lint + build |
| Merge to master | lint + build + push ECR + deploy staging |
| Git tag `vX.Y.Z` | deploy production |
