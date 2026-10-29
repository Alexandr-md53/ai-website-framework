"""
Cafe Image Service v0.2 — showcase-local, adapted from Nursery ImageService pattern
FROZEN Framework — no ai_framework changes
No Nursery import — pattern copied/adapted, terminology dish/menu

What copied/adapted from Nursery (services/image_service.py):
- uploads_root Path("static/uploads")
- allowed_extensions {jpg,jpeg,png,webp}
- secure_filename + uuid4().hex unique naming
- original_dir mkdir + uploaded_file.save(original_path)
- create_versions loop IMAGE_PRESETS[module]
- resize_image center crop no distortion + RGB + LANCZOS + quality 85 optimize
- delete_image iterates module_dir.iterdir() + unlink + guards filename None / module_dir not exists
- get_image_url f"/static/uploads/{module}/{version}/{filename}" + None guard
- _get_extension rsplit(".",1)[-1].lower()

What adapted:
- module = "menu" (not "plants"/"categories") — isolation Café vs Nursery
- presets = {"menu": {"catalog": 500x350, "detail": 1000x700}} — ADAPTABLE, same dimensions justified: dish grid same landscape as plant catalog
- terminology: dish/menu not plant/nursery
- uploads_root configurable via __init__ for test isolation
- added malformed file handling: try/except around create_versions, cleanup original on failure
- original preserved + catalog + detail variants

What NOT copied: Nursery models, routes, templates, business logic
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional
from uuid import uuid4

from PIL import Image
from werkzeug.utils import secure_filename


# Café presets — showcase-local, ADAPTABLE from Nursery
# Nursery: plants catalog 500x350 detail 1000x700 categories catalog 350x350
# Café: menu catalog 500x350 detail 1000x700 — reason: dish grid landscape same as plant catalog, suitable for menu listing
# No blind copy of "plants"/"categories" keys — use "menu" module
CAFE_IMAGE_PRESETS: Dict[str, Dict[str, Dict[str, int]]] = {
    "menu": {
        "catalog": {"width": 500, "height": 350},
        "detail": {"width": 1000, "height": 700},
    }
}


class CafeImageService:
    def __init__(self, uploads_root: Path | str | None = None) -> None:
        self.uploads_root = Path(uploads_root) if uploads_root else Path("static/uploads")
        self.allowed_extensions = {"jpg", "jpeg", "png", "webp"}
        self.presets = CAFE_IMAGE_PRESETS

    def save_image(self, uploaded_file, module: str = "menu") -> Optional[str]:
        """
        Save uploaded dish image and create configured variants.
        Returns saved unique filename or None if no file.
        Raises ValueError for unsupported extension.
        Raises ValueError for malformed image (with cleanup).
        """
        if not uploaded_file or getattr(uploaded_file, "filename", "") == "":
            return None

        extension = self._get_extension(uploaded_file.filename)
        if extension not in self.allowed_extensions:
            raise ValueError("Unsupported image format")

        safe_name = secure_filename(uploaded_file.filename)
        unique_filename = f"{uuid4().hex}_{safe_name}"

        original_dir = self.uploads_root / module / "original"
        original_dir.mkdir(parents=True, exist_ok=True)

        original_path = original_dir / unique_filename
        uploaded_file.save(str(original_path))

        # Try to create variants — if fails (malformed), cleanup original and raise
        try:
            self.create_versions(unique_filename, module)
        except Exception as e:
            # cleanup original to avoid orphan on malformed
            if original_path.exists():
                original_path.unlink()
            # also cleanup any partial variants
            self.delete_image(unique_filename, module)
            raise ValueError(f"Invalid image file: {e}") from e

        return unique_filename

    def create_versions(self, filename: str, module: str = "menu") -> None:
        """
        Create all image versions defined in CAFE_IMAGE_PRESETS.
        """
        if module not in self.presets:
            return

        original_path = self.uploads_root / module / "original" / filename
        if not original_path.exists():
            return

        for version, settings in self.presets[module].items():
            version_dir = self.uploads_root / module / version
            version_dir.mkdir(parents=True, exist_ok=True)

            destination_path = version_dir / filename
            self.resize_image(
                source_path=original_path,
                destination_path=destination_path,
                width=settings["width"],
                height=settings["height"],
            )

    def resize_image(self, source_path: Path, destination_path: Path, width: int, height: int) -> None:
        """
        Resize image without distortion, crops center if proportions differ.
        """
        with Image.open(source_path) as image:
            image = image.convert("RGB")

            source_ratio = image.width / image.height
            target_ratio = width / height

            if source_ratio > target_ratio:
                new_height = image.height
                new_width = int(new_height * target_ratio)
                left = (image.width - new_width) // 2
                top = 0
                right = left + new_width
                bottom = image.height
            else:
                new_width = image.width
                new_height = int(new_width / target_ratio)
                left = 0
                top = (image.height - new_height) // 2
                right = image.width
                bottom = top + new_height

            image = image.crop((left, top, right, bottom))
            image = image.resize((width, height), Image.LANCZOS)

            destination_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(destination_path, quality=85, optimize=True)

    def delete_image(self, filename: Optional[str], module: str = "menu") -> None:
        """
        Delete original and all generated versions.
        """
        if not filename:
            return

        module_dir = self.uploads_root / module
        if not module_dir.exists():
            return

        for version_dir in module_dir.iterdir():
            if not version_dir.is_dir():
                continue
            image_path = version_dir / filename
            if image_path.exists():
                image_path.unlink()

    def get_image_url(self, module: str, filename: Optional[str], version: str = "catalog") -> Optional[str]:
        """
        Return URL for browser. Returns None if no filename.
        """
        if not filename:
            return None
        return f"/static/uploads/{module}/{version}/{filename}"

    def _get_extension(self, filename: str) -> str:
        return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


# singleton for app usage (like Nursery image_service = ImageService())
cafe_image_service = CafeImageService()
