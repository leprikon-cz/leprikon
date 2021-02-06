from django import template

from ..rocketchat import get_rc_id, get_rc_url, get_rc_ws_url

register = template.Library()


@register.inclusion_tag("rocketchat/chat.html", takes_context=True)
def chat(context):
    user = getattr(context.get("request"), "user")
    return {
        "rocketchat_url": get_rc_url(),
        "websocket_url": get_rc_ws_url(),
        "user": user,
        "user_id": user and user.is_authenticated and get_rc_id(user),
    }


@register.inclusion_tag("rocketchat/livechat.html", takes_context=True)
def livechat(context):
    return {
        "rocketchat_url": get_rc_url(),
        "user": getattr(context.get("request"), "user"),
    }
