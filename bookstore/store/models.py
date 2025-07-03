from django.db import models
from django.contrib.auth import get_user_model
from django.db import models

class Book(models.Model):
    isbn = models.CharField(max_length=13, unique=True)
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    edition = models.CharField(max_length=20)
    publisher = models.CharField(max_length=100)
    publication_year = models.PositiveIntegerField()
    cover_image = models.URLField()  # ✅ using URL for now instead of file upload
    quantity_in_stock = models.PositiveIntegerField()
    minimum_threshold = models.PositiveIntegerField()
    buying_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_featured = models.BooleanField(default=False, db_index=True)
    release_date = models.DateField(null=True, blank=True, db_index=True)
    def __str__(self):
        return self.title

User = get_user_model()

class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey('Book', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    shipping_address = models.TextField()
    payment_card_last4 = models.CharField(max_length=4)
    total_before_tax = models.DecimalField(max_digits=10, decimal_places=2)
    total_after_tax = models.DecimalField(max_digits=10, decimal_places=2)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    book = models.ForeignKey('Book', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price_each = models.DecimalField(max_digits=10, decimal_places=2)
