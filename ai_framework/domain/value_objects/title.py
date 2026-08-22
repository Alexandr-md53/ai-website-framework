from dataclasses import dataclass


@dataclass(frozen=True)
class Title:
    value: str

    @property
    def is_empty(self) -> bool:
        return not self.value or not self.value.strip()
