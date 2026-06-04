# Prompt: Implement Feature

Use this prompt when starting work on a new feature.
Fill in the blanks and give it to Claude Code to plan the implementation.

---

Using the project standards and context in `.claude/`:

Implement the following feature:

**Feature name:**
**Feature branch:**  feature/RND-NNN-...

**Description:**
(What should the user be able to do after this is implemented?)

**Affected services:**
- [ ] Backend (app.py / routes / services)
- [ ] Frontend
- [ ] Database (schema change or seed data)
- [ ] Helm chart
- [ ] GitHub Actions workflow
- [ ] Other:

**API changes (if any):**
(New endpoints, changed request/response shape)

**Database changes (if any):**
(New tables, columns, indexes, migrations, seed data)

**Tests required:**
(What must pass before this is mergeable?)

**Definition of done:**
- [ ] Code written and linted
- [ ] Docker build passes
- [ ] Unit/integration tests pass
- [ ] Helm chart updated if needed
- [ ] PR created against master with a description
