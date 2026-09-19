# cms_lite — Phase 2 e2e
Type A Dynamic CMS Lite — first end-to-end per Target Matrix v0.1

Flow: CRUD Category/Tag -> CRUD Item (draft validation slug unique) -> publish (requires content >=20) -> unpublish -> duplicate -> public read only PUBLISHED

Auth: UserRole ADMIN/EDITOR/VIEWER, PermissionDeniedError 403
Validation: slug regex, required, not_unique, content length for publish
Public guard: get_published_by_slug, list_published, search_published — DRAFT invisible

Excludes: Publisher, Stock, G1/G2/G12/G3/G4/C16.6 — per freeze doc
