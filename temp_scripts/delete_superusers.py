import os
import sys

# configure Django the same way demo/manage.py does
sys.path.insert(0, r'C:\Users\Nadine San Juan\Desktop\django-helpdesk\django-helpdesk\demo')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'demodesk.config.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()
qs = User.objects.filter(is_superuser=True)
print('will_delete_usernames=', list(qs.values_list('username', flat=True)))
result = qs.delete()
print('delete_result=', result)
