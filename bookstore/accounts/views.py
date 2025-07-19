from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.cache import cache
import uuid
import logging
from django.views.decorators.http import require_POST
from bookstore.store.models import CartItem, Book
from django.views.decorators.csrf import csrf_protect
from django.middleware.csrf import rotate_token

from .forms import (
    SignUpForm, LoginForm, EditProfileForm, CustomPasswordChangeForm,
    AddressForm, PaymentCardForm
)
from .models import Users, Address, PaymentCard
from bookstore.utils import custom_login_required, staff_required

# Setup logging
logger = logging.getLogger(__name__)

# ------------------------------
# SIGN UP
# ------------------------------
@require_http_methods(["GET", "POST"])
def signup_view(request):
    """Handle user registration with email verification"""
    if request.user.is_authenticated:
        return redirect('store_home')
    
    if request.method == 'POST':
        user_form = SignUpForm(request.POST)
        address_form = AddressForm(request.POST)
        card_forms = [PaymentCardForm(request.POST, prefix=str(i)) for i in range(4)]

        # Validate all forms
        forms_valid = (
            user_form.is_valid() and 
            address_form.is_valid() and 
            all(cf.is_valid() or not cf.has_changed() for cf in card_forms)
        )

        if forms_valid:
            try:
                with transaction.atomic():
                    # Create user
                    user = user_form.save(commit=False)
                    user.status = "Inactive"
                    user.set_password(user_form.cleaned_data['password'])
                    user.save()

                    # Save address
                    address = address_form.save(commit=False)
                    address.user = user
                    address.save()

                    # Save payment cards (only non-empty ones)
                    cards_saved = 0
                    for cf in card_forms:
                        if cf.cleaned_data.get('card_number'):
                            card = cf.save(commit=False)
                            card.user = user
                            card.save()
                            cards_saved += 1

                    # Send verification email
                    if _send_verification_email(request, user):
                        logger.info(f"User {user.email} registered successfully with {cards_saved} payment cards")
                        return render(request, 'accounts/email_sent.html', {'email': user.email})
                    else:
                        messages.error(request, 'Account created but verification email failed to send. Please contact support.')
                        return redirect('login')
                        
            except Exception as e:
                logger.error(f"Error during signup: {str(e)}")
                messages.error(request, 'An error occurred during registration. Please try again.')
        else:
            # Log form errors for debugging
            logger.warning(f"Signup form validation failed: {user_form.errors}, {address_form.errors}")
            messages.error(request, 'Please correct the errors below.')
    else:
        user_form = SignUpForm()
        address_form = AddressForm()
        card_forms = [PaymentCardForm(prefix=str(i)) for i in range(4)]

    return render(request, 'accounts/signup.html', {
        'form': user_form,
        'address_form': address_form,
        'card_forms': card_forms
    })

def _send_verification_email(request, user):
    """Send verification email to user"""
    try:
        token = get_random_string(32)
        cache.set(f'verify_token_{token}', user.email, 86400)
        verification_link = request.build_absolute_uri(
            reverse('verify_email', args=[token])
        )
        send_mail(
            subject='Verify your email – Bookstore',
            message=f'Click to verify:\n\n{verification_link}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        return True
    except Exception:
        return False

# ------------------------------
# EMAIL VERIFICATION
# ------------------------------
@require_http_methods(["GET"])
def verify_email(request, token):
    """Verify user email with token"""
    try:
        email = cache.get(f'verify_token_{token}')
        if not email:
            return render(request, 'accounts/invalid_token.html', {
                'message': 'Invalid or expired verification link.'
            })

        user = get_object_or_404(Users, email=email)
        
        if user.status == "Active":
            messages.info(request, 'Your account is already verified.')
            return redirect('login')
        
        with transaction.atomic():
            user.status = "Active"
            if not user.account_id:
                user.account_id = uuid.uuid4()
            user.save()
            
        # Remove token from cache
        cache.delete(f'verify_token_{token}')
        
        logger.info(f"User {user.email} verified successfully")
        return render(request, 'accounts/verified.html', {'account_id': user.account_id})
        
    except Users.DoesNotExist:
        logger.warning(f"Verification attempted for non-existent user with token: {token}")
        return render(request, 'accounts/invalid_token.html', {
            'message': 'User not found.'
        })
    except Exception as e:
        logger.error(f"Error during email verification: {str(e)}")
        return render(request, 'accounts/invalid_token.html', {
            'message': 'An error occurred during verification.'
        })

# ------------------------------
# LOGIN
# ------------------------------
# Replace your login_view function with this corrected version:

# Replace your login_view function with this final version:

@require_http_methods(["GET", "POST"])
@never_cache
def login_view(request):
    """Handle user login with optional 'remember me'."""
    if request.user.is_authenticated:
        return redirect('store_home')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data['identifier'].strip()
            password = form.cleaned_data['password']
            remember_me = form.cleaned_data['remember_me']
            
            user = _find_user_by_identifier(identifier)
            
            if not user:
                messages.error(request, 'No user found with that email or account ID.')
            elif not user.check_password(password):
                messages.error(request, 'Incorrect password.')
            elif user.status == "Suspended":
                messages.error(request, 'Your account has been suspended.')
            elif user.status == "Inactive":
                _send_verification_email(request, user)
                messages.warning(request, 'Please verify your email; we sent you another link.')
            else:
                # Log in the user
                login(request, user)

                # Set session expiry based on remember_me
                if remember_me:
                    # Keep logged in for 2 weeks (or whatever SESSION_COOKIE_AGE is set to)
                    request.session.set_expiry(settings.SESSION_COOKIE_AGE)
                    request.session['remember_me'] = True
                else:
                    # Expire when browser closes
                    request.session.set_expiry(0)
                    request.session['remember_me'] = False

                merge_session_cart(request, user)
                logger.info(f"User {user.email} logged in successfully (remember_me: {remember_me})")
                
                # Redirect
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                if user.is_staff or user.is_superuser:
                    return redirect('admin_home')
                return redirect('store_home')
    else:
        form = LoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})

# Also add this view to check session status (for debugging)
@login_required
def session_debug(request):
    """Debug view to check session expiry settings"""
    session_info = {
        'session_key': request.session.session_key,
        'remember_me': request.session.get('remember_me', False),
        'session_expiry': request.session.get_expiry_age(),
        'session_expires_at_browser_close': request.session.get_expire_at_browser_close(),
    }
    return JsonResponse(session_info)

def _find_user_by_identifier(identifier):
    """Find user by email or account ID"""
    try:
        # Try email first
        return Users.objects.get(email=identifier)
    except Users.DoesNotExist:
        try:
            # Try UUID
            uuid_obj = uuid.UUID(identifier)
            return Users.objects.get(account_id=uuid_obj)
        except (Users.DoesNotExist, ValueError):
            return None

@require_http_methods(["GET", "POST"])
@csrf_protect
def logout_view(request):
    """Logout and reset CSRF token."""
    if request.user.is_authenticated:
        logger.info(f"User {request.user.email} logged out")
        logout(request)
        messages.success(request, 'You have been logged out successfully.')

    # Rotate the CSRF token (this sets a new one in the session)
    rotate_token(request)

    # Redirect to home
    return redirect('store_home')

# ------------------------------
# PROFILE
# ------------------------------
@custom_login_required
@require_http_methods(["GET", "POST"])
def profile_view(request):
    """Handle user profile management with email alerts on change"""
    user = request.user
    address_instance = getattr(user, 'address', None)
    card_qs = user.cards.all()

    updates = []

    if request.method == 'POST':
        profile_form = EditProfileForm(request.POST, instance=user)
        password_form = CustomPasswordChangeForm(user, request.POST)
        address_form = AddressForm(request.POST, instance=address_instance)
        card_forms = [
            PaymentCardForm(request.POST, prefix=str(i), instance=card_qs[i] if i < len(card_qs) else None)
            for i in range(4)
        ]

        password_change_requested = any([
            request.POST.get('old_password'),
            request.POST.get('new_password1'),
            request.POST.get('new_password2')
        ])

        profile_valid = profile_form.is_valid()
        address_valid = address_form.is_valid()
        cards_valid = all(cf.is_valid() or not cf.has_changed() for cf in card_forms)
        password_valid = password_form.is_valid() if password_change_requested else True

        if profile_valid and address_valid and cards_valid and password_valid:
            try:
                with transaction.atomic():
                    # Detect changes
                    if profile_form.has_changed():
                        updates.append("profile details")
                    if address_form.has_changed():
                        updates.append("address")
                        address = address_form.save(commit=False)
                        address.user = user
                        address.save()

                    profile_form.save()

                    address = address_form.save(commit=False)
                    address.user = user
                    address.save()

                    # Handle cards
                    card_changes = _handle_payment_cards(user, card_forms, card_qs)
                    if card_changes:
                        updates.append("payment method(s)")

                    # Handle password
                    if password_change_requested and password_valid:
                        updated_user = password_form.save()
                        update_session_auth_hash(request, updated_user)
                        updates.append("password")

                    messages.success(request, 'Profile updated successfully!')
                    logger.info(f"User {user.email} updated profile")

                    # Send notification if anything changed
                    if updates:
                        update_list = ", ".join(updates)
                        email_subject = "Confirmation: Your Bookstore Account Was Updated"
                        email_message = (
                            f"Dear {user.first_name or 'Customer'},\n\n"
                            f"We wanted to let you know that the following change(s) were made to your Bookstore account:\n"
                            f"• {update_list.capitalize()}\n\n"
                            f"If you made these changes, no further action is needed.\n"
                            f"If you did not authorize these changes, please contact our support team immediately.\n\n"
                            f"Thank you for using Bookstore.\n"
                            f"— The Bookstore Team"
                        )

                        send_mail(
                            subject=email_subject,
                            message=email_message,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[user.email],
                            fail_silently=True
                        )

                    return redirect('profile')

            except Exception as e:
                logger.error(f"Error updating profile for {user.email}: {str(e)}")
                messages.error(request, 'An error occurred while updating your profile.')
        else:
            if password_change_requested and not password_valid:
                messages.error(request, 'Password change failed. Please check your entries.')
            else:
                messages.error(request, 'Please correct the errors in the form.')
    else:
        profile_form = EditProfileForm(instance=user)
        password_form = CustomPasswordChangeForm(user)
        address_form = AddressForm(instance=address_instance)
        card_forms = [
            PaymentCardForm(prefix=str(i), instance=card_qs[i] if i < len(card_qs) else None)
            for i in range(4)
        ]

    return render(request, 'accounts/profile.html', {
        'user': user,
        'profile_form': profile_form,
        'password_form': password_form,
        'address_form': address_form,
        'card_forms': card_forms,
    })


def _handle_payment_cards(user, card_forms, existing_cards):
    """Handle creation, update, deletion of payment cards"""
    changed = False
    existing_cards_list = list(existing_cards)

    for i, cf in enumerate(card_forms):
        if not cf.has_changed():
            continue  # Skip unmodified forms to avoid accidental deletion

        card_number = cf.cleaned_data.get('card_number')
        if card_number:
            card = cf.save(commit=False)
            card.user = user
            card.save()
            changed = True
        elif i < len(existing_cards_list):
            existing_cards_list[i].delete()
            logger.info(f"Deleted payment card for {user.email}")
            changed = True

    return changed


# ------------------------------
# STAFF ADMIN DASHBOARD
# ------------------------------
@staff_required
@require_http_methods(["GET"])
def admin_home(request):
    """Staff admin dashboard"""
    return render(request, 'admin/home.html')

@require_http_methods(["GET"])
def unauthorized(request):
    """Unauthorized access page"""
    return render(request, 'accounts/unauthorized.html')

@login_required
@require_http_methods(["GET"])
def login_success(request):
    """Login success page"""
    return HttpResponse("Yay! You're in. This is the login success page.")

# ------------------------------
# API ENDPOINTS (Optional)
# ------------------------------
@require_http_methods(["POST"])
def resend_verification(request):
    """Resend verification email"""
    if request.method == 'POST':
        email = request.POST.get('email')
        if not email:
            return JsonResponse({'error': 'Email is required'}, status=400)
        
        try:
            user = Users.objects.get(email=email, status='Inactive')
            if _send_verification_email(request, user):
                return JsonResponse({'success': 'Verification email sent'})
            else:
                return JsonResponse({'error': 'Failed to send email'}, status=500)
        except Users.DoesNotExist:
            return JsonResponse({'error': 'User not found or already active'}, status=404)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
@require_POST
def delete_card(request, card_id):
    try:
        card = PaymentCard.objects.get(pk=card_id, user=request.user)
        card.delete()
        return JsonResponse({'success': True})
    except PaymentCard.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Card not found or unauthorized'}, status=404)
    

def merge_session_cart(request, user):
    """Merge session cart into the database cart for the authenticated user"""
    session_cart = request.session.get('cart', {})
    for book_id_str, quantity in session_cart.items():
        try:
            book = Book.objects.get(id=int(book_id_str))
            cart_item, created = CartItem.objects.get_or_create(user=user, book=book)
            cart_item.quantity += quantity
            cart_item.save()
        except Book.DoesNotExist:
            continue  # Ignore invalid book IDs
    # Clear session cart after merging
    request.session['cart'] = {}