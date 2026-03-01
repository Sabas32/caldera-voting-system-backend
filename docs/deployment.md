# Deployment

Environment variables:

- Core: `DJANGO_SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `TIME_ZONE`
- DB: `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- Security: `COOKIE_SECURE`, `TOKEN_HASH_PEPPER`
- Frontend integration: `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`
- Rate limits: `DRF_USER_RATE`, `TOKEN_LOGIN_RATE`, `TOKEN_SUBMIT_RATE`
- Jobs/cache: `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `CACHE_BACKEND`, `CACHE_LOCATION`

Docker:

- `docker-compose up --build` starts PostgreSQL, Redis, and backend.
- Update `.env` before starting services.

Production recommendations:

- Use PostgreSQL and Redis managed services.
- Set secure cookies and strict allowed hosts.
- Run behind reverse proxy with TLS.
