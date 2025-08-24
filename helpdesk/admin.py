from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from helpdesk import settings as helpdesk_settings
from helpdesk.models import (
    Checklist,
    ChecklistTask,
    ChecklistTemplate,
    CustomField,
    EmailTemplate,
    EscalationExclusion,
    FollowUp,
    FollowUpAttachment,
    IgnoreEmail,
    KBIAttachment,
    PreSetReply,
    Queue,
    Ticket,
    TicketChange,
)


if helpdesk_settings.HELPDESK_KB_ENABLED:
    from helpdesk.models import KBCategory, KBItem


@admin.register(Queue)
class QueueAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "email_address", "locale", "time_spent")
    prepopulated_fields = {"slug": ("title",)}
    change_form_template = "admin/helpdesk/queue/change_form.html"

    fieldsets = (
        (None, {"fields": ("title", "slug", "default_owner", "allow_public_submission", "email_address", "escalate_days")} ),
        ("Advanced options", {
            "classes": ("collapse",),
            "fields": (
                "locale",
                "allow_email_submission",
                "new_ticket_cc",
                "updated_ticket_cc",
                "enable_notifications_on_email_events",
                "email_box_type",
                "email_box_host",
                "email_box_port",
                "email_box_ssl",
                "email_box_user",
                "email_box_pass",
                "email_box_imap_folder",
                "email_box_local_dir",
                "email_box_interval",
                "socks_proxy_type",
                "socks_proxy_host",
                "socks_proxy_port",
                "logging_type",
                "logging_dir",
                "dedicated_time",
            ),
        }),
    )

    def get_urls(self):
        from django.urls import path

        urls = super().get_urls()
        custom_urls = [
            path(
                "test-mailbox/",
                self.admin_site.admin_view(self.test_mailbox_view),
                name="helpdesk_queue_test_mailbox",
            ),
        ]
        return custom_urls + urls

    def test_mailbox_view(self, request):
        """AJAX endpoint to validate mailbox settings provided in the form."""
        from django.http import JsonResponse

        # read params from POST or GET
        data = request.POST or request.GET
        box_type = data.get("email_box_type")
        host = data.get("email_box_host")
        port = data.get("email_box_port")
        ssl_flag = data.get("email_box_ssl") in ("True", "true", "1", "on")
        user = data.get("email_box_user")
        pwd = data.get("email_box_pass")
        imap_folder = data.get("email_box_imap_folder")
        local_dir = data.get("email_box_local_dir")

        # Basic validation
        if not box_type:
            return JsonResponse({"ok": False, "message": "Missing email box type"})

        try:
            if box_type == "imap" or box_type == "oauth":
                import imaplib

                if ssl_flag:
                    M = imaplib.IMAP4_SSL(host, int(port) if port else None)
                else:
                    M = imaplib.IMAP4(host, int(port) if port else None)
                if user:
                    M.login(user, pwd or "")
                if imap_folder:
                    typ, data = M.select(imap_folder)
                    if typ != "OK":
                        M.logout()
                        return JsonResponse({"ok": False, "message": f"Failed to select folder '{imap_folder}'"})
                M.logout()
                return JsonResponse({"ok": True, "message": "IMAP connection successful"})

            elif box_type == "pop3":
                import poplib

                if ssl_flag:
                    p = poplib.POP3_SSL(host, int(port) if port else None)
                else:
                    p = poplib.POP3(host, int(port) if port else None)
                if user:
                    p.user(user)
                    p.pass_(pwd or "")
                p.quit()
                return JsonResponse({"ok": True, "message": "POP3 connection successful"})

            elif box_type == "local":
                import os

                if not local_dir:
                    return JsonResponse({"ok": False, "message": "Local directory not specified"})
                if not os.path.isdir(local_dir):
                    return JsonResponse({"ok": False, "message": "Local directory does not exist"})
                if not os.access(local_dir, os.R_OK):
                    return JsonResponse({"ok": False, "message": "Local directory is not readable"})
                return JsonResponse({"ok": True, "message": "Local directory is accessible"})

            else:
                return JsonResponse({"ok": False, "message": "Unknown mailbox type"})
        except Exception as e:
            return JsonResponse({"ok": False, "message": str(e)})

    def time_spent(self, q):
        if q.dedicated_time:
            return "{} / {}".format(q.time_spent, q.dedicated_time)
        elif q.time_spent:
            return q.time_spent
        else:
            return "-"

    def delete_queryset(self, request, queryset):
        for queue in queryset:
            queue.delete()


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "status",
        "assigned_to",
        "queue",
        "hidden_submitter_email",
        "time_spent",
    )
    date_hierarchy = "created"
    list_filter = ("queue", "assigned_to", "status")
    search_fields = ("id", "title")

    @admin.display(description=_("Submitter E-Mail"))
    def hidden_submitter_email(self, ticket):
        if ticket.submitter_email:
            username, domain = ticket.submitter_email.split("@")
            username = username[:2] + "*" * (len(username) - 2)
            domain = domain[:1] + "*" * (len(domain) - 2) + domain[-1:]
            return "%s@%s" % (username, domain)
        else:
            return ticket.submitter_email

    def time_spent(self, ticket):
        return ticket.time_spent


class TicketChangeInline(admin.StackedInline):
    model = TicketChange
    extra = 0


class FollowUpAttachmentInline(admin.StackedInline):
    model = FollowUpAttachment
    extra = 0


class KBIAttachmentInline(admin.StackedInline):
    model = KBIAttachment
    extra = 0


@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    inlines = [TicketChangeInline, FollowUpAttachmentInline]
    list_display = (
        "ticket_get_ticket_for_url",
        "title",
        "date",
        "ticket",
        "user",
        "new_status",
        "time_spent",
    )
    list_filter = ("user", "date", "new_status")

    @admin.display(description=_("Slug"))
    def ticket_get_ticket_for_url(self, obj):
        return obj.ticket.ticket_for_url


if helpdesk_settings.HELPDESK_KB_ENABLED:

    @admin.register(KBItem)
    class KBItemAdmin(admin.ModelAdmin):
        list_display = ("category", "title", "last_updated", "team", "order", "enabled", "allow_ticket_creation")
        inlines = [KBIAttachmentInline]
        readonly_fields = ("voted_by", "downvoted_by")
        list_display_links = ("title",)
        fields = ("category", "title", "question", "answer", "allow_ticket_creation", "last_updated", "team", "order", "enabled")

    if helpdesk_settings.HELPDESK_KB_ENABLED:
        # Import the KBCategoryForm so description can be optional in admin
        try:
            from helpdesk.forms import KBCategoryForm
        except Exception:
            KBCategoryForm = None

        @admin.register(KBCategory)
        class KBCategoryAdmin(admin.ModelAdmin):
            list_display = ("name", "title", "slug", "public")
            form = KBCategoryForm

            def get_fields(self, request, obj=None):
                """Hide 'slug' and 'queue' when adding a new KBCategory; show them when editing."""
                if obj is None:
                    # add form: exclude slug and queue
                    return ["name", "title", "description", "public"]
                # edit form: include all fields
                return ["name", "title", "slug", "description", "public", "queue"]

            def save_model(self, request, obj, form, change):
                """Auto-generate a unique slug on create when not provided. Also create a Queue and link it to KBCategory."""
                from django.utils.text import slugify
                from helpdesk.models import Queue

                if not change:
                    # creating new object
                    if not getattr(obj, "slug", None):
                        base = slugify(getattr(obj, "name", None) or getattr(obj, "title", ""))
                        slug = base or "kbcategory"
                        counter = 1
                        # ensure uniqueness
                        while KBCategory.objects.filter(slug=slug).exists():
                            slug = f"{base}-{counter}"
                            counter += 1
                        obj.slug = slug
                    # Automatically create a Queue for this KBCategory
                    queue_title = obj.name or obj.title or "KB Queue"
                    queue_slug = obj.slug
                    queue = Queue.objects.create(title=queue_title, slug=queue_slug, allow_public_submission=True)
                    obj.queue = queue
                super().save_model(request, obj, form, change)


@admin.register(CustomField)
class CustomFieldAdmin(admin.ModelAdmin):
    list_display = ("name", "label", "data_type")


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ("template_name", "heading", "locale")
    list_filter = ("locale",)


@admin.register(IgnoreEmail)
class IgnoreEmailAdmin(admin.ModelAdmin):
    list_display = ("name", "queue_list", "email_address", "keep_in_mailbox")


@admin.register(ChecklistTemplate)
class ChecklistTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "task_list")
    search_fields = ("name", "task_list")


class ChecklistTaskInline(admin.TabularInline):
    model = ChecklistTask


@admin.register(Checklist)
class ChecklistAdmin(admin.ModelAdmin):
    list_display = ("name", "ticket")
    search_fields = ("name", "ticket__id", "ticket__title")
    autocomplete_fields = ("ticket",)
    list_select_related = ("ticket",)
    inlines = (ChecklistTaskInline,)


admin.site.register(PreSetReply)
admin.site.register(EscalationExclusion)
