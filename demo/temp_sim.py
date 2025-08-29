import os, json
os.environ['DJANGO_SETTINGS_MODULE']='demodesk.config.settings'
import django
django.setup()
from django.contrib.auth import get_user_model
User=get_user_model()
print('STAFF:', User.objects.filter(is_staff=True).count(), 'SUPER:', User.objects.filter(is_superuser=True).count())
from helpdesk.models import FollowUp
print('FOLLOWUPS:', FollowUp.objects.count())
user = User.objects.filter(is_staff=True).first() or User.objects.filter(is_superuser=True).first()
print('USER:', getattr(user,'pk',None))
from django.test import Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
client=Client()
if user:
    client.force_login(user)
followup=FollowUp.objects.first()
print('FOLLOWUP PK:', getattr(followup,'pk',None))
if followup:
    ticket=followup.ticket
    url=reverse('helpdesk:followup_edit', args=[ticket.id, followup.id])
    print('POST URL:', url)
    data={'title': followup.title or 't','ticket': str(ticket.id), 'comment': followup.comment or 'test', 'public': '1' if followup.public else '0', 'new_status': followup.new_status or ticket.status, 'time_spent': followup.time_spent or '', 'replace_attachment_id': ''}
    uploaded=SimpleUploadedFile('test.txt', b'Test file contents', content_type='text/plain')
    files={'replacement_attachment': uploaded}
    resp=client.post(url, data, files=files, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    print('STATUS', resp.status_code)
    try:
        print(json.dumps(resp.json(), indent=2))
    except Exception:
        print(resp.content)
