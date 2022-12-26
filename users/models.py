from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django_cryptography.fields import encrypt

from .managers import BasketUserManager


class BasketUser(AbstractUser):
    PHONE_REGEX = RegexValidator(
        regex=r"^\+?1?\d{9,15}$",
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.",
    )

    username = None
    tckn = models.CharField(max_length=255, unique=True)
    third_party_app_password = encrypt(
        models.CharField(max_length=255, null=True, blank=True)
    )
    phone_number = models.CharField(validators=[PHONE_REGEX], max_length=17, blank=True)

    USERNAME_FIELD = "tckn"

    objects = BasketUserManager()

    def __str__(self):
        return f"User {self.tckn}"
