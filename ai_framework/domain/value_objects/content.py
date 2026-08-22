from dataclasses import dataclass


@dataclass(frozen=True)
class Content:
    value: str

    @property
    def is_empty(self) -> bool:
        return not self.value or not self.value.strip()
