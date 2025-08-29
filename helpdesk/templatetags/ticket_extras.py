from django import template
from urllib.parse import urlencode

register = template.Library()

@register.simple_tag(takes_context=True)
def qs_with(context, **kwargs):
    """Return the current request GET querystring updated with the provided kwargs."""
    request = context.get('request')
    if not request:
        return urlencode(kwargs)
    params = request.GET.copy()
    for k, v in kwargs.items():
        if v is None:
            if k in params:
                del params[k]
        else:
            params[k] = v
    return params.urlencode()


@register.simple_tag(takes_context=True)
def qs_with_var(context, key_name, value):
    """Return the current request GET querystring updated with the provided key_name (string) and value."""
    request = context.get('request')
    if not request:
        from urllib.parse import urlencode
        return urlencode({key_name: value})
    params = request.GET.copy()
    params[key_name] = value
    return params.urlencode()
