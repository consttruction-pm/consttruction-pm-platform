"""Local full-stack CUBI preview.

The preview composes the real Web client, the real WSGI application boundary,
SQLite persistence and the Shared Domain/Calculation Core. It is a development
fixture surface only: it is not a production deployment and it never exposes
demo credentials as production secrets.
"""

from .runtime import PreviewRuntime, PreviewRuntimeError, open_preview_runtime

__all__ = [
    "PreviewRuntime",
    "PreviewRuntimeError",
    "open_preview_runtime",
]
