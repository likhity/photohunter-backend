from django.utils.deprecation import MiddlewareMixin
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


class DisableCSRFMiddleware(MiddlewareMixin):
    """
    Middleware to disable CSRF protection for API endpoints.
    Since we're using JWT authentication, CSRF protection is not needed.
    """
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        # Disable CSRF for all API endpoints
        if request.path.startswith('/api/'):
            setattr(request, '_dont_enforce_csrf_checks', True)
        return None
