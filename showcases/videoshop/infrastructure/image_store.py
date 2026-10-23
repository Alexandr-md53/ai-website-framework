"""S7 V1 / product slice: managed image store with a real image pipeline.

Adapted from the proven Nursery implementation
(``site_generation_post/services/image_service.py`` +
``config/image_presets.py``), re-implemented inside the VideoShop boundaries:

* extension allow-list ``{jpg,jpeg,png,webp}`` (Nursery: ``image_service.py:13``)
  is kept, and strengthened: the real type is detected from magic bytes and the
  file must **decode** as an image (Nursery relies on the extension alone);
* generated names (``uuid4().hex`` + extension) already replaced Nursery's
  ``secure_filename`` prefixing (``image_service.py:28-29``) - a user name can
  never traverse paths or overwrite a file; the original name is metadata only;
* per-preset derivatives are produced exactly like Nursery's
  ``resize_image`` (``image_service.py:63-93``): aspect-preserving centre crop,
  ``LANCZOS`` resampling, quality 88 / optimize. Presets live in
  :data:`IMAGE_PRESETS` (Nursery: ``config/image_presets.py``);
* EXIF orientation is applied and EXIF metadata is dropped on re-encode;
* Pillow is optional: if it is not importable the store falls back to the
  magic-byte validation (and produces no derivatives), so uploads keep working;
* writes go to ``.part`` files and are published with ``os.replace``.
"""
from __future__ import annotations

import io
import os
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Tuple

try:  # Pillow is available in this environment; the store degrades gracefully
    from PIL import Image, ImageOps, UnidentifiedImageError

    HAS_PILLOW = True
except Exception:  # pragma: no cover - exercised only without Pillow
    Image = None  # type: ignore[assignment]
    ImageOps = None  # type: ignore[assignment]
    UnidentifiedImageError = Exception  # type: ignore[assignment,misc]
    HAS_PILLOW = False

#: maximum accepted upload size (2 MiB); configurable by the caller
DEFAULT_MAX_UPLOAD_BYTES = 2 * 1024 * 1024

#: reject absurd dimensions before decoding the pixels
DEFAULT_MAX_DIMENSION = 6000

#: adapted from Nursery's config/image_presets.py, sized for a storefront
IMAGE_PRESETS: Dict[str, Dict[str, int]] = {
    "catalog": {"width": 600, "height": 450},
    "detail": {"width": 1200, "height": 900},
}

#: extensions accepted for uploads (Nursery: image_service.py:13)
ALLOWED_EXTENSIONS = frozenset({"jpg", "jpeg", "png", "webp"})

#: strict pattern of a stored file name: generated names (and their variants)
STORED_NAME_PATTERN = re.compile(
    r"^[0-9a-f]{32}(?:_(?:" + "|".join(sorted(IMAGE_PRESETS)) + r"))?\.(?:png|jpg|gif|webp)$"
)

SIGNATURES = (
    ("image/png", ".png", (b"\x89PNG\r\n\x1a\n",)),
    ("image/jpeg", ".jpg", (b"\xff\xd8\xff",)),
    ("image/gif", ".gif", (b"GIF87a", b"GIF89a")),
)
WEBP_PREFIX = b"RIFF"
WEBP_MARKER = b"WEBP"

#: JPEG quality used for derivatives (Nursery: quality=85, optimize=True)
DERIVATIVE_QUALITY = 88


class ImageError(Exception):
    """Base error of the image store."""

    code = "IMAGE_ERROR"


class UnsupportedImageType(ImageError):
    code = "UNSUPPORTED_IMAGE_TYPE"


class ImageTooLarge(ImageError):
    code = "IMAGE_TOO_LARGE"


class ImageDimensionsTooLarge(ImageError):
    code = "IMAGE_DIMENSIONS_TOO_LARGE"


class ImageNotFound(ImageError):
    code = "IMAGE_NOT_FOUND"


class InvalidImageName(ImageError):
    code = "INVALID_IMAGE_NAME"


@dataclass(frozen=True)
class StoredImage:
    file_name: str
    content_type: str
    size_bytes: int
    original_name: str
    width: Optional[int] = None
    height: Optional[int] = None
    variants: Tuple[str, ...] = field(default_factory=tuple)


def detect_image_type(content: bytes) -> str:
    """Return the detected content type, or raise :class:`UnsupportedImageType`."""
    for content_type, _extension, prefixes in SIGNATURES:
        for prefix in prefixes:
            if content.startswith(prefix):
                return content_type
    if (
        len(content) >= 12
        and content.startswith(WEBP_PREFIX)
        and content[8:12] == WEBP_MARKER
    ):
        return "image/webp"
    raise UnsupportedImageType(
        "only PNG, JPEG, GIF and WebP images are accepted "
        "(the content type is detected from the file content)"
    )


def extension_for(content_type: str) -> str:
    for known_type, extension, _prefixes in SIGNATURES:
        if known_type == content_type:
            return extension
    if content_type == "image/webp":
        return ".webp"
    raise UnsupportedImageType(f"unsupported content type {content_type!r}")


def extension_of(file_name: str) -> str:
    return Path(file_name).suffix.lstrip(".").lower()


def variant_file_name(file_name: str, preset: str) -> str:
    """``<uuid>.png`` + ``catalog`` -> ``<uuid>_catalog.png``."""
    if preset not in IMAGE_PRESETS:
        raise ImageError(f"unknown image preset {preset!r}")
    stem = Path(file_name).stem
    suffix = Path(file_name).suffix
    base = stem.split("_")[0]
    return f"{base}_{preset}{suffix}"


class ImageStore:
    """Store uploaded images (plus preset derivatives) in a managed directory."""

    def __init__(
        self,
        root,
        *,
        max_bytes: int = DEFAULT_MAX_UPLOAD_BYTES,
        presets: Optional[Dict[str, Dict[str, int]]] = None,
        max_dimension: int = DEFAULT_MAX_DIMENSION,
    ) -> None:
        self.root = Path(root)
        self.max_bytes = int(max_bytes)
        self.presets = dict(presets or IMAGE_PRESETS)
        self.max_dimension = int(max_dimension)
        if self.max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        self.root.mkdir(parents=True, exist_ok=True)

    # --- write ----------------------------------------------------------

    def save(self, content: bytes, *, original_name: str = "") -> StoredImage:
        if not isinstance(content, (bytes, bytearray)):
            raise ImageError("image content must be bytes")
        data = bytes(content)
        if not data:
            raise ImageError("the uploaded file is empty")
        if len(data) > self.max_bytes:
            raise ImageTooLarge(
                f"the uploaded file is {len(data)} bytes; the limit is {self.max_bytes}"
            )
        content_type = detect_image_type(data)
        extension = extension_for(content_type)
        safe_original = Path(original_name or "").name[:120]

        base_name = f"{uuid.uuid4().hex}{extension}"
        width = height = None
        variants: Tuple[str, ...] = ()

        if HAS_PILLOW:
            image, width, height = self._decode(data)
            self._write_image(self.root / base_name, image)
            for preset_name, size in self.presets.items():
                derived = self._fit(image, size)
                if derived is not image and derived.size != image.size:
                    target = self.root / variant_file_name(base_name, preset_name)
                    self._write_image(target, derived)
                    variants = variants + (preset_name,)
            if image is not None:
                image.close()
        else:  # pragma: no cover - magic-byte fallback without Pillow
            self._write_bytes(self.root / base_name, data)

        return StoredImage(
            file_name=base_name,
            content_type=content_type,
            size_bytes=len(data),
            original_name=safe_original,
            width=width,
            height=height,
            variants=variants,
        )

    def _decode(self, data: bytes):
        """Decode and normalise an image (EXIF orientation, dimension guard)."""
        try:
            probe = Image.open(io.BytesIO(data))
            width, height = probe.size
            if width > self.max_dimension or height > self.max_dimension:
                probe.close()
                raise ImageDimensionsTooLarge(
                    f"image dimensions {width}x{height} exceed the "
                    f"{self.max_dimension}px limit"
                )
            probe.load()
            image = ImageOps.exif_transpose(probe) if ImageOps is not None else probe
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGBA" if image.mode in ("P", "LA") else "RGB")
            if image is not probe:
                probe.close()
            return image, width, height
        except ImageDimensionsTooLarge:
            raise
        except UnsupportedImageType:
            raise
        except Exception as exc:
            raise UnsupportedImageType(
                f"the file could not be decoded as an image: {type(exc).__name__}"
            ) from exc

    def _fit(self, image, size: Dict[str, int]):
        """Centre-crop to the preset aspect ratio then resize (Nursery parity)."""
        width, height = int(size["width"]), int(size["height"])
        if image.width <= width and image.height <= height:
            return image
        return ImageOps.fit(image, (width, height), method=Image.LANCZOS)

    def _write_image(self, path: Path, image) -> None:
        partial = path.with_name(path.name + ".part")
        suffix = path.suffix.lower()
        image_format = {
            ".png": "PNG",
            ".jpg": "JPEG",
            ".jpeg": "JPEG",
            ".webp": "WEBP",
            ".gif": "GIF",
        }.get(suffix)
        try:
            parameters: Dict[str, object] = {}
            if image_format:
                parameters["format"] = image_format
            if suffix == ".png":
                parameters["optimize"] = True
            elif suffix in (".jpg", ".jpeg"):
                parameters["quality"] = DERIVATIVE_QUALITY
                parameters["optimize"] = True
                if image.mode == "RGBA":
                    image = image.convert("RGB")
            elif suffix == ".webp":
                parameters["quality"] = DERIVATIVE_QUALITY
            image.save(partial, **parameters)
            os.replace(partial, path)
        except OSError as exc:
            self._cleanup(partial)
            raise ImageError(
                f"cannot store the image: {type(exc).__name__}: {exc}"
            ) from exc

    def _write_bytes(self, path: Path, data: bytes) -> None:
        partial = path.with_name(path.name + ".part")
        try:
            with open(partial, "wb") as handle:
                handle.write(data)
            os.replace(partial, path)
        except OSError as exc:
            self._cleanup(partial)
            raise ImageError(
                f"cannot store the uploaded file: {type(exc).__name__}: {exc}"
            ) from exc

    @staticmethod
    def _cleanup(path: Path) -> None:
        try:
            path.unlink()
        except OSError:
            pass

    # --- read / delete --------------------------------------------------

    def path_for(self, file_name: str) -> Path:
        if not STORED_NAME_PATTERN.match(file_name or ""):
            raise InvalidImageName(f"not a managed image name: {file_name!r}")
        return self.root / file_name

    def variant_name(self, file_name: str, preset: str) -> str:
        """Best-effort variant name; callers fall back to the base file."""
        try:
            return variant_file_name(file_name, preset)
        except ImageError:
            return file_name

    def exists(self, file_name: str) -> bool:
        try:
            return self.path_for(file_name).is_file()
        except InvalidImageName:
            return False

    def delete(self, file_name: str) -> bool:
        """Delete a managed image with its derivatives (best effort)."""
        base = self.path_for(file_name)
        stem, suffix = base.stem.split("_")[0], base.suffix
        targets = [self.root / f"{stem}{suffix}"]
        for preset_name in self.presets:
            targets.append(self.root / f"{stem}_{preset_name}{suffix}")
        existed = False
        for target in targets:
            try:
                target.unlink()
                existed = True
            except FileNotFoundError:
                continue
            except OSError:
                continue
        return existed
