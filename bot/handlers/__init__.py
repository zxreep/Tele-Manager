"""Centralized handler router registry and loading helpers."""

from __future__ import annotations

import importlib
import logging
from collections.abc import Iterable
from typing import Any


logger = logging.getLogger(__name__)

# Key: feature/module name
# Value: dotted import path to a module-level aiogram Router instance.
ROUTER_REGISTRY: dict[str, str] = {
    "admin_panel": "bot.handlers.admin_panel:router",
    "start": "bot.handlers.start:router",
    "help": "bot.handlers.help:router",
    "premium": "bot.handlers.premium:router",
    "analytics": "bot.handlers.analytics:router",
}


def iter_router_import_paths(enabled_features: Iterable[str] | None = None) -> list[str]:
    """Return router import paths, optionally filtered by enabled features."""
    if enabled_features is None:
        return list(ROUTER_REGISTRY.values())

    enabled = set(enabled_features)
    return [path for name, path in ROUTER_REGISTRY.items() if name in enabled]


def load_registered_routers(enabled_features: Iterable[str] | None = None) -> list[Any]:
    """Load routers declared in ROUTER_REGISTRY.

    Invalid entries are skipped with a warning to avoid startup crashes.
    """
    routers: list[Any] = []
    for import_path in iter_router_import_paths(enabled_features):
        module_path, _, attr_name = import_path.partition(":")
        if not module_path or not attr_name:
            logger.warning("Invalid router import path: %s", import_path)
            continue

        module = importlib.import_module(module_path)
        router = getattr(module, attr_name, None)
        if router is None:
            logger.warning("Router not found for import path: %s", import_path)
            continue

        routers.append(router)

    return routers
