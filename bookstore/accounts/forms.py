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
import re
import hashlib
from django import forms
from .models import PaymentCard

class PaymentCardForm(forms.ModelForm):
    CARD_TYPE_CHOICES = [
        ('', 'Select Card Type'),
        ('Visa', 'Visa'),
        ('Mastercard', 'Mastercard'),
        ('American Express', 'American Express'),
        ('Discover', 'Discover'),
    ]
    
    card_number = forms.CharField(
        max_length=19,
        min_length=12,
        widget=forms.TextInput(attrs={'class': 'input-auth'}),
        required=False,
        label="Card Number"
    )
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'input-auth'}),
        required=False,
        label="Name on Card"
    )
    expiration_date = forms.CharField(
        max_length=5,
        widget=forms.TextInput(attrs={'class': 'input-auth', 'placeholder': 'MM/YY'}),
        required=False,
        label="Expiration Date"
    )
    cvv = forms.CharField(
        max_length=3,
        min_length=3,
        widget=forms.PasswordInput(attrs={'class': 'input-auth', 'placeholder': 'CVV'}),
        required=False,
        label="CVV"
    )
    zipcode = forms.CharField(
        max_length=5,
        min_length=5,
        widget=forms.TextInput(attrs={'class': 'input-auth', 'placeholder': 'ZIP Code'}),
        required=False,
        label="ZIP Code"
    )
    card_type = forms.ChoiceField(
        choices=CARD_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'input-auth'}),
        required=False,
        label="Card Type"
    )

    class Meta:
        model = PaymentCard
        fields = ['card_type', 'name', 'card_number', 'expiration_date', 'cvv', 'zipcode']
        widgets = {
            'card_type':       forms.Select(attrs={'class': 'input-auth'}),
            'name':            forms.TextInput(attrs={'class': 'input-auth'}),
            'expiration_date': forms.TextInput(attrs={'class': 'input-auth', 'placeholder': 'MM/YY'}),
            'zipcode':         forms.TextInput(attrs={'class': 'input-auth', 'placeholder': 'ZIP Code'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If this is an existing card (has instance with pk), modify field requirements
        if self.instance and self.instance.pk:
            # For existing cards, show placeholder values but don't require re-entry
            self.fields['card_number'].widget.attrs['placeholder'] = f"**** **** **** {self.instance.last4}"
            self.fields['card_number'].widget.attrs['readonly'] = True
            self.fields['card_number'].help_text = "Card number cannot be changed for security reasons"
            
            self.fields['cvv'].widget.attrs['placeholder'] = "***"
            self.fields['cvv'].help_text = "Re-enter CVV only if updating card details"
            
            # Pre-populate other fields for existing cards
            if self.instance.card_type:
                self.fields['card_type'].initial = self.instance.card_type
            if self.instance.name:
                self.fields['name'].initial = self.instance.name
            if self.instance.expiration_date:
                self.fields['expiration_date'].initial = self.instance.expiration_date
            if self.instance.zipcode:
                self.fields['zipcode'].initial = self.instance.zipcode

    def clean(self):
        cleaned_data = super().clean()
        
        # Check if this is an existing card
        is_existing_card = self.instance and self.instance.pk
        
        if is_existing_card:
            # For existing cards, CVV is optional unless user explicitly wants to update it
            # Don't require CVV for existing cards at all
            pass
                
        else:
            # For new cards, check if any field has data
            has_data = any([
                cleaned_data.get('card_number', '').strip(),
                cleaned_data.get('card_type', '').strip(),
                cleaned_data.get('name', '').strip(),
                cleaned_data.get('expiration_date', '').strip(),
                cleaned_data.get('cvv', '').strip(),
                cleaned_data.get('zipcode', '').strip()
            ])
            
            # If form has any data, validate all required fields for new cards
            if has_data:
                required_fields = ['card_number', 'card_type', 'name', 'expiration_date', 'cvv', 'zipcode']
                for field in required_fields:
                    if not cleaned_data.get(field, '').strip():
                        self.add_error(field, f"{field.replace('_', ' ').title()} is required when adding a card.")
        
        return cleaned_data

    def clean_expiration_date(self):
        exp = self.cleaned_data.get('expiration_date', '')
        if exp and not re.match(r'^(0[1-9]|1[0-2])\/\d{2}$', exp):
            raise forms.ValidationError("Expiration date must be in MM/YY format.")
        return exp

    def clean_cvv(self):
        cvv = self.cleaned_data.get('cvv', '')
        if cvv and (not cvv.isdigit() or len(cvv) != 3):
            raise forms.ValidationError("CVV must be exactly 3 digits.")
        return cvv

    def clean_zipcode(self):
        zipcode = self.cleaned_data.get('zipcode', '')
        if zipcode and (not zipcode.isdigit() or len(zipcode) != 5):
            raise forms.ValidationError("ZIP code must be exactly 5 digits.")
        return zipcode

    def clean_card_number(self):
        card_number = self.cleaned_data.get('card_number', '')
        
        # For existing cards, keep the original card number (don't change it)
        if self.instance and self.instance.pk:
            # Return None to indicate this field shouldn't be updated
            return None
            
        if card_number and (not card_number.isdigit() or not (12 <= len(card_number) <= 19)):
            raise forms.ValidationError("Enter a valid card number (12–19 digits).")
        return card_number

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Handle existing vs new cards differently
        if self.instance and self.instance.pk:
            # For existing cards, only update fields that were actually changed
            print(f"DEBUG: Processing existing card {self.instance.pk}")
            print(f"DEBUG: Cleaned data: {self.cleaned_data}")
            print(f"DEBUG: Changed data: {self.changed_data}")
            
            # Only update fields that are in changed_data (excluding card_number)
            for field_name in ['card_type', 'name', 'expiration_date', 'zipcode']:
                if field_name in self.changed_data:
                    setattr(instance, field_name, self.cleaned_data.get(field_name))
                    print(f"DEBUG: Updated {field_name} to {self.cleaned_data.get(field_name)}")
            
            # Handle CVV separately - only update if provided
            cvv = self.cleaned_data.get('cvv')
            if cvv:  # Only if CVV was explicitly entered
                import hashlib
                new_hash = hashlib.sha256(cvv.encode()).hexdigest()
                instance.cvv_hash = new_hash
                print(f"DEBUG: CVV hash updated to {new_hash}")
                
        else:
            print("DEBUG: Processing new card")
            # For new cards, set all fields
            card_number = self.cleaned_data.get('card_number')
            cvv = self.cleaned_data.get('cvv')
            
            instance.card_type = self.cleaned_data.get('card_type')
            instance.name = self.cleaned_data.get('name')
            instance.expiration_date = self.cleaned_data.get('expiration_date')
            instance.zipcode = self.cleaned_data.get('zipcode')

            if card_number:
                import hashlib
                instance.card_number_hash = hashlib.sha256(card_number.encode()).hexdigest()
                instance.last4 = card_number[-4:]
            if cvv:
                instance.cvv_hash = hashlib.sha256(cvv.encode()).hexdigest()
                print(f"DEBUG: New card CVV hash: {instance.cvv_hash}")

        if commit:
            print(f"DEBUG: Saving instance to database")
            instance.save()
            print(f"DEBUG: Instance saved successfully")
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