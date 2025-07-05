from django import forms
from .models import Book

class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = '__all__'
        widgets = {
            'isbn': forms.TextInput(attrs={'class': 'form-input'}),
            'title': forms.TextInput(attrs={'class': 'form-input'}),
            'author': forms.TextInput(attrs={'class': 'form-input'}),
            'category': forms.TextInput(attrs={'class': 'form-input'}),
            'edition': forms.TextInput(attrs={'class': 'form-input'}),
            'publisher': forms.TextInput(attrs={'class': 'form-input'}),
            'publication_year': forms.NumberInput(attrs={'class': 'form-input'}),
            'cover_image': forms.URLInput(attrs={'class': 'form-input'}),
            'quantity_in_stock': forms.NumberInput(attrs={'class': 'form-input'}),
            'minimum_threshold': forms.NumberInput(attrs={'class': 'form-input'}),
            'buying_price': forms.NumberInput(attrs={'class': 'form-input'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'release_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
        }
       