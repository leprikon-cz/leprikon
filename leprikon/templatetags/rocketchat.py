from django import template
from django.conf import settings

register = template.Library()


@register.inclusion_tag('rocketchat/livechat.html')
def livechat():
    return {
        'rocketchat_url': getattr(settings, 'ROCKETCHAT_URL', None),
        'DEBUG': settings.DEBUG,
    }
