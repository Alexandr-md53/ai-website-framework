# IMPORT_MAP_FROZEN_V2

Generated: Phase 10.1 B1 - A1 closed, B2 guardrail 395 passed
Root: C:\Projects\AI_Website_Framework
Modules scanned: 106

## Architecture Invariants

Rule 1: CORE -> no api/crud_ui/application/infrastructure/showcases
- PASS 0 violations

Rule 2: FRAMEWORK -> no showcases (framework never depends on showcase)
- PASS 0 violations

Rule 3: CRUD contracts boundary (A1.2 91351d0)
- contracts must not import engine/persistence - checked in test_architecture.py

## Dependency Model
```text
CORE (core/, domain/, services/slug/, validation/, crud/contracts)
 | (depends only on stdlib / core itself)
ENGINE (crud/engine, pipeline/)
 |
EXTENSION (api/, crud_ui/, application/, infrastructure/)
 |
SHOWCASE (showcases/ - may depend on framework, never reverse)
```

## Full Import Map (ai_framework/*)

### ai_framework.ai_provider.__init__
- ai_framework.ai_provider.cache
- ai_framework.ai_provider.contracts
- ai_framework.ai_provider.mock
- ai_framework.ai_provider.resilient

### ai_framework.ai_provider.adapters.openrouter
- ai_framework.ai_provider.contracts
- json
- urllib.error
- urllib.request

### ai_framework.ai_provider.cache
- ai_framework.ai_provider.contracts
- hashlib
- time
- typing

### ai_framework.ai_provider.contracts
- dataclasses
- enum
- string
- typing

### ai_framework.ai_provider.mock
- ai_framework.ai_provider.contracts
- typing

### ai_framework.ai_provider.resilient
- ai_framework.ai_provider.contracts
- dataclasses
- time

### ai_framework.api.__init__
- .adapter
- .contracts
- .endpoint
- .registry
- .router

### ai_framework.api.adapter
- ai_framework.api.router
- dataclasses

### ai_framework.api.contracts
- ai_framework.crud.contracts
- dataclasses
- typing

### ai_framework.api.endpoint
- typing

### ai_framework.api.registry
- ai_framework.api.endpoint
- typing

### ai_framework.api.router
- re

### ai_framework.application.dto.article_dto
- ai_framework.domain.value_objects.article_id
- dataclasses

### ai_framework.application.pipeline.__init__
- ai_framework.application.pipeline.adapter
- ai_framework.application.pipeline.contracts
- ai_framework.application.pipeline.executor

### ai_framework.application.pipeline.adapter
- ai_framework.application.pipeline.contracts
- typing

### ai_framework.application.pipeline.contracts
- dataclasses
- typing

### ai_framework.application.pipeline.executor
- ai_framework.application.pipeline.contracts
- typing

### ai_framework.application.use_cases.archive_article
- ai_framework.application.dto.article_dto
- ai_framework.domain.contracts.repositories
- ai_framework.domain.value_objects.article_id

### ai_framework.application.use_cases.create_article
- ai_framework.application.dto.article_dto
- ai_framework.domain.contracts.repositories
- ai_framework.domain.entities.article
- ai_framework.domain.exceptions
- ai_framework.domain.value_objects.article_id
- ai_framework.domain.value_objects.content
- ai_framework.domain.value_objects.title
- uuid

### ai_framework.application.use_cases.publish_article
- ai_framework.application.dto.article_dto
- ai_framework.domain.contracts.repositories
- ai_framework.domain.value_objects.article_id

### ai_framework.asset_manager.contracts
- ai_framework.crud.contracts
- dataclasses
- datetime
- typing

### ai_framework.asset_manager.manager
- ai_framework.asset_manager.contracts
- ai_framework.crud.contracts
- datetime
- os
- typing
- uuid

### ai_framework.asset_manager.storage
- ai_framework.asset_manager.contracts
- os
- pathlib
- typing

### ai_framework.core.__init__
- .exceptions

### ai_framework.crud.__init__
- .contracts
- .crud_engine
- .engine
- .persistence
- .sqlite_persistence

### ai_framework.crud.contracts
- dataclasses
- typing

### ai_framework.crud.crud_engine
- inspect
- typing

### ai_framework.crud.engine
- .crud_engine
- ai_framework.crud.contracts
- inspect
- typing

### ai_framework.crud.persistence
- ai_framework.crud.contracts
- typing

### ai_framework.crud.slug_orchestrator
- ai_framework.crud.contracts
- ai_framework.services.slug
- inspect
- typing

### ai_framework.crud.sqlite_persistence
- ai_framework.crud.contracts
- contextlib
- sqlite3
- typing

### ai_framework.crud_ui.__init__
- ai_framework.crud_ui.actions
- ai_framework.crud_ui.config
- ai_framework.crud_ui.engine
- ai_framework.crud_ui.exceptions
- ai_framework.crud_ui.models

### ai_framework.crud_ui.actions
- ai_framework.crud_ui.exceptions
- dataclasses
- enum

### ai_framework.crud_ui.config
- ai_framework.crud_ui.actions
- dataclasses

### ai_framework.crud_ui.engine
- ai_framework.crud_ui.config
- ai_framework.crud_ui.models
- ai_framework.metadata.models
- typing

### ai_framework.crud_ui.media_bridge
- ai_framework.asset_manager.contracts
- typing

### ai_framework.crud_ui.models
- ai_framework.metadata.models
- dataclasses
- typing

### ai_framework.crud_ui.web
- ai_framework.crud_ui.media_bridge
- dataclasses
- typing
- unittest.mock

### ai_framework.crud_ui.web_adapter
- dataclasses
- datetime
- enum
- json
- typing
- uuid

### ai_framework.domain.contracts.repositories
- abc
- ai_framework.domain.entities.article
- ai_framework.domain.value_objects.article_id
- typing

### ai_framework.domain.entities.article
- ai_framework.domain.exceptions
- ai_framework.domain.value_objects.article_id
- ai_framework.domain.value_objects.content
- ai_framework.domain.value_objects.title
- dataclasses
- enum

### ai_framework.domain.value_objects.article_id
- dataclasses

### ai_framework.domain.value_objects.content
- dataclasses

### ai_framework.domain.value_objects.title
- dataclasses

### ai_framework.infrastructure.repositories.article_repository
- ai_framework.domain.contracts.repositories
- ai_framework.domain.entities.article
- ai_framework.domain.value_objects.article_id
- ai_framework.domain.value_objects.content
- ai_framework.domain.value_objects.title
- asyncio
- concurrent.futures
- typing

### ai_framework.metadata.__init__
- ai_framework.metadata.contracts
- ai_framework.metadata.engine
- ai_framework.metadata.exceptions
- ai_framework.metadata.models
- ai_framework.metadata.registry

### ai_framework.metadata.contracts
- dataclasses
- typing

### ai_framework.metadata.engine
- ai_framework.metadata.contracts
- ai_framework.metadata.exceptions
- ai_framework.metadata.models
- ai_framework.metadata.normalizer

### ai_framework.metadata.models
- dataclasses
- enum
- types
- typing

### ai_framework.metadata.normalizer
- ai_framework.metadata.exceptions
- types
- typing

### ai_framework.metadata.registry
- ai_framework.metadata.exceptions
- ai_framework.metadata.models
- threading

### ai_framework.pipeline.__init__
- .contracts
- .exceptions
- .parser
- .prompt
- .service

### ai_framework.pipeline.contracts
- ai_framework.ai_provider.contracts
- dataclasses

### ai_framework.pipeline.parser
- ai_framework.pipeline.exceptions
- ai_framework.validation.exceptions
- json
- re
- typing

### ai_framework.pipeline.prompt
- ai_framework.ai_provider.contracts
- ai_framework.pipeline.contracts
- ai_framework.pipeline.exceptions
- typing

### ai_framework.pipeline.service
- ai_framework.ai_provider.contracts
- ai_framework.pipeline.parser
- ai_framework.pipeline.prompt
- typing

### ai_framework.security.__init__
- ai_framework.security.authorization
- ai_framework.security.credentials
- dataclasses
- typing

### ai_framework.security.authorization
- __future__
- ai_framework.security
- typing

### ai_framework.security.credentials
- dataclasses

### ai_framework.security.web
- ai_framework.security
- typing

### ai_framework.services.slug.__init__
- .engine
- .exceptions
- .generator
- .protocols
- .resolver

### ai_framework.services.slug.engine
- typing
- unicodedata

### ai_framework.services.slug.exceptions
- ai_framework.core.exceptions

### ai_framework.services.slug.generator
- .engine
- .exceptions
- .protocols
- .resolver
- re
- typing

### ai_framework.services.slug.protocols
- typing

### ai_framework.services.slug.resolver
- .exceptions
- typing

### ai_framework.settings.manager
- ai_framework.settings.provider
- typing

### ai_framework.settings.provider
- typing

### ai_framework.settings.ui_bridge
- ai_framework.settings.manager
- typing

### ai_framework.tools.import_map
- ast
- collections
- pathlib
- sys

### ai_framework.validation.context
- dataclasses
- typing

### ai_framework.validation.providers.persistence
- typing

### ai_framework.validation.result
- dataclasses
- typing

### ai_framework.validation.types
- typing

### ai_framework.validation.validators.base
- abc
- typing

## Reverse Map - Who imports what (Top 50 internal)

### ai_framework.ai_provider.contracts (imported by 8)
- ai_framework.ai_provider.__init__:6
- ai_framework.ai_provider.adapters.openrouter:10
- ai_framework.ai_provider.cache:10
- ai_framework.ai_provider.mock:7
- ai_framework.ai_provider.resilient:9
- ai_framework.pipeline.contracts:6
- ai_framework.pipeline.prompt:8
- ai_framework.pipeline.service:8

### ai_framework.crud.contracts (imported by 7)
- ai_framework.api.contracts:4
- ai_framework.asset_manager.contracts:5
- ai_framework.asset_manager.manager:13
- ai_framework.crud.engine:3
- ai_framework.crud.persistence:3
- ai_framework.crud.slug_orchestrator:4
- ai_framework.crud.sqlite_persistence:5

### ai_framework.domain.value_objects.article_id (imported by 7)
- ai_framework.application.dto.article_dto:2
- ai_framework.application.use_cases.archive_article:6
- ai_framework.application.use_cases.create_article:10
- ai_framework.application.use_cases.publish_article:6
- ai_framework.domain.contracts.repositories:5
- ai_framework.domain.entities.article:8
- ai_framework.infrastructure.repositories.article_repository:6

### ai_framework.metadata.models (imported by 5)
- ai_framework.crud_ui.engine:2
- ai_framework.crud_ui.models:3
- ai_framework.metadata.__init__:15
- ai_framework.metadata.engine:3
- ai_framework.metadata.registry:6

### ai_framework.domain.contracts.repositories (imported by 4)
- ai_framework.application.use_cases.archive_article:5
- ai_framework.application.use_cases.create_article:7
- ai_framework.application.use_cases.publish_article:5
- ai_framework.infrastructure.repositories.article_repository:4

### ai_framework.metadata.exceptions (imported by 4)
- ai_framework.metadata.__init__:9
- ai_framework.metadata.engine:2
- ai_framework.metadata.normalizer:4
- ai_framework.metadata.registry:2

### ai_framework.application.pipeline.contracts (imported by 3)
- ai_framework.application.pipeline.__init__:2
- ai_framework.application.pipeline.adapter:3
- ai_framework.application.pipeline.executor:3

### ai_framework.application.dto.article_dto (imported by 3)
- ai_framework.application.use_cases.archive_article:1
- ai_framework.application.use_cases.create_article:3
- ai_framework.application.use_cases.publish_article:1

### ai_framework.domain.entities.article (imported by 3)
- ai_framework.application.use_cases.create_article:8
- ai_framework.domain.contracts.repositories:4
- ai_framework.infrastructure.repositories.article_repository:5

### ai_framework.domain.value_objects.content (imported by 3)
- ai_framework.application.use_cases.create_article:11
- ai_framework.domain.entities.article:9
- ai_framework.infrastructure.repositories.article_repository:7

### ai_framework.domain.value_objects.title (imported by 3)
- ai_framework.application.use_cases.create_article:12
- ai_framework.domain.entities.article:10
- ai_framework.infrastructure.repositories.article_repository:8

### ai_framework.asset_manager.contracts (imported by 3)
- ai_framework.asset_manager.manager:6
- ai_framework.asset_manager.storage:5
- ai_framework.crud_ui.media_bridge:2

### ai_framework.domain.exceptions (imported by 2)
- ai_framework.application.use_cases.create_article:9
- ai_framework.domain.entities.article:4

### ai_framework.crud_ui.exceptions (imported by 2)
- ai_framework.crud_ui.__init__:1
- ai_framework.crud_ui.actions:3

### ai_framework.crud_ui.actions (imported by 2)
- ai_framework.crud_ui.__init__:2
- ai_framework.crud_ui.config:2

### ai_framework.crud_ui.models (imported by 2)
- ai_framework.crud_ui.__init__:8
- ai_framework.crud_ui.engine:4

### ai_framework.crud_ui.config (imported by 2)
- ai_framework.crud_ui.__init__:19
- ai_framework.crud_ui.engine:3

### ai_framework.metadata.contracts (imported by 2)
- ai_framework.metadata.__init__:1
- ai_framework.metadata.engine:1

### ai_framework.pipeline.exceptions (imported by 2)
- ai_framework.pipeline.parser:10
- ai_framework.pipeline.prompt:14

### ai_framework.security (imported by 2)
- ai_framework.security.authorization:5
- ai_framework.security.web:3

### ai_framework.ai_provider.cache (imported by 1)
- ai_framework.ai_provider.__init__:1

### ai_framework.ai_provider.mock (imported by 1)
- ai_framework.ai_provider.__init__:17

### ai_framework.ai_provider.resilient (imported by 1)
- ai_framework.ai_provider.__init__:18

