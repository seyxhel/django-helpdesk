"""
django-helpdesk - A Django powered ticket tracker for small enterprise.

(c) Copyright 2008-2025 Jutda. All Rights Reserved. See LICENSE for details.

views/public.py - All public facing views, eg non-staff (no authentication
                  required) views.
"""

from django.conf import settings
from django.contrib.auth import views as auth_views
from django.core.exceptions import (
    ImproperlyConfigured,
    ObjectDoesNotExist,
    PermissionDenied,
)
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView
from helpdesk import settings as helpdesk_settings
from helpdesk.decorators import is_helpdesk_staff, protect_view
from helpdesk.lib import text_is_spam
from helpdesk.models import Queue, Ticket, UserSettings
from helpdesk.user import huser_from_request
import helpdesk.views.abstract_views as abstract_views
import helpdesk.views.staff as staff
from importlib import import_module
import logging
import os
import smtplib
from urllib.parse import quote
from django.urls import reverse_lazy
from django.views.generic.edit import FormView
from django.core import mail
from helpdesk.forms import RegistrationForm
from helpdesk.forms import AddUserForm
from django.db import IntegrityError, transaction
from django.contrib.auth import get_user_model, login


logger = logging.getLogger(__name__)


def create_ticket(request, *args, **kwargs):
    if is_helpdesk_staff(request.user):
        return staff.CreateTicketView.as_view()(request, *args, **kwargs)
    else:
        return protect_view(CreateTicketView.as_view())(request, *args, **kwargs)


class BaseCreateTicketView(abstract_views.AbstractCreateTicketMixin, FormView):
    # Provide a sensible default redirect for non-iframe public submissions so
    # FormView.post() can resolve a success URL and avoid ImproperlyConfigured
    # when no explicit redirect is returned by form_valid().
    success_url = reverse_lazy("helpdesk:home")

    def form_valid(self, form):
        """
        Persist the ticket using the form's save() method. The public form
        returns the created Ticket instance. Store it on the view so
        get_success_url() can return the ticket's public URL.
        """
        # Pass the authenticated user if present so assigned-to logic can run
        user = self.request.user if self.request.user.is_authenticated else None
        try:
            self.ticket = form.save(user=user)
        except TypeError:
            # Some custom form classes might not accept a user argument;
            # fall back to calling save() without arguments.
            self.ticket = form.save()
        return super().form_valid(form)

    def get_success_url(self):
        """Prefer redirecting to the ticket's public URL when available."""
        if getattr(self, "ticket", None):
            try:
                return self.ticket.ticket_url
            except Exception:
                pass
        return super().get_success_url()
    def get_form_class(self):
        try:
            the_module, the_form_class = (
                helpdesk_settings.HELPDESK_PUBLIC_TICKET_FORM_CLASS.rsplit(".", 1)
            )
            the_module = import_module(the_module)
            the_form_class = getattr(the_module, the_form_class)
        except Exception as e:
            raise ImproperlyConfigured(
                f"Invalid custom form class {helpdesk_settings.HELPDESK_PUBLIC_TICKET_FORM_CLASS}"
            ) from e
        return the_form_class

    def dispatch(self, *args, **kwargs):
        request = self.request
        if (
            not request.user.is_authenticated
            and helpdesk_settings.HELPDESK_REDIRECT_TO_LOGIN_BY_DEFAULT
        ):
            return HttpResponseRedirect(reverse("login"))

        if is_helpdesk_staff(request.user) or (
            request.user.is_authenticated
            and helpdesk_settings.HELPDESK_ALLOW_NON_STAFF_TICKET_UPDATE
        ):
            try:
                if request.user.usersettings_helpdesk.login_view_ticketlist:
                    return HttpResponseRedirect(reverse("helpdesk:list"))
                else:
                    return HttpResponseRedirect(reverse("helpdesk:dashboard"))
            except UserSettings.DoesNotExist:
                return HttpResponseRedirect(reverse("helpdesk:dashboard"))

        # If none of the above conditions returned, continue normal dispatch
        return super().dispatch(*args, **kwargs)


def initial_setup(request):
    """
    Initial setup view: if no superuser exists, present a form to create the
    first superuser. Once a superuser exists this view redirects to the home.
    """
    User = get_user_model()
    if User.objects.filter(is_superuser=True).exists():
        # Someone already created a superuser - redirect to normal home
        return HttpResponseRedirect(reverse("helpdesk:home"))

    if request.method == "POST":
        form = AddUserForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create user but disable the account app's automatic account/email creation
                    user = form.save(commit=False)
                    user._disable_account_creation = True
                    # Ensure the created account is a superuser and staff
                    user.is_superuser = True
                    user.is_staff = True
                    user.is_active = True
                    user.save()
                    try:
                        form.save_m2m()
                    except Exception:
                        pass

                    # If the optional `account` app is installed, create an Account
                    # without auto-adding the EmailAddress, then create the
                    # EmailAddress via get_or_create so we can detect duplicates
                    try:
                        from account.models import Account, EmailAddress

                        try:
                            # Create Account but do NOT auto-create an EmailAddress
                            Account.create(user=user, create_email=False)
                        except Exception:
                            logger.exception("Failed to create Account for initial setup user %s", user)

                        # Ensure EmailAddress exists and belongs to our user. If an
                        # EmailAddress with the same email exists for another user
                        # this will raise IntegrityError which we catch below and
                        # convert into a friendly form error.
                        try:
                            with transaction.atomic():
                                email_obj, created = EmailAddress.objects.get_or_create(
                                    email=user.email,
                                    defaults={"user": user, "verified": True, "primary": True},
                                )
                                if not created:
                                    # Existing EmailAddress found; if it belongs to a different
                                    # user that's a duplicate-email conflict.
                                    if getattr(email_obj, "user_id", None) != user.id:
                                        raise IntegrityError("account_emailaddress.email")
                                    # Otherwise ensure flags are set for this user
                                    email_obj.verified = True
                                    email_obj.primary = True
                                    if getattr(email_obj, "user", None) != user:
                                        email_obj.user = user
                                    email_obj.save()
                        except IntegrityError:
                            # Re-raise to be handled by outer block which will
                            # attach a form error and not crash the page.
                            raise
                    except ImportError:
                        # account app not installed — nothing further to do
                        pass

                    # Log the new superuser in and redirect to home
                    try:
                        login(request, user)
                    except Exception:
                        # Ignore login failures; still redirect
                        pass
                    return HttpResponseRedirect(reverse("helpdesk:home"))
            except IntegrityError as e:
                msg = str(e)
                if "account_emailaddress.email" in msg or "UNIQUE constraint failed: account_emailaddress.email" in msg:
                    form.add_error("email", "Invalid Email.")
                else:
                    form.add_error(None, _("A database error occurred. Please try again or contact support."))
    else:
        form = AddUserForm()

    return render(request, "helpdesk/setup_initial_superuser.html", {"form": form})



class SuccessIframeView(TemplateView):
    template_name = "helpdesk/success_iframe.html"

    @xframe_options_exempt
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class CreateTicketView(BaseCreateTicketView):
    template_name = "helpdesk/public_create_ticket.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Add the CSS error class to the form in order to better see them in
        # the page
        form.error_css_class = "text-danger"
        return form

    def get_success_url(self):
        """Redirect back to the homepage with a flag so we can show an inline toast.

        We prefer to show the ticket list on the home page rather than navigating
        immediately to the ticket public view so users get immediate confirmation
        and can see their newly created ticket there.
        """
        try:
            # Stay on the submit page so we can show the success overlay there,
            # then the client JS will redirect to the My Tickets page.
            return reverse("helpdesk:submit") + "?created=1"
        except Exception:
            return super().get_success_url()


class CreateTicketIframeView(BaseCreateTicketView):
    template_name = "helpdesk/public_create_ticket_iframe.html"

    @csrf_exempt
    @xframe_options_exempt
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def form_valid(self, form):
        if super().form_valid(form).status_code == 302:
            return HttpResponseRedirect(reverse("helpdesk:success_iframe"))


class Homepage(CreateTicketView):
    template_name = "helpdesk/public_homepage.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["kb_categories"] = huser_from_request(
            self.request
        ).get_allowed_kb_categories()
        # Provide the logged-in user's tickets so the public homepage can
        # render a pre-populated table of their existing tickets.
        try:
            user = self.request.user
            if user.is_authenticated and getattr(user, 'email', None):
                tickets = Ticket.objects.filter(submitter_email__iexact=user.email).order_by('-created')
            else:
                tickets = Ticket.objects.none()
            context['customer_tickets'] = tickets
        except Exception:
            context['customer_tickets'] = Ticket.objects.none()
        return context


class PublicUserSettingsView(LoginRequiredMixin, FormView):
    """Allow non-staff public users to edit their basic profile (username/email).

    Staff users are redirected to the staff EditUserSettingsView.
    """

    template_name = "helpdesk/public_user_settings.html"
    form_class = None
    success_url = reverse_lazy("helpdesk:home")

    def dispatch(self, request, *args, **kwargs):
        # Staff should continue to use the staff settings view
        if request.user.is_staff:
            return staff.EditUserSettingsView.as_view()(request, *args, **kwargs)

        # Lazy import to avoid circular imports at module load
        # Use the top-level helpdesk.forms module (not helpdesk.views.forms)
        from helpdesk.forms import PublicUserProfileForm

        self.form_class = PublicUserProfileForm
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        return {
            "username": self.request.user.username,
            "email": self.request.user.email,
            "first_name": self.request.user.first_name,
            "last_name": self.request.user.last_name,
        }

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"instance": self.request.user})
        return kwargs

    def form_valid(self, form):
        form.save()
        return HttpResponseRedirect(self.get_success_url())


class AdaptivePasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    """PasswordChangeView that uses `public_base.html` for non-staff users so
    the sidebar is not shown for customers.
    """

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Choose base template: staff keep the normal admin base; public users get public_base
        if self.request.user.is_staff:
            ctx["base_template"] = "helpdesk/base.html"
        else:
            ctx["base_template"] = "helpdesk/public_base.html"
        # Provide a page-scoped modified help_text for new_password1 so templates
        # can alter wording without using unsupported template filters.
        try:
            form = ctx.get('form', None)
            if form and hasattr(form, 'fields') and 'new_password1' in form.fields:
                original = form.fields['new_password1'].help_text
                if original:
                    # Replace only the English prefix; this is page-local and
                    # avoids touching translations globally.
                    ctx['new_password1_help_text'] = original.replace('Your password', 'Password')
        except Exception:
            # Silently ignore any unexpected issues when computing help text
            pass
        return ctx


class SearchForTicketView(TemplateView):
    template_name = "helpdesk/public_view_form.html"

    def get(self, request, *args, **kwargs):
        if (
            hasattr(settings, "HELPDESK_VIEW_A_TICKET_PUBLIC")
            and settings.HELPDESK_VIEW_A_TICKET_PUBLIC
        ):
            context = self.get_context_data(**kwargs)
            return self.render_to_response(context)
        else:
            raise PermissionDenied(
                "Public viewing of tickets without a secret key is forbidden."
            )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        email = request.GET.get("email", None)
        error_message = kwargs.get("error_message", None)

        context.update(
            {
                "ticket": False,
                "email": email,
                "error_message": error_message,
                "helpdesk_settings": helpdesk_settings,
            }
        )
        return context


class ViewTicket(TemplateView):
    template_name = "helpdesk/public_view_ticket.html"

    def get(self, request, *args, **kwargs):
        ticket_req = request.GET.get("ticket", None)
        email = request.GET.get("email", None)
        key = request.GET.get("key", "")

        if not (ticket_req and email):
            if ticket_req is None and email is None:
                return SearchForTicketView.as_view()(request)
            else:
                return SearchForTicketView.as_view()(
                    request, _("Missing ticket ID or e-mail address. Please try again.")
                )

        try:
            queue, ticket_id = Ticket.queue_and_id_from_query(ticket_req)
            if request.user.is_authenticated and request.user.email == email:
                ticket = Ticket.objects.get(id=ticket_id, submitter_email__iexact=email)
            elif (
                hasattr(settings, "HELPDESK_VIEW_A_TICKET_PUBLIC")
                and settings.HELPDESK_VIEW_A_TICKET_PUBLIC
            ):
                ticket = Ticket.objects.get(id=ticket_id, submitter_email__iexact=email)
            else:
                ticket = Ticket.objects.get(
                    id=ticket_id, submitter_email__iexact=email, secret_key__iexact=key
                )
        except (ObjectDoesNotExist, ValueError):
            return SearchForTicketView.as_view()(
                request, _("Invalid ticket ID or e-mail address. Please try again.")
            )

        if "close" in request.GET and ticket.status == Ticket.RESOLVED_STATUS:
            from helpdesk.update_ticket import update_ticket

            update_ticket(
                request.user,
                ticket,
                public=True,
                comment=_("Submitter accepted resolution and closed ticket"),
                new_status=Ticket.CLOSED_STATUS,
            )
            return HttpResponseRedirect(ticket.ticket_url)

        # Prepare context for rendering
        context = {
            "key": key,
            "mail": email,
            "ticket": ticket,
            "helpdesk_settings": helpdesk_settings,
            "next": self.get_next_url(ticket_id),
        }
        # For authenticated non-staff users, render inside the main site shell
        # so the sidebar and 'My Tickets' navigation remain visible.
        try:
            if request.user.is_authenticated and not request.user.is_staff:
                context["base_template"] = "helpdesk/base.html"
        except Exception:
            pass
        return self.render_to_response(context)

    def get_next_url(self, ticket_id):
        redirect_url = ""
        if is_helpdesk_staff(self.request.user):
            redirect_url = reverse("helpdesk:view", args=[ticket_id])
            if "close" in self.request.GET:
                redirect_url += "?close"
        elif helpdesk_settings.HELPDESK_NAVIGATION_ENABLED:
            redirect_url = reverse("helpdesk:view", args=[ticket_id])
        return redirect_url


class MyTickets(TemplateView):
    template_name = "helpdesk/my_tickets.html"

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseRedirect(reverse("helpdesk:login"))

        context = self.get_context_data(**kwargs)
        # Provide status choices to populate the status filter dropdown
        try:
            from helpdesk import settings as helpdesk_settings
            context['status_choices'] = helpdesk_settings.TICKET_STATUS_CHOICES
        except Exception:
            context['status_choices'] = []
        return self.render_to_response(context)


class RegisterView(FormView):
    """Public registration view that creates a normal user account."""

    template_name = "helpdesk/register.html"
    form_class = RegistrationForm
    success_url = reverse_lazy("helpdesk:login")

    def form_valid(self, form):
        # create the user
        form.save()
        # Render a success page that links to the login page and auto-redirects
        context = self.get_context_data()
        context["login_url"] = str(self.success_url)
        return render(self.request, "helpdesk/registration/register_done.html", context)


class HelpdeskPasswordResetView(auth_views.PasswordResetView):
    """PasswordResetView that ensures a valid from_email is provided when sending."""

    template_name = "helpdesk/password_reset.html"
    success_url = "./done"
    email_template_name = "helpdesk/registration/password_reset_email.html"
    subject_template_name = "helpdesk/registration/password_reset_subject.txt"

    def form_valid(self, form):
        # Choose a sane from_email so SMTP servers (Gmail) don't reject with 'None'.
        # Coerce literal 'None' or empty strings to missing and fall back to
        # EMAIL_HOST_USER, SERVER_EMAIL, or a safe default.
        def _coerce(val):
            if not val:
                return None
            if isinstance(val, str) and val.strip().lower() == "none":
                return None
            return val

        from_email = _coerce(getattr(settings, "DEFAULT_FROM_EMAIL", None))
        if not from_email:
            from_email = _coerce(getattr(settings, "EMAIL_HOST_USER", None))
        if not from_email:
            # SERVER_EMAIL is often set to a valid bounce/sender address
            from_email = _coerce(getattr(settings, "SERVER_EMAIL", None))
        if not from_email:
            # final fallback (local dev): use a recognisable default
            from_email = "webmaster@localhost"
        # Ensure we explicitly tell the form which email template to use so
        # the namespaced helpdesk template is rendered (avoids admin template
        # which may reference non-existent global URL names).
        opts = {
            "from_email": from_email,
            "email_template_name": "helpdesk/registration/password_reset_email.html",
            "html_email_template_name": "helpdesk/registration/password_reset_email_html.html",
        }
        # Ensure the reset link uses the current request host and protocol
        try:
            host = self.request.get_host()
        except Exception:
            host = None
        if host:
            opts["domain_override"] = host
            opts["use_https"] = self.request.is_secure()
            # Some Django versions accept the request argument to render URLs
            opts["request"] = self.request
            # Also provide a trimmed hostname (no port) for email templates
            try:
                host_only = host.split(":")[0]
            except Exception:
                host_only = host
            # extra_email_context is passed through to the email template rendering
            opts.setdefault("extra_email_context", {})
            opts["extra_email_context"]["domain_host"] = host_only
        # Also allow subject template override if present on the view
        if getattr(self, "subject_template_name", None):
            opts["subject_template_name"] = self.subject_template_name

        logger.info("password-reset: sending with from_email=%s opts=%s", from_email, opts)

        # Build a fresh mail connection and attempt explicit login so the
        # SMTP envelope is sent on an authenticated session. If login fails
        # fall back to default form.save() behavior.
        conn = mail.get_connection()
        try:
            conn.open()
        except Exception:
            # connection may be lazily opened later by the backend
            pass

        authenticated = False
        if hasattr(conn, 'connection') and conn.connection is not None:
            # Optionally enable smtplib debug output
            if os.environ.get('HELPDESK_SMTP_DEBUG') in ('1', 'true', 'True') or getattr(
                settings, 'HELPDESK_SMTP_DEBUG', False
            ):
                try:
                    conn.connection.set_debuglevel(1)
                except Exception:
                    logger.exception('Failed to set smtplib debuglevel')

            # Prefer explicit settings values for credentials
            username = getattr(settings, 'EMAIL_HOST_USER', None)
            password = getattr(settings, 'EMAIL_HOST_PASSWORD', None)
            if not username and hasattr(conn, 'username'):
                username = getattr(conn, 'username', None)
            if not password and hasattr(conn, 'password'):
                password = getattr(conn, 'password', None)

            if username and password:
                try:
                    # Ensure proper SMTP handshake: EHLO, optional STARTTLS, then AUTH.
                    try:
                        # Some backends require an explicit EHLO before STARTTLS/AUTH
                        conn.connection.ehlo()
                    except Exception:
                        # Not all connection wrappers expose ehlo; ignore failures
                        logger.debug('SMTP ehlo() failed or unavailable')

                    # If TLS is configured but not already negotiated, try to start it
                    # only if the server advertises the STARTTLS extension.
                    use_tls = getattr(settings, 'EMAIL_USE_TLS', False)
                    use_ssl = getattr(settings, 'EMAIL_USE_SSL', False)
                    if use_tls and not use_ssl:
                        try:
                            has_starttls = False
                            try:
                                # smtplib.SMTP provides has_extn
                                has_starttls = bool(getattr(conn.connection, 'has_extn', lambda x: False)('starttls'))
                            except Exception:
                                # If we can't check, avoid forcing starttls; try starting and handle failures
                                has_starttls = False

                            if has_starttls:
                                conn.connection.starttls()
                                try:
                                    conn.connection.ehlo()
                                except Exception:
                                    logger.debug('SMTP ehlo() after STARTTLS failed or unavailable')
                            else:
                                logger.info('SMTP server does not advertise STARTTLS; skipping STARTTLS negotiation')
                        except smtplib.SMTPNotSupportedError:
                            # Server explicitly doesn't support STARTTLS
                            logger.warning('STARTTLS not supported by server; skipping TLS negotiation')
                        except Exception:
                            logger.exception('Failed to negotiate STARTTLS')

                    # Now attempt authentication
                    try:
                        conn.connection.login(username, password)
                        authenticated = True
                        logger.info('SMTP authenticated for %s', username)
                    except smtplib.SMTPAuthenticationError:
                        logger.exception('SMTP authentication failed for %s', username)
                        authenticated = False
                    except Exception:
                        logger.exception('Unexpected SMTP error during login')
                        authenticated = False
                except Exception:
                    logger.exception('Unexpected error during SMTP handshake')
                    authenticated = False

        try:
            if authenticated:
                # Temporarily override django.core.mail.get_connection so the
                # PasswordResetForm uses our already-open, authenticated
                # connection. PasswordResetForm.save() doesn't accept a
                # 'connection' kwarg on this Django version.
                import django.core.mail as _dmail

                _orig_get_connection = _dmail.get_connection

                def _get_conn_override(*a, **k):
                    return conn

                _dmail.get_connection = _get_conn_override
                try:
                    form.save(**opts)
                finally:
                    _dmail.get_connection = _orig_get_connection
            else:
                # SMTP authentication was not available or failed. For local
                # development, fall back to the console email backend so the
                # reset email is printed instead of raising SMTP errors.
                try:
                    import django.core.mail as _dmail

                    _orig_get_connection = _dmail.get_connection

                    console_conn = mail.get_connection(backend='django.core.mail.backends.console.EmailBackend')

                    def _get_conn_override(*a, **k):
                        return console_conn

                    _dmail.get_connection = _get_conn_override
                    try:
                        logger.info('Falling back to console email backend for password reset')
                        form.save(**opts)
                    finally:
                        _dmail.get_connection = _orig_get_connection
                except Exception:
                    # As a last resort, attempt the normal save which may
                    # raise; ensure we surface the original behavior if the
                    # fallback fails.
                    logger.exception('Console fallback failed; attempting normal send')
                    form.save(**opts)
        finally:
            try:
                conn.close()
            except Exception:
                pass
        # Call FormView.form_valid directly (skip PasswordResetView.form_valid to
        # avoid double-sending). Using super(auth_views.PasswordResetView, self)
        # resolves to FormView in the MRO.
        return super(auth_views.PasswordResetView, self).form_valid(form)


def change_language(request):
    return_to = ""
    if "return_to" in request.GET:
        return_to = request.GET["return_to"]

    return render(request, "helpdesk/public_change_language.html", {"next": return_to})
