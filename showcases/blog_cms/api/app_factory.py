from __future__ import annotations
"""API factory is re-export of main factory — single source of truth"""
from ..app_factory import create_app, create_test_app, FROZEN_ROUTES

__all__ = ["create_app", "create_test_app", "FROZEN_ROUTES"]
