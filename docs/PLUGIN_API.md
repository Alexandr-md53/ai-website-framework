# PLUGIN_API.md
# AI Website Framework — Plugin System Specification

## 1. Purpose
This document defines the interface standards for creating reusable Publisher Plugins in AI Website Framework.

## 2. Plugin Architecture
All plugins reside in the `plugins/` directory. Each plugin must be independent of the business domain.

## 3. Required Interface
Every Publisher Plugin must inherit from `PublisherPluginContract` and implement 3 required methods:
- `get_metadata()`: Returns plugin identification, visual icon, and supported capabilities.
- `validate(publication)`: Validates payload data before execution.
- `publish(publication, settings)`: Handles payload delivery using configuration provided by the Framework Settings module.

## 4. Standard Exception Handling
Plugins must not raise generic errors or directly inspect environment variables. 
Configurations are fetched from `Settings`, and errors must be wrapped in Framework exceptions (`ValidationError`, `PluginExecutionError`).