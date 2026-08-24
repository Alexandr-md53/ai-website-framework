from typing import Any, Protocol


class SettingsProviderProtocol(Protocol):
    """Канонический протокол хранилища настроек (Key-Value storage)."""

    def get(self, key: str, default: Any = None) -> Any: ...

    def set(self, key: str, value: Any) -> None: ...

    def get_all(self) -> dict[str, Any]: ...

    def has(self, key: str) -> bool: ...


class InMemorySettingsProvider:
    """In-Memory реализация SettingsProviderProtocol."""

    def __init__(self, initial_data: dict[str, Any] | None = None) -> None:
        self._data: dict[str, Any] = dict(initial_data) if initial_data else {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def get_all(self) -> dict[str, Any]:
        return dict(self._data)

    def has(self, key: str) -> bool:
        return key in self._data


from typing import Any, Protocol


class SettingsProviderProtocol(Protocol):
    """Канонический протокол хранилища настроек (Key-Value storage)."""

    def get(self, key: str, default: Any = None) -> Any: ...

    def set(self, key: str, value: Any) -> None: ...

    def delete(self, key: str) -> None: ...

    def get_all(self) -> dict[str, Any]: ...

    def has(self, key: str) -> bool: ...


class InMemorySettingsProvider:
    """In-Memory реализация SettingsProviderProtocol."""

    def __init__(self, initial_data: dict[str, Any] | None = None) -> None:
        self._data: dict[str, Any] = dict(initial_data) if initial_data else {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def delete(self, key: str) -> None:
        self._data.pop(key, None)

    def get_all(self) -> dict[str, Any]:
        return dict(self._data)

    def has(self, key: str) -> bool:
        return key in self._data
