"""Media optimisation for the storefront (portfolio photos).

Converts the owner's portfolio originals into WebP for the home page:

* width is capped at :data:`MAX_WIDTH` (800 px), height follows the aspect;
* WebP quality :data:`QUALITY` (80);
* originals stay untouched in ``data/images/portfolio`` and are never modified;
* the derived files land in ``web/static/media/portfolio`` and are served at
  ``/media/portfolio/<name>.webp``.

Run from the repository root::

    python -B showcases/videoshop/tools/optimize_media.py
"""
from __future__ import annotations

from pathlib import Path
from typing import Tuple

from PIL import Image

#: showcases/videoshop/tools -> videoshop -> showcases -> repository root
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SOURCE_DIR = REPOSITORY_ROOT / "data" / "images" / "portfolio"
TARGET_DIR = Path(__file__).resolve().parents[1] / "web" / "static" / "media" / "portfolio"

MAX_WIDTH = 800
MAX_HEIGHT = 900
QUALITY = 80
#: display order on the home page (city, bloom, street, window)
PROJECTS: Tuple[str, ...] = ("portfolio-city", "portfolio-bloom", "portfolio-street", "portfolio-window")
SOURCES = (".jpeg", ".jpg", ".png", ".webp")


def source_for(stem: str) -> Path:
    for suffix in SOURCES:
        candidate = SOURCE_DIR / f"{stem}{suffix}"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"portfolio photo not found for {stem!r} in {SOURCE_DIR}")


def convert(stem: str) -> dict:
    source = source_for(stem)
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    target = TARGET_DIR / f"{stem}.webp"
    with Image.open(source) as image:
        image = image.convert("RGB")
        original = image.size
        # two-dimensional cap: a portrait original is bounded by its height
        scale = min(MAX_WIDTH / image.width, MAX_HEIGHT / image.height, 1.0)
        if scale < 1.0:
            image = image.resize(
                (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
                Image.LANCZOS,
            )
        image.save(target, "WEBP", quality=QUALITY, method=6)
        size = image.size
    return {
        "stem": stem,
        "source": str(source),
        "target": str(target),
        "original_size": original,
        "size": size,
        "source_bytes": source.stat().st_size,
        "target_bytes": target.stat().st_size,
    }


def main() -> int:
    if not SOURCE_DIR.is_dir():
        print(f"source directory is missing: {SOURCE_DIR}")
        return 1
    for stem in PROJECTS:
        info = convert(stem)
        print(
            f"{info['stem']:<18} {info['original_size'][0]}x{info['original_size'][1]}"
            f" -> {info['size'][0]}x{info['size'][1]}  "
            f"{info['source_bytes'] // 1024} KB -> {info['target_bytes'] // 1024} KB"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
