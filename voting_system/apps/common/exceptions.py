from __future__ import annotations

from typing import Any

from rest_framework.views import exception_handler as drf_exception_handler


def _normalize_error(value: Any):
    if isinstance(value, dict):
        return {str(key): _normalize_error(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_error(item) for item in value]
    return str(value)


def _derive_message_from_details(details: Any) -> str | None:
    if isinstance(details, dict):
        non_field = details.get("non_field_errors")
        if isinstance(non_field, list) and non_field:
            return "; ".join(str(item) for item in non_field)
        if isinstance(non_field, str) and non_field:
            return non_field

        for field, value in details.items():
            if isinstance(value, list) and value:
                return f"{field}: {value[0]}"
            if isinstance(value, str) and value:
                return f"{field}: {value}"
            nested = _derive_message_from_details(value)
            if nested:
                return f"{field}: {nested}"

    if isinstance(details, list) and details:
        return str(details[0])
    if isinstance(details, str) and details:
        return details
    return None


def _is_authentication_failure(details: Any) -> bool:
    normalized = str(details).lower()
    return "not authenticated" in normalized or "authentication credentials were not provided" in normalized


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    normalized = _normalize_error(response.data)
    if response.status_code == 403 and _is_authentication_failure(normalized):
        response.status_code = 401

    message = "Request failed"

    if isinstance(normalized, dict):
        if isinstance(normalized.get("message"), str) and normalized["message"]:
            message = normalized["message"]
        elif isinstance(normalized.get("detail"), str) and normalized["detail"]:
            message = normalized["detail"]
        else:
            message = _derive_message_from_details(normalized) or message
    elif isinstance(normalized, list) and normalized:
        message = str(normalized[0])
    elif isinstance(normalized, str) and normalized:
        message = normalized

    response.data = {
        "success": False,
        "message": message,
        "details": normalized,
        "status_code": response.status_code,
    }
    return response
