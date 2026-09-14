# coding: utf-8, ASCII only
from typing import Dict, Any
from showcases.plant_nursery.application.use_cases import (
    AddPlantDTO,
    FrostFilterDTO,
    QuoteDTO,
    CreateCategoryDTO,
    MoveCategoryDTO,
    ListPlantsByCategoryDTO,
    AddPlantImageDTO,
    GetPlantImagesDTO,
    RemovePlantImageDTO,
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


def _get_path_params(data: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return {}
    pp = data.get("path_params")
    if isinstance(pp, dict):
        return pp
    return {}


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


def move_category_dto_factory(data: Dict[str, Any]) -> MoveCategoryDTO:
    body = _get_body(data)
    path = _get_path_params(data)
    cat_id = path.get("id") or body.get("id") or data.get("id")
    if "parent_id" in body:
        parent_id = body.get("parent_id")
    else:
        parent_id = data.get("parent_id")
    return MoveCategoryDTO(
        id=str(cat_id) if cat_id else None,
        parent_id=parent_id,
    )


def list_plants_by_category_dto_factory(
    data: Dict[str, Any],
) -> ListPlantsByCategoryDTO:
    path = _get_path_params(data)
    query = _get_query(data)
    body = _get_body(data)

    cat_id = path.get("id") or body.get("id") or query.get("id") or data.get("id")

    raw = None
    if "include_descendants" in query:
        raw = query.get("include_descendants")
    elif "include_descendants" in body:
        raw = body.get("include_descendants")
    elif "include_descendants" in data:
        raw = data.get("include_descendants")

    include = False
    if isinstance(raw, bool):
        include = raw
    elif isinstance(raw, str):
        include = raw.lower() in ("true", "1", "yes", "on")
    elif raw is not None:
        include = bool(raw)

    return ListPlantsByCategoryDTO(
        id=str(cat_id) if cat_id else None,
        include_descendants=include,
    )


def add_plant_image_dto_factory(data: Dict[str, Any]) -> AddPlantImageDTO:
    body = _get_body(data)
    path = _get_path_params(data)
    query = _get_query(data)

    plant_id = path.get("id") or body.get("id") or query.get("id") or data.get("id")
    image_id = body.get("image_id") or query.get("image_id") or data.get("image_id")

    return AddPlantImageDTO(
        id=str(plant_id) if plant_id else None,
        image_id=str(image_id) if image_id else None,
    )


def get_plant_images_dto_factory(data: Dict[str, Any]) -> GetPlantImagesDTO:
    path = _get_path_params(data)
    query = _get_query(data)
    body = _get_body(data)

    plant_id = path.get("id") or body.get("id") or query.get("id") or data.get("id")

    return GetPlantImagesDTO(
        id=str(plant_id) if plant_id else None,
    )


def remove_plant_image_dto_factory(data: Dict[str, Any]) -> RemovePlantImageDTO:
    path = _get_path_params(data)
    query = _get_query(data)
    body = _get_body(data)

    # Support both {id, image_id} and {plant_id, image_id} naming
    plant_id = (
        path.get("id")
        or path.get("plant_id")
        or body.get("id")
        or body.get("plant_id")
        or query.get("id")
        or query.get("plant_id")
        or data.get("id")
        or data.get("plant_id")
    )
    image_id = (
        path.get("image_id")
        or path.get("imageId")
        or body.get("image_id")
        or query.get("image_id")
        or data.get("image_id")
    )

    return RemovePlantImageDTO(
        id=str(plant_id) if plant_id else None,
        image_id=str(image_id) if image_id else None,
    )
