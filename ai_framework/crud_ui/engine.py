from typing import Any, Mapping, Sequence
from ai_framework.metadata.models import EntityMetadata, FormMetadata, FieldWidgetType
from ai_framework.crud_ui.config import CrudUIConfig, FieldUIConfig
from ai_framework.crud_ui.models import (
    ListViewModel,
    TableColumnViewModel,
    DetailViewModel,
    DetailSectionViewModel,
    DetailFieldViewModel,
    FormViewModel,
    FormFieldViewModel,
    FormGroupViewModel,
    PaginationSpec,
)


class CrudUIEngine:
    def __init__(self, metadata: EntityMetadata, config: CrudUIConfig | None = None):
        self.metadata = metadata
        self.config = config
        self._field_config_map: dict[str, FieldUIConfig] = {}
        if config and config.field_configs:
            for fc in config.field_configs:
                self._field_config_map[fc.field_name] = fc

    def _is_default_sortable(
        self, widget_type: FieldWidgetType, data_type: str
    ) -> bool:
        if widget_type in (FieldWidgetType.TEXTAREA, FieldWidgetType.FILE):
            return False
        return data_type in ("str", "int", "float", "bool", "datetime", "date")

    def build_list_view(
        self,
        items: Sequence[Mapping[str, Any]] = (),
        pagination: PaginationSpec | None = None,
    ) -> ListViewModel:
        sorted_fields = sorted(self.metadata.fields, key=lambda f: f.display_order)
        columns: list[TableColumnViewModel] = []

        for field_meta in sorted_fields:
            cfg = self._field_config_map.get(field_meta.name)

            visible = cfg.visible if (cfg and cfg.visible is not None) else True
            if not visible:
                continue

            sortable = (
                cfg.sortable
                if (cfg and cfg.sortable is not None)
                else self._is_default_sortable(
                    field_meta.widget_type, field_meta.data_type
                )
            )

            columns.append(
                TableColumnViewModel(
                    name=field_meta.name,
                    label=field_meta.label or field_meta.name.title(),
                    data_type=field_meta.data_type,
                    widget_type=field_meta.widget_type,
                    display_order=field_meta.display_order,
                    visible=True,
                    sortable=sortable,
                )
            )

        pag_spec = (
            pagination
            if pagination is not None
            else PaginationSpec(
                page=1,
                page_size=len(items) if items else 20,
                total_items=len(items),
            )
        )

        actions = self.config.actions if self.config else ()

        return ListViewModel(
            entity_name=self.metadata.entity_name,
            title=self.metadata.label or self.metadata.entity_name,
            columns=tuple(columns),
            items=tuple(items),
            pagination=pag_spec,
            actions=tuple(actions),
        )

    def build_detail_view(
        self,
        instance_data: Mapping[str, Any],
    ) -> DetailViewModel:
        sorted_fields = sorted(self.metadata.fields, key=lambda f: f.display_order)
        detail_fields: list[DetailFieldViewModel] = []

        for field_meta in sorted_fields:
            val = instance_data.get(field_meta.name)
            detail_fields.append(
                DetailFieldViewModel(
                    name=field_meta.name,
                    label=field_meta.label or field_meta.name.title(),
                    value=val,
                    data_type=field_meta.data_type,
                    widget_type=field_meta.widget_type,
                    display_order=field_meta.display_order,
                )
            )

        section = DetailSectionViewModel(
            name="main",
            label="General Information",
            fields=tuple(detail_fields),
            display_order=1,
        )

        actions = self.config.actions if self.config else ()

        return DetailViewModel(
            entity_name=self.metadata.entity_name,
            title=f"{self.metadata.label or self.metadata.entity_name} Details",
            sections=(section,),
            actions=tuple(actions),
        )

    def build_create_form(
        self,
        form_metadata: Any | None = None,
        initial_data: Mapping[str, Any] | None = None,
    ) -> FormViewModel:
        return self._build_form(
            form_metadata=form_metadata,
            instance_data=initial_data,
        )

    def build_edit_form(
        self,
        form_metadata: FormMetadata | None = None,
        instance_data: Mapping[str, Any] | None = None,
    ) -> FormViewModel:
        return self._build_form(
            form_metadata=form_metadata, instance_data=instance_data
        )

    def _build_form(
        self,
        form_metadata: FormMetadata | None = None,
        instance_data: Mapping[str, Any] | None = None,
    ) -> FormViewModel:
        field_map = {f.name: f for f in self.metadata.fields}
        form_fields: list[FormFieldViewModel] = []
        groups_vm: list[FormGroupViewModel] = []

        if form_metadata and form_metadata.groups:
            for grp in form_metadata.groups:
                grp_field_names = []
                for fname in grp.field_names:
                    if fname in field_map:
                        fmeta = field_map[fname]
                        cur_val = instance_data.get(fname) if instance_data else None
                        form_fields.append(
                            FormFieldViewModel(
                                name=fmeta.name,
                                label=fmeta.label or fmeta.name.title(),
                                widget_type=fmeta.widget_type,
                                required=fmeta.required,
                                current_value=cur_val,
                            )
                        )
                        grp_field_names.append(fname)
                groups_vm.append(
                    FormGroupViewModel(
                        name=grp.name,
                        label=grp.label,
                        field_names=tuple(grp_field_names),
                    )
                )
        else:
            for fmeta in self.metadata.fields:
                cur_val = instance_data.get(fmeta.name) if instance_data else None
                form_fields.append(
                    FormFieldViewModel(
                        name=fmeta.name,
                        label=fmeta.label or fmeta.name.title(),
                        widget_type=fmeta.widget_type,
                        required=fmeta.required,
                        current_value=cur_val,
                    )
                )

        return FormViewModel(
            entity_name=self.metadata.entity_name,
            title=f"{'Edit' if instance_data else 'Create'} {self.metadata.label or self.metadata.entity_name}",
            fields=tuple(form_fields),
            groups=tuple(groups_vm),
        )
