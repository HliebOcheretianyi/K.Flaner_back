from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        USER = 'user', 'Користувач'
        EDITOR = 'editor', 'Редактор'
        ADMIN = 'admin', 'Адміністратор'

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.USER)
