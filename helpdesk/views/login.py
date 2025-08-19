from django.conf import settings
from django.contrib.auth import authenticate, login as auth_login, get_user_model
from django.shortcuts import render, redirect, resolve_url
from django import forms
from django.utils.translation import gettext as _
from django.conf import settings
from helpdesk.models import RememberMeToken
import secrets, hashlib
from django.http import JsonResponse, HttpResponseForbidden
from django.core import signing
from helpdesk.models import RememberedCredentials

class CustomLoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Username or Email",
                "autofocus": "autofocus",
                "autocomplete": "username",
            }
        ),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Password",
                # discourage browser autofill / password managers
                "autocomplete": "new-password",
                "spellcheck": "false",
                "autocorrect": "off",
                "autocapitalize": "off",
                "data-lpignore": "true",
            }
        )
    )
    remember_me = forms.BooleanField(required=False)

def login(request):
    if request.user.is_authenticated:
        return redirect('helpdesk:home')

    form = CustomLoginForm(request.POST or None)
    # Ensure browser HTML5 required validation is disabled; use server-side validation instead
    for fname in ('username', 'password', 'remember_me'):
        if fname in form.fields:
            form.fields[fname].widget.attrs.pop('required', None)
    error_type = None
    if request.method == 'POST':
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            # Try authenticating by username first. If that fails, try resolving username as an email.
            candidate_used = False
            user = authenticate(request, username=username, password=password)
            if user is None:
                # Attempt to find a user with this email (case-insensitive), prefer active users
                User = get_user_model()
                candidate = User.objects.filter(email__iexact=username, is_active=True).first()
                if candidate:
                    user = authenticate(request, username=candidate.get_username(), password=password)
                    if user is not None:
                        # Mark that we authenticated via an email lookup so we can preserve the entered identifier
                        candidate_used = True
            if user is not None:
                auth_login(request, user)
                response = redirect('helpdesk:home')
                if form.cleaned_data.get('remember_me'):
                    request.session.set_expiry(60 * 60 * 24 * 30)  # 30 days
                    # create token and store hash
                    raw_token = secrets.token_urlsafe(32)
                    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
                    rm = RememberMeToken.objects.create(user=user, token_hash=token_hash, user_agent=request.META.get('HTTP_USER_AGENT','')[:300])
                    # create signed credentials and store
                    # store the identifier the user entered when logging in (email if they used it),
                    # otherwise use canonical username
                    store_identifier = username if candidate_used else user.get_username()
                    signed = signing.dumps({'username': store_identifier, 'password': password})
                    RememberedCredentials.objects.create(token=rm, signed_data=signed)
                    cookie_value = f"{user.pk}:{raw_token}"
                    response.set_cookie(getattr(settings, 'HELPDESK_REMEMBER_COOKIE_NAME', 'helpdesk_remember'), cookie_value, max_age=getattr(settings, 'HELPDESK_REMEMBER_DURATION', 60*60*24*30), httponly=True, secure=getattr(settings, 'SESSION_COOKIE_SECURE', False))
                else:
                    # User did not check remember_me: ensure any existing remember token for this cookie is removed
                    request.session.set_expiry(0)  # Browser close
                    cookie_name = getattr(settings, 'HELPDESK_REMEMBER_COOKIE_NAME', 'helpdesk_remember')
                    existing_cookie = request.COOKIES.get(cookie_name)
                    if existing_cookie:
                        try:
                            u_id, token = existing_cookie.split(':', 1)
                            token_hash = hashlib.sha256(token.encode()).hexdigest()
                            RememberMeToken.objects.filter(user__pk=int(u_id), token_hash=token_hash).delete()
                        except Exception:
                            pass
                        # delete cookie in response so it no longer persists in browser
                        response.delete_cookie(cookie_name)
                return response
            else:
                error_type = 'invalid_credentials'
        else:
            error_type = 'missing_fields'

    return render(request, 'helpdesk/registration/login.html', {'form': form, 'error_type': error_type})


def logout(request):
    # Clear remember-me tokens and cookie
    cookie_name = getattr(settings, 'HELPDESK_REMEMBER_COOKIE_NAME', 'helpdesk_remember')
    cookie = request.COOKIES.get(cookie_name)
    # Do not delete the remember-me cookie or token here so the login page
    # can still autofill credentials if the user chose 'Remember Password'.
    from django.contrib.auth import logout as auth_logout
    auth_logout(request)
    return redirect('helpdesk:home')


def remember_credentials(request):
    # Endpoint to return signed credentials if the remember cookie is valid
    cookie_name = getattr(settings, 'HELPDESK_REMEMBER_COOKIE_NAME', 'helpdesk_remember')
    cookie = request.COOKIES.get(cookie_name)
    if not cookie:
        return HttpResponseForbidden()
    try:
        user_id, token = cookie.split(':', 1)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        rm = RememberMeToken.objects.filter(user__pk=int(user_id), token_hash=token_hash).first()
        if not rm:
            return HttpResponseForbidden()
        # verify user agent matches (simple check)
        ua = request.META.get('HTTP_USER_AGENT', '')[:300]
        if rm.user_agent and ua and not ua.startswith(rm.user_agent[:50]):
            # possible client mismatch
            return HttpResponseForbidden()
        # load signed data and return plaintext credentials
        signed = rm.credentials.signed_data
        try:
            data = signing.loads(signed)
        except Exception:
            return HttpResponseForbidden()
        # Only return username/password over HTTPS in production; caller should use secure connection
        return JsonResponse({'username': data.get('username'), 'password': data.get('password')})
    except Exception:
        return HttpResponseForbidden()
