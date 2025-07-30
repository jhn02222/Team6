from django import forms
from .models import Book

class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = [
            'isbn', 'title', 'author', 'category', 'edition', 
            'publisher', 'publication_year', 'cover_image',
            'quantity_in_stock', 'minimum_threshold', 'buying_price',
            'selling_price', 'is_featured', 'release_date', 'rating'
        ]
        widgets = {
            'release_date': forms.DateInput(attrs={'type': 'date'}),
            'rating': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '5'}),
            'publication_year': forms.NumberInput(attrs={'min': '1000', 'max': '2030'}),
        }
from .models import Promotion

class PromotionForm(forms.ModelForm):
    class Meta:
        model = Promotion
        fields = ['promo_code', 'percentage', 'start_date', 'expiration_date']