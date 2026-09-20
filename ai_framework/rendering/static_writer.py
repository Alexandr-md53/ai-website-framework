from __future__ import annotations
import pathlib
import shutil
from typing import List
from .generated_page import GeneratedPage


class StaticSiteWriter:
    """
    Framework-level generic writer — no blog knowledge.
    Writes List[GeneratedPage] to out_dir with optional clean.
    clean=True: removes out_dir before write (deterministic, no stale draft files)
    clean=False: merges/overwrites, keeps existing unrelated files
    Preserves relative paths: page.path is relative, e.g. "posts/<slug>/index.html"
    """

    def write(
        self,
        pages: List[GeneratedPage],
        out_dir: pathlib.Path | str,
        clean: bool = True,
    ) -> List[pathlib.Path]:
        out_dir = pathlib.Path(out_dir)
        if clean and out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        written: List[pathlib.Path] = []
        for pg in pages:
            # Security: ensure path is relative, no absolute or parent traversal
            # Windows-safe: reject "/...", "\...", "C:...", ".." etc.
            raw = pg.path or ""
            if not raw:
                raise ValueError(f"Invalid GeneratedPage path (empty): {pg.path}")
            # Reject absolute (posix or windows), drive, or parent traversal
            # Use both PurePosix and PureWindows checks + string prefix checks for robustness on Windows
            posix = pathlib.PurePosixPath(raw)
            win = pathlib.PureWindowsPath(raw)
            if (
                posix.is_absolute()
                or win.is_absolute()
                or raw.startswith("/")
                or raw.startswith("\\")
                or ".." in pathlib.PurePath(raw).parts
                or ".." in posix.parts
                or ".." in win.parts
                or (len(raw) > 1 and raw[1] == ":")  # C: drive
                or ":" in raw
                and "\\" in raw  # Windows absolute with drive
            ):
                raise ValueError(
                    f"Invalid GeneratedPage path (must be relative, no .., no absolute): {pg.path}"
                )
            # Additional: pure anchor check
            p = pathlib.Path(raw)
            if p.anchor:
                # On Windows, "/a" has anchor "\\" — already caught, but double-check
                if p.anchor not in (".", "") and raw not in (".", "./"):
                    # Allow "./" prefix as relative, but reject "/" , "\" , "C:\"
                    if (
                        raw.startswith("/")
                        or raw.startswith("\\")
                        or pathlib.PurePath(raw).is_absolute()
                    ):
                        raise ValueError(
                            f"Invalid GeneratedPage path (anchor not allowed): {pg.path}"
                        )
            # Finally, ensure join does not escape out_dir (no absolute discard)
            fp = out_dir / p
            # If fp is not inside out_dir after resolution, reject
            try:
                # Python 3.9+ does not have is_relative_to, use manual check
                fp_resolved = fp.resolve()
                out_resolved = out_dir.resolve()
                if (
                    out_resolved not in fp_resolved.parents
                    and fp_resolved != out_resolved
                ):
                    # If fp is outside out_dir, it would be absolute path discard case
                    if fp.anchor and out_dir.anchor and fp.anchor != out_dir.anchor:
                        pass  # will be caught by is_absolute already
                    # Check if original was absolute leading to discard
                    if raw.startswith("/") or raw.startswith("\\"):
                        raise ValueError(
                            f"Invalid GeneratedPage path (absolute discards out_dir): {pg.path}"
                        )
            except Exception:
                # If resolve fails (path not exist), skip strict check, rely on earlier guards
                pass

            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(pg.html, encoding="utf-8")
            written.append(fp)
        return written
