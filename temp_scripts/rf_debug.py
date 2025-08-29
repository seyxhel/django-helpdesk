import os
import django
from django.test import RequestFactory
from django.core.files.uploadedfile import SimpleUploadedFile

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'helpdesk.settings')
django.setup()

from helpdesk import urls as helpdesk_urls
from django.urls import reverse
from django.conf import settings

rf = RequestFactory()

post = {
    'title': 'Test',
    'body': 'desc',
    'priority': '3',
    'submitter_email': 'a@b.com',
    'queue': '1'
}
file = SimpleUploadedFile('test.txt', b'hello', content_type='text/plain')

req = rf.post(reverse('helpdesk:home'), data=post, files={'attachment': file})

print('Request created:', req.method, req.content_type)

try:
    resp = helpdesk_urls.home_view(req)
    print('Response status:', getattr(resp, 'status_code', None))
    try:
        print('Response content:', resp.content.decode('utf-8'))
    except Exception:
        print('Response repr:', resp)
except Exception as e:
    import traceback
    traceback.print_exc()
