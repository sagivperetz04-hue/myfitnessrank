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
- **infra repo** — Terraform modules (VPC, EKS, ECR, S3, helm installs)

GitOps state (ArgoCD ApplicationSets, per-env K8s overlays) lives **in this repo** under `deploy/argocd/` and `deploy/envs/` — no separate gitops repo.

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

**No signature.** Never add `Co-Authored-By: Claude` or any Claude attribution to commit messages or files.

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

- **Keep the manifest current.** Every change — and every project directory it touches — must be recorded in `PROJECT_MANIFEST.md` (update the relevant section and the `Last updated` line) in the same branch/PR as the change itself.
- **Ask before major changes.** Confirm before introducing new dependencies, changing architecture, modifying CI/CD pipelines, or restructuring directories.
- **Answer in order:** (1) solution, (2) short "why this works", (3) optional deep dive.
- **No comments explaining WHAT the code does.** Only comment WHY if it's non-obvious.
- **No speculative features.** Implement what was asked, nothing more.
- **No new technologies.** Never introduce a new language, framework, library, tool, or service into the stack unless it is absolutely necessary or I explicitly asked for it. If it is necessary, stop and notify me first — explain why, and what it replaces or adds — and wait for my approval before adding it.
- **No unsolicited documentation.** Do not create or write documentation (READMEs, docs files, comment blocks, guides) unless I specifically ask for it.
- **Security first.** No hardcoded secrets, no `latest` tags in production manifests, no running as root.

## GitHub Actions — SHA Pinning Rules

Every `uses:` line must be pinned to a full commit SHA, never a floating tag (`@v4`, `@latest`).

**Always resolve SHAs live via the GitHub API before writing or updating any action.** Never use a SHA from memory — it may be stale.

Resolution process for every action:
1. `curl -s https://api.github.com/repos/<owner>/<action>/releases/latest` → get tag name
2. `curl -s https://api.github.com/repos/<owner>/<action>/git/ref/tags/<tag>` → get object type + SHA
3. If type is `tag` (annotated): `curl -s https://api.github.com/repos/<owner>/<action>/git/tags/<sha>` → use `.object.sha`
4. If type is `commit`: use the SHA directly
5. Write: `uses: owner/action@<commit-sha>  # <tag>`

Always check `releases/latest` — never assume the version you know is current.

## CI Overview

| Trigger | Jobs |
|---|---|
| PR to master | per-service lint + test + build — only for services whose code/chart changed (`CI OK` is the required check) |
| Merge to master | same, plus push changed services' images to ECR → ArgoCD deploys staging |
| Git tag `vX.Y.Z` | build all images at the version + promotion PR → prod |
| Feature branch push (no PR) | nothing |
