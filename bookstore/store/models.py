from django.db import models
from django.conf import settings
from django.utils.crypto import get_random_string

class Book(models.Model):
    isbn = models.CharField(max_length=13, unique=True)
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    edition = models.CharField(max_length=20)
    publisher = models.CharField(max_length=100)
    publication_year = models.PositiveIntegerField()
    cover_image = models.URLField()
    quantity_in_stock = models.PositiveIntegerField()
    minimum_threshold = models.PositiveIntegerField()
    buying_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_featured = models.BooleanField(default=False, db_index=True)
    release_date = models.DateField(null=True, blank=True, db_index=True)
    rating = models.DecimalField(
        max_digits=3, decimal_places=2, null=True, blank=True, default=None
    )
    def __str__(self):
        return self.title


class CartItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        to_field='account_id',
        db_column='account_id'
    )
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)


def generate_order_id():
    return get_random_string(12).upper()

class Order(models.Model):
    order_id = models.CharField(
        primary_key=True,
        max_length=12,
        unique=True,
        editable=False,
        default=generate_order_id 
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        to_field='account_id',
        db_column='account_id'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    shipping_address = models.TextField()
    payment_card_last4 = models.CharField(max_length=4)
    total_before_tax = models.DecimalField(max_digits=10, decimal_places=2)
    total_after_tax = models.DecimalField(max_digits=10, decimal_places=2)


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        to_field='order_id',
        db_column='order_id',
        related_name='items'
    )
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price_each = models.DecimalField(max_digits=10, decimal_places=2)