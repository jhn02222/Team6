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
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'input-auth'}),
        required=False
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'input-auth'}),
        required=False
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'input-auth'}),
        required=False
    )

    def clean(self):
        cleaned_data = super().clean()
        old = cleaned_data.get("old_password")
        new1 = cleaned_data.get("new_password1")
        new2 = cleaned_data.get("new_password2")

        if new1 or new2:
            if not old:
                self.add_error("old_password", "Enter your current password.")
            if not new1:
                self.add_error("new_password1", "Enter a new password.")
            if not new2:
                self.add_error("new_password2", "Confirm your new password.")
        return cleaned_data

from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth import get_user_model

class CustomPasswordResetForm(PasswordResetForm):
    def get_users(self, email):
        UserModel = get_user_model()
        return UserModel._default_manager.filter(
            email__iexact=email,
            status='Active'  
        )