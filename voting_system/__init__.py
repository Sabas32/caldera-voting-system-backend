from __future__ import annotations

from typing import Any

__all__ = ("celery_app",)


def __getattr__(name: str) -> Any:
    # Avoid importing Celery app during Django settings bootstrap.
    if name == "celery_app":
        from voting_system.config.celery import app

        return app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
