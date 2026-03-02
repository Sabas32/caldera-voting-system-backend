# Auth Strategy

Admin auth:

- Django session authentication with HttpOnly session cookie.
- CSRF enabled (`CsrfViewMiddleware`) and trusted origins configurable.
- Login endpoint: `POST /api/v1/auth/login/`.
- Logout endpoint: `POST /api/v1/auth/logout/`.
- Current user endpoint: `GET /api/v1/auth/me/`.
- Change password endpoint: `POST /api/v1/auth/change-password/` (requires `current_password`, `new_password`, and `confirm_password`).

Voter auth:

- Token login endpoint validates hashed token and issues signed HttpOnly cookie (`voter_session`).
- Cookie stores signed `token_id` + `election_slug`, no plaintext token storage.
- Cookie TTL configurable via `VOTER_SESSION_MAX_AGE_SECONDS`.

Security notes:

- Tokens are never persisted as plaintext.
- Session cookies can be marked secure in production with `COOKIE_SECURE=true`.
