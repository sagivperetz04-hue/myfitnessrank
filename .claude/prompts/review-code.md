# Prompt: Review Code / PR

Use this prompt when reviewing a PR or a completed feature.
Give it to Claude Code with the diff or PR number.

---

Review the following code/PR against:
- `.claude/standards.md`
- `.claude/context.md`

Check for:

**Correctness**
- [ ] Business logic is correct (1RM formula, ranking tiers, etc.)
- [ ] API response shape matches the spec in context.md
- [ ] DB queries are safe (no SQL injection, parameterized queries)
- [ ] Error cases are handled

**Docker**
- [ ] Base image is pinned (no `latest`)
- [ ] Multi-stage build used
- [ ] Non-root user in final stage
- [ ] Layer cache is not broken unnecessarily

**Kubernetes / Helm**
- [ ] No `namespace: default`
- [ ] Resource limits and requests set
- [ ] No `:latest` image tag
- [ ] Health probes defined
- [ ] imagePullSecrets configured

**CI/CD**
- [ ] Build and deploy jobs are separate
- [ ] No secrets printed in logs
- [ ] Dependencies cached

**Security**
- [ ] No hardcoded secrets or credentials
- [ ] Containers not running as root
- [ ] IAM roles follow least privilege

**Code quality**
- [ ] No unnecessary comments (no "what" comments, only "why")
- [ ] Business logic is not inside route handlers
- [ ] `/health` endpoint exists and returns 200

Report findings as:
- BLOCKER — must fix before merge
- WARNING — should fix, not a merge blocker
- SUGGESTION — optional improvement
