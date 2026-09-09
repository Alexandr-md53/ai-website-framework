# Showcases - Public Hooks Contract (C3.3)

All showcases are crud product.

Structure (real, not invented):
`
showcases/<name>/
|-- manifest.json          # C3.2 generated from contract
|-- domain/                # dataclass models + enums
|   |-- __init__.py        # EMPTY - no public re-export
|   └── *.py               # MenuItem, Attorney, Plant etc
|-- metadata/ or domain/validators  # UI schema / validation
└── services/
    |-- __init__.py        # ONLY place with __all__
    └── *_service.py       # Service + UserContext + Role
`

B3 rule: ai_framework/ NEVER imports showcases/*.
Showcase -> framework via manifest.json only.

Public hooks per showcase:
- cafe: domain.menu_item.MenuItem + metadata.cafe_metadata.get_menu_item_ui_schema + services.CafeService
- lawyer: domain.models.* + domain.validators.ConsultationRequestValidator + services.LawyerService
- plant_nursery: domain.plant.Plant + metadata.plant_metadata.get_plant_ui_schema + services.catalog_service.PlantNurseryCatalogService + validation/category_rules
