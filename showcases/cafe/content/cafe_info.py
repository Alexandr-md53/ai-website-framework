from dataclasses import dataclass
from typing import Optional, List, Dict
from collections import defaultdict


@dataclass
class MenuItem:
    slug: str
    name_ru: str
    name_ro: str
    name_en: str
    price_mdl: int
    category: str
    description_ru: str
    description_ro: str
    description_en: str
    category_ru: str = ""
    category_ro: str = ""
    category_en: str = ""
    image: Optional[str] = None

    def category_name(self, lang: str = "ru") -> str:
        lv = (lang or "ru").lower()
        if lv == "ro" and self.category_ro:
            return self.category_ro
        if lv == "en" and self.category_en:
            return self.category_en
        return self.category_ru or self.category_en or self.category_ro or self.category


# === STANDARD DEMO DATA — placeholder only ===
CAFE_IDENTITY = {
    "name": "Cafe Name",
    "city_ru": "City",
    "city_ro": "City",
    "city_en": "City",
    "tagline_ru": "Cafe Name — specialty coffee and breakfast",
    "tagline_ro": "Cafe Name — specialty coffee and breakfast",
    "tagline_en": "Cafe Name — specialty coffee and breakfast",
    "about_ru": "Cafe Name — demo cafe template. Placeholder content for standard demo.",
    "about_ro": "Cafe Name — template demo de cafenea. Continut demonstrativ standard.",
    "about_en": "Cafe Name — demo cafe template. Placeholder content for standard demo.",
}

CAFE_CONTACT = {
    "address_ru": "Street Address, City, Country",
    "address_ro": "Street Address, City, Country",
    "address_en": "Street Address, City, Country",
    "phone": "123 456 789",
    "email": "hello@example.com",
    "hours_ru": "Mon–Sun, 08:00–22:00",
    "hours_ro": "Mon–Sun, 08:00–22:00",
    "hours_en": "Mon–Sun, 08:00–22:00",
    "map_url": "https://www.example.com/maps",
}

MENU: List[MenuItem] = [
    MenuItem(
        "bread_white",
        "Белый хлеб",
        "Pâine albă",
        "White Bread",
        25,
        "bakery",
        "Домашний белый хлеб",
        "Pâine albă de casă",
        "Homemade white bread",
        "Выпечка",
        "Produse de panificație",
        "Bakery",
    ),
    MenuItem(
        "bread_rye",
        "Ржаной хлеб",
        "Pâine de secară",
        "Rye Bread",
        28,
        "bakery",
        "Ржаной хлеб на закваске",
        "Pâine de secară cu maia",
        "Rye sourdough bread",
        "Выпечка",
        "Produse de panificație",
        "Bakery",
    ),
    MenuItem(
        "croissant",
        "Круассан",
        "Croissant",
        "Croissant",
        35,
        "bakery",
        "Классический круассан",
        "Croissant clasic",
        "Classic croissant",
        "Выпечка",
        "Produse de panificație",
        "Bakery",
        "dishes/croissant.png",
    ),
    MenuItem(
        "croissant_choco",
        "Круассан с шоколадом",
        "Croissant cu ciocolată",
        "Chocolate Croissant",
        40,
        "bakery",
        "Круассан с шоколадом",
        "Croissant cu ciocolată",
        "Chocolate croissant",
        "Выпечка",
        "Produse de panificație",
        "Bakery",
    ),
    MenuItem(
        "baguette",
        "Багет",
        "Baghetă",
        "Baguette",
        30,
        "bakery",
        "Хрустящий багет",
        "Baghetă crocantă",
        "Crispy baguette",
        "Выпечка",
        "Produse de panificație",
        "Bakery",
    ),
    MenuItem(
        "cinnamon_roll",
        "Булочка с корицей",
        "Rulou cu scorțișoară",
        "Cinnamon Roll",
        32,
        "bakery",
        "Булочка с корицей",
        "Rulou cu scorțișoară",
        "Cinnamon roll",
        "Выпечка",
        "Produse de panificație",
        "Bakery",
    ),
    MenuItem(
        "espresso",
        "Эспрессо",
        "Espresso",
        "Espresso",
        30,
        "coffee",
        "30 мл, крепкий",
        "30 ml, tare",
        "30ml, strong",
        "Кофе",
        "Cafea",
        "Coffee",
    ),
    MenuItem(
        "cappuccino",
        "Капучино",
        "Cappuccino",
        "Cappuccino",
        45,
        "coffee",
        "200 мл, с молочной пенкой",
        "200 ml, cu spumă de lapte",
        "200ml, with milk foam",
        "Кофе",
        "Cafea",
        "Coffee",
        "dishes/cappuccino.png",
    ),
    MenuItem(
        "latte",
        "Латте",
        "Latte",
        "Latte",
        50,
        "coffee",
        "250 мл, мягкий",
        "250 ml, catifelat",
        "250ml, soft",
        "Кофе",
        "Cafea",
        "Coffee",
    ),
    MenuItem(
        "avg_check",
        "Средний чек",
        "Bon mediu",
        "Average Check",
        150,
        "meta",
        "Средний чек 150 MDL",
        "Bon mediu 150 MDL",
        "Average check 150 MDL",
        "Информация",
        "Informații",
        "Information",
    ),
]


def get_menu_by_category(lang: str = "ru") -> Dict[str, List[MenuItem]]:
    by_cat: Dict[str, List[MenuItem]] = defaultdict(list)
    for item in MENU:
        by_cat[item.category].append(item)
    return dict(by_cat)


def get_menu(lang: str = "ru"):
    return MENU


CATEGORY_NAMES = {
    "bakery": {"ru": "Выпечка", "ro": "Produse de panificație", "en": "Bakery"},
    "coffee": {"ru": "Кофе", "ro": "Cafea", "en": "Coffee"},
    "meta": {"ru": "Информация", "ro": "Informații", "en": "Information"},
}
