# API Overview

Base prefix: `/api/v1/`

Auth:
- `POST /auth/login/`
- `POST /auth/logout/`
- `GET /auth/me/`

System:
- `GET /system/dashboard/`
- `GET/POST /system/organizations/`
- `GET/PATCH /system/organizations/{orgId}/`
- `POST /system/organizations/{orgId}/admins/`
- `GET /system/audit/` with optional `org_id`, `action`, `date_from`, `date_to`

Organization:
- `GET /org/dashboard/` (requires `X-Org-Id`)
- `GET/PATCH /org/settings/` (requires `X-Org-Id`)
- `GET/POST /org/elections/` (requires `X-Org-Id`)
- `GET/PATCH /org/elections/{id}/`
- `POST /org/elections/{id}/status/`
- `POST /org/elections/{id}/duplicate/`
- `GET/POST /org/elections/{id}/posts/`
- `PATCH/DEL /org/posts/{postId}/`
- `GET/POST /org/posts/{postId}/candidates/`
- `PATCH/DEL /org/candidates/{candidateId}/`
- `GET/POST /org/users/` (requires `X-Org-Id`)
- `PATCH /org/users/{membershipId}/`
- `GET /org/audit/` with optional `action`, `date_from`, `date_to`

Tokens:
- `POST /org/elections/{id}/token-batches/`
- `GET /org/elections/{id}/token-batches/`
- `POST /org/token-batches/{batchId}/revoke/`
- `GET /org/token-batches/{batchId}/export/csv/`
- `GET /org/token-batches/{batchId}/export/print/`
- `GET /org/token-batches/{batchId}/export/qr/`

Voting:
- `POST /vote/token-login/`
- `GET /vote/elections/{slug}/ballot/`
- `POST /vote/elections/{slug}/submit/`
- `GET /vote/elections/{slug}/status/`
- `GET /vote/elections/{slug}/results/`

Results:
- `GET /org/elections/{id}/results/`
- `POST /org/elections/{id}/publish-results/`
- `GET /org/elections/{id}/export/excel/`

OpenAPI:
- `GET /api/schema/`
- `GET /api/docs/`
