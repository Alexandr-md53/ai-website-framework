from __future__ import annotations
from fastapi import FastAPI, HTTPException, Header
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, field_validator
import uuid

# ---- Imports with fallbacks ----
try:
    from showcases.cms_lite.domain.user import UserContext, UserRole
except Exception:
    from enum import Enum

    class UserRole(str, Enum):
        ADMIN = "ADMIN"
        EDITOR = "EDITOR"
        VIEWER = "VIEWER"

    from dataclasses import dataclass

    @dataclass
    class UserContext:
        user_id: str
        role: UserRole


try:
    from showcases.cms_lite.services.cms_service import CmsLiteService as OldService
except Exception:
    OldService = None

try:
    from showcases.cms_lite.services.cms_service_framework_wired import (
        CmsLiteFrameworkWiredService as NewService,
    )
except Exception:
    NewService = None


# ---------- Helpers ----------
def _map_role_str(role_val: Optional[str]) -> UserRole:
    if not role_val:
        return UserRole.EDITOR
    hv = str(role_val).strip().upper()
    try:
        return UserRole(hv)
    except Exception:
        # allow lowercase
        if hv == "ADMIN":
            return UserRole.ADMIN
        if hv == "EDITOR":
            return UserRole.EDITOR
        return UserRole.VIEWER


def _make_user_context(user_id: Optional[str], role_str: Optional[str]) -> UserContext:
    uid = user_id or str(uuid.uuid4())
    # keep uid as string (service accepts uuid string check internally)
    try:
        uuid.UUID(uid)
        uid_str = uid
    except Exception:
        uid_str = str(uuid.uuid5(uuid.NAMESPACE_DNS, uid))
    role = _map_role_str(role_str)
    return UserContext(user_id=uid_str, role=role)


def _to_dict(obj):
    if obj is None:
        return {}
    if isinstance(obj, dict):
        # normalize status inside dict too
        d = dict(obj)
        if "status" in d:
            st = d["status"]
            if hasattr(st, "value"):
                d["status"] = st.value
            elif hasattr(st, "name"):
                d["status"] = st.name
            else:
                s = str(st)
                # "ItemStatus.DRAFT" -> "DRAFT"
                if "." in s:
                    s = s.split(".")[-1]
                d["status"] = s
        return d
    if hasattr(obj, "to_dict"):
        try:
            inner = obj.to_dict()
            return _to_dict(inner)
        except Exception:
            pass
    data = {}
    for k in [
        "id",
        "title",
        "slug",
        "content",
        "status",
        "category_id",
        "tag_ids",
        "media_ids",
        "seo_title",
        "seo_description",
        "og_title",
        "og_description",
        "canonical_url",
        "filename",
        "filepath",
        "media_type",
        "alt_text",
        "name",
        "description",
    ]:
        if hasattr(obj, k):
            v = getattr(obj, k)
            if callable(v):
                continue
            if isinstance(v, uuid.UUID):
                v = str(v)
            elif isinstance(v, list):
                v = [str(x) if isinstance(x, uuid.UUID) else x for x in v]
            elif k == "status":
                # Enum -> "DRAFT" not "ItemStatus.DRAFT"
                if hasattr(v, "value"):
                    v = v.value
                elif hasattr(v, "name"):
                    v = v.name
                else:
                    s = str(v)
                    if "." in s:
                        s = s.split(".")[-1]
                    v = s
            elif hasattr(v, "value"):
                # other enums
                try:
                    v = v.value
                except Exception:
                    pass
            data[k] = v
    if not data and hasattr(obj, "__dict__"):
        data = {}
        for kk, vv in obj.__dict__.items():
            if kk.startswith("_"):
                continue
            if isinstance(vv, uuid.UUID):
                vv = str(vv)
            elif kk == "status":
                if hasattr(vv, "value"):
                    vv = vv.value
                elif hasattr(vv, "name"):
                    vv = vv.name
                else:
                    s = str(vv)
                    if "." in s:
                        s = s.split(".")[-1]
                    vv = s
            elif hasattr(vv, "value"):
                try:
                    vv = vv.value
                except Exception:
                    pass
            data[kk] = vv
    # final safety
    if "status" in data:
        st = data["status"]
        if hasattr(st, "value"):
            data["status"] = st.value
        elif hasattr(st, "name"):
            data["status"] = st.name
        else:
            s = str(st)
            if "." in s:
                s = s.split(".")[-1]
            data["status"] = s
    if "id" in data and isinstance(data["id"], uuid.UUID):
        data["id"] = str(data["id"])
    return data


def _parse_uuid(val, field_name="id"):
    if isinstance(val, uuid.UUID):
        return val
    if isinstance(val, str):
        try:
            return uuid.UUID(val)
        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid {field_name}: {val}")
    raise HTTPException(status_code=400, detail=f"Invalid {field_name}: {val}")


# ---------- OLD Phase 4 App (body user_role) ----------
def _build_old_app(svc) -> FastAPI:
    app = FastAPI(title="CMS Lite — Phase 4 (body role)")

    def _user_from_payload(payload: dict) -> UserContext:
        return _make_user_context(payload.get("user_id"), payload.get("user_role"))

    @app.post("/categories")
    def create_category(payload: dict):
        try:
            user = _user_from_payload(payload)
            cat = svc.create_category(
                user=user,
                name=payload.get("name"),
                slug=payload.get("slug"),
                description=payload.get("description"),
            )
            return _to_dict(cat)
        except Exception as e:
            msg = str(e)
            low = msg.lower()
            if "forbidden" in low or "permission" in low or "unauthorized" in low:
                raise HTTPException(status_code=403, detail=msg)
            if "not found" in low:
                raise HTTPException(status_code=404, detail=msg)
            raise HTTPException(status_code=400, detail=msg)

    @app.get("/categories")
    def list_categories():
        return [_to_dict(c) for c in svc.list_categories()]

    @app.post("/items")
    def create_item(payload: dict):
        try:
            user = _user_from_payload(payload)
            cat_raw = payload.get("category_id")
            if not cat_raw:
                raise HTTPException(status_code=400, detail="category_id required")
            try:
                cat_id = uuid.UUID(cat_raw) if isinstance(cat_raw, str) else cat_raw
            except Exception:
                raise HTTPException(
                    status_code=400, detail=f"Invalid category_id {cat_raw}"
                )
            tag_ids = payload.get("tag_ids")
            norm_tags = None
            if tag_ids:
                norm_tags = []
                for t in tag_ids:
                    try:
                        norm_tags.append(uuid.UUID(t) if isinstance(t, str) else t)
                    except Exception:
                        raise HTTPException(
                            status_code=400, detail=f"Invalid tag_id {t}"
                        )
            item = svc.create_item(
                user=user,
                title=payload.get("title"),
                slug=payload.get("slug"),
                content=payload.get("content", ""),
                category_id=cat_id,
                tag_ids=norm_tags,
            )
            return _to_dict(item)
        except HTTPException:
            raise
        except Exception as e:
            msg = str(e)
            low = msg.lower()
            if "forbidden" in low:
                raise HTTPException(status_code=403, detail=msg)
            if "not found" in low:
                raise HTTPException(status_code=404, detail=msg)
            raise HTTPException(status_code=400, detail=msg)

    @app.post("/items/{item_id}/publish")
    def publish_item(item_id: str, payload: dict):
        try:
            user = _user_from_payload(payload)
            iid = _parse_uuid(item_id, "item_id")
            item = svc.publish_item(user=user, item_id=iid)
            return _to_dict(item)
        except HTTPException:
            raise
        except Exception as e:
            msg = str(e)
            low = msg.lower()
            if "forbidden" in low:
                raise HTTPException(status_code=403, detail=msg)
            if "not found" in low:
                raise HTTPException(status_code=404, detail=msg)
            raise HTTPException(status_code=400, detail=msg)

    @app.post("/items/{item_id}/unpublish")
    def unpublish_item(item_id: str, payload: dict):
        try:
            user = _user_from_payload(payload)
            iid = _parse_uuid(item_id, "item_id")
            item = svc.unpublish_item(user=user, item_id=iid)
            return _to_dict(item)
        except HTTPException:
            raise
        except Exception as e:
            msg = str(e)
            low = msg.lower()
            if "forbidden" in low:
                raise HTTPException(status_code=403, detail=msg)
            if "not found" in low:
                raise HTTPException(status_code=404, detail=msg)
            raise HTTPException(status_code=400, detail=msg)

    @app.post("/items/{item_id}/duplicate")
    def duplicate_item(item_id: str, payload: dict):
        try:
            user = _user_from_payload(payload)
            iid = _parse_uuid(item_id, "item_id")
            dup = svc.duplicate_item(user=user, item_id=iid)
            d = _to_dict(dup)
            # Ensure status string
            if "status" not in d:
                d["status"] = "DRAFT"
            return d
        except HTTPException:
            raise
        except Exception as e:
            msg = str(e)
            low = msg.lower()
            if "forbidden" in low:
                raise HTTPException(status_code=403, detail=msg)
            if "not found" in low:
                raise HTTPException(status_code=404, detail=msg)
            raise HTTPException(status_code=400, detail=msg)

    @app.get("/public/items/{slug}")
    def get_public_by_slug(slug: str):
        try:
            item = svc.get_published_by_slug(slug)
            return _to_dict(item)
        except Exception as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.get("/public/items")
    def list_public():
        try:
            items = svc.list_published()
            return [_to_dict(i) for i in items]
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    # aliases for some tests
    @app.get("/published/{slug}")
    def get_published_alias(slug: str):
        return get_public_by_slug(slug)

    @app.get("/published")
    def list_published_alias():
        return list_public()

    return app


# ---------- NEW Phase 5 App (header role) ----------
class SeoUpdateRequest(BaseModel):
    seo_title: Optional[str] = Field(default=None, max_length=70)
    seo_description: Optional[str] = Field(default=None, max_length=160)
    og_title: Optional[str] = Field(default=None, max_length=70)
    og_description: Optional[str] = Field(default=None, max_length=200)
    canonical_url: Optional[str] = None

    @field_validator("canonical_url")
    @classmethod
    def validate_canonical(cls, v):
        if v is None or v == "":
            return v
        if not (
            v.startswith("http://") or v.startswith("https://") or v.startswith("/")
        ):
            raise ValueError("canonical_url must start with http://, https:// or /")
        return v


class MediaCreateRequest(BaseModel):
    filename: str
    filepath: str
    media_type: str = "image"
    alt_text: Optional[str] = None


def _build_new_app(svc) -> FastAPI:
    app = FastAPI(title="CMS Lite — Phase 5 SEO + Media")

    def get_current_user(
        x_role: Optional[str] = Header(default="EDITOR"),
        x_user_id: Optional[str] = Header(default="test-user"),
    ) -> UserContext:
        return _make_user_context(x_user_id, x_role)

    # Need to define routes using closure over svc and get_current_user
    from fastapi import Depends

    @app.post("/categories")
    def create_category(payload: dict, user: UserContext = Depends(get_current_user)):
        try:
            cat = svc.create_category(
                user=user,
                name=payload.get("name"),
                slug=payload.get("slug"),
                description=payload.get("description"),
            )
            return _to_dict(cat)
        except Exception as e:
            low = str(e).lower()
            if "forbidden" in low or "permission" in low or "unauthorized" in low:
                raise HTTPException(status_code=403, detail=str(e))
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/categories")
    def list_categories():
        return [_to_dict(c) for c in svc.list_categories()]

    @app.post("/items")
    def create_item(payload: dict, user: UserContext = Depends(get_current_user)):
        try:
            cat_raw = payload.get("category_id")
            if not cat_raw:
                raise HTTPException(status_code=400, detail="category_id required")
            cat_id = _parse_uuid(cat_raw, "category_id")
            tag_ids = payload.get("tag_ids")
            if tag_ids:
                tag_ids = [_parse_uuid(t, "tag_id") for t in tag_ids]
            item = svc.create_item(
                user=user,
                title=payload.get("title"),
                slug=payload.get("slug"),
                content=payload.get("content", ""),
                category_id=cat_id,
                tag_ids=tag_ids,
            )
            return _to_dict(item)
        except HTTPException:
            raise
        except Exception as e:
            low = str(e).lower()
            if "forbidden" in low:
                raise HTTPException(status_code=403, detail=str(e))
            if "not found" in low:
                raise HTTPException(status_code=404, detail=str(e))
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/items/{item_id}")
    def get_item(item_id: str):
        try:
            iid = _parse_uuid(item_id, "item_id")
            # try admin get first, fallback to _get_item
            try:
                # if svc has get_item
                if hasattr(svc, "get_item"):
                    return _to_dict(svc.get_item(iid))
                if hasattr(svc, "_get_item"):
                    return _to_dict(svc._get_item(iid))
                # last resort
                return _to_dict(
                    svc.get_item_admin(_make_user_context(None, "ADMIN"), iid)
                )
            except Exception:
                # for old service compatibility
                return _to_dict(svc._get_item(iid))
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.post("/items/{item_id}/publish")
    def publish_item(item_id: str, user: UserContext = Depends(get_current_user)):
        try:
            iid = _parse_uuid(item_id, "item_id")
            return _to_dict(svc.publish_item(user=user, item_id=iid))
        except Exception as e:
            low = str(e).lower()
            if "forbidden" in low:
                raise HTTPException(status_code=403, detail=str(e))
            if "not found" in low:
                raise HTTPException(status_code=404, detail=str(e))
            raise HTTPException(status_code=400, detail=str(e))

    @app.patch("/items/{item_id}/seo")
    def update_seo(
        item_id: str,
        payload: SeoUpdateRequest,
        user: UserContext = Depends(get_current_user),
    ):
        try:
            iid = _parse_uuid(item_id, "item_id")
            item = svc.update_item_seo(
                user=user,
                item_id=iid,
                seo_title=payload.seo_title,
                seo_description=payload.seo_description,
                og_title=payload.og_title,
                og_description=payload.og_description,
                canonical_url=payload.canonical_url,
            )
            d = _to_dict(item)
            return {
                "id": d.get("id"),
                "seo_title": d.get("seo_title"),
                "seo_description": d.get("seo_description"),
                "og_title": d.get("og_title"),
                "og_description": d.get("og_description"),
                "canonical_url": d.get("canonical_url"),
            }
        except Exception as e:
            low = str(e).lower()
            if "forbidden" in low:
                raise HTTPException(status_code=403, detail=str(e))
            if "not found" in low:
                raise HTTPException(status_code=404, detail=str(e))
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/media")
    def create_media(
        payload: MediaCreateRequest, user: UserContext = Depends(get_current_user)
    ):
        try:
            return _to_dict(
                svc.create_media(
                    user=user,
                    filename=payload.filename,
                    filepath=payload.filepath,
                    media_type=payload.media_type,
                    alt_text=payload.alt_text,
                )
            )
        except Exception as e:
            if "forbidden" in str(e).lower():
                raise HTTPException(status_code=403, detail=str(e))
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/items/{item_id}/media/{media_id}/attach")
    def attach_media(
        item_id: str, media_id: str, user: UserContext = Depends(get_current_user)
    ):
        try:
            item = svc.attach_media_to_item(
                user=user,
                item_id=_parse_uuid(item_id, "item_id"),
                media_id=_parse_uuid(media_id, "media_id"),
            )
            d = _to_dict(item)
            return {
                "item_id": d.get("id"),
                "media_id": str(media_id),
                "media_ids": [str(x) for x in d.get("media_ids", [])],
            }
        except Exception as e:
            low = str(e).lower()
            if "forbidden" in low:
                raise HTTPException(status_code=403, detail=str(e))
            if "not found" in low:
                raise HTTPException(status_code=404, detail=str(e))
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/items/{item_id}/media/{media_id}/detach")
    def detach_media(
        item_id: str, media_id: str, user: UserContext = Depends(get_current_user)
    ):
        try:
            item = svc.detach_media_from_item(
                user=user,
                item_id=_parse_uuid(item_id, "item_id"),
                media_id=_parse_uuid(media_id, "media_id"),
            )
            d = _to_dict(item)
            return {
                "item_id": d.get("id"),
                "media_id": str(media_id),
                "media_ids": [str(x) for x in d.get("media_ids", [])],
            }
        except Exception as e:
            low = str(e).lower()
            if "forbidden" in low:
                raise HTTPException(status_code=403, detail=str(e))
            if "not found" in low:
                raise HTTPException(status_code=404, detail=str(e))
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/items/{item_id}/media")
    def list_media(item_id: str):
        try:
            medias = svc.list_item_media(item_id=_parse_uuid(item_id, "item_id"))
            return {"item_id": str(item_id), "media": [_to_dict(m) for m in medias]}
        except Exception as e:
            if "not found" in str(e).lower():
                raise HTTPException(status_code=404, detail=str(e))
            raise HTTPException(status_code=400, detail=str(e))

    # Public also for new service
    @app.get("/public/items/{slug}")
    def get_public_by_slug(slug: str):
        try:
            return _to_dict(svc.get_published_by_slug(slug))
        except Exception as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.get("/public/items")
    def list_public():
        try:
            return [_to_dict(i) for i in svc.list_published()]
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    return app


# ---------- Public factories ----------
def create_app(service=None, *args, **kwargs) -> FastAPI:
    svc = service or kwargs.get("service_override") or kwargs.get("service")
    # If no service given, default to NewService (Phase 5)
    if svc is None:
        if NewService:
            svc = NewService()
        elif OldService:
            svc = OldService()
        else:
            raise RuntimeError("No service available")
    # Detect old vs new
    if OldService and isinstance(svc, OldService):
        return _build_old_app(svc)
    else:
        return _build_new_app(svc)


def build_cms_lite_app(*args, **kwargs) -> FastAPI:
    svc = kwargs.get("service_override") or kwargs.get("service")
    if svc is None and args:
        svc = args[0]
    return create_app(service=svc)


def build_app(*args, **kwargs) -> FastAPI:
    return build_cms_lite_app(*args, **kwargs)


__all__ = ["create_app", "build_cms_lite_app", "build_app"]
