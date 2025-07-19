from django import forms
from django.contrib.auth.forms import PasswordChangeForm, PasswordResetForm
from django.contrib.auth import get_user_model
from .models import Users, Address, PaymentCard


# -------------------------------
# SIGN UP FORM
# -------------------------------
class SignUpForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'input-auth'}))

    class Meta:
        model = Users
        fields = [
            'email', 'first_name', 'last_name', 'phone',
            'password', 'promotions_opt_in'
        ]
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'input-auth'}),
            'first_name': forms.TextInput(attrs={'class': 'input-auth'}),
            'last_name': forms.TextInput(attrs={'class': 'input-auth'}),
            'phone': forms.TextInput(attrs={'class': 'input-auth'}),
            'promotions_opt_in': forms.CheckboxInput(attrs={'class': 'input-auth'})
        }


# -------------------------------
# LOGIN FORM
# -------------------------------
class LoginForm(forms.Form):
    identifier = forms.CharField(
        label="Email or Account ID",
        widget=forms.TextInput(attrs={'class': 'input-auth'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'input-auth'})
    )
    remember_me = forms.BooleanField(
        required=False,
        initial=False,  # This ensures it defaults to False (unchecked)
        widget=forms.CheckboxInput(attrs={'class': 'remember-checkbox'}),
        label="Remember me"
    )

# -------------------------------
# EDIT PROFILE FORM
# -------------------------------
class EditProfileForm(forms.ModelForm):
    class Meta:
        model = Users
        fields = [
            'first_name', 'last_name', 'phone', 'promotions_opt_in'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'input-auth'}),
            'last_name': forms.TextInput(attrs={'class': 'input-auth'}),
            'phone': forms.TextInput(attrs={'class': 'input-auth'}),
            'promotions_opt_in': forms.CheckboxInput(attrs={'class': 'input-auth'}),
        }


# -------------------------------
# ADDRESS FORM (Separate Model)
# -------------------------------
class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['street', 'city', 'state', 'zip_code', 'country']


# -------------------------------
# PAYMENT CARD FORM (Separate Model)
# -------------------------------
import hashlib
from django import forms
from .models import PaymentCard

class PaymentCardForm(forms.ModelForm):
    card_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'input-auth'}),
        required=False
    )

    class Meta:
        model = PaymentCard
        fields = ['card_type', 'card_number', 'expiration_date']
        widgets = {
            'card_type':       forms.TextInput(attrs={'class': 'input-auth'}),
            'expiration_date': forms.TextInput(attrs={'class': 'input-auth'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make all fields optional to avoid validation errors in partially filled forms
        for field in self.fields.values():
            field.required = False

        # Allow entire form to be skipped
        if self.is_bound and self._is_completely_empty():
            self.empty_permitted = True

    def _is_completely_empty(self):
        return not any(
            self.data.get(f"{self.prefix}-{field}", "").strip()
            for field in self.fields
        )

    def clean(self):
        cleaned_data = super().clean()

        card_type = cleaned_data.get('card_type', '').strip()
        card_number = cleaned_data.get('card_number', '').strip()
        expiration_date = cleaned_data.get('expiration_date', '').strip()

        if card_type or card_number or expiration_date:
            if not card_type:
                self.add_error('card_type', 'Card type is required.')
            if not card_number:
                self.add_error('card_number', 'Card number is required.')
            elif not card_number.isdigit() or len(card_number) < 12 or len(card_number) > 19:
                self.add_error('card_number', 'Enter a valid card number (12–19 digits).')
            if not expiration_date:
                self.add_error('expiration_date', 'Expiration date is required.')

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        card_number = self.cleaned_data.get('card_number')

        if card_number:
            instance.card_number_hash = hashlib.sha256(card_number.encode()).hexdigest()
            instance.last4 = card_number[-4:]

        if commit:
            instance.save()
        return instance


# -------------------------------
# PASSWORD CHANGE FORM (Custom)
# -------------------------------
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

        # If none of the fields are filled, skip validation
        if not old and not new1 and not new2:
            self._errors = {}
            return cleaned_data

        # If any field is filled, require them all
        if new1 or new2 or old:
            if not old:
                self.add_error("old_password", "Enter your current password.")
            if not new1:
                self.add_error("new_password1", "Enter a new password.")
            if not new2:
                self.add_error("new_password2", "Confirm your new password.")
            elif new1 != new2:
                self.add_error("new_password2", "Passwords do not match.")

        return cleaned_data



# -------------------------------
# PASSWORD RESET FORM (Custom)
# -------------------------------
class CustomPasswordResetForm(PasswordResetForm):
    def get_users(self, email):
        UserModel = get_user_model()
        return UserModel._default_manager.filter(
            email__iexact=email,
            status='Active'
        )
