# coding: utf-8, ASCII only
from typing import Dict, Any
from showcases.plant_nursery.application.use_cases import (
    AddPlantDTO,
    FrostFilterDTO,
    QuoteDTO,
    CreateCategoryDTO,
)


def _get_body(data: Dict[str, Any]) -> Dict[str, Any]:
    if "body" in data and isinstance(data["body"], dict):
        return data["body"]
    return data if isinstance(data, dict) else {}


def _get_query(data: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return {}
    q = data.get("query")
    if isinstance(q, dict):
        return q
    return data


def add_plant_dto_factory(data: Dict[str, Any]) -> AddPlantDTO:
    body = _get_body(data)
    return AddPlantDTO(
        category_id=str(body.get("category_id")),
        name=body.get("name"),
        description=body.get("description"),
        light_req=body.get("light_req", "MEDIUM"),
        water_req=body.get("water_req", "MODERATE"),
        frost_resistance=int(body.get("frost_resistance", 0) or 0),
        main_image_id=body.get("main_image_id"),
    )


def frost_filter_dto_factory(data: Dict[str, Any]) -> FrostFilterDTO:
    query = _get_query(data)
    body = _get_body(data)
    min_temp_raw = query.get("min_temp")
    if min_temp_raw is None:
        min_temp_raw = body.get("min_temp")
    if min_temp_raw is None:
        min_temp_raw = data.get("min_temp")
    if min_temp_raw is None:
        min_temp_raw = -100
    return FrostFilterDTO(min_temp=int(min_temp_raw))


def quote_dto_factory(data: Dict[str, Any]) -> QuoteDTO:
    body = _get_body(data)
    return QuoteDTO(
        unit_price=str(body.get("unit_price")),
        quantity=int(body.get("quantity", 0) or 0),
        discount_policy=str(body.get("discount_policy", "NONE")),
    )


def create_category_dto_factory(data: Dict[str, Any]) -> CreateCategoryDTO:
    body = _get_body(data)
    return CreateCategoryDTO(
        name=body.get("name"),
        slug=body.get("slug"),
        parent_id=body.get("parent_id"),
        id=body.get("id"),
    )
