from __future__ import annotations

from django.core.checks import Critical, Tags, register


@register(Tags.compatibility)
def check_qr_export_dependencies(app_configs, **kwargs):
    errors = []

    try:
        import qrcode  # noqa: F401
    except Exception as exc:  # pragma: no cover - import guard
        errors.append(
            Critical(
                f"QR exports dependency check failed: qrcode import error ({exc}).",
                hint="Install backend dependencies with `pip install -r requirements.txt` and restart the backend.",
                id="tokens.E001",
            )
        )

    try:
        from PIL import Image  # noqa: F401
    except Exception as exc:  # pragma: no cover - import guard
        errors.append(
            Critical(
                f"QR exports dependency check failed: Pillow import error ({exc}).",
                hint="Install backend dependencies with `pip install -r requirements.txt` and restart the backend.",
                id="tokens.E002",
            )
        )

    return errors
