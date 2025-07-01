from django import forms
from .models import Users
from django.contrib.auth.forms import PasswordChangeForm

class SignUpForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = Users
        fields = ['email', 'name', 'phone', 'shipping_address', 'card_type', 'card_number', 'expiration_date', 'password']

class LoginForm(forms.Form):
    identifier = forms.CharField(label="Email or Account ID")
    password = forms.CharField(widget=forms.PasswordInput)

class EditProfileForm(forms.ModelForm):
    class Meta:
        model = Users
        fields = ['name', 'phone', 'shipping_address', 'card_type', 'card_number', 'expiration_date']

class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(widget=forms.PasswordInput)
    new_password1 = forms.CharField(widget=forms.PasswordInput)
    new_password2 = forms.CharField(widget=forms.PasswordInput)
