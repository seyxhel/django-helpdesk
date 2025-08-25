from helpdesk.decorators import helpdesk_staff_member_required
from django.shortcuts import render

def sla_staff(request):
    """Staff SLA overview page."""
    return render(request, 'helpdesk/sla_staff.html', {})
