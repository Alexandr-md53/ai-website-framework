from ai_framework.api.registry import list_products, get_product, clear_cache


def test_enrichment_from_pyproject():
    clear_cache()
    products = list_products()
    assert len(products) >= 3
    for p in products:
        if p.name in {"cafe", "lawyer", "plant_nursery"}:
            # enrichment optional but pyproject exists
            assert p.pyproject_version is not None
            # name in pyproject is like cafe-crud
            assert p.pyproject_name is not None
            assert "crud" in p.pyproject_name


def test_cache_hit():
    clear_cache()
    p1 = get_product("cafe")
    p2 = get_product("cafe")
    assert p1 is not None
    assert p1 is p2  # lru_cache returns same object
    # list_products also cached
    l1 = list_products()
    l2 = list_products()
    assert l1 is l2
