import os
import sys
import django

proj = r'C:\Users\Nadine San Juan\Desktop\django-helpdesk\django-helpdesk\demo'
os.chdir(proj)
sys.path.insert(0, proj)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'demodesk.config.settings')

try:
    django.setup()
    from django.template import engines
    engines['django'].get_template('helpdesk/include/tickets.html')
    print('TEMPLATE OK')
except Exception as e:
    print('ERROR', type(e).__name__, e)
