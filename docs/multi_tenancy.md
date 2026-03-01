# Multi-Tenancy

Isolation model:

- Every business entity is linked to `Organization`.
- `OrgMembership` binds users to organizations with role-based access.
- System admins (`is_system_admin=true`) can cross tenant boundaries.

Enforcement:

- Org endpoints require org context (`X-Org-Id` header or `org_id` query param).
- Views validate active membership before any tenant data access.
- All list/detail queries are filtered by organization.

Guarantee:

- Non-system users cannot read/write data outside their memberships.
- Test coverage includes positive and negative org isolation cases.
