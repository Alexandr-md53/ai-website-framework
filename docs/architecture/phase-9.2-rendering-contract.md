Phase 9.2 — Rendering Contract v1.0 (Design)
Baseline: 161e23e / phase-8-publishable-lifecycle-green / 657 passed
Status: CONTRACT DESIGN — no runtime changes
Parent: phase-9-audit-v0.1.md + gap-matrix-v0.3-reviewed.md

0. Context — Framework primitives already exist
Phase 7 extraction PR already introduced ai_framework/rendering/:

text
ai_framework/rendering/
├── __init__.py                → GeneratedPage, SeoContext, SeoInjector, TemplateRendererProtocol, JinjaTemplateRenderer, StaticSiteWriter
├── generated_page.py          → frozen VO
├── protocols.py               → TemplateRendererProtocol
├── jinja.py                   → JinjaTemplateRenderer
├── seo.py                     → SeoContext + SeoInjector
└── static_writer.py           → StaticSiteWriter (FS-safe)
Phase 9 is NOT a new extraction. Phase 9.2 must define what v1.0 contract means and eliminate legacy duplication.

Current factual code state (read from container):

blog_cms (legacy):

showcases/blog_cms/services/site_generator.py
Local @dataclass GeneratedPage(path, html, kind) — duplicate of framework VO
class Renderer — 163 LOC:
__init__(templates_dir) — own Jinja Environment(FileSystemLoader) + _jinja fallback flag
_seo_context(post_or_dict) -> dict — own normalization: seo_title = seo_title or title or fallback, og_title = og_title or seo_title or title
_inject_seo(html, seo_ctx: dict) -> str — own injection: if "<title>" not in html: inject <title> + meta, else ensure meta after </title>
render_post(category_name, author_name), render_index, render_category, render_tag, render_rss, render_sitemap — domain-aware (posts/, categories/, tags/)
_ensure_post_links(html, posts) — guarantee href="/posts/{slug}/" fallback
class SiteGenerator(service, renderer: Renderer)
generate() -> List[GeneratedPage] — G1 index, G2 post detail, G12 taxonomy+ rss/sitemap — domain owns URL semantics
write(pages, out_dir) -> List[Path] — NO FS safety: fp = out_dir / pg.path; fp.parent.mkdir(); fp.write_text() — missing checks for "..", "/", "", "C:", absolute, anchor
docs_site (modernized, reference implementation):

showcases/docs_site/services/docs_renderer.py
class DocsRenderer:
__init__ → self.template_renderer = JinjaTemplateRenderer(templates_dir), self.seo_injector = SeoInjector()
_seo_context(doc_or_dict) -> dict → delegates to SeoContext.normalize(d, fallback) then returns dict view
_seo_obj(doc_or_dict) -> SeoContext → direct SeoContext.normalize
_inject(html, seo_ctx: dict|SeoContext) -> str → converts dict to SeoContext if needed, then seo_injector.ensure_seo(html, seo)
render_doc(section_name, version_name), render_index, render_section, render_version, render_sitemap — domain owns URL semantics guides/, sections/, versions/
_ensure_doc_links(html, docs) — guarantee href="/guides/{slug}/" — analogous to blog but docs-specific
class DocsSiteGenerator(service, renderer: DocsRenderer)
generate() -> List[GeneratedPage] — same pattern, domain owns guides/{slug}/, sections/, versions/
write(pages, out_dir, clean=True) -> List[Path] → delegates to framework: self._writer = StaticSiteWriter(); return self._writer.write(pages, out_dir, clean)
framework (extracted):

generated_page.py: @dataclass(frozen=True, slots=True) GeneratedPage(path: str, html: str, kind: str) — immutable VO, no domain deps, path is relative logical path
protocols.py: @runtime_checkable class TemplateRendererProtocol(Protocol): def render(template_name: str, context: dict) -> str: ...
jinja.py: JinjaTemplateRenderer(templates_dir) → Environment(FileSystemLoader, autoescape), render(template_name, context) -> str — generic, no domain
seo.py: SeoContext(frozen, slots) with fields seo_title, seo_description, og_title, og_description, canonical_url, title; normalize(data, title_fallback="Blog") -> SeoContext with explicit rules (seo_title = seo_title_raw or title or fallback, seo_description = data.seo_description or "", og_title = og_title_raw or seo_title_raw or title or fallback, og_description = og_desc_raw or seo_desc, canonical = canonical_raw); SeoInjector.ensure_seo(html, seo) -> str with rules: if "<title>" not in html: inject <title> + optional meta only if non-empty, else ensure optional tags after </title> if not present, preserve existing, no duplication
static_writer.py: StaticSiteWriter.write(pages, out_dir, clean=True) -> List[Path] — FS safety: reject empty path, reject posix.is_absolute(), win.is_absolute(), raw.startswith("/") or "", ".." in PurePath.parts / posix.parts / win.parts, C: drive (raw[1]==":"), ":" and "" in raw, anchor not allowed, resolve out_dir escape check; clean flag deterministic
Call graph for security:

blog_cms production path: app_factory.create_app() -> SiteGenerator(service, Renderer()) -> generator.generate() -> generator.write(pages, out_dir) → legacy write, bypasses StaticSiteWriter
docs_site production path: DocsSiteGenerator(service, DocsRenderer()) -> generate() -> _writer.write() → uses StaticSiteWriter, secure
Conclusion: legacy SiteGenerator.write() is second filesystem boundary, must be eliminated.

1. GeneratedPage — Stable Framework VO
python
@dataclass(frozen=True, slots=True)
class GeneratedPage:
    path: str  # relative, e.g. "index.html", "posts/hello-world/index.html", "guides/getting-started/index.html"
    html: str
    kind: str  # logical: index | post | category | tag | doc | section | version | rss | sitemap | custom
Contract:

Immutable: frozen, slots — no mutation after creation
Value semantics: no identity, no domain deps (no Post, no DocPage)
path is logical relative path — domain owns URL semantics, framework owns FS safety validation in writer, not in VO itself (parallel to Slug pattern: Slug domain-valid only, FS rules owned by writer)
html is opaque rendered string — framework does not parse or validate domain content
kind is logical hint for consumers (index vs post vs doc), not filesystem type
Legacy: blog_cms/services/site_generator.py defines local GeneratedPage — must be replaced by import from ai_framework.rendering

2. TemplateRendererProtocol — Minimal Contract Derived from 2 Consumers
Actual signatures observed:

Legacy Renderer: render_post(post: Post, category_name: str, author_name: str) -> str, render_index(posts) -> str, etc. — domain-specific methods, NOT generic
DocsRenderer: render_doc(doc: DocPage, section_name, version_name) -> str, render_index(docs) -> str — also domain-specific
Both internally call generic template_renderer.render(template_name, context) -> str (DocsRenderer) or self._env.get_template(template_name).render(**context) (legacy Renderer)
Minimal framework contract must be generic, not domain-specific:

python
@runtime_checkable
class TemplateRendererProtocol(Protocol):
    def render(self, template_name: str, context: dict) -> str: ...
Implementation:

JinjaTemplateRenderer(templates_dir: Path|str|None) — framework impl
Showcase renderers (BlogRenderer, DocsRenderer) are composition wrappers that own domain URL semantics and call TemplateRendererProtocol.render()
Decision:

Do NOT define render(template_name, context, seo?) -> str with seo param — SEO is separate concern (SeoContext + SeoInjector). TemplateRenderer is pure template → HTML.
Do NOT define render_post, render_doc, render_index in protocol — those belong to showcase renderers (domain owns posts/, guides/, sections/ etc)
Protocol is 1 method only — maximally narrow, same principle as PublishableProtocol status+slug in Phase 8
Acceptance:

JinjaTemplateRenderer implements protocol
DocsRenderer.template_renderer is instance of protocol
Legacy Renderer._env.get_template(...).render(**context) is equivalent behavior but not via protocol — migration will replace with composition
3. SEO — Boundary Between Data and HTML Transformation
SeoContext — Data:

python
@dataclass(frozen=True, slots=True)
class SeoContext:
    seo_title: str
    seo_description: str = ""
    og_title: str = ""
    og_description: str = ""
    canonical_url: str = ""
    title: str = ""
    @staticmethod
    def normalize(data: dict|None, title_fallback: str = "Blog") -> SeoContext: ...
Framework-level generic SEO context — no domain knowledge about posts, taxonomies, sections, versions
normalize behavior-preserving from loose dict (like Post.to_dict()): same fallback chain as legacy Renderer._seo_context but implemented once
Empty strings mean "do not render that tag" except seo_title which has fallback — explicit empty handling
Location: ai_framework/rendering/seo.py
SeoInjector — HTML Transformation:

python
class SeoInjector:
    def ensure_seo(self, html: str, seo: SeoContext) -> str: ...
Generic: html + SeoContext -> html
Rules (must match both legacy _inject_seo and framework ensure_seo):
If "<title>" missing → inject "<title>seo_title</title>" + optional meta tags only if non-empty, insert after <head> or prepend
If "<title>" present → ensure missing optional tags after </title> only if non-empty and not already present (substring check for name="description", og:title, og:description, rel="canonical")
Preserve existing tags — no duplication
No domain knowledge — does not know about blog entities, taxonomy routes, guides/, sections/
Location: same file seo.py
Boundary:

text
SeoContext normalization (data → SeoContext)  → pure data transformation
SeoInjector (html + SeoContext → html)        → HTML transformation
TemplateRenderer (template + context → html)  → template → HTML (may already contain SEO tags from template)
Showcase renderers compose them:

text
docs_site: _seo_obj = SeoContext.normalize(doc.to_dict()) → template_renderer.render("doc_page.html", {...seo_dict}) → seo_injector.ensure_seo(html, seo_obj)

blog_cms (legacy): _seo_context(post) -> dict → _env.get_template("post.html").render(**seo_ctx) → _inject_seo(html, seo_ctx)
blog_cms (target): same as docs_site — use SeoContext.normalize + JinjaTemplateRenderer + SeoInjector
Not framework responsibility:

blog URLs (/posts/{slug}/, /categories/{slug}/)
docs URLs (/guides/{slug}/, /sections/{slug}/, /versions/{slug}/)
taxonomy link guarantees (_ensure_post_links, _ensure_doc_links) — showcase-owned fallback for broken templates
SEO Meta VO (SeoMeta in domain models) — domain may have richer fields, but framework SeoContext is minimal normalized view
4. StaticSiteWriter — One Filesystem Boundary
Contract:

python
class StaticSiteWriter:
    def write(self, pages: List[GeneratedPage], out_dir: Path|str, clean: bool = True) -> List[Path]: ...
Framework-level generic writer — no domain knowledge
clean=True: removes out_dir before write (deterministic, no stale files), clean=False: merges
Preserves relative paths: page.path is relative
FS safety — single ownership of all path safety checks:
Reject empty path
Reject absolute: PurePosixPath.is_absolute(), PureWindowsPath.is_absolute(), raw.startswith("/"), raw.startswith("\")
Reject parent traversal: ".." in PurePath.parts / posix.parts / win.parts
Reject Windows drive: raw[1]==":" (C:), ":" and "" in raw
Reject anchor not allowed (except "." / "./")
Ensure join does not escape out_dir (resolve check, absolute discard)
No Slug FS rules — Slug owns domain-valid only (Phase 8 guard preserved), writer owns FS safety
Security requirement (contract requirement, not optional):

Any write of generated output MUST go through StaticSiteWriter. Showcase-local write() with out_dir / pg.path and no traversal guards is NOT a valid generic rendering boundary.

Current violation:

blog_cms SiteGenerator.write() is legacy second boundary — bypasses StaticSiteWriter
docs_site DocsSiteGenerator.write() correctly delegates to StaticSiteWriter — reference implementation
Migration target:

text
legacy showcase Renderer (blog_cms)
        ↓
temporary compatibility shim (BlogRenderer that composes framework primitives)
        ↓
framework rendering primitives (JinjaTemplateRenderer + SeoContext + SeoInjector + GeneratedPage)
        ↓
one filesystem writer (StaticSiteWriter)
Generator contract remains frozen:

python
def generate() -> list[GeneratedPage]
Domain → pages — domain owns URL semantics (posts/hello-world/index.html vs guides/getting-started/index.html), taxonomy filtering, content fetching via service.list_published()
Generator does NOT write to filesystem — separation of generate vs write
5. Generator — Frozen
python
# showcase-owned, not framework
class BlogSiteGenerator:
    def __init__(self, service: BlogCmsService, renderer: BlogRenderer): ...
    def generate(self) -> List[GeneratedPage]: ...

class DocsSiteGenerator:
    def __init__(self, service: DocsService, renderer: DocsRenderer): ...
    def generate(self) -> List[GeneratedPage]: ...
Not framework responsibility to define StaticSiteGeneratorProtocol beyond optional:

python
class StaticSiteGeneratorProtocol(Protocol):
    def generate(self) -> List[GeneratedPage]: ...
    def write(self, pages: List[GeneratedPage], out_dir: Path, clean: bool = True) -> List[Path]: ...
But Phase 9.2 does NOT expand protocol — keep generate() -> list[GeneratedPage] frozen. If protocol exists in protocols.py, it should be minimal and not required for showcase generators (they can implement same methods without inheriting).

6. What Is NOT Framework Responsibility (v1.0)
Explicit non-scope for rendering v1.0, same principle as Phase 8 non-scope:

blog URLs: /posts/{slug}/, /categories/{slug}/, /tags/{slug}/, /rss.xml, /sitemap.xml — owned by blog_cms SiteGenerator + Renderer
docs URLs: /guides/{slug}/, /sections/{slug}/, /versions/{slug}/ — owned by docs_site DocsSiteGenerator + DocsRenderer
posts/categories/tags taxonomy filtering — showcase services
guides/sections/versions taxonomy — showcase services
taxonomy link guarantees: _ensure_post_links, _ensure_doc_links — showcase fallback for broken templates
deployment: where out_dir is, CDN, hosting
identity/auth: UserContext, PipelineContext, X-User-Id, X-User-Role — separate candidate
app factories, frozen route maps, FastAPI dependencies — domain-owned
RenderingEngine, RenderingService, BaseRenderer, umbrella interface — must NOT be created — one filesystem writer principle, composition over inheritance
7. Security Gap — Contract Requirement
Any write of generated output passes through StaticSiteWriter; showcase-local write() is not a valid generic rendering boundary.

Evidence:

blog_cms legacy write() allows pg.path = "../../etc/passwd" → out_dir / "../../etc/passwd" → writes outside out_dir (no guard)
StaticSiteWriter rejects ".." in parts → ValueError
If legacy write() is not used in production path (check call graph in app_factory.py: generator.write(pages, out) — it IS used in POST /site/generate), then removal is migration cleanup, not contract change. Call graph confirms production usage, so security gap is real and must be fixed in Phase 9.3 migration.

8. Acceptance Criteria for 9.2
After this document, it must be unambiguously clear:

text
GeneratedPage       → immutable output value (path relative, html, kind) — framework VO, no domain
TemplateRenderer    → template_name + context → HTML — generic, protocol 1 method
SeoContext          → SEO data normalization (dict → SeoContext) — pure data, no HTML
SeoInjector         → SEO HTML transformation (html + SeoContext → html) — generic injection
Generator           → domain → pages (domain owns URL semantics, taxonomy, content fetching)
StaticSiteWriter    → pages → filesystem (one FS boundary, FS safety owned here)
And separately:

text
NOT framework responsibility:
- blog URLs, docs URLs
- posts/categories/tags, guides/sections/versions
- taxonomy filtering
- deployment
- identity/auth
- app factories / frozen routes
- umbrella RenderingEngine / BaseRenderer
9. Next — Phase 9.3 Migration Plan (preview, not executed)
Replace showcases/blog_cms/services/site_generator.py::GeneratedPage with from ai_framework.rendering import GeneratedPage
Replace Renderer with BlogRenderer that composes JinjaTemplateRenderer + SeoContext + SeoInjector (same pattern as DocsRenderer) — no inheritance from framework, composition only
Replace SiteGenerator.write() with delegation to StaticSiteWriter().write(pages, out_dir, clean=True) — eliminate second FS boundary
Keep SiteGenerator.generate() unchanged in terms of URL semantics (posts/, categories/, tags/, rss, sitemap) — domain-owned
DocsSiteGenerator already compliant — verify no further changes needed, use as reference
Tests: existing test_blog_cms_e2e.py must still pass (G1/G2/G12 + SEO persist), plus new FS safety tests: .., /, C: paths must raise ValueError via StaticSiteWriter
Baseline remains 161e23e / 657 until Phase 9.3 introduces code changes — no runtime changes in 9.2
10. Verification
bash
python -m pytest -q
# 657 passed (no code changes in 9.2)

git status
# docs/architecture/phase-9.2-rendering-contract.md new file only
