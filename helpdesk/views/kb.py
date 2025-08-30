"""
django-helpdesk - A Django powered ticket tracker for small enterprise.

(c) Copyright 2008 Jutda. All Rights Reserved. See LICENSE for details.

views/kb.py - Public-facing knowledgebase views. The knowledgebase is a
              simple categorised question/answer system to show common
              resolutions to common problems.
"""

from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.views.decorators.clickjacking import xframe_options_exempt
from helpdesk import settings as helpdesk_settings, user
from helpdesk.models import KBCategory, KBItem, Queue
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from helpdesk.forms import KBItemForm
from helpdesk.forms import KBCategoryForm
from django.utils.text import slugify


def index(request):
    huser = user.huser_from_request(request)
    # TODO: It'd be great to have a list of most popular items here.
    return render(
        request,
        "helpdesk/kb_index.html",
        {
            "kb_categories": huser.get_allowed_kb_categories(),
            "helpdesk_settings": helpdesk_settings,
        },
    )


def category(request, slug, iframe=False):
    category = get_object_or_404(KBCategory, slug__iexact=slug)
    if not user.huser_from_request(request).can_access_kbcategory(category):
        raise Http404
    items = category.kbitem_set.filter(enabled=True)
    selected_item = request.GET.get("kbitem", None)
    try:
        selected_item = int(selected_item)
    except TypeError:
        pass
    qparams = request.GET.copy()
    try:
        del qparams["kbitem"]
    except KeyError:
        pass
    template = "helpdesk/kb_category.html"
    if iframe:
        template = "helpdesk/kb_category_iframe.html"
    staff = request.user.is_authenticated and request.user.is_staff
    return render(
        request,
        template,
        {
            "category": category,
            "items": items,
            "selected_item": selected_item,
            "query_param_string": qparams.urlencode(),
            "helpdesk_settings": helpdesk_settings,
            "iframe": iframe,
            "staff": staff,
        },
    )


@xframe_options_exempt
def category_iframe(request, slug):
    return category(request, slug, iframe=True)


def vote(request, item, vote):
    item = get_object_or_404(KBItem, pk=item)
    if request.method == "POST":
        if vote == "up":
            if not item.voted_by.filter(pk=request.user.pk):
                item.votes += 1
                item.voted_by.add(request.user.pk)
                item.recommendations += 1
            if item.downvoted_by.filter(pk=request.user.pk):
                item.votes -= 1
                item.downvoted_by.remove(request.user.pk)
        if vote == "down":
            if not item.downvoted_by.filter(pk=request.user.pk):
                item.votes += 1
                item.downvoted_by.add(request.user.pk)
                item.recommendations -= 1
            if item.voted_by.filter(pk=request.user.pk):
                item.votes -= 1
                item.voted_by.remove(request.user.pk)
        item.save()
    return HttpResponseRedirect(item.get_absolute_url())


@user_passes_test(lambda u: u.is_authenticated and u.is_staff)
def add_kb_category(request):
    """Simple staff-only view to create a KBCategory via a minimal form."""
    if request.method == "POST":
        form = KBCategoryForm(request.POST)
        # Hide slug and queue in the UI; we will generate slug and assign queue server-side
        for f in ("slug", "queue"):
            if f in form.fields:
                form.fields.pop(f)
        if form.is_valid():
            # Ensure slug is present; if user omitted it (we hide it from UI)
            category = form.save(commit=False)
            # Generate slug from name (lowercase) or title if name missing
            base = (category.name or category.title or "category").lower()
            category.slug = slugify(base)[:50]

            # Map/create a Queue matching this category's name/slug and assign it
            qslug = category.slug
            qtitle = category.name or category.title or category.slug
            queue_obj, created = Queue.objects.get_or_create(slug=qslug, defaults={"title": qtitle})
            category.queue = queue_obj
            category.save()
            return redirect('helpdesk:kb_category', slug=category.slug)
    else:
        form = KBCategoryForm()
        # Hide slug and queue in the UI form; server will generate slug and assign queue
        for f in ("slug", "queue"):
            if f in form.fields:
                form.fields.pop(f)

    # Provide a lightweight, unsaved KBCategory instance and minimal context
    # so we can reuse the existing kb_category.html layout to host the add form.
    category = KBCategory()
    items = []
    selected_item = None
    qparams = ""

    staff = request.user.is_authenticated and request.user.is_staff
    return render(
        request,
        "helpdesk/kb_category.html",
        {
            "form": form,
            "staff": staff,
            "category": category,
            "items": items,
            "selected_item": selected_item,
            "query_param_string": qparams,
            "helpdesk_settings": helpdesk_settings,
            "iframe": False,
        },
    )


def add_kb_item(request):
    """
    View to create a KBItem.

    - Staff users can create and publish items directly (full form).
    - Non-staff (including anonymous) users may submit items but are limited to
      public categories. Public submissions will be saved with `enabled=False`
      so staff can review/publish them.
    """
    staff = request.user.is_authenticated and request.user.is_staff

    if request.method == "POST":
        form = KBItemForm(request.POST)

        # Restrict category choices and strip publish flag for non-staff
        if not staff and "category" in form.fields:
            form.fields["category"].queryset = KBCategory.objects.filter(public=True)

        if form.is_valid():
            if staff:
                kbitem = form.save()
            else:
                # Save but keep disabled for moderation
                kbitem = form.save(commit=False)
                kbitem.enabled = False
                kbitem.save()

            return redirect(kbitem.get_absolute_url())
    else:
        form = KBItemForm()
        if not staff:
            # Limit categories available to public ones for non-staff
            if "category" in form.fields:
                form.fields["category"].queryset = KBCategory.objects.filter(public=True)
            # Hide the enabled/publish field from public-facing form
            for f in ("enabled", "allow_ticket_creation"):
                if f in form.fields:
                    form.fields.pop(f)

    return render(request, "helpdesk/kb_item.html", {"form": form, "staff": staff})
