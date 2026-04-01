"""Centralized handler router registry.

This module provides a single place to register and discover handler routers,
so new features can be plugged in without scattering imports across the app.
"""

from collections.abc import Iterable

# NOTE: Keep this map as the single source of truth for feature routers.
# Key: feature name / module name
# Value: dotted import path to the router object
ROUTER_REGISTRY: dict[str, str] = {
    "start": "bot.handlers.start:router",
    "admin": "bot.handlers.admin:router",
}


def iter_router_import_paths(enabled_features: Iterable[str] | None = None) -> list[str]:
    """Return router import paths, optionally filtered by enabled features."""
    if enabled_features is None:
        return list(ROUTER_REGISTRY.values())

    enabled = set(enabled_features)
    return [path for name, path in ROUTER_REGISTRY.items() if name in enabled]
"""Message and callback handlers."""
