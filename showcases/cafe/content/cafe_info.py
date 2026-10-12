from dataclasses import dataclass
from typing import Optional, List, Dict
from collections import defaultdict


@dataclass
class MenuItem:
    slug: str
    name_ru: str
    name_en: str
    price_mdl: int
    category: str
    description_ru: str
    description_en: str
    image: Optional[str] = None


CAFE_IDENTITY = {
    "name": "Café Aurora",
    "city_ru": "Кишинев",
    "city_en": "Chisinau",
    "tagline_ru": "Кофе и свежая выпечка",
    "tagline_en": "Coffee and fresh bakery",
    "about_ru": "Уютное кафе в центре Кишинева. Семейная пекарня. Готовим на месте каждый день.",
    "about_en": "Cozy cafe in the center of Chisinau. Family bakery. Freshly baked every day.",
}

# v0.8 — REAL CONTACTS from project owner
CAFE_CONTACT = {
    "address_ru": "ул. Штефан Чел Маре 64, Кишинев, Молдова",
    "address_en": "64 Stefan cel Mare St., Chisinau, Moldova",
    "phone": "+373 79 68 73 82",
    "hours_ru": "08:00–22:00, пн–вс",
    "hours_en": "08:00–22:00, Mon–Sun",
    "map_url": "https://www.google.com/maps/search/?api=1&query=Stefan+cel+Mare+64+Chisinau+Moldova",
}

MENU: List[MenuItem] = [
    MenuItem(
        "bread_white",
        "Хлеб белый",
        "White Bread",
        25,
        "bakery",
        "Домашний белый хлеб",
        "Homemade white bread",
    ),
    MenuItem(
        "bread_rye",
        "Хлеб ржаной",
        "Rye Bread",
        28,
        "bakery",
        "Ржаной хлеб на закваске",
        "Rye sourdough bread",
    ),
    MenuItem(
        "croissant",
        "Круассан",
        "Croissant",
        35,
        "bakery",
        "Классический круассан",
        "Classic croissant",
        "dishes/croissant.png",
    ),
    MenuItem(
        "croissant_choco",
        "Круассан с шоколадом",
        "Chocolate Croissant",
        40,
        "bakery",
        "Круассан с шоколадом",
        "Chocolate croissant",
    ),
    MenuItem(
        "baguette",
        "Багет",
        "Baguette",
        30,
        "bakery",
        "Хрустящий багет",
        "Crispy baguette",
    ),
    MenuItem(
        "cinnamon_roll",
        "Булочка с корицей",
        "Cinnamon Roll",
        32,
        "bakery",
        "Булочка с корицей",
        "Cinnamon roll",
    ),
    MenuItem(
        "espresso",
        "Эспрессо",
        "Espresso",
        30,
        "coffee",
        "30 мл, крепкий",
        "30ml, strong",
    ),
    MenuItem(
        "cappuccino",
        "Капучино",
        "Cappuccino",
        45,
        "coffee",
        "200 мл, с молочной пенкой",
        "200ml, with milk foam",
        "dishes/cappuccino.png",
    ),
    MenuItem("latte", "Латте", "Latte", 50, "coffee", "250 мл, мягкий", "250ml, soft"),
    MenuItem(
        "avg_check",
        "Средний чек",
        "Average Check",
        150,
        "meta",
        "Средний чек 150 MDL",
        "Average check 150 MDL",
    ),
]


def get_menu_by_category(lang: str = "ru") -> Dict[str, List[MenuItem]]:
    by_cat: Dict[str, List[MenuItem]] = defaultdict(list)
    for item in MENU:
        by_cat[item.category].append(item)
    return dict(by_cat)


def get_menu(lang: str = "ru"):
    return MENU
