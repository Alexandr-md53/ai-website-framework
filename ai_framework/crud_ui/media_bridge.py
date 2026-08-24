from typing import Any, Dict, Optional, Sequence
from ai_framework.asset_manager.contracts import (
    Asset,
    FileUploadInput,
    AssetManagerProtocol,
)


class MediaUIBridge:
    def __init__(self, asset_manager: AssetManagerProtocol):
        self.asset_manager = asset_manager

    def handle_upload(self, file_input: FileUploadInput) -> str:
        asset = self.asset_manager.upload(file_input)
        return asset.id

    def resolve_asset(self, asset_id: str) -> Optional[Asset]:
        return self.asset_manager.get_metadata(asset_id)

    def present_asset(self, asset_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not asset_id:
            return None
        asset = self.resolve_asset(asset_id)
        if not asset:
            return None
        return {
            "asset_id": asset.id,
            "filename": asset.filename,
            "mime_type": asset.mime_type,
            "size": asset.size,
            "storage_key": asset.storage_key,
        }

    def enrich_context(
        self, context: Dict[str, Any], file_fields: Sequence[str]
    ) -> Dict[str, Any]:
        result = dict(context)
        for field in file_fields:
            if field in result and isinstance(result[field], str):
                result[field] = self.present_asset(result[field])
        return result
