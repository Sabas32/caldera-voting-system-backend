from __future__ import annotations

from collections.abc import MutableMapping


def _normalize_path(path: str) -> str:
    if path.startswith("/api/v1/"):
        return path[len("/api/v1/") :]
    if path.startswith("/api/"):
        return path[len("/api/") :]
    return path.lstrip("/")


def _resolve_tag(path: str) -> str:
    normalized = _normalize_path(path)

    if normalized.startswith("auth/"):
        return "Authentication"

    if normalized.startswith("system/"):
        if normalized.startswith("system/organizations/"):
            return "System Organizations"
        if normalized.startswith("system/audit/"):
            return "System Audit"
        if normalized.startswith("system/dashboard/") or normalized.startswith("system/health/"):
            return "System Analytics"
        return "System Administration"

    if normalized.startswith("org/"):
        if normalized.startswith("org/users/"):
            return "Organization Users"
        if normalized.startswith("org/settings/"):
            return "Organization Settings"
        if normalized.startswith("org/dashboard/"):
            return "Organization Dashboard"
        if normalized.startswith("org/audit/"):
            return "Organization Audit"
        if normalized.startswith("org/elections/") and "/token-batches/" in normalized:
            return "Token Management"
        if normalized.startswith("org/elections/") and "/results/" in normalized:
            return "Election Results"
        if normalized.startswith("org/elections/"):
            return "Election Management"
        if normalized.startswith("org/posts/") or normalized.startswith("org/candidates/"):
            return "Election Management"
        if normalized.startswith("org/token-batches/") or normalized.startswith("org/tokens/"):
            return "Token Management"
        return "Organization Administration"

    if normalized.startswith("vote/"):
        return "Public Voting"

    if normalized.startswith("schema/") or normalized.startswith("docs/"):
        return "Documentation"

    return "Miscellaneous"


def group_operations_by_domain(result: MutableMapping, generator, request, public):
    paths = result.get("paths", {})
    for path, path_item in paths.items():
        if not isinstance(path_item, MutableMapping):
            continue

        tag = _resolve_tag(path)
        for method, operation in path_item.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete", "head", "options", "trace"}:
                continue
            if not isinstance(operation, MutableMapping):
                continue
            operation["tags"] = [tag]

    return result

