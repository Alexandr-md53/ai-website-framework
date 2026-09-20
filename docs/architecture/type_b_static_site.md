Type B: Domain → Generator → Renderer → Output
Framework provides generic primitives, showcase owns domain semantics.

Domain (showcase)
  ↓ list_published(), to_dict()
Generator (showcase)
  ↓ generate() -> List[GeneratedPage]
Renderer (showcase uses framework primitives)
  ↓ template render + SeoInjector
Writer (framework)
  ↓ write(pages, out_dir, clean=True)
Static Output
Framework
GeneratedPage(path, html, kind)
SeoContext + SeoInjector (html + SeoContext -> html, no Post/Blog/slug knowledge)
TemplateRendererProtocol + JinjaTemplateRenderer
StaticSiteWriter
Showcase (Blog CMS)
BlogCmsService: CRUD + publish + list_published
BlogRenderer: Post -> SeoContext, template context, posts/<slug>/, categories/<slug>/, tags/<slug>/, RSS, Sitemap, _ensure_post_links
SiteGenerator: knows taxonomy tree, uses BlogRenderer + StaticSiteWriter
Protocol not extracted yet
StaticSiteGeneratorProtocol — documented only, to be extracted after second Type-B showcase proves abstraction.

