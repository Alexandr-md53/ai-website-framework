from __future__ import annotations
from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True, slots=True)
class SeoContext:
    """
    Framework-level generic SEO context — no domain knowledge about posts or taxonomies.
    Explicit empty handling: empty strings mean "do not render that tag" except seo_title which is required fallback.
    """

    seo_title: str
    seo_description: str = ""
    og_title: str = ""
    og_description: str = ""
    canonical_url: str = ""
    title: str = (
        ""  # optional fallback display title, not used for SEO injection directly
    )

    @staticmethod
    def normalize(
        data: Dict[str, str] | None, title_fallback: str = "Blog"
    ) -> "SeoContext":
        """
        Behavior-preserving normalization from loose dict (like Post.to_dict()).
        - seo_title: data.seo_title or data.title or fallback
        - seo_description: data.seo_description or ""
        - og_title: data.og_title or data.seo_title or data.title or fallback
        - og_description: data.og_description or data.seo_description or ""
        - canonical_url: data.canonical_url or ""
        Empty strings are preserved as empty (meaning tag not injected, except seo_title).
        """
        d = data or {}
        title = (d.get("title") or "").strip()
        seo_title_raw = (d.get("seo_title") or "").strip()
        seo_title = seo_title_raw or title or title_fallback

        seo_desc = (d.get("seo_description") or "").strip()
        og_title_raw = (d.get("og_title") or "").strip()
        og_title = og_title_raw or seo_title_raw or title or title_fallback
        og_desc_raw = (d.get("og_description") or "").strip()
        og_desc = og_desc_raw or seo_desc

        canonical = (d.get("canonical_url") or "").strip()

        return SeoContext(
            seo_title=seo_title,
            seo_description=seo_desc,
            og_title=og_title,
            og_description=og_desc,
            canonical_url=canonical,
            title=title or title_fallback,
        )


class SeoInjector:
    """
    Generic: html + SeoContext -> html
    No domain knowledge about blog entities or taxonomy routes.
    Rules:
    - If <title> missing -> inject <title>seo_title</title> + optional meta tags (only if non-empty)
    - If <title> present -> ensure missing optional tags are added after </title> (only if non-empty and not already present)
    - Empty seo_description/og_title/og_description/canonical_url => do NOT inject that tag
    - Preserves existing tags — does not duplicate if already present (checks substring presence)
    """

    def ensure_seo(self, html: str, seo: SeoContext) -> str:
        if not html:
            html = ""

        # Build injection block for missing <title> case
        if "<title>" not in html:
            inject = f"<title>{seo.seo_title}</title>\n"
            if seo.seo_description:
                inject += f'<meta name="description" content="{seo.seo_description}">\n'
            if seo.og_title:
                inject += f'<meta property="og:title" content="{seo.og_title}">\n'
            if seo.og_description:
                inject += (
                    f'<meta property="og:description" content="{seo.og_description}">\n'
                )
            if seo.canonical_url:
                inject += f'<link rel="canonical" href="{seo.canonical_url}">\n'
            if "<head>" in html:
                return html.replace("<head>", f"<head>\n{inject}", 1)
            else:
                return inject + html
        else:
            # Title exists — ensure optional tags
            out = html
            if seo.seo_description and 'name="description"' not in out:
                out = out.replace(
                    "</title>",
                    f'</title>\n<meta name="description" content="{seo.seo_description}">',
                    1,
                )
            if seo.og_title and "og:title" not in out:
                out = out.replace(
                    "</title>",
                    f'</title>\n<meta property="og:title" content="{seo.og_title}">',
                    1,
                )
            if seo.og_description and "og:description" not in out:
                out = out.replace(
                    "</title>",
                    f'</title>\n<meta property="og:description" content="{seo.og_description}">',
                    1,
                )
            if seo.canonical_url and 'rel="canonical"' not in out:
                out = out.replace(
                    "</title>",
                    f'</title>\n<link rel="canonical" href="{seo.canonical_url}">',
                    1,
                )
            return out
