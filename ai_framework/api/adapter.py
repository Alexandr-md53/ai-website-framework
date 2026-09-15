import dataclasses
from ai_framework.api.router import Router, RouteNotFoundError, MethodNotAllowedError


def _serialize(obj):
    if obj is None or isinstance(obj, (int, float, str, bool)):
        return obj
    if isinstance(obj, list):
        return [_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        return _serialize(obj.to_dict())
    if dataclasses.is_dataclass(obj):
        return _serialize(dataclasses.asdict(obj))
    if hasattr(obj, "__dict__"):
        return _serialize(obj.__dict__)
    return str(obj)


class RequestAdapter:
    def __init__(self, http_request=None):
        self.http_request = http_request or {}

    def to_dict(self):
        req = self.http_request
        return {
            "method": req.get("method"),
            "path": req.get("path"),
            "query": req.get("query", {}),
            "body": req.get("body", {}),
            "headers": req.get("headers", {}),
            "path_params": req.get("path_params", {}),
        }

    def adapt(self, method=None, path=None, http_request=None):
        req = http_request if http_request is not None else self.http_request
        if not isinstance(req, dict):
            req = {}
        return {
            "method": method or req.get("method"),
            "path": path or req.get("path"),
            "query": req.get("query", {}),
            "body": req.get("body", {}),
            "headers": req.get("headers", {}),
            "path_params": req.get("path_params", {}),
        }


class ResponseAdapter:
    @classmethod
    def build(cls, *args, **kwargs):
        status = 200
        response = None
        if "status" in kwargs:
            status = kwargs["status"]
        if "response" in kwargs:
            response = kwargs["response"]
        if len(args) == 1:
            if isinstance(args[0], int):
                status = args[0]
            else:
                response = args[0]
        elif len(args) >= 2:
            if isinstance(args[0], int):
                status = args[0]
                response = args[1]
            elif isinstance(args[1], int):
                response = args[0]
                status = args[1]
            else:
                response = args[0]
        serialized = _serialize(response)
        success = True
        if isinstance(response, dict):
            success = response.get("success", True)
        elif hasattr(response, "success"):
            success = getattr(response, "success", True)
        res = {
            "status": status,
            "json": serialized,
            "success": success,
        }
        if isinstance(serialized, dict):
            for k, v in serialized.items():
                if k not in res:
                    res[k] = v
        return res

    def adapt(self, raw_result, method=None):
        serialized_data = _serialize(raw_result)
        status_code = 200
        success = True
        if isinstance(raw_result, dict):
            status_code = raw_result.get("status", 200)
            success = raw_result.get("success", True)
            if "json" in raw_result:
                serialized_data = _serialize(raw_result["json"])
        elif hasattr(raw_result, "success"):
            success = raw_result.success
            if not raw_result.success:
                status_code = 400
                if hasattr(raw_result, "errors") and raw_result.errors:
                    first_err = raw_result.errors[0]
                    err_code = (
                        getattr(first_err, "code", "")
                        if not isinstance(first_err, dict)
                        else first_err.get("code", "")
                    )
                    if err_code == "VALIDATION_ERROR":
                        status_code = 422
                    elif err_code == "NOT_FOUND":
                        status_code = 404
                    elif err_code == "PERSISTENCE_ERROR":
                        status_code = 500
            else:
                operation = getattr(raw_result, "operation", "read")
                if operation == "create" and method != "GET":
                    status_code = 201
                else:
                    status_code = 200
        return {
            "status": status_code,
            "json": serialized_data,
            "success": success,
        }


class APIAdapter:
    def __init__(self, registry_or_router):
        if isinstance(registry_or_router, Router):
            self.router = registry_or_router
            self.registry = getattr(registry_or_router, "registry", None)
        else:
            self.registry = registry_or_router
            self.router = Router(registry_or_router)
        self.request_adapter = RequestAdapter()
        self.response_adapter = ResponseAdapter()

    def handle_request(self, method, path, http_request):
        body = http_request.get("body") if isinstance(http_request, dict) else None
        if body is not None and not isinstance(body, (dict, list)):
            return {
                "status": 400,
                "json": {
                    "success": False,
                    "error": "Malformed JSON body",
                    "code": "BAD_REQUEST",
                    "errors": [
                        {"code": "BAD_REQUEST", "message": "Malformed JSON body"}
                    ],
                },
                "success": False,
            }
        adapted_request = self.request_adapter.adapt(method, path, http_request)
        try:
            raw_result = self.router.route(method, path, adapted_request)
            return self.response_adapter.adapt(raw_result, method=method)
        except RouteNotFoundError as e:
            return {
                "status": 404,
                "json": {
                    "success": False,
                    "error": str(e),
                    "code": "NOT_FOUND",
                    "errors": [{"code": "NOT_FOUND", "message": str(e)}],
                },
                "success": False,
            }
        except MethodNotAllowedError as e:
            return {
                "status": 405,
                "json": {
                    "success": False,
                    "error": str(e),
                    "code": "METHOD_NOT_ALLOWED",
                    "errors": [{"code": "METHOD_NOT_ALLOWED", "message": str(e)}],
                },
                "success": False,
            }
        except ValueError as e:
            msg = str(e)
            if "OUT_OF_STOCK" in msg or "INSUFFICIENT_STOCK" in msg:
                return {
                    "status": 400,
                    "json": {
                        "success": False,
                        "error": msg,
                        "code": "BAD_REQUEST",
                        "errors": [{"code": "BAD_REQUEST", "message": msg}],
                    },
                    "success": False,
                }
            if msg.startswith("validation."):
                code = "VALIDATION_ERROR" if "not_found" not in msg else "NOT_FOUND"
                status = 404 if "not_found" in msg else 422
                return {
                    "status": status,
                    "json": {
                        "success": False,
                        "error": msg,
                        "code": code,
                        "errors": [{"code": code, "message": msg}],
                    },
                    "success": False,
                }
            return {
                "status": 400,
                "json": {
                    "success": False,
                    "error": msg,
                    "code": "BAD_REQUEST",
                    "errors": [{"code": "BAD_REQUEST", "message": msg}],
                },
                "success": False,
            }
        except Exception as e:
            return {
                "status": 500,
                "json": {
                    "success": False,
                    "error": str(e),
                    "code": "INTERNAL_SERVER_ERROR",
                    "errors": [{"code": "INTERNAL_SERVER_ERROR", "message": str(e)}],
                },
                "success": False,
            }
