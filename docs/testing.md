# Testing

Run all tests:

```bash
python manage.py test
```

Current automated coverage includes:
- token login invalid, revoked, expired, and used-token modes
- election lifecycle gating for ballot access
- ballot constraints for single-choice, multi-choice max-selection, and abstain behavior
- results visibility gates (public and org-facing)
- organization isolation for tenant access
- org user management update permissions and password reset behavior
- org settings update authorization

Database model drift check:

```bash
python manage.py makemigrations --check --dry-run
```
