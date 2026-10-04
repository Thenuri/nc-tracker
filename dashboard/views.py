from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render

from accounts import permissions as perms
from ncs.queries import visible_ncs

from .filters import RegisterFilterForm, apply_filters
from .stats import build_dashboard

PAGE_SIZE = 25


def filtered_register(request):
    """The NCs this person may see, narrowed by the filters in the URL."""
    form = RegisterFilterForm(request.GET or None)
    ncs = apply_filters(visible_ncs(request.user), form).order_by("-year", "-sequence")
    return form, ncs


@login_required
def register(request):
    """Central register with filters (FR-29, FR-32)."""
    form, ncs = filtered_register(request)
    page = Paginator(ncs, PAGE_SIZE).get_page(request.GET.get("page"))

    # Keep the filters when moving between pages or exporting.
    params = request.GET.copy()
    params.pop("page", None)
    context = {
        "form": form,
        "page": page,
        "total": page.paginator.count,
        "querystring": params.urlencode(),
        "sees_everything": perms.can_view_all_ncs(request.user),
        "filters_used": any(v for k, v in request.GET.items() if k != "page"),
    }
    return render(request, "dashboard/register.html", context)


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
