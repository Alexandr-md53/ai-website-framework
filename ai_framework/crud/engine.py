import inspect
from typing import Any, Optional
from ai_framework.crud.contracts import CRUDContext, CRUDError, CRUDResult


class UniversalCRUDEngine:
    def __init__(
        self,
        persistence_provider=None,
        validation_engine=None,
        slug_orchestrator=None,
    ):
        self.persistence_provider = persistence_provider
        self.validation_engine = validation_engine
        self.slug_orchestrator = slug_orchestrator

    async def _await_if_needed(self, val: Any) -> Any:
        if inspect.isawaitable(val):
            return await val
        return val

    def _format_validation_errors(self, raw_errors: list) -> list[CRUDError]:
        formatted_errors = []
        for err in raw_errors:
            if isinstance(err, CRUDError):
                formatted_errors.append(err)
                continue

            raw_code = getattr(err, "code", None)
            code = raw_code if isinstance(raw_code, str) else "VALIDATION_ERROR"

            raw_message_key = getattr(err, "message_key", None)
            if isinstance(raw_message_key, str):
                message_key = raw_message_key
            else:
                raw_message = getattr(err, "message", None)
                message_key = (
                    raw_message if isinstance(raw_message, str) else "Validation error"
                )

            field_raw = getattr(err, "field", None)
            field = field_raw if isinstance(field_raw, str) else None

            params_raw = getattr(err, "params", {})
            params = params_raw if isinstance(params_raw, dict) else {}

            crud_err = CRUDError(
                code=code,
                message_key=message_key,
                field=field,
                params=params,
            )
            formatted_errors.append(crud_err)
        return formatted_errors

    async def create(
        self,
        entity_name: str,
        payload: dict,
        context: Optional[CRUDContext] = None,
    ) -> CRUDResult:
        if self.validation_engine:
            val_fn = getattr(
                self.validation_engine,
                "validate_entity",
                getattr(self.validation_engine, "validate", None),
            )
            if val_fn:
                val_res = await self._await_if_needed(val_fn(entity_name, payload))
                if hasattr(val_res, "valid") and not val_res.valid:
                    raw_errors = getattr(val_res, "errors", [])
                    return CRUDResult(
                        success=False,
                        data=None,
                        errors=self._format_validation_errors(raw_errors),
                    )

        if self.slug_orchestrator:
            payload = await self.slug_orchestrator.process(
                entity_name=entity_name,
                payload=payload,
                context=context,
            )

        try:
            insert_fn = getattr(
                self.persistence_provider,
                "insert",
                getattr(self.persistence_provider, "create", None),
            )
            res = insert_fn(entity_name, payload)
            record = await self._await_if_needed(res)
            return CRUDResult(success=True, data=record)
        except Exception as e:
            err = CRUDError(
                code="PERSISTENCE_ERROR",
                message_key=str(e),
                params={"details": str(e)},
            )
            return CRUDResult(success=False, data=None, errors=[err])

    async def get(
        self,
        entity_name: str,
        entity_id: Any,
        context: Optional[CRUDContext] = None,
    ) -> CRUDResult:
        try:
            fetch_fn = getattr(
                self.persistence_provider,
                "fetch",
                getattr(self.persistence_provider, "get", None),
            )
            res = fetch_fn(entity_name, entity_id)
            record = await self._await_if_needed(res)
            if record is None:
                err = CRUDError(
                    code="NOT_FOUND",
                    message_key=f"Record '{entity_id}' not found for entity '{entity_name}'",
                    params={"entity_name": entity_name, "entity_id": entity_id},
                )
                return CRUDResult(success=False, data=None, errors=[err])
            return CRUDResult(success=True, data=record)
        except Exception as e:
            err = CRUDError(
                code="PERSISTENCE_ERROR",
                message_key=str(e),
                params={"details": str(e)},
            )
            return CRUDResult(success=False, data=None, errors=[err])

    async def list(
        self,
        entity_name: str,
        filters: Optional[dict] = None,
        context: Optional[CRUDContext] = None,
    ) -> CRUDResult:
        try:
            fetch_all_fn = getattr(
                self.persistence_provider,
                "fetch_all",
                getattr(self.persistence_provider, "list", None),
            )
            if filters is not None:
                res = fetch_all_fn(entity_name, filters=filters)
            else:
                res = fetch_all_fn(entity_name)
            records = await self._await_if_needed(res)
            return CRUDResult(success=True, data=records)
        except Exception as e:
            err = CRUDError(
                code="PERSISTENCE_ERROR",
                message_key=str(e),
                params={"details": str(e)},
            )
            return CRUDResult(success=False, data=None, errors=[err])

    async def update(
        self,
        entity_name: str,
        entity_id: Any,
        payload: dict,
        context: Optional[CRUDContext] = None,
    ) -> CRUDResult:
        try:
            update_fn = getattr(
                self.persistence_provider,
                "update_record",
                getattr(self.persistence_provider, "update", None),
            )
            res = update_fn(entity_name, entity_id, payload)
            record = await self._await_if_needed(res)
            if record is None:
                err = CRUDError(
                    code="NOT_FOUND",
                    message_key=f"Record '{entity_id}' not found for entity '{entity_name}'",
                    params={"entity_name": entity_name, "entity_id": entity_id},
                )
                return CRUDResult(success=False, data=None, errors=[err])
            return CRUDResult(success=True, data=record)
        except Exception as e:
            err = CRUDError(
                code="PERSISTENCE_ERROR",
                message_key=str(e),
                params={"details": str(e)},
            )
            return CRUDResult(success=False, data=None, errors=[err])

    async def delete(
        self,
        entity_name: str,
        entity_id: Any,
        context: Optional[CRUDContext] = None,
    ) -> CRUDResult:
        try:
            delete_fn = getattr(
                self.persistence_provider,
                "delete_record",
                getattr(self.persistence_provider, "delete", None),
            )
            res = delete_fn(entity_name, entity_id)
            deleted = await self._await_if_needed(res)
            if not deleted:
                err = CRUDError(
                    code="NOT_FOUND",
                    message_key=f"Record '{entity_id}' not found for entity '{entity_name}'",
                    params={"entity_name": entity_name, "entity_id": entity_id},
                )
                return CRUDResult(success=False, data=None, errors=[err])
            return CRUDResult(success=True, data=deleted)
        except Exception as e:
            err = CRUDError(
                code="PERSISTENCE_ERROR",
                message_key=str(e),
                params={"details": str(e)},
            )
            return CRUDResult(success=False, data=None, errors=[err])


from ai_framework.crud.crud_engine import CRUDEngine
