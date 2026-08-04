# System architecture (Modules 1–16)

High-level view of InterviewAI Pro for README embeds and system-design interviews.

## Runtime topology

```mermaid
flowchart LR
  subgraph Client
    SPA["React SPA\nVite + Tailwind"]
  end

  subgraph Edge
    NGX["Nginx\nprod gateway"]
  end

  subgraph App
    API["FastAPI\n/api/v1"]
    WRK["Celery workers"]
  end

  subgraph Data
    PG[(PostgreSQL)]
    RD[(Redis)]
    FS["Object storage\nlocal / S3-ready"]
  end

  subgraph External
    OAI["OpenAI optional\nchat / Whisper"]
    STR["Stripe optional\nCheckout"]
  end

  SPA -->|dev :5173| API
  SPA -->|prod :80| NGX --> API
  API --> PG
  API --> RD
  API --> FS
  API --> OAI
  API --> STR
  API -->|enqueue| RD
  WRK --> RD
  WRK --> PG
  WRK --> FS
```

## Backend layering

```mermaid
flowchart TB
  R["API routes\napp/api"] --> S["Services\napp/services"]
  S --> REP["Repositories\napp/repositories"]
  REP --> M["ORM models\napp/models"]
  S --> INF["Infra\nstorage · speech · Stripe · LLM"]
  R --> DEP["Auth / RBAC\napp/dependencies"]
```

## Core product flows

| Flow | Path |
|------|------|
| Auth | Register → verify → JWT + refresh rotation |
| Resume ATS | Upload → parse → score → optional LLM tips |
| Interview | Create → answer → Celery/heuristic evaluate |
| Voice | TTS/STT browser → audio upload → Whisper/transcript → evaluate |
| Coding | Submit → restricted runner → verdict |
| Coach | Analytics → study plan tasks → chat |
| Roadmaps | Company catalog → enrollment → auto milestones |
| Billing | Plans → local activate or Stripe Checkout → entitlements |
| Reports | Bundle analytics → PDF/MD/JSON → notification |

## Entitlements (billing)

```mermaid
flowchart LR
  Free["Free"] -->|3 interviews/mo| Core["Coding · ATS · Roadmaps"]
  Pro["Pro"] --> All["Unlimited + Voice + Coach"]
  Team["Team"] --> All
  Team --> Pri["Priority support flag"]
```

## Related docs

- Module history: [`architecture.md`](architecture.md) (Module 1 notes)
- ER sketch: [`database-er.md`](database-er.md)
- Production: [`production.md`](production.md)
- Publish checklist: [`PUBLISH.md`](PUBLISH.md)
