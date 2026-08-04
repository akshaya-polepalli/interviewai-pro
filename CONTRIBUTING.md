# Contributing

This is primarily a portfolio / learning monorepo. Contributions are welcome if you are collaborating with the owner.

## Ground rules

1. Never commit `.env`, secrets, or real API keys — use `.env.example`.
2. Prefer small PRs that map to one concern (API, UI, docs, or tests).
3. Run backend tests before opening a PR:

```powershell
docker compose exec api pytest -q
```

4. Match existing layering: routes → services → repositories → models.
5. Document new modules under `docs/` and add a row to the README module table.

## Local setup

See [`README.md`](README.md) and [`docs/DEMO.md`](docs/DEMO.md).

## Security

If you find a vulnerability, please open a private report rather than a public issue with exploit details. See [`SECURITY.md`](SECURITY.md).
