from __future__ import annotations
import pathlib
import shutil
from typing import List
from .generated_page import GeneratedPage


class StaticSiteWriter:
    """
    Framework-level generic writer — no domain knowledge.
    Writes List[GeneratedPage] to out_dir with optional clean.
    clean=True: removes out_dir before write (deterministic, no stale files)
    clean=False: merges/overwrites, keeps existing unrelated files
    Preserves relative paths: page.path is relative, e.g. "section/page/index.html"
    Fail-fast on duplicate paths and FS safety violations.
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

        # Fail-fast duplicate detection (Phase 7.2)
        seen = set()
        for pg in pages:
            norm = (pg.path or "").strip()
            if not norm:
                raise ValueError(f"Invalid GeneratedPage path (empty): {pg.path}")
            if norm in seen:
                raise ValueError(f"Duplicate GeneratedPage path: {pg.path}")
            seen.add(norm)

        written: List[pathlib.Path] = []
        for pg in pages:
            raw = pg.path or ""
            if not raw:
                raise ValueError(f"Invalid GeneratedPage path (empty): {pg.path}")
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
                or (len(raw) > 1 and raw[1] == ":")
                or ":" in raw
                and "\\" in raw
            ):
                raise ValueError(
                    f"Invalid GeneratedPage path (must be relative, no .., no absolute): {pg.path}"
                )
            p = pathlib.Path(raw)
            if p.anchor:
                if p.anchor not in (".", "") and raw not in (".", "./"):
                    if (
                        raw.startswith("/")
                        or raw.startswith("\\")
                        or pathlib.PurePath(raw).is_absolute()
                    ):
                        raise ValueError(
                            f"Invalid GeneratedPage path (anchor not allowed): {pg.path}"
                        )
            fp = out_dir / p
            try:
                fp_resolved = fp.resolve()
                out_resolved = out_dir.resolve()
                if (
                    out_resolved not in fp_resolved.parents
                    and fp_resolved != out_resolved
                ):
                    if raw.startswith("/") or raw.startswith("\\"):
                        raise ValueError(
                            f"Invalid GeneratedPage path (absolute discards out_dir): {pg.path}"
                        )
            except Exception:
                pass

            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(pg.html, encoding="utf-8")
            written.append(fp)
        return written
