from django import forms
from .models import Users
from django.contrib.auth.forms import PasswordChangeForm

class SignUpForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'input-auth'}))

    class Meta:
        model = Users
        fields = ['email', 'name', 'phone', 'shipping_address', 'card_type', 'card_number', 'expiration_date', 'password']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'input-auth'}),
            'name': forms.TextInput(attrs={'class': 'input-auth'}),
            'phone': forms.TextInput(attrs={'class': 'input-auth'}),
            'shipping_address': forms.Textarea(attrs={'class': 'input-auth', 'rows': 3}),
            'card_type': forms.TextInput(attrs={'class': 'input-auth'}),
            'card_number': forms.TextInput(attrs={'class': 'input-auth'}),
            'expiration_date': forms.TextInput(attrs={'class': 'input-auth'}),
        }

class LoginForm(forms.Form):
    identifier = forms.CharField(label="Email or Account ID", widget=forms.TextInput(attrs={'class': 'input-auth'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'input-auth'}))

class EditProfileForm(forms.ModelForm):
    class Meta:
        model = Users
        fields = ['name', 'phone', 'shipping_address', 'card_type', 'card_number', 'expiration_date']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input-auth'}),
            'phone': forms.TextInput(attrs={'class': 'input-auth'}),
            'shipping_address': forms.Textarea(attrs={'class': 'input-auth', 'rows': 3}),
            'card_type': forms.TextInput(attrs={'class': 'input-auth'}),
            'card_number': forms.TextInput(attrs={'class': 'input-auth'}),
            'expiration_date': forms.TextInput(attrs={'class': 'input-auth'}),
        }

class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'input-auth'}))
    new_password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'input-auth'}))
    new_password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'input-auth'}))