# ✅ ПРАВИЛЬНО:
import re


class RouteNotFoundError(KeyError):
    pass


class MethodNotAllowedError(Exception):
    pass


class Router:
    def __init__(self, registry):
        self.registry = registry
        self.middlewares = []

    def use_middleware(self, middleware_fn):
        self.middlewares.append(middleware_fn)

    def _get_registered_endpoints(self):
        for attr in ["endpoints", "_endpoints", "routes", "_routes"]:
            if hasattr(self.registry, attr):
                return getattr(self.registry, attr)
        if isinstance(self.registry, dict):
            return self.registry
        return {}

    def route(self, method, path, request):
        endpoints = self._get_registered_endpoints()
        path_matched = False
        target_endpoint = None

        for key, endpoint in endpoints.items():
            if isinstance(key, tuple):
                reg_method, reg_path = key
            else:
                reg_method = getattr(endpoint, "method", "")
                reg_path = getattr(endpoint, "path", key)

            pattern = "^" + re.sub(r"\{([^/]+)\}", r"([^/]+)", reg_path) + "$"
            match = re.match(pattern, path)

            if match:
                path_matched = True
                if reg_method.upper() == method.upper():
                    target_endpoint = endpoint
                    keys = re.findall(r"\{([^/]+)\}", reg_path)
                    values = match.groups()
                    if "path_params" not in request:
                        request["path_params"] = {}
                    for k, v in zip(keys, values):
                        request["path_params"][k] = v
                        request[k] = v
                    break

        if not path_matched:
            raise RouteNotFoundError(f"No route found for path: {path}")
        if not target_endpoint:
            raise MethodNotAllowedError(f"Method {method} not allowed for path: {path}")

        def execute_endpoint(req):
            return target_endpoint.handle(req)

        handler = getattr(endpoint, "handler", endpoint)
        for mw in reversed(self.middlewares):
            current_mw = mw
            next_fn = handler
            handler = lambda req, m=current_mw, n=next_fn: m(req, n)

        return handler(request)
