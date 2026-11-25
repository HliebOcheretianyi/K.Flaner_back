import hashlib
import secrets
from uuid import UUID, uuid4

from django.conf import settings
from django.db import models
from django.utils import timezone

from kflaner.models.users import User

TOKEN_BYTES = 48


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


class RefreshToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="refresh_tokens")
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "refresh_tokens"

    @classmethod
    def issue(cls, user_id: UUID) -> str:
        raw_token = secrets.token_urlsafe(TOKEN_BYTES)
        cls.objects.create(
            user_id=user_id,
            token_hash=hash_token(raw_token),
            expires_at=timezone.now() + settings.REFRESH_TOKEN_LIFETIME,
        )
        return raw_token

    @classmethod
    def consume(cls, raw_token: str) -> UUID | None:
        now = timezone.now()
        record = cls.objects.filter(
            token_hash=hash_token(raw_token), revoked_at__isnull=True, expires_at__gt=now
        ).first()
        if record is None:
            return None
        # Conditional update so two concurrent refreshes cannot both use the same token.
        claimed = cls.objects.filter(id=record.id, revoked_at__isnull=True).update(revoked_at=now)
        return record.user_id if claimed else None

    @classmethod
    def revoke(cls, raw_token: str) -> None:
        cls.objects.filter(token_hash=hash_token(raw_token), revoked_at__isnull=True).update(
            revoked_at=timezone.now()
        )
