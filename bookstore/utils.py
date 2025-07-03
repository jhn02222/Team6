from functools import wraps
from django.shortcuts import redirect

def custom_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        print("User:", request.user)
        print("Authenticated:", request.user.is_authenticated)
        print("Staff:", request.user.is_staff)
        print("Superuser:", request.user.is_superuser)

        if not request.user.is_authenticated:
            return redirect('/accounts/unauthorized/')
        return view_func(request, *args, **kwargs)
    return wrapper

def staff_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        print("User:", request.user)
        print("Authenticated:", request.user.is_authenticated)
        print("Staff:", request.user.is_staff)
        print("Superuser:", request.user.is_superuser)
        if not (request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)):
            return redirect('/accounts/unauthorized/')
        return view_func(request, *args, **kwargs)
    return wrapper
