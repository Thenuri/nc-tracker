"""Helpers for the admin home page cards (templates/admin/index.html)."""

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# One line under each card, so the NC Manager knows what each list is for.
DESCRIPTIONS = {
    "core.department": "APIIT departments, their Head of Department and HoD nominee.",
    "core.process": "Areas / processes an NC can relate to.",
    "core.source": "How an NC was found, e.g. internal review or stakeholder feedback.",
    "ncs.nc": "Every NC, for reference. NCs are worked on in the app, not here.",
    "notifications.notification": "Every message the app has sent, and to whom.",
    "accounts.user": "Staff accounts with their role and department.",
    "auth.group": "Permission groups. The NC Manager group is set up automatically.",
}

# Simple outline icons (24x24), same style as the app's top bar.
_PATHS = {
    "core.department": '<path d="M3 21h18M5 21V7l7-4 7 4v14M9 21v-6h6v6M9 10h.01M15 10h.01"/>',
    "core.process": '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
    "core.source": '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
    "ncs.nc": '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6M8 13h8M8 17h5"/>',
    "notifications.notification": '<path d="M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
    "accounts.user": '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    "auth.group": '<circle cx="9" cy="8" r="3.5"/><path d="M2 20a7 7 0 0 1 14 0M16 4.5a3.5 3.5 0 0 1 0 7M18 13.5a7 7 0 0 1 4 6.5"/>',
}
_DEFAULT_PATH = '<rect x="4" y="4" width="16" height="16" rx="3"/>'


def _key(model):
    return f"{model['model']._meta.app_label}.{model['model']._meta.model_name}"


@register.simple_tag
def card_description(model):
    return DESCRIPTIONS.get(_key(model), "")


@register.simple_tag
def card_count(model):
    """How many records the list holds, shown on the card."""
    return model["model"]._default_manager.count()


@register.simple_tag
def card_icon(model):
    path = _PATHS.get(_key(model), _DEFAULT_PATH)
    return mark_safe(
        '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{path}</svg>'
    )
