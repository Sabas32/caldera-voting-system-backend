# Backend Architecture

`voting_system` uses domain apps under `voting_system/apps`:

- `common`: abstract base models, token hash/session helpers, throttling, standard API responses.
- `organizations`: tenant root model and system-level organization management endpoints.
- `accounts`: custom user model + org memberships + role management.
- `elections`: election lifecycle, posts, candidates, results publishing, excel export.
- `tokens`: token batch generation, hash-only token storage, revocation and export endpoints.
- `ballots`: voter token login, ballot fetch/submit/status/public results.
- `audit`: centralized event log + request correlation IDs.
- `analytics`: aggregation helpers for summaries and turnout series.

Service-first approach:

- Critical business logic is in `services.py` (transitions, token generation, ballot submit).
- Views perform transport/authorization and call services.
- Audit events are emitted in services/views on every important mutation.
