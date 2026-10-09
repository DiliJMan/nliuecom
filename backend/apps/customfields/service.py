from __future__ import annotations

from datetime import date

from django.db.models import Q

from .models import CustomFieldDefinition, FieldType

MAX_TEXT = 2000


class CustomFieldError(Exception):
    def __init__(self, errors: dict[str, str]):
        super().__init__(errors)
        self.errors = errors


def definitions_for(object_type: str, domain) -> list[CustomFieldDefinition]:
    """Definitions that apply to objects of `object_type` living in `domain`."""
    scope = Q(domain__isnull=True)
    if domain is not None:
        scope |= Q(domain__pk__in=[*domain.ancestor_ids(), domain.pk])
    return list(CustomFieldDefinition.objects.filter(scope, object_type=object_type))


def _clean_value(definition: CustomFieldDefinition, value):
    kind = definition.field_type
    if kind == FieldType.TEXT:
        if not isinstance(value, str) or len(value) > MAX_TEXT:
            raise ValueError(f"Enter text of at most {MAX_TEXT} characters.")
        return value
    if kind == FieldType.NUMBER:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError("Enter a number.")
        return value
    if kind == FieldType.BOOLEAN:
        if not isinstance(value, bool):
            raise ValueError("Enter true or false.")
        return value
    if kind == FieldType.DATE:
        try:
            return date.fromisoformat(str(value)).isoformat()
        except ValueError:
            raise ValueError("Enter a date as YYYY-MM-DD.") from None
    if kind == FieldType.CHOICE:
        if value not in definition.choices:
            raise ValueError("Pick one of the listed choices.")
        return value
    if kind == FieldType.MULTI_CHOICE:
        if not isinstance(value, list) or not set(value) <= set(definition.choices):
            raise ValueError("Pick only from the listed choices.")
        return sorted(set(value), key=definition.choices.index)
    raise ValueError("Unsupported field type.")


def validate_values(object_type: str, domain, values, *, partial: bool = False) -> dict:
    """Return the cleaned values, or raise CustomFieldError naming each bad key."""
    if values is None:
        values = {}
    if not isinstance(values, dict):
        raise CustomFieldError({"": "Custom fields must be an object of key-value pairs."})
    definitions = {d.key: d for d in definitions_for(object_type, domain)}
    errors: dict[str, str] = {}
    cleaned: dict = {}
    for key in values:
        if key not in definitions:
            errors[key] = "Unknown custom field."
    for key, definition in definitions.items():
        value = values.get(key)
        if value in (None, ""):
            if definition.required and not partial:
                errors[key] = "This field is required."
            continue
        try:
            cleaned[key] = _clean_value(definition, value)
        except ValueError as exc:
            errors[key] = str(exc)
    if errors:
        raise CustomFieldError(errors)
    return cleaned
