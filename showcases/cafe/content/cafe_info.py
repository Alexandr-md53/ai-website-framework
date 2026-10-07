"""
Cafe v0.5 Product Slice - Business Domain
Consumer #1 : Café
Framework: NO dependency on business data, only engine

This file is ALLOWED to contain business domain:
- 150 MDL
- bakery
- menu prices
- about / SEO
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict

CAFE_IDENTITY = {
    "name": "Café Aurora",
    "tagline": {"ru": "Пекарня и кофе в Комрате", "en": "Bakery & Coffee in Comrat"},
    "city": "Comrat",
    "currency": "MDL",
}

ABOUT = {
    "ru": "Café Aurora — семейная пекарня в Комрате. Свежий хлеб, круассаны и кофе каждый день.",
    "en": "Café Aurora is a family bakery in Comrat. Fresh bread, croissants and coffee every day."
}

SEO_DEFAULT = {
    "title_ru": "Кафе Аврора Комрат — пекарня, меню, цены",
    "title_en": "Cafe Aurora Comrat - bakery, menu, prices",
    "description_ru": "Меню пекарни в Комрате, цены от 15 MDL, свежая выпечка, хлеб, кофе. Café Aurora.",
    "description_en": "Bakery menu in Comrat, prices from 15 MDL, fresh bakery, bread, coffee. Cafe Aurora.",
    "keywords": ["bakery", "cafe", "Comrat", "Komrat", "bread", "croissant", "MDL"]
}

@dataclass(frozen=True)
class MenuItem:
    id: str
    name_ru: str
    name_en: str
    price_mdl: int
    category: str
    description_ru: str
    description_en: str

MENU: List[MenuItem] = [
    MenuItem("bread_white", "Белый хлеб", "White bread", 25, "bakery", "Свежий белый хлеб", "Fresh white bread"),
    MenuItem("bread_rye", "Ржаной хлеб", "Rye bread", 28, "bakery", "Ржаной на закваске", "Sourdough rye"),
    MenuItem("croissant", "Круассан", "Croissant", 35, "bakery", "Слоистый круассан", "Buttery croissant"),
    MenuItem("croissant_choco", "Круассан с шоколадом", "Chocolate croissant", 40, "bakery", "С бельгийским шоколадом", "With Belgian chocolate"),
    MenuItem("baguette", "Багет", "Baguette", 22, "bakery", "Хрустящий багет", "Crunchy baguette"),
    MenuItem("cinnamon_roll", "Булочка с корицей", "Cinnamon roll", 38, "bakery", "С корицей и глазурью", "With cinnamon glaze"),
    MenuItem("espresso", "Эспрессо", "Espresso", 20, "coffee", "30мл", "30ml"),
    MenuItem("cappuccino", "Капучино", "Cappuccino", 45, "coffee", "200мл", "200ml"),
    MenuItem("latte", "Латте", "Latte", 50, "coffee", "250мл с молоком", "250ml with milk"),
    MenuItem("avg_check", "Средний чек", "Average check", 150, "meta", "150 MDL на человека", "150 MDL per person"),
]

def get_menu_by_category() -> Dict[str, List[MenuItem]]:
    out: Dict[str, List[MenuItem]] = {}
    for it in MENU:
        out.setdefault(it.category, []).append(it)
    return out

def get_seo_for_page(page: str, lang: str) -> Dict[str, str]:
    lang = "ru" if lang == "ru" else "en"
    if page == "index":
        return {"title": SEO_DEFAULT[f"title_{lang}"], "description": SEO_DEFAULT[f"description_{lang}"]}
    if page == "menu":
        return {"title": f"Меню {CAFE_IDENTITY['name']} - цены в MDL" if lang=="ru" else f"{CAFE_IDENTITY['name']} Menu - prices in MDL",
                "description": SEO_DEFAULT[f"description_{lang}"]}
    if page == "about":
        return {"title": f"О нас - {CAFE_IDENTITY['name']}" if lang=="ru" else f"About - {CAFE_IDENTITY['name']}",
                "description": ABOUT[lang]}
    return {"title": SEO_DEFAULT[f"title_{lang}"], "description": SEO_DEFAULT[f"description_{lang}"]}
