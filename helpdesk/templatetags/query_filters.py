from django import template

register = template.Library()

@register.filter
def get_param(getdict, key):
    try:
        return getdict.get(key)
    except Exception:
        return None
