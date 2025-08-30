from helpdesk.decorators import helpdesk_staff_member_required
from django.shortcuts import render
from helpdesk.models import Ticket


@helpdesk_staff_member_required
def sla_staff(request):
    """Staff SLA overview page: list tickets assigned to the current user ordered by priority."""
    user = request.user
    tickets = Ticket.objects.filter(assigned_to=user).order_by('priority', 'created')[:100]
    return render(request, 'helpdesk/sla_staff.html', {'tickets': tickets})
