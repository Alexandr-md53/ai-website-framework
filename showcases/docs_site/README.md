# docs_site — Type C Showcase (Versioned Documentation Site)

Type C showcase для AI Website Framework. Демонстрирует полный цикл: Section → Version → Page → Publish → SEO → Static Generation.

## Frozen Architecture
Base: `64ad35b Step 5 GREEN / CLOSED / FROZEN`
Hardening: `609e2ab Step 6 closure`

- Domain: `domain/models.py` — DocPage, DocSection, DocVersion
- Service: `services/docs_service.py` — Slug VO, global slug index, publish/unpublish, SEO
- Renderer: `services/docs_renderer.py` — JinjaTemplateRenderer + SeoInjector из ai_framework/rendering
- Generator: `services/docs_site_generator.py` — Type-B → List[GeneratedPage]
- Writer: `ai_framework.rendering.StaticSiteWriter` — единственная FS boundary
- ai_framework/ не изменён

## How to Run
```powershell
pytest -q tests/test_docs_site_e2e.py -v
pytest -q