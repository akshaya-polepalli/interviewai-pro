# Analytics & Progress (Module 8)

## Flow
1. Source events (interview evaluation, coding submission, resume ATS) call `touch_analytics`.
2. `AnalyticsService.recompute` rebuilds counters, streaks, skill radar, weekly series, and roadmap.
3. Achievements unlock when criteria are met (`first_interview`, `first_accepted`, `ats_80`, …).
4. Dashboard loads `GET /analytics/me?refresh=true`.

## Endpoints
- `GET /analytics/me?refresh=`
- `POST /analytics/me/refresh`
- `GET /analytics/achievements`

## Rollup fields
- Interview totals / average score
- Coding submissions / accepted
- Streak days
- Skill radar: technical, behavioral, communication, coding, resume
- Weekly activity series (8 weeks)
- Prep roadmap checklist
- Strong / weak topics from answer scores

## UI
`/dashboard` — stats, radar bars, roadmap, weekly chart, achievements

## Permissions
Uses `users:read` (own progress only).
