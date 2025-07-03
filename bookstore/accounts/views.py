from django.shortcuts import render, redirect
from .forms import SignUpForm, LoginForm
from .models import Users
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.conf import settings
from django.http import HttpResponse
import uuid
from bookstore.utils import custom_login_required, staff_required
from django.contrib.auth import logout
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from .forms import EditProfileForm, CustomPasswordChangeForm

verification_tokens = {}  # Ideally, store in a real model

def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.status = "Inactive"
            user.set_password(form.cleaned_data['password'])
            user.save()

            token = get_random_string(32)
            verification_tokens[token] = user.email

            verification_link = f"http://127.0.0.1:8000/accounts/verify-email/{token}/"
            send_mail(
                subject='Verify your email',
                message=f'Click to verify your account: {verification_link}',
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'webmaster@localhost'),
                recipient_list=[user.email]
            )
            return render(request, 'accounts/email_sent.html')
    else:
        form = SignUpForm()
    return render(request, 'accounts/signup.html', {'form': form})


def verify_email(request, token):
    email = verification_tokens.get(token)
    if email:
        user = Users.objects.get(email=email)
        user.status = "Active"
        if not user.account_id:
            user.account_id = uuid.uuid4()
        user.save()
        del verification_tokens[token]
        return render(request, 'accounts/verified.html', {'account_id': user.account_id})
    return render(request, 'accounts/invalid_token.html')


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data['identifier']
            password = form.cleaned_data['password']
            user = None

            # Try to find user by email
            try:
                user = Users.objects.get(email=identifier)
            except Users.DoesNotExist:
                # Try to parse as UUID and fetch by account_id
                try:
                    uuid_obj = uuid.UUID(identifier)
                    user = Users.objects.get(account_id=uuid_obj)
                except (Users.DoesNotExist, ValueError):
                    user = None

            if not user:
                messages.error(request, 'No user found with that email or account ID.')
            elif not user.check_password(password):
                messages.error(request, 'Incorrect password.')
            elif user.status == "Suspended":
                messages.error(request, 'Your account has been suspended. Please contact support.')
            elif user.status == "Inactive":
                # Resend verification email
                token = get_random_string(32)
                verification_tokens[token] = user.email
                verification_link = f"http://127.0.0.1:8000/accounts/verify-email/{token}/"
                send_mail(
                    subject='Verify your email',
                    message=f'Click to verify your account: {verification_link}',
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'webmaster@localhost'),
                    recipient_list=[user.email]
                )
                messages.warning(request, 'Please verify your email. A new verification link has been sent.')
            else:
                login(request, user)
                return redirect('admin' if user.is_staff or user.is_superuser else 'store_home')

    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})

def login_success(request):
    return HttpResponse("Yay! You're in. This is the login success page.")


@staff_required
def admin_home(request):
    return render(request, 'admin/home.html')

def unauthorized(request):
    return render(request, 'accounts/unauthorized.html')

@custom_login_required
def profile_view(request):
    user = request.user
    if request.method == 'POST':
        profile_form = EditProfileForm(request.POST, instance=user)
        password_form = CustomPasswordChangeForm(user, request.POST)

        if profile_form.is_valid() and password_form.is_valid():
            profile_form.save()
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Profile and password updated successfully!')
            return redirect('profile')
    else:
        profile_form = EditProfileForm(instance=user)
        password_form = CustomPasswordChangeForm(user)

    return render(request, 'accounts/profile.html', {
        'user': user,
        'profile_form': profile_form,
        'password_form': password_form
    })


def logout_view(request):
    logout(request)
    return redirect('store_home') 

