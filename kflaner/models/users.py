from uuid import UUID, uuid4

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import IntegrityError, models, transaction

from kflaner.domain.errors import ConflictError
from kflaner.domain.users import MAX_EMAIL_LENGTH, Credentials, Registration, Role
from kflaner.domain.users import User as UserEntity
from kflaner.domain.users import normalize_email

ROLE_LABELS = {
    Role.USER: "Користувач",
    Role.EDITOR: "Редактор",
    Role.ADMIN: "Адміністратор",
}


class UserManager(BaseUserManager["User"]):
    use_in_migrations = True

    @classmethod
    def normalize_email(cls, email: str | None) -> str:
        return normalize_email(email or "")

    def create_user(self, email: str, password: str | None = None, **extra_fields) -> "User":
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields) -> "User":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", Role.ADMIN)
        return self._create(email, password, **extra_fields)

    def _create(self, email: str, password: str | None, **extra_fields) -> "User":
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    username = None
    email = models.EmailField(max_length=MAX_EMAIL_LENGTH, unique=True)
    role = models.CharField(max_length=16, choices=list(ROLE_LABELS.items()), default=Role.USER)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"

    @classmethod
    def email_taken(cls, email: str) -> bool:
        return cls.objects.filter(email__iexact=email).exists()

    @classmethod
    def register(cls, registration: Registration, password: str) -> UserEntity:
        try:
            with transaction.atomic():
                record = cls.objects.create_user(
                    email=registration.email,
                    password=password,
                    first_name=registration.first_name,
                    last_name=registration.last_name,
                )
        except IntegrityError as error:
            raise ConflictError("A user with this email already exists.") from error
        return record.to_entity()

    @classmethod
    def find_by_credentials(cls, credentials: Credentials) -> UserEntity | None:
        record = cls.objects.filter(email__iexact=credentials.email, is_active=True).first()
        if record is None:
            # Hash anyway so response time does not reveal whether the email is registered.
            cls().set_password(credentials.password)
            return None
        return record.to_entity() if record.check_password(credentials.password) else None

    @classmethod
    def find_active(cls, user_id: UUID) -> UserEntity | None:
        record = cls.objects.filter(id=user_id, is_active=True).first()
        return record.to_entity() if record else None

    @classmethod
    def exists(cls, user_id: UUID) -> bool:
        return cls.objects.filter(id=user_id).exists()

    def to_entity(self) -> UserEntity:
        return UserEntity(
            id=self.id,
            email=self.email,
            first_name=self.first_name,
            last_name=self.last_name,
            role=Role(self.role),
        )
