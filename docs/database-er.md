# Database ER Diagram (text)

## Entity overview

```
users ──┬──< user_roles >── roles ──< role_permissions >── permissions
        ├──< sessions ──< refresh_tokens
        ├──< refresh_tokens
        ├──< resumes ── resume_analyses (1:1)
        ├──< interviews ──< questions ──< answers
        │                    └── feedback (1:1)
        ├──< submissions ──< execution_results
        │         └── coding_problems
        ├── analytics (1:1)
        ├──< user_achievements >── achievements
        ├──< notifications
        ├──< reports
        ├──< study_plans ──< study_plan_tasks
        ├──< coach_messages
        ├──< user_company_roadmaps
        ├──< user_subscriptions
        └──< activity_logs
```

## Cardinality notes

| Relationship | Type | On delete |
|--------------|------|-----------|
| User → Roles | M:N | CASCADE on join rows |
| Role → Permissions | M:N | CASCADE on join rows |
| User → Sessions | 1:N | CASCADE |
| Session → RefreshTokens | 1:N | CASCADE |
| User → Resumes | 1:N | CASCADE |
| Resume → ResumeAnalysis | 1:0..1 | CASCADE |
| User → Interviews | 1:N | CASCADE |
| Interview → Questions | 1:N | CASCADE |
| Question → Answers | 1:N | CASCADE |
| Question → Question (follow-up) | self FK | SET NULL |
| Interview → Feedback | 1:0..1 | CASCADE |
| CodingProblem → Submissions | 1:N | CASCADE |
| Submission → ExecutionResults | 1:N | CASCADE |
| User → Analytics | 1:0..1 | CASCADE |

## Design choices

1. **UUID PKs** — avoid enumerable IDs in URLs.
2. **JSONB** — AI payloads evolve without constant ALTER TABLE.
3. **Enums** — constrain status/type columns at the DB layer.
4. **Soft delete on users/resumes** — retain audit trail; hard-delete for GDPR.
5. **token_hash only** — never store raw refresh tokens.
6. **ARRAY tags** on coding problems — simple tag queries in Postgres.

## Migration command

```bash
docker compose exec api alembic upgrade head
docker compose exec api python -m app.db.seed
```
