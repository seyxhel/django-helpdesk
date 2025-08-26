"""
django-helpdesk - A Django powered ticket tracker for small enterprise.

(c) Copyright 2008 Jutda. All Rights Reserved. See LICENSE for details.

urls.py - Mapping of URL's to our various views. Note we always used NAMED
          views for simplicity in linking later on.
"""

from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from helpdesk import settings as helpdesk_settings
from helpdesk.decorators import helpdesk_staff_member_required, protect_view
from helpdesk.views import feeds, login, public, staff
from helpdesk.views import sla_staff
from helpdesk.forms import CustomSetPasswordForm
from helpdesk.views.api import (
    CreateUserView,
    FollowUpAttachmentViewSet,
    FollowUpViewSet,
    TicketViewSet,
    UserTicketViewSet,
    QueueViewSet,
)
from rest_framework.routers import DefaultRouter
from django.shortcuts import redirect


if helpdesk_settings.HELPDESK_KB_ENABLED:
    from helpdesk.views import kb

try:
    # TODO: why is it imported? due to some side-effect or by mistake?
    import helpdesk.tasks  # NOQA
except ImportError:
    pass


class DirectTemplateView(TemplateView):
    extra_context = None

    def get_context_data(self, **kwargs):
        context = super(self.__class__, self).get_context_data(**kwargs)
        if self.extra_context is not None:
            for key, value in self.extra_context.items():
                if callable(value):
                    context[key] = value()
                else:
                    context[key] = value
        return context


app_name = "helpdesk"

base64_pattern = r"(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$"

urlpatterns = [
    path("dashboard/", staff.dashboard, name="dashboard"),
    path("ajax/email_exists/", staff.ajax_email_exists, name="ajax_email_exists"),
    path("sla/", sla_staff.sla_staff, name="sla_staff"),
    # Dashboard dynamic stats
    path("ajax/dashboard/ticket_count/", staff.ajax_ticket_count, name="ajax_ticket_count"),
    path("ajax/dashboard/user_count/", staff.ajax_user_count, name="ajax_user_count"),
]

urlpatterns += [
    path("ajax/dashboard/kb_likes/", staff.ajax_kb_likes, name="ajax_kb_likes"),
    path("ajax/dashboard/kb_dislikes/", staff.ajax_kb_dislikes, name="ajax_kb_dislikes"),
    path("tickets/", staff.ticket_list, name="list"),
    path("tickets/update/", staff.mass_update, name="mass_update"),
    path("tickets/merge", staff.merge_tickets, name="merge_tickets"),
    path("tickets/<int:ticket_id>/", staff.view_ticket, name="view"),
    path(
        "tickets/<int:ticket_id>/followup_edit/<int:followup_id>/",
        staff.followup_edit,
        name="followup_edit",
    ),
    path(
        "tickets/<int:ticket_id>/followup_delete/<int:followup_id>/",
        staff.followup_delete,
        name="followup_delete",
    ),
    path(
        "tickets/<int:ticket_id>/followup_attachments_fragment/<int:followup_id>/",
        staff.followup_attachments_fragment,
        name="followup_attachments_fragment",
    ),
    path(
        "tickets/<int:ticket_id>/followup_attachments_json/<int:followup_id>/",
        staff.followup_attachments_json,
        name="followup_attachments_json",
    ),
    path("tickets/<int:ticket_id>/edit/", staff.edit_ticket, name="edit"),
    path("tickets/<int:ticket_id>/update/", staff.update_ticket_view, name="update"),
    path("tickets/<int:ticket_id>/delete/", staff.delete_ticket, name="delete"),
    path("tickets/<int:ticket_id>/hold/", staff.hold_ticket, name="hold"),
    path("tickets/<int:ticket_id>/unhold/", staff.unhold_ticket, name="unhold"),
    path("tickets/<int:ticket_id>/cc/", staff.ticket_cc, name="ticket_cc"),
    path("tickets/<int:ticket_id>/cc/add/", staff.ticket_cc_add, name="ticket_cc_add"),
    path(
        "tickets/<int:ticket_id>/cc/delete/<int:cc_id>/",
        staff.ticket_cc_del,
        name="ticket_cc_del",
    ),
    path(
        "tickets/<int:ticket_id>/dependency/add/",
        staff.ticket_dependency_add,
        name="ticket_dependency_add",
    ),
    path(
        "tickets/<int:ticket_id>/dependency/delete/<int:dependency_id>/",
        staff.ticket_dependency_del,
        name="ticket_dependency_del",
    ),
    path(
        "tickets/<int:ticket_id>/resolves/add/",
        staff.ticket_resolves_add,
        name="ticket_resolves_add",
    ),
    path(
        "tickets/<int:ticket_id>/resolves/delete/<int:dependency_id>/",
        staff.ticket_resolves_del,
        name="ticket_resolves_del",
    ),
    path(
        "tickets/<int:ticket_id>/attachment_delete/<int:attachment_id>/",
        staff.attachment_del,
        name="attachment_del",
    ),
    path(
        "tickets/<int:ticket_id>/checklists/<int:checklist_id>/",
        staff.edit_ticket_checklist,
        name="edit_ticket_checklist",
    ),
    path(
        "tickets/<int:ticket_id>/checklist-select-ajax/",
        staff.create_checklist_ajax,
        name="create_checklist_ajax",
    ),
    path(
        "tickets/<int:ticket_id>/checklists/<int:checklist_id>/delete/",
        staff.delete_ticket_checklist,
        name="delete_ticket_checklist",
    ),
    re_path(r"^raw/(?P<type_>\w+)/$", staff.raw_details, name="raw"),
    path("rss/", staff.rss_list, name="rss_index"),
    path("reports/", staff.report_index, name="report_index"),
    re_path(r"^reports/(?P<report>\w+)/$", staff.run_report, name="run_report"),
    path("saved-searches/", staff.saved_searches_list, name="saved_searches_list"),
    path("save_query/", staff.save_query, name="savequery"),
    path("delete_query/<int:pk>/", staff.delete_saved_query, name="delete_query"),
    # User settings: staff continue to use the staff EditUserSettingsView; public users
    # are handled by PublicUserSettingsView which lives in public.py.
    path("settings/", public.PublicUserSettingsView.as_view(), name="user_settings"),
    path("ignore/", staff.email_ignore, name="email_ignore"),
    path("ignore/add/", staff.email_ignore_add, name="email_ignore_add"),
    path("ignore/delete/<int:id>/", staff.email_ignore_del, name="email_ignore_del"),
    path("checklist-templates/", staff.checklist_templates, name="checklist_templates"),
    path(
        "checklist-templates/<int:checklist_template_id>/",
        staff.checklist_templates,
        name="edit_checklist_template",
    ),
    path(
        "checklist-templates/<int:checklist_template_id>/delete/",
        staff.delete_checklist_template,
        name="delete_checklist_template",
    ),
    re_path(
        r"^datatables_ticket_list/(?P<query>{})$".format(base64_pattern),
        staff.datatables_ticket_list,
        name="datatables_ticket_list",
    ),
    re_path(
        r"^timeline_ticket_list/(?P<query>{})$".format(base64_pattern),
        staff.timeline_ticket_list,
        name="timeline_ticket_list",
    ),
]

if helpdesk_settings.HELPDESK_ENABLE_DEPENDENCIES_ON_TICKET:
    urlpatterns += [
        path(
            "tickets/<int:ticket_id>/dependency/add/",
            staff.ticket_dependency_add,
            name="ticket_dependency_add",
        ),
        path(
            "tickets/<int:ticket_id>/dependency/delete/<int:dependency_id>/",
            staff.ticket_dependency_del,
            name="ticket_dependency_del",
        ),
    # ] removed to fix unmatched bracket error

## Removed duplicate root URL pattern so home_view is used exclusively
    path(
        "tickets/my-assigned-tickets/",
        protect_view(public.MyTickets.as_view()),
        name="my-assigned-tickets",
    ),
    # Public / regular-user standalone tickets page
    path(
        "tickets/my-tickets/",
        protect_view(public.MyTickets.as_view(template_name="helpdesk/my_tickets_public.html")),
        name="my-tickets",
    ),
    path("tickets/submit/", public.create_ticket, name="submit"),
    # Staff-only ticket creation URL (preserves staff-specific fields like case owner)
    path("tickets/submit_staff/", staff.CreateTicketView.as_view(), name="submit_staff"),
    path(
        "tickets/submit_iframe/",
        protect_view(public.CreateTicketIframeView.as_view()),
        name="submit_iframe",
    ),
    path(
        "tickets/success_iframe/",  # Ticket was submitted successfully
        protect_view(public.SuccessIframeView.as_view()),
        name="success_iframe",
    ),
    path("view/", protect_view(public.ViewTicket.as_view()), name="public_view"),
    path("tickets/<int:ticket_id>/public_update/", public.public_update_ticket, name="public_update"),
    path("change_language/", public.change_language, name="public_change_language"),
]

urlpatterns += [
    re_path(
        r"^rss/user/(?P<user_name>[^/]+)/",
        helpdesk_staff_member_required(feeds.OpenTicketsByUser()),
        name="rss_user",
    ),
    re_path(
        r"^rss/user/(?P<user_name>[^/]+)/(?P<queue_slug>[A-Za-z0-9_-]+)/$",
        helpdesk_staff_member_required(feeds.OpenTicketsByUser()),
        name="rss_user_queue",
    ),
    re_path(
        r"^rss/queue/(?P<queue_slug>[A-Za-z0-9_-]+)/$",
        helpdesk_staff_member_required(feeds.OpenTicketsByQueue()),
        name="rss_queue",
    ),
    path(
        "rss/unassigned/",
        helpdesk_staff_member_required(feeds.UnassignedTickets()),
        name="rss_unassigned",
    ),
    path(
        "rss/recent_activity/",
        helpdesk_staff_member_required(feeds.RecentFollowUps()),
        name="rss_activity",
    ),
]


router = DefaultRouter()
router.register(r"tickets", TicketViewSet, basename="ticket")
router.register(r"user_tickets", UserTicketViewSet, basename="user_tickets")
router.register(r"queues", QueueViewSet, basename="queue")
router.register(r"followups", FollowUpViewSet, basename="followups")
router.register(
    r"followups-attachments", FollowUpAttachmentViewSet, basename="followupattachments"
)
router.register(r"users", CreateUserView, basename="user")
urlpatterns += [path("api/", include(router.urls))]


urlpatterns += [
    path("login/", login.login, name="login"),
    path(
        "logout/",
        login.logout,
        name="logout",
    ),
    path("remember_credentials/", login.remember_credentials, name="remember_credentials"),
    path(
        "password_change/",
        public.AdaptivePasswordChangeView.as_view(
            template_name="helpdesk/registration/change_password.html",
            # redirect back to the same page with a flag so we can show an inline toast
            success_url="/password_change/?changed=1",
        ),
        name="password_change",
    ),
]

if helpdesk_settings.HELPDESK_KB_ENABLED:
    urlpatterns += [
        path("kb/", kb.index, name="kb_index"),
    path("kb/add/", kb.add_kb_item, name="kb_add"),
    path("kb/category/add/", kb.add_kb_category, name="kb_category_add"),
        re_path(r"^kb/(?P<slug>[A-Za-z0-9_-]+)/$", kb.category, name="kb_category"),
        re_path(r"^kb/(?P<item>\d+)/vote/(?P<vote>up|down)/$", kb.vote, name="kb_vote"),
        re_path(
            r"^kb_iframe/(?P<slug>[A-Za-z0-9_-]+)/$",
            kb.category_iframe,
            name="kb_category_iframe",
        ),
    ]

urlpatterns += [
    path(
        "help/context/",
        TemplateView.as_view(template_name="helpdesk/help_context.html"),
        name="help_context",
    ),
    path(
        "system_settings/",
        login_required(
            DirectTemplateView.as_view(template_name="helpdesk/system_settings.html")
        ),
        name="system_settings",
    ),
    path(
        "users/add/",
        login_required(
            staff.add_user
        ),
        name="add_user",
    ),
    path(
        "users/",
        login_required(
            staff.user_list
        ),
        name="user_list",
    ),
    path(
        "users/<int:user_id>/edit/",
        login_required(
            staff.edit_user
        ),
        name="edit_user",
    ),
    # About page
    path("about/", TemplateView.as_view(template_name="helpdesk/about.html"), name="about"),
    # Dedicated pages for user self-service
    path("register/", public.RegisterView.as_view(), name="register"),
    # Password reset (forgot password) - show form to enter email and send reset link
    path(
        "password-reset/",
        public.HelpdeskPasswordResetView.as_view(),
        name="password_reset",
    ),
    path(
        "password-reset/done",
        auth_views.PasswordResetDoneView.as_view(
            template_name="helpdesk/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "password-reset/confirm/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="helpdesk/password_reset_confirm.html",
            success_url="/password-reset/complete",
            form_class=CustomSetPasswordForm,
        ),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/complete",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="helpdesk/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]

def home_view(request):
    # If no superuser exists, present the initial setup page so an admin
    # can be created via the web UI instead of requiring manage.py createsuperuser.
    from django.contrib.auth import get_user_model
    User = get_user_model()
    if not User.objects.filter(is_superuser=True).exists():
        return public.initial_setup(request)

    if request.user.is_authenticated:
        return public.Homepage.as_view()(request)
    return TemplateView.as_view(template_name="helpdesk/index.html")(request)

urlpatterns += [
    path("", home_view, name="home"),
]
