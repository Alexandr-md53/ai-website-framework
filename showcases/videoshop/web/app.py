"""VideoShop web app: public catalog + protected admin panel (product slice V1).

Scope of this slice:

* **admin panel** (``/admin``) - the shop owner creates and edits categories,
  products, prices, attributes, uploads images and edits the shop's own settings
  (name, description, contacts, languages). No code, JSON or hand-written SQL is
  involved: everything is data entered in the browser;
* **public site** (``/``, ``/catalog``, ``/product/{slug}``) - published
  categories and products; historical slugs redirect (301) to the current one
  through the S4 resolver; unpublished products are not visible;
* **every mutating request requires an authenticated session AND a CSRF token**.
  There is no unprotected POST/PUT/DELETE and no default password: when the
  environment has no credential/secret the whole admin area refuses to work
  (fail closed).

Uploads use a raw request body (``Content-Type: image/png`` etc. plus the
``X-File-Name`` header) because ``python-multipart`` is not installed in this
environment; the content type is detected from the file's magic bytes, so the
browser-supplied header is never trusted. No new dependency is added.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import parse_qs
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from ai_framework.rendering.jinja import JinjaTemplateRenderer
from ai_framework.rendering.seo import SeoContext, SeoInjector

from ..domain.catalog import (
    REQUEST_STATES,
    RequestValidationError,
    CatalogError,
    CategoryInUseError,
    DEFAULT_LANGUAGE,
    CONTENT_LANGUAGES,
    NotFoundError,
    fill_attribute_translations,
    ValidationError,
    resolve_publish_moment,
)
from ..domain.consultant import recommend
from ..domain.scenarios import (
    CATEGORY_ALIASES,
    CATEGORY_KEYS,
    SCENARIOS,
    SCENARIOS_BY_ID,
)
from ..infrastructure.image_store import (
    DEFAULT_MAX_UPLOAD_BYTES,
    ImageError,
    ImageStore,
)
from ..infrastructure.slug_registry import SlugRegistry
from ..infrastructure.sqlite_provider import VideoShopSQLiteProvider
from ..infrastructure.storage import (
    MODE_FILE,
    MODE_MEMORY,
    MEMORY_PATH,
    StoragePaths,
    resolve_storage,
)
from ..security.admin import COOKIE_NAME, AdminConfig
from ..services.cart import (
    CART_COOKIE,
    CART_TTL_SECONDS,
    CartBadSignature,
    CartError,
    CartItemNotFound,
    CartLimitError,
    CartService,
)
from ..services.orders import (
    ALLOWED_TRANSITIONS,
    ORDER_STATUSES,
    InvalidStatusTransition,
    OrderError,
    OrderPriceChangedError,
    OrderService,
    OrderUnavailableError,
    OrderValidationError,
)
from ..services.catalog import CatalogService, slugify
from ..services.publications import PublicationsService
from ..publishers.telegram_formatter import TEXT_LIMIT, escape_html
from .i18n import admin_language_choices, get_admin_ui, get_ui
from .config import StoreConfig, StoreConfigError, default_store_config
from ..infrastructure.storage import StoragePathMissing

#: packaged photos shipped with the showcase; used as a fallback for a category
#: without an uploaded photo (the demo seeds the same files into ``image``)
PACKAGED_CATEGORY_PHOTOS = (
    (("camera", "камер", "camere"), "category-camera.jpg"),
    (("lens", "objektiv", "объектив", "obiectiv", "optik"), "category-lens.jpg"),
    (("light", "свет", "svet", "lumin", "panou"), "category-light.jpg"),
    (("mic", "звук", "zvuk", "sound", "sunet", "microfon"), "category-mic.png"),
    (("tripod", "штатив", "shtativ", "treppiede"), "category-tripod.jpg"),
    (("gimbal", "стабилиз", "stabiliz"), "category-gimbal.jpg"),
)


def request_localized_error(context: Dict[str, Any]) -> str:
    """Localized storage-failure message for the public request form."""
    ui = context.get("ui") or {}
    return (ui.get("request_error") or "") if isinstance(ui, dict) else ""


def category_photo(category: Any) -> str:
    """Resolve the photo for a category: uploaded → packaged guess → placeholder."""
    uploaded = (getattr(category, "image", "") or "").strip()
    if uploaded:
        return uploaded
    haystack = " ".join(
        [getattr(category, "slug", "") or ""]
        + [getattr(text, "name", "") or "" for text in (getattr(category, "texts", {}) or {}).values()]
    ).lower()
    for keywords, file_name in PACKAGED_CATEGORY_PHOTOS:
        if any(keyword in haystack for keyword in keywords):
            return file_name
    return PLACEHOLDER_IMAGE

#: packaged storefront assets shipped with the showcase (hero, category photos,
#: placeholder); managed uploads live in the shop's own images directory
PACKAGED_MEDIA_DIR = Path(__file__).resolve().parent / "static" / "media"
PACKAGED_MEDIA_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.(?:jpg|jpeg|png|webp|gif)$")
PLACEHOLDER_IMAGE = "placeholder.jpg"

#: technical details of form errors go here, never to the page
REQUEST_LOGGER = logging.getLogger("videoshop.request")
MAX_HOME_PRODUCTS = 6
EMAIL_PATTERN = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[A-Za-z]{2,}$")

WEB_DIR = Path(__file__).resolve().parent
DEFAULT_TEMPLATES_DIR = WEB_DIR / "templates"
DEFAULT_IMAGES_DIRNAME = "images"
#: total row budget of product_attributes (guards >48 rows overall)
ATTRIBUTE_SLOTS = 48
#: the admin characteristics table is fixed: 12 groups x (en, ru, ro) = 36 slots
ATTRIBUTE_ROWS_PER_LANGUAGE = 12
#: column order of the table; the first column is the master language
ATTRIBUTE_TABLE_LANGUAGES = CONTENT_LANGUAGES
LANGUAGE_SLOTS = 6


def default_storage_paths(root: Path, *, name: str = "videoshop") -> Tuple[Path, Path, Path]:
    """Return ``(db_path, backup_dir, images_dir)`` under ``root``.

    The caller supplies the root (in the future from ``VIDEOSHOP_DB_PATH``); this
    helper only builds the conventional layout, it never invents a hidden path.
    """
    base = Path(root)
    return (
        base / f"{name}.sqlite",
        base / "backups",
        base / DEFAULT_IMAGES_DIRNAME,
    )


def _resolve_storage(db_path: Optional[str], backup_dir: Optional[str]) -> StoragePaths:
    """Apply the S7 storage contract (explicit file path; no silent :memory:)."""
    if db_path is None or str(db_path) == MEMORY_PATH:
        # an explicitly declared memory database is allowed for tests/dev
        return resolve_storage(mode=MODE_MEMORY)
    if not str(db_path).strip():
        raise ValidationError("a database path is required in storage mode")
    if backup_dir:
        return resolve_storage(db_path=db_path, backup_dir=backup_dir)
    candidate = Path(str(db_path)).expanduser()
    if not candidate.is_absolute():
        raise ValidationError(f"the database path must be absolute: {str(candidate)!r}")
    if candidate.exists() and candidate.is_dir():
        raise ValidationError(f"the database path is a directory: {str(candidate)!r}")
    if not candidate.parent.exists():
        raise ValidationError(
            f"the database directory does not exist: {str(candidate.parent)!r}"
        )
    return StoragePaths(mode=MODE_FILE, db_path=candidate.resolve(), backup_dir=None)


def create_app(
    *,
    db_path: Optional[str] = None,
    backup_dir: Optional[str] = None,
    images_dir: Optional[str] = None,
    templates_dir: Optional[str] = None,
    admin_config: Optional[AdminConfig] = None,
    env: Optional[Mapping[str, str]] = None,
    seed_demo: bool = False,
    max_upload_bytes: int = DEFAULT_MAX_UPLOAD_BYTES,
    store_config: Optional[StoreConfig] = None,
) -> FastAPI:
    """Build the VideoShop application (public catalog + admin panel)."""
    source = os.environ if env is None else env
    config = store_config or default_store_config()
    features = config.to_flags()  # also validates unknown modes / conflicts
    # a store without an explicit database path must fail loudly: an in-memory
    # store cannot run the multi-statement migrations and used to surface a
    # confusing MigrationError from deep inside the migration runner
    if db_path is None or str(db_path).strip() in ("", ":memory:"):
        raise StoragePathMissing(
            "create_app requires an explicit file db_path; in-memory storage must be "
            "requested through resolve_storage(mode=MEMORY) in tests"
        )
    storage = _resolve_storage(db_path, backup_dir)

    if images_dir is None:
        if storage.db_path is not None:
            images_dir = str(storage.db_path.parent / DEFAULT_IMAGES_DIRNAME)
        else:
            images_dir = str(Path.cwd() / DEFAULT_IMAGES_DIRNAME)

    provider = VideoShopSQLiteProvider(
        db_path=str(storage.db_path) if storage.db_path is not None else MEMORY_PATH
    )
    registry = SlugRegistry(provider)
    images = ImageStore(images_dir, max_bytes=max_upload_bytes)
    catalog = CatalogService(provider, registry, images)
    catalog.migrate()
    if features["request_form"]:
        # the request form lives on the contacts page (block 3a, decision 2)
        catalog.ensure_contacts_page()
    if seed_demo:
        catalog.seed_demo_catalog()
    cart_secret = (source.get("VIDEOSHOP_SECRET_KEY") or "").encode("utf-8")
    if not cart_secret:
        cart_secret = secrets.token_bytes(32)
    cart_service = CartService(provider, catalog, secret=cart_secret)
    order_service = OrderService(provider, catalog, cart_service)

    admin = admin_config if admin_config is not None else AdminConfig.from_env(source)
    renderer = JinjaTemplateRenderer(templates_dir or DEFAULT_TEMPLATES_DIR)

    app = FastAPI(title="VideoShop", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.catalog = catalog
    app.state.images = images
    app.state.admin = admin
    app.state.storage = storage

    # --- auth / csrf helpers -------------------------------------------

    def admin_or_refuse(request: Request, *, page: bool) -> Tuple[AdminConfig, str, str]:
        configured = getattr(app.state, "admin", None)
        if configured is None:
            raise HTTPException(
                status_code=503,
                detail=(
                    "the admin area is not configured: set VIDEOSHOP_SECRET_KEY and "
                    "VIDEOSHOP_ADMIN_PASSWORD_HASH (or VIDEOSHOP_ADMIN_PASSWORD)"
                ),
            )
        token = request.cookies.get(COOKIE_NAME)
        user = configured.read_session(token)
        if user is None:
            if page:
                raise HTTPException(status_code=303, headers={"Location": "/admin/login"})
            raise HTTPException(status_code=401, detail="authentication required")
        return configured, user, token or ""

    async def admin_form(request: Request) -> Tuple[AdminConfig, str, Dict[str, Any]]:
        configured, user, token = admin_or_refuse(request, page=False)
        form = await read_urlencoded(request)
        if not configured.check_csrf(token, form.get("csrf")):
            raise HTTPException(status_code=403, detail="invalid or missing CSRF token")
        return configured, user, form

    def _cart_position_count(request: Request) -> int:
        if not features["cart"]:
            return 0
        try:
            cart = cart_service.peek(request.cookies.get(CART_COOKIE))
        except CartError:
            return 0
        return 0 if cart is None else cart_service.count(cart)

    def page_context(request: Request) -> Dict[str, Any]:
        settings = catalog.get_settings()
        lang = _requested_language(request, settings)
        configured = getattr(app.state, "admin", None)
        token = request.cookies.get(COOKIE_NAME)
        return {
            "settings": settings,
            "languages": settings.languages,
            "lang": lang,
            "ui": get_ui(lang),
            # the switcher keeps the page query and changes only ``lang``
            "lang_url": lambda code: _language_switch_url(request, code),
            # published informational pages feed the footer navigation
            "pages": catalog.list_pages(published_only=True),
            # the admin link is rendered for a signed-in administrator only
            "is_admin": configured is not None and configured.read_session(token) is not None,
            # storefront chrome: cart badge (demo, no cart backend) and the
            # newsletter confirmation shown after POST /subscribe
            "show_cart": True,
            "cart_count": _cart_position_count(request),
            "placeholder_image": PLACEHOLDER_IMAGE,
            # photo resolution for category cards: uploaded → packaged → placeholder
            "category_photo": category_photo,
            "subscribed": request.query_params.get("subscribed") == "1",
            "subscribe_error": request.query_params.get("subscribe_error") == "1",
            # store mode / capabilities (block 3a)
            "features": features,
            "store_mode": config.mode,
            "sent": request.query_params.get("sent") == "1",
            "request_error": "",
            "request_error_code": "",
            "request_token": _request_token(),
        }

    def admin_context(request: Request, *, error: str = "", values: Mapping[str, Any] = None) -> Dict[str, Any]:
        configured = getattr(app.state, "admin", None)
        token = request.cookies.get(COOKIE_NAME)
        context = page_context(request)
        # the admin UI language works independently of the shop's content
        # languages, so RU/RO/EN can always be switched inside the panel
        admin_lang, admin_ui = get_admin_ui(
            request.query_params.get("lang", ""), context["settings"].default_language
        )
        context.update(
            {
                "lang": admin_lang,
                "ui": admin_ui,
                # the admin panel always offers RU/RO/EN, whatever content
                # languages the shop itself is configured with
                "admin_languages": admin_language_choices(),
                "show_cart": False,
                "subscribed": False,
                "subscribe_error": False,
                "csrf": configured.csrf_token(token) if configured is not None else "",
                "error": error,
                "values": dict(values or {}),
                "slugify": slugify,
                "attribute_slots": list(range(ATTRIBUTE_SLOTS)),
                "attribute_groups": list(range(ATTRIBUTE_ROWS_PER_LANGUAGE)),
                "attribute_columns": _attribute_columns(context["settings"]),
                "language_slots": list(range(LANGUAGE_SLOTS)),
            }
        )
        return context

    seo_injector = SeoInjector()

    def context_for_redirect(request: Request) -> Dict[str, Any]:
        return page_context(request)

    def render(
        template: str,
        context: Dict[str, Any],
        status_code: int = 200,
        seo: Optional[Mapping[str, str]] = None,
    ) -> HTMLResponse:
        """Render a template and inject SEO tags through the framework injector.

        Site-wide SEO comes from the editable shop settings; a page may override
        the title/description by passing ``seo``. Empty values inject nothing.
        """
        html = renderer.render(template, context)
        settings = context.get("settings")
        payload: Dict[str, str] = dict(seo or {})
        if settings is not None:
            fallback_title = settings.seo_title or settings.name or "VideoShop"
            payload.setdefault("seo_title", fallback_title)
            payload.setdefault(
                "seo_description", settings.seo_description or settings.description or ""
            )
            payload.setdefault("title", fallback_title)
        seo_context = SeoContext.normalize(
            payload, title_fallback=(settings.name if settings is not None else "VideoShop")
        )
        return HTMLResponse(seo_injector.ensure_seo(html, seo_context), status_code=status_code)

    # --- public ---------------------------------------------------------

    @app.get("/", response_class=HTMLResponse)
    async def public_home(request: Request) -> HTMLResponse:
        context = page_context(request)
        context.update(
            {
                "categories": catalog.list_categories(published_only=True),
                # the home page shows no product showcase, and visitka must not
                # read products at all (block 3a)
                "products": (
                    catalog.list_products(published_only=True)
                    if features["public_catalog"]
                    else []
                ),
            }
        )
        return render("public_home.html", context)

    @app.get("/catalog", response_class=HTMLResponse)
    async def public_catalog(request: Request, category: Optional[str] = None) -> HTMLResponse:
        if not features["public_catalog"]:
            raise HTTPException(status_code=404, detail="not found")
        context = page_context(request)
        categories = catalog.list_categories(published_only=True)
        selected = _find_category(categories, category)
        context.update(
            {
                "categories": categories,
                "selected_category": selected,
                "products": catalog.list_products(
                    published_only=True,
                    category_id=None if selected is None else selected.id,
                ),
            }
        )
        return render("public_catalog.html", context)

    @app.get("/product/{slug}", response_class=HTMLResponse)
    async def public_product(request: Request, slug: str):
        if not features["product_page"]:
            raise HTTPException(status_code=404, detail="not found")
        context = page_context(request)
        product, redirect_slug = catalog.resolve_product(slug)
        if product is None:
            context["slug"] = slug
            return render("public_not_found.html", context, status_code=404)
        if redirect_slug:
            return RedirectResponse(url=f"/product/{redirect_slug}", status_code=301)
        category = None
        if product.category_id is not None:
            try:
                category = catalog.get_category(product.category_id)
            except CatalogError:
                category = None
        related: List[Any] = []
        if product.category_id is not None:
            related = [
                item
                for item in catalog.list_products(
                    published_only=True, category_id=product.category_id
                )
                if item.id != product.id
            ][:4]
        context.update({"product": product, "category": category, "related": related})
        return render("public_product.html", context)

    # --- packaged portfolio photos (optimised WebP) ---------------------

    @app.get("/media/portfolio/{file_name}")
    async def public_portfolio_media(file_name: str) -> FileResponse:
        if not PACKAGED_MEDIA_PATTERN.match(file_name or ""):
            raise HTTPException(status_code=404, detail="image not found")
        directory = PACKAGED_MEDIA_DIR / "portfolio"
        try:
            resolved = (directory / file_name).resolve()
            resolved.relative_to(directory.resolve())
        except (OSError, ValueError):
            raise HTTPException(status_code=404, detail="image not found")
        if not resolved.is_file():
            raise HTTPException(status_code=404, detail="image not found")
        return FileResponse(str(resolved))

    @app.get("/media/{file_name}")
    async def public_media(file_name: str) -> FileResponse:
        # 1) images uploaded through the admin panel (managed directory)
        try:
            path = images.path_for(file_name)
        except ImageError:
            path = None
        if path is not None:
            if path.is_file():
                return FileResponse(str(path))
            # a preset derivative can be missing (for example when the source was
            # smaller than the preset): fall back to the stored base file
            base = Path(file_name).stem.split("_")[0] + Path(file_name).suffix
            try:
                fallback = images.path_for(base)
            except ImageError:
                fallback = None
            if fallback is not None and fallback.is_file():
                return FileResponse(str(fallback))
        # 2) packaged storefront assets (hero, category photos, placeholder)
        if PACKAGED_MEDIA_PATTERN.match(file_name or ""):
            packaged = PACKAGED_MEDIA_DIR / file_name
            try:
                resolved = packaged.resolve()
                resolved.relative_to(PACKAGED_MEDIA_DIR.resolve())
            except (OSError, ValueError):
                raise HTTPException(status_code=404, detail="image not found")
            if resolved.is_file():
                return FileResponse(str(resolved))
        raise HTTPException(status_code=404, detail="image not found")

    @app.post("/subscribe")
    async def subscribe(request: Request):
        """Newsletter form in the footer.

        The address is validated but **not stored**: the slice has no mailing
        infrastructure yet, so the page only confirms the intent.
        """
        if not features["subscription"]:
            raise HTTPException(status_code=404, detail="not found")
        form = await read_urlencoded(request)
        email = (form.get("email") or "").strip()
        valid = bool(EMAIL_PATTERN.match(email)) and len(email) <= 254
        lang = request.query_params.get("lang", "")
        prefix = f"/?lang={lang}&" if lang else "/?"
        if not valid:
            return RedirectResponse(url=f"{prefix}subscribe_error=1", status_code=303)
        return RedirectResponse(url=f"{prefix}subscribed=1", status_code=303)


    # --- public request form helpers (block 3a) --------------------------

    _REQUEST_SECRET = secrets.token_bytes(32)
    _REQUEST_TTL_SECONDS = 30 * 60
    _REQUEST_WINDOW_SECONDS = 60.0
    _REQUEST_MAX_PER_WINDOW = 5
    _request_hits: Dict[str, List[float]] = {}

    def _request_token() -> str:
        stamp = str(int(time.time()))
        mac = hmac.new(_REQUEST_SECRET, stamp.encode("ascii"), hashlib.sha256).digest()
        return base64.urlsafe_b64encode(stamp.encode("ascii") + mac).decode("ascii")

    def _request_token_is_valid(token: str) -> bool:
        try:
            raw = base64.urlsafe_b64decode((token or "").encode("ascii"))
            stamp, mac = raw[:10], raw[10:]
        except Exception:
            return False
        try:
            issued = int(stamp.decode("ascii"))
        except Exception:
            return False
        if abs(time.time() - issued) > _REQUEST_TTL_SECONDS:
            return False
        expected = hmac.new(_REQUEST_SECRET, stamp, hashlib.sha256).digest()
        return hmac.compare_digest(mac, expected)

    def _request_rate_ok(client: str) -> bool:
        now = time.monotonic()
        hits = [moment for moment in _request_hits.get(client, []) if now - moment < _REQUEST_WINDOW_SECONDS]
        if len(hits) >= _REQUEST_MAX_PER_WINDOW:
            _request_hits[client] = hits
            return False
        hits.append(now)
        _request_hits[client] = hits
        return True


    @app.post("/request")
    async def public_request(request: Request):
        """Store a public request (visitka). PRG: success -> /?sent=1."""
        if not features["request_form"]:
            raise HTTPException(status_code=404, detail="not found")
        form = await read_urlencoded(request)
        client = request.client.host if request.client is not None else "unknown"
        if not _request_rate_ok(client):
            raise HTTPException(status_code=429, detail="too many requests")
        if (form.get("company") or "").strip():
            raise HTTPException(status_code=400, detail="spam")
        if not _request_token_is_valid(form.get("csrf") or ""):
            raise HTTPException(status_code=403, detail="invalid or missing CSRF token")
        try:
            catalog.add_request(
                name=form.get("name") or "",
                contact=form.get("contact") or "",
                message=form.get("message") or "",
                source_lang=request.query_params.get("lang", ""),
            )
        except RequestValidationError as exc:
            # the code is rendered through i18n; the technical text is logged
            REQUEST_LOGGER.warning("request rejected (%s): %s", exc.code, exc)
            context = page_context(request)
            context["request_error_code"] = exc.code
            context["request_values"] = dict(form)
            return render("public_home.html", context, status_code=400)
        except ValidationError as exc:
            REQUEST_LOGGER.warning("request rejected: %s", exc)
            context = page_context(request)
            context["request_error"] = str(exc)
            context["request_values"] = dict(form)
            return render("public_home.html", context, status_code=400)
        except CatalogError as exc:
            context = page_context(request)
            context["request_error"] = str(exc)
            context["request_values"] = dict(form)
            return render("public_home.html", context, status_code=500)
        except Exception:
            # storage failure must never look like success
            context = page_context(request)
            context["request_error"] = request_localized_error(context)
            context["request_values"] = dict(form)
            return render("public_home.html", context, status_code=500)
        return RedirectResponse(url="/?sent=1", status_code=303)

    # --- public: cart (shop mode only) ----------------------------------

    def _cart_guard() -> None:
        if not features["cart"]:
            raise HTTPException(status_code=404, detail="not found")

    def _cart_redirect(request: Request, cart, *, fresh: bool = False) -> RedirectResponse:
        lang = page_context(request)["lang"]
        target = f"/cart?lang={lang}" if lang else "/cart"
        response = RedirectResponse(url=target, status_code=303)
        if fresh:
            response.set_cookie(
                CART_COOKIE,
                cart_service.issue_token(cart.id),
                max_age=CART_TTL_SECONDS,
                httponly=True,
                samesite="lax",
            )
        return response

    async def _cart_csrf(request: Request) -> Dict[str, Any]:
        form = await read_urlencoded(request)
        if not _request_token_is_valid(form.get("csrf") or ""):
            raise HTTPException(status_code=403, detail="invalid or missing CSRF token")
        return form

    def _cart_response(context: Dict[str, Any], cart, *, status_code: int = 200, expired: bool = False, fresh: bool = False):
        view = cart_service.read(cart, context["lang"])
        context.update(
            {
                "cart_view": view,
                "cart_lines": view.lines,
                "cart_total": view.total,
                "cart_positions": view.count,
                "cart_expired": expired,
            }
        )
        response = render("cart.html", context, status_code=status_code)
        if fresh:
            response.set_cookie(
                CART_COOKIE,
                cart_service.issue_token(cart.id),
                max_age=CART_TTL_SECONDS,
                httponly=True,
                samesite="lax",
            )
        return response

    @app.get("/consultant", response_class=HTMLResponse)
    async def public_consultant(request: Request) -> HTMLResponse:
        if not features["public_catalog"]:
            raise HTTPException(status_code=404, detail="not found")
        context = page_context(request)
        scenario_id = (request.query_params.get("scenario") or "").strip()
        budget_raw = (request.query_params.get("budget") or "").strip()
        already_have = tuple(
            key
            for key in request.query_params.getlist("have")
            if key in CATEGORY_KEYS
        )
        recommendation = None
        if scenario_id in SCENARIOS_BY_ID:
            budget_minor = _parse_budget_minor(budget_raw)
            recommendation = recommend(
                catalog.list_products(published_only=True),
                SCENARIOS_BY_ID[scenario_id],
                category_ids=_category_ids(catalog.list_categories()),
                budget_minor=budget_minor,
                already_have=already_have,
                lang=context["lang"],
            )
        context.update(
            {
                "scenarios": SCENARIOS,
                "scenario_id": scenario_id,
                "budget": budget_raw,
                "already_have": already_have,
                "consultant_categories": CATEGORY_KEYS,
                "recommendation": recommendation,
                "contact_email": context["settings"].contact_email,
            }
        )
        return render("public_consultant.html", context)

    @app.get("/cart", response_class=HTMLResponse)
    async def public_cart(request: Request) -> HTMLResponse:
        _cart_guard()
        context = page_context(request)
        try:
            cart, expired, fresh = cart_service.resolve(request.cookies.get(CART_COOKIE))
        except CartBadSignature:
            raise HTTPException(status_code=403, detail="invalid cart cookie")
        return _cart_response(context, cart, expired=expired, fresh=fresh)

    @app.post("/cart/add")
    async def cart_add(request: Request):
        _cart_guard()
        form = await _cart_csrf(request)
        try:
            cart, _expired, fresh = cart_service.resolve(request.cookies.get(CART_COOKIE))
        except CartBadSignature:
            raise HTTPException(status_code=403, detail="invalid cart cookie")
        try:
            cart_service.add(cart, int(form.get("product_id") or 0), int(form.get("qty") or 1))
        except CartLimitError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        return _cart_redirect(request, cart, fresh=fresh)

    @app.post("/cart/update")
    async def cart_update(request: Request):
        _cart_guard()
        form = await _cart_csrf(request)
        try:
            cart, _expired, fresh = cart_service.resolve(request.cookies.get(CART_COOKIE))
            cart_service.update(cart, int(form.get("item_id") or 0), int(form.get("qty") or 0))
        except CartBadSignature:
            raise HTTPException(status_code=403, detail="invalid cart cookie")
        except CartLimitError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except CartItemNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        return _cart_redirect(request, cart, fresh=fresh)

    @app.post("/cart/remove")
    async def cart_remove(request: Request):
        _cart_guard()
        form = await _cart_csrf(request)
        try:
            cart, _expired, fresh = cart_service.resolve(request.cookies.get(CART_COOKIE))
            cart_service.remove(cart, int(form.get("item_id") or 0))
        except CartBadSignature:
            raise HTTPException(status_code=403, detail="invalid cart cookie")
        except CartItemNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        return _cart_redirect(request, cart, fresh=fresh)

    @app.post("/cart/clear")
    async def cart_clear(request: Request):
        _cart_guard()
        await _cart_csrf(request)
        try:
            cart, _expired, fresh = cart_service.resolve(request.cookies.get(CART_COOKIE))
        except CartBadSignature:
            raise HTTPException(status_code=403, detail="invalid cart cookie")
        cart_service.clear(cart)
        return _cart_redirect(request, cart, fresh=fresh)

    # --- public: checkout (shop mode only) ------------------------------

    def _checkout_csrf_ok(form) -> bool:
        return _request_token_is_valid(form.get("csrf") or "")

    @app.get("/checkout", response_class=HTMLResponse)
    async def public_checkout(request: Request) -> HTMLResponse:
        _cart_guard()
        context = page_context(request)
        try:
            cart, _expired, _fresh = cart_service.resolve(request.cookies.get(CART_COOKIE))
        except CartBadSignature:
            raise HTTPException(status_code=403, detail="invalid cart cookie")
        view = cart_service.read(cart, context["lang"])
        context.update(
            {
                "cart_view": view,
                "cart_lines": view.lines,
                "cart_total": view.total,
                "cart_positions": view.count,
                "checkout_token": secrets.token_urlsafe(32),
                "expected_total_minor": view.total.minor,
                "error_code": "",
                "values": {},
            }
        )
        return render("checkout.html", context)

    @app.post("/checkout")
    async def public_checkout_submit(request: Request):
        _cart_guard()
        form = await read_urlencoded(request)
        if not _checkout_csrf_ok(form):
            raise HTTPException(status_code=403, detail="invalid or missing CSRF token")
        context = page_context(request)
        try:
            cart, _expired, _fresh = cart_service.resolve(request.cookies.get(CART_COOKIE))
        except CartBadSignature:
            raise HTTPException(status_code=403, detail="invalid cart cookie")
        try:
            result = order_service.create_order(
                cart.id,
                name=form.get("name") or "",
                contact=form.get("contact") or "",
                address=form.get("address") or "",
                comment=form.get("comment") or "",
                source_lang=context["lang"],
                checkout_token=form.get("checkout_token") or "",
                lang=context["lang"],
                expected_total_minor=(
                    int(form["expected_total"]) if (form.get("expected_total") or "").isdigit() else None
                ),
            )
        except OrderUnavailableError as exc:
            view = cart_service.read(cart, context["lang"])
            context.update({"cart_view": view, "cart_lines": view.lines, "cart_total": view.total,
                            "cart_positions": view.count, "error_code": "order_error_unavailable",
                            "unavailable_names": exc.names, "values": dict(form),
                            "checkout_token": form.get("checkout_token") or secrets.token_urlsafe(32),
                            "expected_total_minor": view.total.minor})
            return render("checkout.html", context, status_code=400)
        except OrderPriceChangedError:
            view = cart_service.read(cart, context["lang"])
            context.update({"cart_view": view, "cart_lines": view.lines, "cart_total": view.total,
                            "cart_positions": view.count, "error_code": "order_error_price_changed",
                            "values": dict(form),
                            "checkout_token": form.get("checkout_token") or secrets.token_urlsafe(32),
                            "expected_total_minor": view.total.minor})
            return render("checkout.html", context, status_code=409)
        except OrderValidationError as exc:
            view = cart_service.read(cart, context["lang"])
            context.update({"cart_view": view, "cart_lines": view.lines, "cart_total": view.total,
                            "cart_positions": view.count, "error_code": exc.code,
                            "values": dict(form),
                            "checkout_token": form.get("checkout_token") or secrets.token_urlsafe(32),
                            "expected_total_minor": view.total.minor})
            return render("checkout.html", context, status_code=400)
        except OrderError as exc:
            context.update({"error_code": "order_error_failed", "values": dict(form)})
            return render("checkout.html", context, status_code=500)
        location = f"/checkout/success?order={result.number}"
        if result.access_token:
            # the only place the raw token ever appears; repeats get no token
            location += f"&token={result.access_token}"
        return RedirectResponse(url=location, status_code=303)

    @app.get("/checkout/success", response_class=HTMLResponse)
    async def public_checkout_success(request: Request) -> HTMLResponse:
        _cart_guard()
        context = page_context(request)
        context["order_number"] = (request.query_params.get("order") or "").strip()
        context["order_token"] = (request.query_params.get("token") or "").strip()
        return render("checkout_success.html", context)

    @app.get("/order/{number}", response_class=HTMLResponse)
    async def public_order(request: Request, number: str) -> HTMLResponse:
        _cart_guard()
        context = page_context(request)
        order = order_service.find_order(number, request.query_params.get("token") or "")
        if order is None:
            # identical response for "no such order", "no token" and "bad token"
            context["slug"] = number
            return render("public_not_found.html", context, status_code=404)
        context["order"] = order
        return render("order.html", context)

    # --- admin: session -------------------------------------------------

    @app.get("/admin/login", response_class=HTMLResponse)
    async def admin_login_page(request: Request) -> HTMLResponse:
        configured = getattr(app.state, "admin", None)
        context = page_context(request)
        login_lang, login_ui = get_admin_ui(
            request.query_params.get("lang", ""), context["settings"].default_language
        )
        context.update({"lang": login_lang, "ui": login_ui, "csrf": "", "error": ""})
        if configured is None:
            context["error"] = (
                "Admin is not configured. Set VIDEOSHOP_SECRET_KEY and "
                "VIDEOSHOP_ADMIN_PASSWORD_HASH (or VIDEOSHOP_ADMIN_PASSWORD)."
            )
            return render("admin_login.html", context, status_code=503)
        return render("admin_login.html", context)

    @app.post("/admin/login")
    async def admin_login(request: Request):
        configured = getattr(app.state, "admin", None)
        if configured is None:
            raise HTTPException(status_code=503, detail="the admin area is not configured")
        form = await read_urlencoded(request)
        if not configured.check_credentials(form.get("username", ""), form.get("password", "")):
            return render(
                "admin_login.html",
                {
                    **page_context(request),
                    "is_admin": False,
                    "csrf": "",
                    "error": "Invalid credentials.",
                },
                status_code=401,
            )
        response = RedirectResponse(url="/admin", status_code=303)
        response.set_cookie(
            COOKIE_NAME,
            configured.issue_session(),
            httponly=True,
            samesite="lax",
            path="/",
            max_age=configured.session_ttl_seconds,
        )
        return response

    @app.post("/admin/logout")
    async def admin_logout(request: Request):
        await admin_form(request)
        response = RedirectResponse(url="/admin/login", status_code=303)
        response.delete_cookie(COOKIE_NAME, path="/")
        return response

    # --- admin: dashboard ----------------------------------------------

    @app.get("/admin", response_class=HTMLResponse)
    async def admin_dashboard(request: Request) -> HTMLResponse:
        admin_or_refuse(request, page=True)
        context = admin_context(request)
        context.update(
            {
                "categories": catalog.list_categories(),
                "products": catalog.list_products(),
                "new_orders_count": (
                    order_service.count_by_status("new") if features["cart"] else None
                ),
            }
        )
        return render("admin_dashboard.html", context)

    # --- admin: categories ---------------------------------------------

    @app.get("/admin/categories", response_class=HTMLResponse)
    async def admin_categories(request: Request) -> HTMLResponse:
        admin_or_refuse(request, page=True)
        context = admin_context(request)
        context["categories"] = catalog.list_categories(
            q=(request.query_params.get("q") or "").strip() or None
        )
        context["q"] = (request.query_params.get("q") or "").strip()
        return render("admin_categories.html", context)

    @app.get("/admin/categories/new", response_class=HTMLResponse)
    async def admin_category_new(request: Request) -> HTMLResponse:
        admin_or_refuse(request, page=True)
        return render("admin_category_form.html", {**admin_context(request), "category": None})

    @app.post("/admin/categories/new")
    async def admin_category_create(request: Request):
        _, _, form = await admin_form(request)
        try:
            category = catalog.create_category(
                slug=form.get("slug"),
                texts=_texts_from_form(form, catalog.get_settings().language_codes),
                is_published=bool(form.get("is_published")),
            )
        except (ValidationError, CatalogError) as exc:
            return render(
                "admin_category_form.html",
                {**admin_context(request, error=str(exc), values=form), "category": None},
                status_code=400,
            )
        return RedirectResponse(url=f"/admin/categories/{category.id}", status_code=303)

    @app.get("/admin/categories/{category_id}", response_class=HTMLResponse)
    async def admin_category_edit(request: Request, category_id: int) -> HTMLResponse:
        admin_or_refuse(request, page=True)
        try:
            category = catalog.get_category(category_id)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        context = admin_context(request)
        context.update(
            {
                "category": category,
                "categories": catalog.list_categories(),
                "product_count": len(catalog.list_products(category_id=category_id)),
            }
        )
        return render("admin_category_form.html", context)

    @app.post("/admin/categories/{category_id}")
    async def admin_category_update(request: Request, category_id: int):
        _, _, form = await admin_form(request)
        try:
            catalog.update_category(
                category_id,
                slug=form.get("slug") or None,
                texts=_texts_from_form(form, catalog.get_settings().language_codes),
                is_published=bool(form.get("is_published")),
            )
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except (ValidationError, CatalogError) as exc:
            context = admin_context(request, error=str(exc), values=form)
            context.update({"category": catalog.get_category(category_id)})
            return render("admin_category_form.html", context, status_code=400)
        return RedirectResponse(url=f"/admin/categories/{category_id}", status_code=303)

    @app.post("/admin/categories/{category_id}/delete")
    async def admin_category_delete(request: Request, category_id: int):
        _, _, form = await admin_form(request)
        reassign = (form.get("reassign_to") or "").strip()
        try:
            catalog.delete_category(
                category_id, reassign_to=int(reassign) if reassign else None
            )
        except CategoryInUseError as exc:
            context = admin_context(request, error=str(exc), values=form)
            context.update(
                {
                    "category": catalog.get_category(category_id),
                    "categories": catalog.list_categories(),
                    "product_count": len(catalog.list_products(category_id=category_id)),
                }
            )
            return render("admin_category_form.html", context, status_code=409)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except (ValidationError, CatalogError) as exc:
            context = admin_context(request, error=str(exc), values=form)
            context.update({"category": catalog.get_category(category_id)})
            return render("admin_category_form.html", context, status_code=400)
        return RedirectResponse(url="/admin/categories", status_code=303)

    # --- admin: products -----------------------------------------------

    @app.get("/admin/products", response_class=HTMLResponse)
    async def admin_products(request: Request) -> HTMLResponse:
        admin_or_refuse(request, page=True)
        context = admin_context(request)
        incomplete = request.query_params.get("incomplete") == "1"
        products = catalog.list_products(
            q=(request.query_params.get("q") or "").strip() or None,
            category_id=(
                int(request.query_params["category_id"])
                if (request.query_params.get("category_id") or "").isdigit()
                else None
            ),
            incomplete=incomplete,
        )
        context.update(
            {
                "products": products,
                "categories": catalog.list_categories(),
                "categories_by_id": {c.id: c for c in catalog.list_categories()},
                "q": (request.query_params.get("q") or "").strip(),
                "selected_category_id": (request.query_params.get("category_id") or "").strip(),
                "incomplete": incomplete,
                "translation_state": {
                    product.id: _translation_state(product) for product in products
                },
            }
        )
        return render("admin_products.html", context)

    @app.get("/admin/products/new", response_class=HTMLResponse)
    async def admin_product_new(request: Request) -> HTMLResponse:
        admin_or_refuse(request, page=True)
        context = admin_context(request)
        context.update({"product": None, "categories": catalog.list_categories()})
        return render("admin_product_form.html", context)

    @app.post("/admin/products/new")
    async def admin_product_create(request: Request):
        _, _, form = await admin_form(request)
        settings = catalog.get_settings()
        try:
            product = catalog.create_product(
                slug=form.get("slug"),
                category_id=_category_from_form(form),
                price=form.get("price"),
                currency=(form.get("currency") or "MDL").strip().upper(),
                texts=_texts_from_form(form, settings.language_codes),
                attributes=_attributes_from_form(form),
                is_published=bool(form.get("is_published")),
            )
        except (ValidationError, CatalogError) as exc:
            context = admin_context(request, error=str(exc), values=form)
            context.update({"product": None, "categories": catalog.list_categories()})
            return render("admin_product_form.html", context, status_code=400)
        return RedirectResponse(url=f"/admin/products/{product.id}", status_code=303)

    @app.get("/admin/products/{product_id}", response_class=HTMLResponse)
    async def admin_product_edit(request: Request, product_id: int) -> HTMLResponse:
        admin_or_refuse(request, page=True)
        try:
            product = catalog.get_product(product_id)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        context = admin_context(request)
        context.update({"product": product, "categories": catalog.list_categories()})
        requested = (request.query_params.get("missing") or "").strip()
        context["publish_warning"] = list(
            dict.fromkeys(
                code for code in requested.split(",") if code in CONTENT_LANGUAGES
            )
        )
        return render("admin_product_form.html", context)

    @app.post("/admin/products/{product_id}")
    async def admin_product_update(request: Request, product_id: int):
        _, _, form = await admin_form(request)
        settings = catalog.get_settings()
        try:
            existing = catalog.get_product(product_id).attribute_rows
            per_language: Dict[str, int] = {}
            for row in existing:
                if row[0]:
                    per_language[row[0]] = per_language.get(row[0], 0) + 1
            if (
                len(existing) > ATTRIBUTE_SLOTS
                or max(per_language.values(), default=0) > ATTRIBUTE_ROWS_PER_LANGUAGE
            ):
                context = admin_context(request, values=form)
                context["error"] = context["ui"]["admin"]["attributes_limit"]
                context.update({"product": catalog.get_product(product_id),
                                "categories": catalog.list_categories()})
                return render("admin_product_form.html", context, status_code=400)
            catalog.update_product(
                product_id,
                slug=form.get("slug") or None,
                category_id=_category_from_form(form),
                price=form.get("price"),
                currency=(form.get("currency") or "MDL").strip().upper(),
                texts=_texts_from_form(form, settings.language_codes),
                attributes=_attributes_from_form(form),
                is_published=bool(form.get("is_published")),
            )
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except (ValidationError, CatalogError) as exc:
            context = admin_context(request, error=str(exc), values=form)
            context.update(
                {"product": catalog.get_product(product_id), "categories": catalog.list_categories()}
            )
            return render("admin_product_form.html", context, status_code=400)
        return RedirectResponse(url=f"/admin/products/{product_id}", status_code=303)

    @app.post("/admin/products/{product_id}/publish")
    async def admin_product_publish(request: Request, product_id: int):
        _, _, form = await admin_form(request)
        published = form.get("published") == "1"
        _, missing = catalog.set_product_published(product_id, published)
        target = f"/admin/products/{product_id}"
        if missing:
            target = target + "?missing=" + ",".join(missing)
        return RedirectResponse(url=target, status_code=303)

    @app.post("/admin/products/{product_id}/delete")
    async def admin_product_delete(request: Request, product_id: int):
        await admin_form(request)
        catalog.delete_product(product_id)
        return RedirectResponse(url="/admin/products", status_code=303)

    @app.post("/admin/products/{product_id}/images")
    async def admin_product_image_upload(request: Request, product_id: int):
        configured, _, token = admin_or_refuse(request, page=False)
        if not configured.check_csrf(token, request.headers.get("x-csrf-token")):
            raise HTTPException(status_code=403, detail="invalid or missing CSRF token")
        content = await request.body()
        # a browser cannot send non-ASCII header values (Fetch throws), so the
        # original name travels as a URL-encoded query parameter; the header is
        # still accepted for compatibility with older pages
        original_name = request.query_params.get("name") or request.headers.get("x-file-name", "")
        try:
            catalog.add_product_image(product_id, content, original_name=original_name)
        except ImageError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        return RedirectResponse(url=f"/admin/products/{product_id}", status_code=303)

    @app.post("/admin/products/{product_id}/images/{image_id}/delete")
    async def admin_product_image_delete(request: Request, product_id: int, image_id: int):
        await admin_form(request)
        try:
            catalog.delete_product_image(product_id, image_id)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        return RedirectResponse(url=f"/admin/products/{product_id}", status_code=303)

    # --- admin: shop settings ------------------------------------------

    @app.get("/admin/settings", response_class=HTMLResponse)
    async def admin_settings(request: Request) -> HTMLResponse:
        admin_or_refuse(request, page=True)
        context = admin_context(request)
        context["languages"] = catalog.list_languages()
        return render("admin_settings.html", context)

    @app.post("/admin/settings")
    async def admin_settings_update(request: Request):
        _, _, form = await admin_form(request)
        try:
            catalog.update_settings(
                {
                    "shop_name": form.get("shop_name", ""),
                    "shop_description": form.get("shop_description", ""),
                    "shop_logo": form.get("shop_logo", ""),
                    "contact_email": form.get("contact_email", ""),
                    "contact_phone": form.get("contact_phone", ""),
                    "contact_address": form.get("contact_address", ""),
                    "default_currency": form.get("default_currency", ""),
                    "publish_timezone": form.get("publish_timezone", ""),
                    "tagline": form.get("tagline", ""),
                    "social_facebook": form.get("social_facebook", ""),
                    "social_instagram": form.get("social_instagram", ""),
                    "social_telegram": form.get("social_telegram", ""),
                    "seo_title": form.get("seo_title", ""),
                    "seo_description": form.get("seo_description", ""),
                }
            )
            languages = _languages_from_form(form)
            if languages:
                catalog.set_languages(languages, form.get("default_language"))
        except (ValidationError, CatalogError) as exc:
            context = admin_context(request, error=str(exc), values=form)
            context["languages"] = catalog.list_languages()
            return render("admin_settings.html", context, status_code=400)
        return RedirectResponse(url="/admin/settings", status_code=303)

    # --- admin: category image (raw body, like product images) ----------

    @app.post("/admin/categories/{category_id}/image")
    async def admin_category_image(request: Request, category_id: int):
        configured, _, token = admin_or_refuse(request, page=False)
        if not configured.check_csrf(token, request.headers.get("x-csrf-token")):
            raise HTTPException(status_code=403, detail="invalid or missing CSRF token")
        try:
            stored = images.save(
                await request.body(),
                original_name=request.query_params.get("name")
                or request.headers.get("x-file-name", ""),
            )
        except ImageError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        try:
            catalog.update_category(category_id, image=stored.file_name)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        return RedirectResponse(url=f"/admin/categories/{category_id}", status_code=303)

    # --- admin: logo upload (raw body, like product images) -------------

    @app.post("/admin/settings/logo")
    async def admin_settings_logo(request: Request):
        configured, _, token = admin_or_refuse(request, page=False)
        if not configured.check_csrf(token, request.headers.get("x-csrf-token")):
            raise HTTPException(status_code=403, detail="invalid or missing CSRF token")
        try:
            stored = images.save(
                await request.body(),
                original_name=request.query_params.get("name")
                or request.headers.get("x-file-name", ""),
            )
        except ImageError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        catalog.update_settings({"shop_logo": stored.file_name})
        return RedirectResponse(url="/admin/settings", status_code=303)

    # --- admin: informational pages -------------------------------------

    @app.get("/admin/pages", response_class=HTMLResponse)
    async def admin_pages(request: Request) -> HTMLResponse:
        admin_or_refuse(request, page=True)
        context = admin_context(request)
        context["pages"] = catalog.list_pages()
        return render("admin_pages.html", context)

    @app.get("/admin/pages/new", response_class=HTMLResponse)
    async def admin_page_new(request: Request) -> HTMLResponse:
        admin_or_refuse(request, page=True)
        return render("admin_page_form.html", {**admin_context(request), "page": None})

    @app.post("/admin/pages/new")
    async def admin_page_create(request: Request):
        _, _, form = await admin_form(request)
        settings = catalog.get_settings()
        try:
            page = catalog.create_page(
                slug=form.get("slug"),
                texts=_page_texts_from_form(form, settings.language_codes),
                is_published=bool(form.get("is_published")),
            )
        except (ValidationError, CatalogError) as exc:
            return render(
                "admin_page_form.html",
                {**admin_context(request, error=str(exc), values=form), "page": None},
                status_code=400,
            )
        return RedirectResponse(url=f"/admin/pages/{page.id}", status_code=303)

    @app.get("/admin/pages/{page_id}", response_class=HTMLResponse)
    async def admin_page_edit(request: Request, page_id: int) -> HTMLResponse:
        admin_or_refuse(request, page=True)
        try:
            page = catalog.get_page(page_id)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        context = admin_context(request)
        context["page"] = page
        return render("admin_page_form.html", context)

    @app.post("/admin/pages/{page_id}")
    async def admin_page_update(request: Request, page_id: int):
        _, _, form = await admin_form(request)
        settings = catalog.get_settings()
        try:
            catalog.update_page(
                page_id,
                slug=form.get("slug") or None,
                texts=_page_texts_from_form(form, settings.language_codes),
                is_published=bool(form.get("is_published")),
            )
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except (ValidationError, CatalogError) as exc:
            context = admin_context(request, error=str(exc), values=form)
            context["page"] = catalog.get_page(page_id)
            return render("admin_page_form.html", context, status_code=400)
        return RedirectResponse(url=f"/admin/pages/{page_id}", status_code=303)

    @app.post("/admin/pages/{page_id}/publish")
    async def admin_page_publish(request: Request, page_id: int):
        _, _, form = await admin_form(request)
        catalog.update_page(page_id, is_published=form.get("published") == "1")
        return RedirectResponse(url=f"/admin/pages/{page_id}", status_code=303)

    @app.post("/admin/pages/{page_id}/delete")
    async def admin_page_delete(request: Request, page_id: int):
        await admin_form(request)
        catalog.delete_page(page_id)
        return RedirectResponse(url="/admin/pages", status_code=303)


    # --- admin: requests (block 3a) ------------------------------------

    # --- admin: publication channels (S5.2) ----------------------------

    def _publications_service() -> PublicationsService:
        return PublicationsService(provider)

    def _channel_chat_id(settings_json: str) -> str:
        try:
            settings = json.loads(settings_json or "{}")
        except ValueError:
            return ""
        if not isinstance(settings, dict):
            return ""
        value = settings.get("chat_id")
        return value if isinstance(value, str) else ""

    def _channel_settings_json(current: str, chat_id: str) -> str:
        try:
            settings = json.loads(current or "{}")
        except ValueError as exc:
            raise ValidationError("settings_json invalid") from exc
        if not isinstance(settings, dict):
            raise ValidationError("settings_json invalid")
        updated = dict(settings)
        updated["chat_id"] = chat_id
        return json.dumps(updated, ensure_ascii=False)

    def _channel_values(form: Mapping[str, Any]) -> Dict[str, str]:
        return {
            "channel_key": (form.get("channel_key") or "").strip(),
            "name": (form.get("name") or "").strip(),
            "credentials_ref": (form.get("credentials_ref") or "").strip(),
            "chat_id": (form.get("chat_id") or "").strip(),
            "timezone": (form.get("timezone") or "").strip() or "Europe/Chisinau",
            "default_language": (form.get("default_language") or "").strip(),
        }

    def _channel_error(request: Request, message: str, form: Mapping[str, Any], channel=None):
        context = admin_context(request, error=message, values=form)
        context["channel"] = channel
        context["channel_chat_id"] = (
            _channel_chat_id(channel.settings_json) if channel is not None else ""
        )
        return render("admin_channel_form.html", context, status_code=400)

    @app.get("/admin/channels", response_class=HTMLResponse)
    async def admin_channels(request: Request) -> HTMLResponse:
        _publications_guard()
        admin_or_refuse(request, page=True)
        context = admin_context(request)
        context["channels"] = _publications_service().list_channels()
        return render("admin_channels.html", context)

    @app.get("/admin/channels/new", response_class=HTMLResponse)
    async def admin_channel_new(request: Request) -> HTMLResponse:
        _publications_guard()
        admin_or_refuse(request, page=True)
        context = admin_context(request)
        context["channel"] = None
        context["channel_chat_id"] = ""
        return render("admin_channel_form.html", context)

    @app.post("/admin/channels/new")
    async def admin_channel_create(request: Request):
        _publications_guard()
        _, _, form = await admin_form(request)
        values = _channel_values(form)
        if not values["chat_id"]:
            return _channel_error(request, "chat_id is required", form)
        try:
            settings_json = _channel_settings_json("{}", values["chat_id"])
            _publications_service().create_channel(
                platform="telegram",
                channel_key=values["channel_key"],
                name=values["name"],
                credentials_ref=values["credentials_ref"],
                settings_json=settings_json,
                default_language=values["default_language"],
                timezone=values["timezone"],
                is_active=bool(form.get("is_active")),
            )
        except sqlite3.IntegrityError:
            return _channel_error(
                request, "channel_key or name already used for this platform", form
            )
        except (ValidationError, CatalogError) as exc:
            return _channel_error(request, str(exc), form)
        return RedirectResponse(url="/admin/channels", status_code=303)

    @app.get("/admin/channels/{channel_id}", response_class=HTMLResponse)
    async def admin_channel_edit(request: Request, channel_id: int) -> HTMLResponse:
        _publications_guard()
        admin_or_refuse(request, page=True)
        try:
            channel = _publications_service().get_channel(channel_id)
        except NotFoundError:
            raise HTTPException(status_code=404, detail="not found")
        context = admin_context(request)
        context["channel"] = channel
        context["channel_chat_id"] = _channel_chat_id(channel.settings_json)
        return render("admin_channel_form.html", context)

    @app.post("/admin/channels/{channel_id}")
    async def admin_channel_update(request: Request, channel_id: int):
        _publications_guard()
        _, _, form = await admin_form(request)
        try:
            channel = _publications_service().get_channel(channel_id)
        except NotFoundError:
            raise HTTPException(status_code=404, detail="not found")
        values = _channel_values(form)
        if not values["chat_id"]:
            return _channel_error(request, "chat_id is required", form, channel)
        try:
            settings_json = _channel_settings_json(
                channel.settings_json, values["chat_id"]
            )
            _publications_service().update_channel(
                channel_id,
                channel_key=values["channel_key"],
                name=values["name"],
                credentials_ref=values["credentials_ref"],
                settings_json=settings_json,
                default_language=values["default_language"],
                timezone=values["timezone"],
                is_active=bool(form.get("is_active")),
            )
        except sqlite3.IntegrityError:
            return _channel_error(
                request,
                "channel_key or name already used for this platform",
                form,
                channel,
            )
        except (ValidationError, CatalogError) as exc:
            return _channel_error(request, str(exc), form, channel)
        return RedirectResponse(url="/admin/channels", status_code=303)

    # --- admin: publications (S5.3) -------------------------------------

    def _publication_rows(
        service: PublicationsService, settings
    ) -> List[Dict[str, Any]]:
        zone = ZoneInfo(settings.publish_timezone)
        by_publication: Dict[int, List[Any]] = {}
        for job in service.list_jobs(limit=100):
            by_publication.setdefault(job.publication_id, []).append(job)
        rows: List[Dict[str, Any]] = []
        for publication_id, jobs in by_publication.items():
            try:
                publication = service.get_publication(publication_id)
            except NotFoundError:
                continue
            nearest = min(job.scheduled_for for job in jobs)
            rows.append(
                {
                    "publication": publication,
                    "texts": service.get_texts(publication_id),
                    "jobs": jobs,
                    "statuses": sorted({job.status for job in jobs}),
                    "nearest_utc": nearest,
                    "nearest_local": datetime.fromisoformat(nearest)
                    .astimezone(zone)
                    .isoformat(),
                }
            )
        rows.sort(key=lambda row: row["publication"].id, reverse=True)
        return rows

    def _publication_form_data(form: Mapping[str, Any], settings, channels):
        texts: Dict[str, tuple] = {}
        for code in settings.language_codes:
            title = (form.get(f"title_{code}") or "").strip()
            body = (form.get(f"body_{code}") or "").strip()
            if title or body:
                texts[code] = (title, body)
        selected_channels = [
            channel.id for channel in channels if form.get(f"channel_{channel.id}")
        ]
        return texts, selected_channels

    def _publication_validate(texts, settings) -> str:
        if not texts:
            return "at least one language text is required"
        for code in settings.language_codes:
            if code not in texts:
                return f"text for language {code!r} is required"
            title, body = texts[code]
            if not title:
                return f"title for language {code!r} is required"
            content = body or title
            if len(escape_html(content)) > TEXT_LIMIT:
                return (
                    f"text for language {code!r} exceeds the Telegram limit "
                    "(escaped length)"
                )
        return ""

    def _publication_channels(service) -> List[Any]:
        return [
            channel
            for channel in service.list_channels(active_only=True)
            if channel.platform == "telegram"
        ]

    @app.get("/admin/publications", response_class=HTMLResponse)
    async def admin_publications(request: Request) -> HTMLResponse:
        _publications_guard()
        admin_or_refuse(request, page=True)
        context = admin_context(request)
        context["publications"] = _publication_rows(
            _publications_service(), context["settings"]
        )
        context["shifted"] = request.query_params.get("shifted") == "1"
        return render("admin_publications.html", context)

    @app.get("/admin/publications/new", response_class=HTMLResponse)
    async def admin_publication_new(request: Request) -> HTMLResponse:
        _publications_guard()
        admin_or_refuse(request, page=True)
        context = admin_context(request)
        context["channels"] = _publication_channels(_publications_service())
        return render("admin_publication_form.html", context)

    @app.post("/admin/publications/new")
    async def admin_publication_create(request: Request):
        _publications_guard()
        _, user, form = await admin_form(request)
        settings = catalog.get_settings()
        service = _publications_service()
        channels = _publication_channels(service)
        texts, selected_channels = _publication_form_data(form, settings, channels)
        error = _publication_validate(texts, settings)
        scheduled_local = (form.get("scheduled_local") or "").strip()
        utc_iso = ""
        shifted = False
        if not error:
            try:
                local_moment = datetime.fromisoformat(scheduled_local)
            except ValueError:
                error = "scheduled time is invalid"
            else:
                try:
                    utc_iso = resolve_publish_moment(
                        local_moment.replace(tzinfo=None),
                        settings.publish_timezone,
                    )
                    shifted = (
                        datetime.fromisoformat(utc_iso)
                        .astimezone(ZoneInfo(settings.publish_timezone))
                        .replace(tzinfo=None)
                        != local_moment.replace(tzinfo=None)
                    )
                except ValidationError as exc:
                    error = str(exc)
        if not error and not selected_channels:
            error = "at least one active telegram channel is required"
        if error:
            context = admin_context(request, error=error, values=form)
            context["channels"] = channels
            return render("admin_publication_form.html", context, status_code=400)

        try:
            publication = service.create_publication(
                texts=texts, created_by=str(user or "")
            )
        except (ValidationError, CatalogError) as exc:
            context = admin_context(request, error=str(exc), values=form)
            context["channels"] = channels
            return render("admin_publication_form.html", context, status_code=400)

        try:
            service.schedule_jobs(
                publication.id,
                channel_ids=selected_channels,
                langs=list(texts),
                scheduled_for=utc_iso,
            )
        except sqlite3.IntegrityError:
            context = admin_context(
                request, error="jobs for these parameters already exist", values=form
            )
            context["channels"] = channels
            return render("admin_publication_form.html", context, status_code=400)
        except Exception as exc:  # noqa: BLE001 - report, never retry automatically
            context = admin_context(
                request,
                error=(
                    f"publication created (id={publication.id}), jobs NOT scheduled: "
                    f"{type(exc).__name__}"
                ),
                values=form,
            )
            context["channels"] = channels
            return render("admin_publication_form.html", context, status_code=400)
        target = "/admin/publications" + ("?shifted=1" if shifted else "")
        return RedirectResponse(url=target, status_code=303)

    @app.get("/admin/requests", response_class=HTMLResponse)
    async def admin_requests(request: Request) -> HTMLResponse:
        admin_or_refuse(request, page=True)
        state = (request.query_params.get("state") or "").strip()
        context = admin_context(request)
        context.update(
            {
                "requests": catalog.list_requests(state=state or None),
                "state_filter": state,
                "states": REQUEST_STATES,
            }
        )
        return render("admin_requests.html", context)

    @app.post("/admin/requests/{request_id}/state")
    async def admin_request_state(request: Request, request_id: int):
        await admin_form(request)
        form = await read_urlencoded(request)
        try:
            catalog.set_request_state(request_id, form.get("state") or "")
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except ValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        state = (form.get("return_state") or "").strip()
        target = f"/admin/requests?state={state}" if state else "/admin/requests"
        return RedirectResponse(url=target, status_code=303)

    # --- admin: orders (shop only, block 3c-3) --------------------------

    def _admin_orders_guard() -> None:
        if not features["cart"]:
            raise HTTPException(status_code=404, detail="not found")

    def _publications_guard() -> None:
        if (source.get("VIDEOSHOP_PUBLICATIONS", "off") or "").strip().lower() != "on":
            raise HTTPException(status_code=404, detail="not found")

    @app.get("/admin/orders", response_class=HTMLResponse)
    async def admin_orders(request: Request) -> HTMLResponse:
        _admin_orders_guard()
        admin_or_refuse(request, page=True)
        status = (request.query_params.get("status") or "").strip()
        if status not in ORDER_STATUSES:
            status = ""  # unknown filters fall back to "all" instead of erroring
        context = admin_context(request)
        context.update(
            {
                "orders": order_service.list_orders(status=status or None),
                "status_filter": status,
                "statuses": ORDER_STATUSES,
            }
        )
        return render("admin_orders.html", context)

    @app.get("/admin/orders/{number}", response_class=HTMLResponse)
    async def admin_order_detail(request: Request, number: str) -> HTMLResponse:
        _admin_orders_guard()
        admin_or_refuse(request, page=True)
        order = order_service.admin_get(number)
        if order is None:
            raise HTTPException(status_code=404, detail="order not found")
        context = admin_context(request)
        context.update(
            {
                "order": order,
                "statuses": ORDER_STATUSES,
                "allowed_targets": order_service.allowed_targets(order.status),
            }
        )
        return render("admin_order.html", context)

    @app.post("/admin/orders/{number}/status")
    async def admin_order_status(request: Request, number: str):
        _admin_orders_guard()
        await admin_form(request)
        form = await read_urlencoded(request)
        try:
            order, previous = order_service.set_status(number, form.get("status") or "")
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except InvalidStatusTransition as exc:
            context = admin_context(request, error=admin_context(request)["ui"]["admin"]["admin_error_status_transition"])
            context.update(
                {
                    "order": order_service.admin_get(number),
                    "statuses": ORDER_STATUSES,
                    "allowed_targets": order_service.allowed_targets(exc.current),
                }
            )
            return render("admin_order.html", context, status_code=400)
        return RedirectResponse(url=f"/admin/orders/{order.number}", status_code=303)

    # --- public: informational pages ------------------------------------

    @app.get("/page/{slug}", response_class=HTMLResponse)
    async def public_page(request: Request, slug: str):
        context = page_context(request)
        page, redirect_slug = catalog.resolve_page(slug)
        if page is None:
            # the home page cards link to /page/about#anchors: render a scaffold
            # instead of a 404 while the owner has not created the page yet
            # (an existing but unpublished page still answers 404)
            if slug == "about" and not any(item.slug == "about" for item in catalog.list_pages()):
                return render("page_stub.html", context)
            context["slug"] = slug
            return render("public_not_found.html", context, status_code=404)
        if redirect_slug:
            return RedirectResponse(url=f"/page/{redirect_slug}", status_code=301)
        context["page"] = page
        text = page.text(context["lang"])
        return render(
            "public_page.html",
            context,
            seo={"title": text.title, "seo_description": text.body[:300]},
        )

    app.state.cart_service = cart_service
    app.state.order_service = order_service
    return app


# --- form parsing helpers ------------------------------------------------


async def read_urlencoded(request: Request) -> Dict[str, Any]:
    """Parse an ``application/x-www-form-urlencoded`` body with the stdlib.

    ``request.form()`` is not used on purpose: in this environment it asserts
    that ``python-multipart`` is installed even for urlencoded bodies, and
    ``python-multipart`` is NOT available. HTML forms post urlencoded by
    default, so the stdlib parser covers every admin form without adding a
    dependency. Multipart bodies are refused explicitly (415).
    """
    content_type = (request.headers.get("content-type") or "").split(";")[0].strip().lower()
    if content_type not in ("application/x-www-form-urlencoded", ""):
        raise HTTPException(
            status_code=415,
            detail="admin forms must be submitted as application/x-www-form-urlencoded",
        )
    body = await request.body()
    if not body:
        return {}
    parsed = parse_qs(body.decode("utf-8", errors="replace"), keep_blank_values=True)
    return {key: values[-1] for key, values in parsed.items()}


def _requested_language(request: Request, settings) -> str:
    requested = (request.query_params.get("lang") or "").strip().lower()
    codes = settings.language_codes
    if requested and requested in codes:
        return requested
    return settings.default_language if settings.default_language in codes else (
        codes[0] if codes else DEFAULT_LANGUAGE
    )


def _find_category(categories, reference: Optional[str]):
    if not reference:
        return None
    for category in categories:
        if str(category.id) == str(reference) or category.slug == reference:
            return category
    return None


def _texts_from_form(form: Mapping[str, Any], languages) -> Dict[str, Dict[str, str]]:
    texts: Dict[str, Dict[str, str]] = {}
    for lang in languages:
        name = (form.get(f"name_{lang}") or "").strip()
        description = (form.get(f"description_{lang}") or "").strip()
        if name or description:
            texts[lang] = {"name": name, "description": description}
    return texts


def _translation_state(
    product: Any, languages: Sequence[str] = CONTENT_LANGUAGES
) -> List[Dict[str, Any]]:
    """Per-language completeness: name, description and attribute warnings.

    Only real rows count: ``Product.text()`` falls back to another language
    and is never used here. Provenance of a stored text is unknown, because
    no flag or column records whether a value was copied or translated.
    """
    has_any_attributes = any(product.attribute_count(code) for code in languages)
    state: List[Dict[str, Any]] = []
    for code in languages:
        name_ok = product.has_text(code)
        description_ok = bool(product.description(code))
        attributes_ok = product.attribute_count(code) > 0
        attributes_na = not has_any_attributes
        state.append(
            {
                "code": code,
                "name_ok": name_ok,
                "description_ok": description_ok,
                "attributes_ok": attributes_ok,
                "attributes_na": attributes_na,
                "warn": name_ok and not (description_ok and (attributes_ok or attributes_na)),
            }
        )
    return state


def _category_ids(categories: Any) -> Dict[str, int]:
    """Rule category key -> catalogue id, resolved through the live slugs."""
    by_slug = {category.slug: category.id for category in categories}
    resolved: Dict[str, int] = {}
    for key in CATEGORY_KEYS:
        live_slug = CATEGORY_ALIASES.get(key, key)
        if live_slug in by_slug:
            resolved[key] = by_slug[live_slug]
    return resolved


#: thousands separators accepted in the budget field: space, no-break,
#: narrow no-break, thin and figure spaces
_BUDGET_SPACES = (" ", "\u00a0", "\u202f", "\u2009", "\u2007")


def _parse_budget_minor(raw: str) -> Optional[int]:
    """Parse the budget field (major units) into minor units.

    Thousands may be separated by spaces; a comma stays a decimal separator.
    Values that are not a finite number are rejected (``None``) instead of being
    silently read as a budget.
    """
    text = (raw or "").strip()
    for space in _BUDGET_SPACES:
        text = text.replace(space, "")
    text = text.replace(",", ".")
    if not text:
        return None
    try:
        amount = Decimal(text)
    except (InvalidOperation, ValueError):
        return None
    if not amount.is_finite():
        return None
    return max(0, int(amount * 100))


def _language_switch_url(request: Request, code: str) -> str:
    """Current page URL with only ``lang`` replaced by ``code``.

    Every other query parameter is preserved, including repeated keys such as
    ``have=a&have=b``. ``lang`` is replaced instead of being duplicated and is
    added when the current URL carries none.
    """
    url = request.url.include_query_params(lang=code)
    return f"{url.path}?{url.query}" if url.query else url.path


def _attribute_columns(settings: Any) -> List[Tuple[str, str]]:
    """Column labels of the characteristics table: code plus its shop title."""
    titles = {code: title for code, title in getattr(settings, "languages", ()) or ()}
    return [(code, titles.get(code) or code.upper()) for code in ATTRIBUTE_TABLE_LANGUAGES]


def _attributes_from_form(form: Mapping[str, Any]) -> List[Tuple[str, str, str]]:
    """Read the 12x(en, ru, ro) table; a row belongs to the language of its column."""
    groups: List[List[Tuple[str, str]]] = []
    for group in range(ATTRIBUTE_ROWS_PER_LANGUAGE):
        cells: List[Tuple[str, str]] = []
        for column in range(len(ATTRIBUTE_TABLE_LANGUAGES)):
            index = group * len(ATTRIBUTE_TABLE_LANGUAGES) + column
            name = (form.get(f"attribute_name_{index}") or "").strip()
            value = (form.get(f"attribute_value_{index}") or "").strip()
            cells.append((name, value))
        groups.append(cells)
    return fill_attribute_translations(groups, ATTRIBUTE_TABLE_LANGUAGES)
def _category_from_form(form: Mapping[str, Any]) -> Optional[int]:
    raw = (form.get("category_id") or "").strip()
    return int(raw) if raw else None


def _languages_from_form(form: Mapping[str, Any]) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    for index in range(LANGUAGE_SLOTS):
        code = (form.get(f"language_code_{index}") or "").strip()
        title = (form.get(f"language_title_{index}") or "").strip()
        if code and title:
            pairs.append((code, title))
    return pairs


def _page_texts_from_form(form: Mapping[str, Any], languages) -> Dict[str, Dict[str, str]]:
    texts: Dict[str, Dict[str, str]] = {}
    for lang in languages:
        title = (form.get(f"title_{lang}") or "").strip()
        body = (form.get(f"body_{lang}") or "").strip()
        if title or body:
            texts[lang] = {"title": title, "body": body}
    return texts
