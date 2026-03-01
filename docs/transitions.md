# Lifecycle Transitions

Election statuses:

- `DRAFT -> SCHEDULED -> LIVE -> CLOSED -> ARCHIVED`

Automated transitions:

- Celery beat task `run_scheduled_transitions_task` runs every minute.
- Moves `SCHEDULED` to `LIVE` when `opens_at <= now`.
- Moves `LIVE` to `CLOSED` when `closes_at <= now`.

Fallback command:

- `python manage.py run_election_transitions`

Manual status changes:

- `POST /api/v1/org/elections/{id}/status/` with `{ "action": "schedule|close|archive" }`.
