from dataclasses import dataclass
from showcases.cms_lite.services.cms_service import CmsLiteService
from showcases.cms_lite.domain.user import UserContext, UserRole

@dataclass
class CreateCategoryDTO:
    name: str
    slug: str
    description: str = ""
    user_id: str = "00000000-0000-0000-0000-000000000000"
    user_role: str = "EDITOR"

@dataclass
class CategoryResponse:
    id: str
    name: str
    slug: str

class CreateCategoryUseCase:
    def __init__(self, service: CmsLiteService):
        self._service = service
    def execute(self, dto: CreateCategoryDTO):
        try:
            user = UserContext(user_id=dto.user_id, role=UserRole(dto.user_role))
            cat = self._service.create_category(user=user, name=dto.name, slug=dto.slug, description=dto.description)
            return CategoryResponse(str(cat.id), cat.name, cat.slug)
        except Exception as e:
            code = "PERMISSION_DENIED" if "Forbidden" in str(e) or "Unauthorized" in str(e) else "VALIDATION_ERROR"
            status = 403 if code=="PERMISSION_DENIED" else 400
            return {"status": status, "json": {"success": False, "error": str(e), "code": code}, "success": False}
