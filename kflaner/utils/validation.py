from kflaner.domain.errors import ValidationError


def require_text(field: str, value: str, max_length: int) -> None:
    if not value.strip():
        raise ValidationError(field, "This field must not be blank.")
    if len(value) > max_length:
        raise ValidationError(field, f"Ensure this field has no more than {max_length} characters.")
