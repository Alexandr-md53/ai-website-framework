from typing import Any, Callable


class Endpoint:
    def __init__(self, path: str, method: str, handler: Callable):
        self.path = path
        self.method = method
        self.handler = handler

    def handle(self, request: Any) -> Any:
        return self.handler(request)
