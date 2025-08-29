# Simulation script to POST to followup_edit via Django test client
from django.test import Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from helpdesk.models import FollowUp

User = get_user_model()

client = Client()
# prefer a superuser or any staff user
user = User.objects.filter(is_staff=True).first() or User.objects.filter(is_superuser=True).first()
if not user:
    print('No staff user in DB; exiting')
else:
    client.force_login(user)
    followup = FollowUp.objects.first()
    if not followup:
        print('No FollowUp objects found; exiting')
    else:
        ticket = followup.ticket
        url = reverse('helpdesk:followup_edit', args=[ticket.id, followup.id])
        print('Posting to', url)
        data = {
            'title': followup.title,
            'ticket': str(ticket.id),
            'comment': followup.comment or 'test',
            'public': '1' if followup.public else '0',
            'new_status': followup.new_status or ticket.status,
            'time_spent': followup.time_spent or '',
            'replace_attachment_id': '',
        }
        # create a small in-memory file
        uploaded = SimpleUploadedFile('test.txt', b'Test file contents', content_type='text/plain')
        files = {'replacement_attachment': uploaded}
        response = client.post(url, data, **{
            'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'
        }, FILES=files)
        print('STATUS', response.status_code)
        try:
            import json
            print(json.dumps(response.json(), indent=2))
        except Exception:
            print(response.content)
