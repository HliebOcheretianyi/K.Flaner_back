from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from kflaner import models
from kflaner.domain.errors import ValidationError
from kflaner.domain.users import Registration


class DjangoPasswordPolicy:
    def validate(self, password: str, registration: Registration) -> None:
        candidate = models.User(
            email=registration.email,
            first_name=registration.first_name,
            last_name=registration.last_name,
        )
        try:
            validate_password(password, user=candidate)
        except DjangoValidationError as error:
            raise ValidationError("password", error.messages[0]) from error
