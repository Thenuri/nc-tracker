"""Template helpers for showing NC status and colour consistently everywhere."""

from django import template

register = template.Library()

STATUS_CLASSES = {
    "PENDING_VALIDATION": "text-bg-info",
    "VALID": "text-bg-primary",
    "DISPUTED": "text-bg-warning",
    "NOT_VALID": "text-bg-secondary",
    "IN_PROGRESS": "text-bg-primary",
    "PENDING_VERIFICATION": "text-bg-info",
    "CLOSED": "text-bg-success",
}

# UI-04: red = overdue, amber = due within 7 days, green = on track or closed
RAG_CLASSES = {
    "red": "text-bg-danger",
    "amber": "text-bg-warning",
    "green": "text-bg-success",
    "grey": "text-bg-secondary",
}


@register.filter
def status_class(status):
    return STATUS_CLASSES.get(status, "text-bg-light")


@register.inclusion_tag("includes/nc_badges.html")
def nc_badges(nc):
    """Status badge plus the overdue / due-soon flag."""
    return {"nc": nc, "status_css": status_class(nc.status), "rag_css": RAG_CLASSES[nc.rag]}
