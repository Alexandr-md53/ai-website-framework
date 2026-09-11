# CODING: utf-8, ASCII only
"""
ai_framework.api.fastapi - Delivery Adapter wiring (C6.1 + C6.2)
Phase 11 C6.1: basic factory
Phase 11 C6.2: extended wiring - middlewares, health, lifespan passthrough
No business logic, only wiring. Uses existing frozen A1.4 components without modification.
"""

from __future__ import annotations
from typing import Optional, List, Callable, Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .registry import EndpointRegistry
from .router import Router
from .adapter import APIAdapter


def _get_framework_version() -> str:
    try:
        from ..tools.scaffold import _framework_version

        return _framework_version()
    except Exception:
        return "unknown"


def create_app(
    registry: Optional[EndpointRegistry] = None,
    middlewares: Optional[List[Callable]] = None,
    include_health: bool = True,
    lifespan: Optional[Any] = None,
) -> FastAPI:
    if registry is None:
        registry = EndpointRegistry()

    router = Router(registry)

    if middlewares:
        for mw in middlewares:
            router.use_middleware(mw)

    adapter = APIAdapter(router)

    if lifespan is not None:
        app = FastAPI(lifespan=lifespan)
    else:
        app = FastAPI()

    if include_health:

        async def health_handler(request: Request):
            return JSONResponse(
                content={"status": "ok", "version": _get_framework_version()},
                status_code=200,
            )

        has_health = any(p == "/health" for _, p in registry.list())
        if not has_health:
            app.add_api_route("/health", health_handler, methods=["GET"])

    routes_snapshot = (
        list(registry.routes.items()) if hasattr(registry, "routes") else []
    )

    for (reg_method, reg_path), endpoint in routes_snapshot:
        method = reg_method
        template_path = reg_path

        async def make_handler(
            request: Request, _method=method, _template=template_path
        ):
            body = {}
            if _method.upper() in ("POST", "PUT", "PATCH"):
                try:
                    if request.headers.get("content-type", "").startswith(
                        "application/json"
                    ):
                        body = await request.json()
                    else:
                        try:
                            body = await request.json()
                        except Exception:
                            body = {}
                except Exception:
                    try:
                        raw = await request.body()
                        if raw:
                            import json as _json

                            try:
                                body = _json.loads(raw.decode("utf-8"))
                            except Exception:
                                body = raw.decode("utf-8", errors="ignore")
                        else:
                            body = {}
                    except Exception:
                        body = {}

            http_request = {
                "query": dict(request.query_params),
                "body": body,
                "headers": dict(request.headers),
                "path_params": dict(request.path_params),
            }
            actual_path = request.url.path
            result = adapter.handle_request(_method, actual_path, http_request)
            return JSONResponse(
                content=result.get("json", {}), status_code=result.get("status", 200)
            )

        app.add_api_route(template_path, make_handler, methods=[method])

    return app
