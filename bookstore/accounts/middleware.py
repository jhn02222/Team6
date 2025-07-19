from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

class SessionExpiryMiddleware(MiddlewareMixin):
    """
    Custom middleware to handle session expiry based on remember_me setting
    """
    def process_response(self, request, response):
        """
        Process the response to set proper session cookie expiry
        """
        if hasattr(request, 'session') and request.session.session_key:
            # Check if remember_me preference is set in session
            remember_me = request.session.get('remember_me', False)
            
            if remember_me:
                # User wants to be remembered - set persistent cookie
                max_age = getattr(settings, 'SESSION_COOKIE_AGE', 1209600)  # 2 weeks default
                response.set_cookie(
                    settings.SESSION_COOKIE_NAME,
                    request.session.session_key,
                    max_age=max_age,
                    expires=None,  # Let max_age handle expiry
                    domain=settings.SESSION_COOKIE_DOMAIN,
                    path=settings.SESSION_COOKIE_PATH,
                    secure=settings.SESSION_COOKIE_SECURE,
                    httponly=settings.SESSION_COOKIE_HTTPONLY,
                    samesite=settings.SESSION_COOKIE_SAMESITE,
                )
            else:
                # User didn't check remember me - session-only cookie
                response.set_cookie(
                    settings.SESSION_COOKIE_NAME,
                    request.session.session_key,
                    max_age=None,  # Session-only cookie
                    expires=None,  # Session-only cookie
                    domain=settings.SESSION_COOKIE_DOMAIN,
                    path=settings.SESSION_COOKIE_PATH,
                    secure=settings.SESSION_COOKIE_SECURE,
                    httponly=settings.SESSION_COOKIE_HTTPONLY,
                    samesite=settings.SESSION_COOKIE_SAMESITE,
                )
        
        return response