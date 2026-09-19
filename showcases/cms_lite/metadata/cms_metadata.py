from typing import Dict, Any
from ai_framework.metadata.models import FieldWidgetType
from showcases.cms_lite.domain.item_status import ItemStatus
from showcases.cms_lite.domain.user import UserRole
from showcases.cms_lite.domain.media import MediaType

def get_category_ui_schema():
    return {"id":{"widget":FieldWidgetType.HIDDEN},"name":{"widget":FieldWidgetType.TEXT,"required":True},"slug":{"widget":FieldWidgetType.TEXT,"required":True,"unique":True},"description":{"widget":FieldWidgetType.TEXTAREA}}

def get_tag_ui_schema():
    return {"id":{"widget":FieldWidgetType.HIDDEN},"name":{"widget":FieldWidgetType.TEXT,"required":True},"slug":{"widget":FieldWidgetType.TEXT,"required":True,"unique":True}}

def get_item_ui_schema():
    return {
        "id":{"widget":FieldWidgetType.HIDDEN},
        "title":{"widget":FieldWidgetType.TEXT,"required":True},
        "slug":{"widget":FieldWidgetType.TEXT,"required":True,"unique":True},
        "content":{"widget":FieldWidgetType.TEXTAREA,"required":True},
        "category_id":{"widget":FieldWidgetType.SELECT,"source":"Category","required":True},
        "status":{"widget":FieldWidgetType.SELECT,"options":[e.value for e in ItemStatus]},
        "tag_ids":{"widget":FieldWidgetType.MULTI_SELECT,"source":"Tag"},
        "media_ids":{"widget":FieldWidgetType.MULTI_SELECT,"source":"Media"},
        "seo_title":{"widget":FieldWidgetType.TEXT},
        "seo_description":{"widget":FieldWidgetType.TEXTAREA},
        "og_title":{"widget":FieldWidgetType.TEXT},
        "og_description":{"widget":FieldWidgetType.TEXTAREA},
    }

def get_media_ui_schema():
    return {"id":{"widget":FieldWidgetType.HIDDEN},"filename":{"widget":FieldWidgetType.TEXT,"required":True},"filepath":{"widget":FieldWidgetType.TEXT,"required":True},"media_type":{"widget":FieldWidgetType.SELECT,"options":[e.value for e in MediaType]},"file":{"widget":FieldWidgetType.FILE,"accept":"image/*"}}

def get_user_ui_schema():
    return {"id":{"widget":FieldWidgetType.HIDDEN},"email":{"widget":FieldWidgetType.TEXT,"required":True},"role":{"widget":FieldWidgetType.SELECT,"options":[e.value for e in UserRole]},"is_active":{"widget":FieldWidgetType.CHECKBOX}}

def get_cms_ui_schemas():
    return {"Category":get_category_ui_schema(),"Tag":get_tag_ui_schema(),"Item":get_item_ui_schema(),"Media":get_media_ui_schema(),"User":get_user_ui_schema()}

def get_item_validation_schema():
    return {
        "title": ["required"],
        "slug": ["required", "slug"],
        "content": ["required"],
        "category_id": ["required"]
    }
