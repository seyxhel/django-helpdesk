import os
import django
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'helpdesk.settings')
django.setup()

from helpdesk import models

MEDIA_DIR = None

# create a public queue
q = models.Queue.objects.create(title='Public Queue', slug='pub_q', allow_public_submission=True, new_ticket_cc='', updated_ticket_cc='')

client = Client()

post_data = {
    'title': 'Test Ticket Title',
    'body': 'Test Ticket Desc',
    'priority': 3,
    'submitter_email': 'submitter@example.com',
    'queue': q.id,
}

test_file = SimpleUploadedFile('test_att.txt', b'attached file content', content_type='text/plain')

response = client.post(reverse('helpdesk:home'), {**post_data, 'attachment': test_file}, follow=True)

print('STATUS:', response.status_code)
print('CONTENT:', getattr(response, 'content', None))
# try to print context keys safely
try:
    ctx = response.context
    if ctx is None:
        print('CONTEXT: None')
    else:
        print('CONTEXT KEYS:', list(ctx.keys()) if hasattr(ctx, 'keys') else type(ctx))
        # print any form errors if present
        if 'form' in ctx:
            form = ctx['form']
            print('FORM ERRORS:', form.errors)
except Exception as e:
    print('ERROR READING CONTEXT:', e)

# if response has content as bytes, print first 1000 chars
if response.content:
    try:
        print('BODY (utf8):')
        print(response.content.decode('utf-8', errors='replace')[:2000])
    except Exception:
        print('BODY (bytes):', response.content[:2000])
