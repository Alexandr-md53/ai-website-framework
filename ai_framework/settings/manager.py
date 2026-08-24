from typing import Any
from ai_framework.settings.provider import SettingsProviderProtocol


class SettingsManager:
    """Оркестратор настроек: отвечает за namespace, defaults, list и reset."""

    def __init__(
        self,
        provider: SettingsProviderProtocol,
        namespace: str = "default",
        defaults: dict[str, Any] | None = None,
    ) -> None:
        self.provider = provider
        self.namespace = namespace
        self.defaults = dict(defaults) if defaults else {}

    def _make_key(self, key: str) -> str:
        return f"{self.namespace}.{key}"

    def get(self, key: str, default: Any = None) -> Any:
        full_key = self._make_key(key)
        if self.provider.has(full_key):
            return self.provider.get(full_key)
        if key in self.defaults:
            return self.defaults[key]
        return default

    def set(self, key: str, value: Any) -> None:
        full_key = self._make_key(key)
        self.provider.set(full_key, value)

    def list(self) -> dict[str, Any]:
        result = dict(self.defaults)
        prefix = f"{self.namespace}."
        for full_key, val in self.provider.get_all().items():
            if full_key.startswith(prefix):
                raw_key = full_key[len(prefix) :]
                result[raw_key] = val
        return result

    def reset(self, key: str) -> None:
        full_key = self._make_key(key)
        if hasattr(self.provider, "delete"):
            self.provider.delete(full_key)

    def has(self, key: str) -> bool:
        full_key = self._make_key(key)
        return self.provider.has(full_key) or (key in self.defaults)
