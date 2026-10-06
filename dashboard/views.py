from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from accounts import permissions as perms
from ncs.models import NC
from ncs.queries import my_tasks, visible_ncs

from . import exports
from .filters import RegisterFilterForm, apply_filters
from .stats import build_dashboard

PAGE_SIZE = 25


def filtered_register(request):
    """The NCs this person may see, narrowed by the filters in the URL."""
    form = RegisterFilterForm(request.GET or None)
    ncs = apply_filters(visible_ncs(request.user).order_by("-year", "-sequence"), form)
    return form, ncs


S = NC.Status

# Quick filter buttons above the register: (label, URL parameters, CSS colour)
QUICK_FILTERS = [
    ("All", {}, ""),
    ("Open", {"status": "open"}, ""),
    ("Overdue", {"overdue": "yes"}, "danger"),
    ("Pending validation", {"status": S.PENDING_VALIDATION}, ""),
    ("Disputed", {"status": S.DISPUTED}, ""),
    ("In progress", {"status": S.IN_PROGRESS}, ""),
    ("Pending verification", {"status": S.PENDING_VERIFICATION}, ""),
    ("Closed", {"status": S.CLOSED}, ""),
]


def quick_filters(request):
    """The quick filter buttons, each with how many NCs it would show.

    Counts respect the person's other filters (department, search, ...) and
    only replace the status / overdue choice, which is what the buttons set.
    """
    others = request.GET.copy()
    for key in ("status", "overdue", "page"):
        others.pop(key, None)
    base = apply_filters(visible_ncs(request.user), RegisterFilterForm(others))

    by_status = dict(base.order_by().values_list("status").annotate(n=Count("pk")))
    counts = {"All": sum(by_status.values()), "Open": base.open().count(), "Overdue": base.overdue().count()}
    current = {key: request.GET.get(key, "") for key in ("status", "overdue")}

    buttons = []
    for label, params, colour in QUICK_FILTERS:
        count = counts.get(label, by_status.get(params.get("status"), 0))
        if count == 0 and label not in ("All", "Open", "Overdue"):
            continue  # hide empty statuses to keep the row short
        query = others.copy()
        query.update(params)
        active = current == {"status": params.get("status", ""), "overdue": params.get("overdue", "")}
        buttons.append({"label": label, "count": count, "url": "?" + query.urlencode(),
                        "active": active, "colour": colour})
    return buttons


@login_required
def register(request):
    """Central register with filters (FR-29, FR-32)."""
    form, ncs = filtered_register(request)
    page = Paginator(ncs, PAGE_SIZE).get_page(request.GET.get("page"))

    # Keep the filters when moving between pages or exporting.
    params = request.GET.copy()
    params.pop("page", None)
    # Cards are the default; "?view=table" shows the compact table instead.
    view_mode = "table" if params.get("view") == "table" else "cards"
    filters_only = params.copy()
    filters_only.pop("view", None)
    context = {
        "form": form,
        "page": page,
        "total": page.paginator.count,
        "querystring": params.urlencode(),
        "filter_querystring": filters_only.urlencode(),  # for the Cards / Table switch
        "view_mode": view_mode,
        "quick_filters": quick_filters(request),
        # NCs on this page that are waiting for this person (same rule as "My tasks")
        "my_action_ids": set(my_tasks(request.user).filter(pk__in=[nc.pk for nc in page])
                             .values_list("pk", flat=True)),
        "sees_everything": perms.can_view_all_ncs(request.user),
        # Opens the "More filters" panel only for filters that are not already
        # visible above it (search, sort and the quick filter buttons).
        "filters_used": any(v for k, v in request.GET.items()
                            if k not in ("page", "view", "q", "sort", "status", "overdue")),
    }
    return render(request, "dashboard/register.html", context)


def describe_filters(form):
    """'Status: Closed · Receiving dept: Finance' – printed on exports."""
    if not form.is_bound or not form.is_valid():
        return "No filters"
    parts = []
    for name, value in form.cleaned_data.items():
        if value in (None, ""):
            continue
        field = form.fields[name]
        if hasattr(field, "choices") and not hasattr(field, "queryset"):
            value = dict(field.choices).get(value, value)
        parts.append(f"{field.label}: {value}")
    return " · ".join(parts) or "No filters"


@login_required
def export_excel(request):
    """Filtered register as Excel (FR-36)."""
    form, ncs = filtered_register(request)
    content = exports.register_excel(ncs, f"NC register – {describe_filters(form)}")
    response = HttpResponse(
        content, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="nc-register-{timezone.localdate():%Y%m%d}.xlsx"'
    return response


@login_required
def export_pdf(request):
    """Filtered register as PDF (FR-36). Falls back to a print-ready page if
    WeasyPrint's system libraries aren't installed on this machine."""
    form, ncs = filtered_register(request)
    filters_text = describe_filters(form)
    pdf = exports.register_pdf(request, ncs, "NC register", filters_text)
    if pdf is None:
        return HttpResponse(exports.register_html(request, ncs, "NC register", filters_text))
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="nc-register-{timezone.localdate():%Y%m%d}.pdf"'
    return response


@login_required
def dashboard(request):
    """Monitoring dashboard (FR-33, FR-34, FR-35, UI-04)."""
    data = build_dashboard(visible_ncs(request.user))
    counts = data["counts"]

    # (label, number, register filter it links to, extra CSS class)
    tiles = [
        ("Open NCs", counts["open"], "status=open", ""),
        ("Overdue ⚠", counts["overdue"], "overdue=yes", "tile-critical" if counts["overdue"] else ""),
        ("Pending validation", counts["pending_validation"], "status=PENDING_VALIDATION", ""),
        ("Disputed", counts["disputed"], "status=DISPUTED", ""),
        ("Valid – awaiting plan", counts["valid"], "status=VALID", ""),
        ("In progress", counts["in_progress"], "status=IN_PROGRESS", ""),
        ("Pending verification", counts["pending_verification"], "status=PENDING_VERIFICATION", ""),
        ("Closed", counts["closed"], "status=CLOSED", ""),
        ("Not valid", counts["not_valid"], "status=NOT_VALID", ""),
        ("Total logged", counts["total"], "", ""),
    ]

    charts = [
        _bar_chart("receiving", "NCs by receiving department", "Department", data["by_receiving"]),
        _bar_chart("raising", "NCs by raising department", "Department", data["by_raising"]),
        _bar_chart("process", "NCs by area / process", "Area / process", data["by_process"]),
        _bar_chart("source", "NCs by source", "Source", data["by_source"]),
        _trend_chart(data["trend"]),
        _bar_chart("ageing", "Closure ageing: time taken to close", "Days to close",
                   data["closure"]["ageing"], horizontal=False,
                   note=f"{data['closure']['closed_count']} closed NCs"),
    ]
    context = {
        "tiles": tiles,
        "closure": data["closure"],
        "charts": charts,
        "chart_data": [c["js"] for c in charts if not c["empty"]],
        "sees_everything": perms.can_view_all_ncs(request.user),
    }
    return render(request, "dashboard/dashboard.html", context)


def _bar_chart(chart_id, title, label_heading, rows, horizontal=True, note="Excludes Not Valid NCs"):
    """One-series bar chart description, shared by the template and dashboard.js."""
    labels = [name for name, _ in rows]
    values = [n for _, n in rows]
    return {
        "id": chart_id, "title": title, "note": note, "label_heading": label_heading,
        "series": [{"name": "NCs"}], "rows": rows,
        "empty": not any(values), "wide": False,
        # Horizontal bars grow with the number of rows so labels never squash.
        "height": max(160, 32 * len(rows) + 40) if horizontal else 240,
        "js": {"id": chart_id, "type": "bar", "horizontal": horizontal, "labels": labels,
               "series": [{"name": "NCs", "values": values}]},
    }


def _trend_chart(trend):
    rows = list(zip(trend["labels"], trend["raised"], trend["closed"]))
    return {
        "id": "trend", "title": "NCs raised vs closed per month", "note": "Last 12 months",
        "label_heading": "Month", "series": [{"name": "Raised"}, {"name": "Closed"}], "rows": rows,
        "empty": not any(trend["raised"] + trend["closed"]), "wide": True, "height": 260,
        "js": {"id": "trend", "type": "line", "labels": trend["labels"],
               "series": [{"name": "Raised", "values": trend["raised"]},
                          {"name": "Closed", "values": trend["closed"]}]},
    }
