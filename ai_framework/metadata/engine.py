from ai_framework.metadata.contracts import RawEntityFragment, RawFieldFragment
from ai_framework.metadata.exceptions import InvalidMetadataConfigurationError
from ai_framework.metadata.models import (
    EntityMetadata,
    FieldConstraint,
    FieldMetadata,
    FieldWidgetType,
    FormMetadata,
)
from ai_framework.metadata.normalizer import normalize_opaque_value


class MetadataEngine:
    """Aggregates, normalizes, and resolves conflicts between raw metadata fragments."""

    def build_entity_metadata(
        self,
        entity_raw: RawEntityFragment,
        validation_fragments: tuple[RawFieldFragment, ...] = (),
        ui_fragments: tuple[RawFieldFragment, ...] = (),
    ) -> EntityMetadata:
        validation_map = {f.name: f for f in validation_fragments}
        ui_map = {f.name: f for f in ui_fragments}

        processed_fields = []

        for field_raw in entity_raw.fields:
            name = field_raw.name
            val_frag = validation_map.get(name)
            ui_frag = ui_map.get(name)

            # 1. Data type resolution
            data_type = field_raw.data_type or (val_frag and val_frag.data_type) or (ui_frag and ui_frag.data_type) or "str"

            # 2. Required precedence: Validation wins over UI and structural defaults
            required = False
            if val_frag and val_frag.required is not None:
                required = val_frag.required
            elif field_raw.required is not None:
                required = field_raw.required
            elif ui_frag and ui_frag.required is not None:
                required = ui_frag.required

            # 3. Label resolution: UI overrides structural defaults
            raw_label = (ui_frag and ui_frag.label) or (field_raw and field_raw.label)
            label = raw_label or self._auto_humanize(name)

            # 4. Widget type resolution
            raw_widget = (ui_frag and ui_frag.widget_type) or (field_raw and field_raw.widget_type)
            widget_type = self._resolve_widget_type(data_type, raw_widget)

            # 5. Display order
            display_order = (ui_frag and ui_frag.display_order) or (field_raw and field_raw.display_order) or 0

            # 6. Default value extraction
            raw_default = None
            if getattr(field_raw, "default_value", None) is not None:
                raw_default = field_raw.default_value
            elif val_frag and getattr(val_frag, "default_value", None) is not None:
                raw_default = val_frag.default_value

            default_value = normalize_opaque_value(raw_default)

            # 7. Constraints aggregation & normalization
            combined_constraints = []
            for f_frag in (field_raw, val_frag, ui_frag):
                if f_frag and f_frag.constraints:
                    for c_name, c_val in f_frag.constraints:
                        combined_constraints.append(FieldConstraint(name=str(c_name), value=normalize_opaque_value(c_val)))

            # 8. Options & Choices normalization
            raw_options = {}
            if field_raw and field_raw.options:
                raw_options.update(dict(field_raw.options))
            if ui_frag and ui_frag.options:
                raw_options.update(dict(ui_frag.options))
            options = tuple((str(k), normalize_opaque_value(v)) for k, v in raw_options.items())

            processed_fields.append(
                FieldMetadata(
                    name=name,
                    data_type=data_type,
                    label=label,
                    widget_type=widget_type,
                    required=required,
                    display_order=display_order,
                    default_value=default_value,
                    constraints=tuple(combined_constraints),
                    options=options,
                )
            )

        entity_label = entity_raw.label or self._auto_humanize(entity_raw.entity_name)
        plural_label = entity_raw.plural_label or f"{entity_label}s"
        primary_key = entity_raw.primary_key_field or "id"

        return EntityMetadata(
            entity_name=entity_raw.entity_name,
            label=entity_label,
            plural_label=plural_label,
            primary_key_field=primary_key,
            fields=tuple(processed_fields),
        )

    def build_form_metadata(
        self,
        entity_raw: RawEntityFragment,
        title: str,
        validation_fragments: tuple[RawFieldFragment, ...] = (),
        ui_fragments: tuple[RawFieldFragment, ...] = (),
    ) -> FormMetadata:
        entity_meta = self.build_entity_metadata(entity_raw, validation_fragments, ui_fragments)
        return FormMetadata(
            entity_name=entity_meta.entity_name,
            title=title,
            fields=entity_meta.fields,
        )

    def _auto_humanize(self, text: str) -> str:
        return text.replace("_", " ").title()

    def _resolve_widget_type(self, data_type: str, custom_widget: str | None) -> FieldWidgetType:
        if custom_widget:
            try:
                return FieldWidgetType(custom_widget.lower())
            except ValueError:
                raise InvalidMetadataConfigurationError(f"Unsupported or invalid widget type: '{custom_widget}'")

        if data_type in ("int", "float"):
            return FieldWidgetType.NUMBER
        if data_type == "bool":
            return FieldWidgetType.BOOLEAN
        return FieldWidgetType.TEXT