# coding: utf-8, ASCII only
from typing import Dict, Any
from showcases.cafe.application.create_menu_item_use_case import CreateMenuItemDTO
from showcases.cafe.application.update_price_use_case import UpdatePriceDTO

def _get_body(data: Dict[str, Any]) -> Dict[str, Any]:
    # C6/C9.2 contract: data = {query, body, headers, path_params}
    # but also support direct dict for unit tests
    if "body" in data and isinstance(data["body"], dict):
        return data["body"]
    return data

def _get_path_params(data: Dict[str, Any]) -> Dict[str, Any]:
    return data.get("path_params", {}) if isinstance(data, dict) else {}

def create_menu_item_dto_factory(data: Dict[str, Any]) -> CreateMenuItemDTO:
    body = _get_body(data)
    # support both body-only and wrapped
    return CreateMenuItemDTO(
        name=body["name"],
        base_price=str(body["base_price"]),
        user_id=body["user_id"],
        user_role=body["user_role"],
    )

def update_price_dto_factory(data: Dict[str, Any]) -> UpdatePriceDTO:
    body = _get_body(data)
    path_params = _get_path_params(data)
    # merge: path_params + body + root fallback
    merged = {**body, **path_params}
    # also check root level for backward compat
    for k in ["item_id", "id", "new_price", "user_id", "user_role"]:
        if k not in merged and k in data:
            merged[k] = data[k]
    item_id = merged.get("item_id") or merged.get("id")
    return UpdatePriceDTO(
        item_id=str(item_id),
        new_price=str(merged["new_price"]),
        user_id=merged["user_id"],
        user_role=merged["user_role"],
    )
