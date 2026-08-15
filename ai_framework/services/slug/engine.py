"""
Default Transliteration Engine implementation (ADR-001, ADR-002).
"""

import unicodedata
from typing import Optional


class DefaultTransliterationEngine:
    GERMAN_MAP = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
        "Ä": "Ae",
        "Ö": "Oe",
        "Ü": "Ue",
    }

    UKRAINIAN_MAP = {
        "и": "y",
        "і": "i",
        "ї": "yi",
        "ґ": "g",
        "И": "Y",
        "І": "I",
        "Ї": "Yi",
        "Ґ": "G",
    }

    CYRILLIC_MAP = {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "yo",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "y",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "kh",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "shch",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "yu",
        "я": "ya",
        "А": "A",
        "Б": "B",
        "В": "V",
        "Г": "G",
        "Д": "D",
        "Е": "E",
        "Ё": "Yo",
        "Ж": "Zh",
        "З": "Z",
        "И": "I",
        "Й": "Y",
        "К": "K",
        "Л": "L",
        "М": "M",
        "Н": "N",
        "О": "O",
        "П": "P",
        "Р": "R",
        "С": "S",
        "Т": "T",
        "У": "U",
        "Ф": "F",
        "Х": "Kh",
        "Ц": "Ts",
        "Ч": "Ch",
        "Ш": "Sh",
        "Щ": "Shch",
        "Ъ": "",
        "Ы": "Y",
        "Ь": "",
        "Э": "E",
        "Ю": "Yu",
        "Я": "Ya",
    }

    def transliterate(self, text: str, locale: Optional[str] = None) -> str:
        if not text:
            return ""

        result = text

        # 1. Locale-specific transformations
        if locale == "de":
            for char, repl in self.GERMAN_MAP.items():
                result = result.replace(char, repl)
        elif locale == "uk":
            for char, repl in self.UKRAINIAN_MAP.items():
                result = result.replace(char, repl)

        # 2. Cyrillic transliteration
        chars = []
        for char in result:
            chars.append(self.CYRILLIC_MAP.get(char, char))
        result = "".join(chars)

        # 3. Unicode diacritics stripping (Latin accents: Café -> Cafe)
        nfd_form = unicodedata.normalize("NFD", result)
        result = "".join(c for c in nfd_form if unicodedata.category(c) != "Mn")

        return result
