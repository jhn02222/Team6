# models.py
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
import uuid
from django.conf import settings

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, status="Inactive", **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)

class Users(AbstractBaseUser, PermissionsMixin):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
        ('Suspended', 'Suspended') 
    ]

    account_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=20)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Inactive")
    is_staff = models.BooleanField(default=False)
    promotions_opt_in = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'phone']

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.first_name} {self.last_name}"



class Address(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='address',
        help_text="The user this address belongs to."
    )
    street   = models.CharField(
        max_length=255,
        blank=True, null=True,
        help_text="Street address, e.g. 123 Main St."
    )
    city     = models.CharField(
        max_length=100,
        blank=True, null=True,
        help_text="City name."
    )
    state    = models.CharField(
        max_length=100,
        blank=True, null=True,
        help_text="State or province."
    )
    zip_code = models.CharField(
        max_length=20,
        blank=True, null=True,
        help_text="Postal / ZIP code."
    )
    country  = models.CharField(
        max_length=100,
        default='USA',
        blank=True,
        help_text="Country name (default: USA)."
    )

    class Meta:
        verbose_name = "Address"
        verbose_name_plural = "Addresses"

    def __str__(self):
        parts = [self.street, self.city, self.state, self.zip_code, self.country]
        # only show the non‑empty bits
        return ", ".join([p for p in parts if p])


import hashlib

class PaymentCard(models.Model):
    user = models.ForeignKey('Users', on_delete=models.CASCADE, related_name='cards')
    card_type = models.CharField(max_length=20)
    name = models.CharField(
        max_length=100,
        help_text="Name on the card"
    )
    card_number_hash = models.CharField(max_length=64)  # SHA-256 hash
    last4 = models.CharField(max_length=4)
    expiration_date = models.CharField(
        max_length=5,
        help_text="Expiration date in MM/YY format, e.g. 02/23"
    )
    cvv_hash = models.CharField(
        max_length=64,
        help_text="SHA-256 hash of the card CVV"
    )
    zipcode = models.CharField(
        max_length=20,
        help_text="Billing ZIP/postal code"
    )

    def __str__(self):
        return f"{self.user.email} - {self.card_type} ending in {self.last4}"
    
    def masked_number(self):
        return f"**** **** **** {self.last4}"
    
    @staticmethod
    def hash_card_number(card_number: str) -> str:
        return hashlib.sha256(card_number.encode()).hexdigest()
    
    @staticmethod
    def hash_cvv(cvv: str) -> str:
        return hashlib.sha256(cvv.encode()).hexdigest()