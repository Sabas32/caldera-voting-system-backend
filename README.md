# Voting System Backend

Production-oriented Django + DRF backend for a multi-tenant, token-only voting platform.

## Stack

- Django + Django REST Framework
- drf-spectacular (OpenAPI/Swagger)
- PostgreSQL (recommended), SQLite (dev default)
- Celery + Redis (recommended for scheduled transitions)
- openpyxl (Excel exports)

## Project Structure

- `voting_system/config`: settings and URL wiring
- `voting_system/apps/*`: domain apps (`organizations`, `accounts`, `elections`, `tokens`, `ballots`, `audit`, `analytics`)
- `docs/`: architecture/auth/api/deployment/testing docs
- `scripts/seed_demo_data.py`: local seed script

## Setup

1. Create and activate environment.

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Git Bash:

```bash
python -m venv .venv
source .venv/Scripts/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure env:

PowerShell:

```powershell
Copy-Item .env.example .env
```

Git Bash:

```bash
cp .env.example .env
```

By default (`DEV_DB=sqlite`) local development uses SQLite, so migrations run without Postgres.
If you want Postgres locally, set `DEV_DB=postgres` and configure `DB_*` values.

4. Apply migrations:

```bash
python manage.py migrate
```

5. Run server:

```bash
python manage.py runserver
```

## Running Locally (Docker)

```bash
docker-compose up --build
```

## Seed Demo Data

```bash
python scripts/seed_demo_data.py
```

Creates:

- system admin: `system@demo.local / Admin12345!`
- org admin: `orgadmin@demo.local / Admin12345!`
- demo tokens: `DEMO0001`, `DEMO0002`

## OpenAPI

- Schema: `http://localhost:8000/api/schema/`
- Swagger UI: `http://localhost:8000/api/docs/`

## End-to-End Demo Flow

1. Login as system admin and create organization.
2. Add org admin user.
3. Login as org admin.
4. Create election + posts + candidates.
5. Generate token batch and export CSV/print.
6. Voter uses `/vote/token-login/` and submits ballot.
7. Close election, publish results, export Excel.

## Notes

- Django Admin is for debugging/ops only.
- Token plaintext is not stored in the database.
- Export endpoints rely on short-lived secure cache for plaintext output.
