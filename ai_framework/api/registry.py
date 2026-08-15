from typing import Dict, List, Tuple, Optional
from ai_framework.api.endpoint import Endpoint


class EndpointRegistry:
    def __init__(self):
        self.routes: Dict[Tuple[str, str], Endpoint] = {}

    def register(self, method: str, path: str, endpoint: Endpoint) -> None:
        self.routes[(method, path)] = endpoint

    def get(self, method: str, path: str) -> Optional[Endpoint]:
        return self.routes.get((method, path))

    def list(self) -> List[Tuple[str, str]]:
        return list(self.routes.keys())
