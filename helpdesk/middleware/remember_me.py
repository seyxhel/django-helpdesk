from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import login as auth_login
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
from helpdesk.models import RememberMeToken
import hashlib
import hmac

User = get_user_model()


class RememberMeMiddleware(MiddlewareMixin):
    COOKIE_NAME = getattr(settings, 'HELPDESK_REMEMBER_COOKIE_NAME', 'helpdesk_remember')
    COOKIE_AGE = getattr(settings, 'HELPDESK_REMEMBER_DURATION', 60 * 60 * 24 * 30)  # 30 days

    def process_request(self, request):
        if request.user.is_authenticated:
            return

        cookie = request.COOKIES.get(self.COOKIE_NAME)
        if not cookie:
            return

        try:
            user_id, token = cookie.split(':', 1)
            user = User.objects.filter(pk=int(user_id)).first()
            if not user:
                return
            # compute hash and compare securely
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            rm = RememberMeToken.objects.filter(user=user, token_hash=token_hash).first()
            if not rm:
                return
            # update last_used
            rm.last_used = timezone.now()
            rm.save(update_fields=['last_used'])
            # log the user in
            user.backend = settings.AUTHENTICATION_BACKENDS[0]
            auth_login(request, user)
        except Exception:
            return
