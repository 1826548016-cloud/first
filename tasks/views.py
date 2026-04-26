import json
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.db import transaction
from datetime import date, timedelta

from django.db.models import F, Max, Q, Sum
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek, TruncYear
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django.utils import timezone
from io import BytesIO

from .forms import (
    RegisterForm,
    StudySessionForm,
    TaskForm,
    TimeEntryForm,
    TopicForm,
    TopicItemAddForm,
)
from .models import (
    ActivityLog,
    StudySession,
    Task,
    TimeEntry,
    Topic,
    TopicItem,
    TopicModule,
    TopicProgress,
    UserProfile,
)

def _ensure_default_topics(user):
    defaults = [
        {"name": "任务", "is_builtin": True, "merge_into_tasks": False, "sort_order": 10},
        {"name": "408", "is_builtin": True, "merge_into_tasks": False, "sort_order": 20},
        {"name": "四六级", "is_builtin": True, "merge_into_tasks": False, "sort_order": 30},
        {"name": "数学", "is_builtin": True, "merge_into_tasks": False, "sort_order": 40},
    ]
    for row in defaults:
        Topic.objects.get_or_create(user=user, name=row["name"], defaults=row)


def _safe_next_url(request) -> str:
    """与主题切换等一致：仅允许站内以 / 开头的相对路径，防开放重定向。"""
    n = ""
    if request.method == "POST":
        n = (request.POST.get("next") or "").strip()
    if not n:
        n = (request.GET.get("next") or "").strip()
    if n.startswith("/") and not n.startswith("//") and "://" not in n:
        return n
    return reverse("tasks:home")


def _log_activity(user, action: str, target_type: str, target_id=None, target_name="", detail=None):
    if not user or not getattr(user, "is_authenticated", False):
        return
    ActivityLog.objects.create(
        user=user,
        action=action,
        target_type=target_type,
        target_id=target_id,
        target_name=(target_name or "")[:200],
        detail=detail or {},
    )


def register(request):
    if request.user.is_authenticated:
        return redirect("tasks:home")
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.update_or_create(
                user=user,
                defaults={"phone": form.cleaned_data["phone"]},
            )
            auth_login(request, user)
            return redirect(_safe_next_url(request))
    else:
        form = RegisterForm()
    return render(
        request,
        "registration/register.html",
        {"form": form, "next": _safe_next_url(request)},
    )


def home(request):
    """站点门户首页：日常区与备考区分开入口。"""
    zones_daily = [
        {
            "icon": "📋",
            "title": "每日计划",
            "description": "任务列表、筛选搜索、完成勾选与列表内备注。",
            "cta": "进入任务区",
            "href": reverse("tasks:list"),
        },
        {
            "icon": "➕",
            "title": "新建任务",
            "description": "填写标题、状态、截止时间等，保存到计划列表。",
            "cta": "添加任务",
            "href": reverse("tasks:create"),
        },
        {
            "icon": "✅",
            "title": "任务进度",
            "description": "在任务列表里按状态筛选，查看当前完成情况。",
            "cta": "查看进度",
            "href": reverse("tasks:list"),
        },
        {
            "icon": "📊",
            "title": "学习看板",
            "description": "任务 + 专题（408/四六级/数学/自定义）按日/周/月/年对比。",
            "cta": "打开看板",
            "href": reverse("tasks:dashboard"),
        },
    ]
    zones_exam = []
    return render(
        request,
        "tasks/home.html",
        {"zones_daily": zones_daily, "zones_exam": zones_exam},
    )


def _date_range(period: str):
    today = timezone.localdate()
    if period == "year":
        start = date(today.year - 4, 1, 1)
    elif period == "month":
        start = (today.replace(day=1) - timedelta(days=365)).replace(day=1)
    elif period == "week":
        start = today - timedelta(days=7 * 12)
    else:
        start = today - timedelta(days=30)
    return start, today


def _bucket_fn(period: str):
    if period == "year":
        return TruncYear("entry_date")
    if period == "month":
        return TruncMonth("entry_date")
    if period == "week":
        return TruncWeek("entry_date")
    # DateField 在 MySQL 下再 TruncDate 可能出现 NULL，直接按日期字段分组最稳。
    return F("entry_date")

def _bucket_keys(period: str, start: date, end: date):
    keys = []
    if period == "year":
        y = start.year
        while y <= end.year:
            keys.append(f"{y}-01-01")
            y += 1
        return keys
    if period == "month":
        y, m = start.year, start.month
        while (y, m) <= (end.year, end.month):
            keys.append(f"{y:04d}-{m:02d}-01")
            m += 1
            if m == 13:
                m = 1
                y += 1
        return keys
    if period == "week":
        d = start
        # align to Monday
        d = d - timedelta(days=d.weekday())
        end_aligned = end - timedelta(days=end.weekday())
        while d <= end_aligned:
            keys.append(d.isoformat())
            d = d + timedelta(days=7)
        return keys
    d = start
    while d <= end:
        keys.append(d.isoformat())
        d = d + timedelta(days=1)
    return keys


@login_required
def dashboard(request):
    period = (request.GET.get("period") or "day").strip().lower()
    if period not in {"day", "week", "month", "year"}:
        period = "day"
    include_topics = (request.GET.get("include_topics") or "1").strip() != "0"
    start, end = _date_range(period)

    _ensure_default_topics(request.user)
    topics = list(Topic.objects.filter(user=request.user).order_by("sort_order", "id"))
    tasks_topic = next((t for t in topics if t.name == "任务"), None)

    bucket = _bucket_fn(period)
    time_qs = TimeEntry.objects.filter(
        user=request.user, entry_date__gte=start, entry_date__lte=end
    )
    if not include_topics and tasks_topic:
        time_qs = time_qs.filter(topic=tasks_topic)
    qs = (
        time_qs.annotate(bucket=bucket)
        .values("bucket", "topic_id")
        .annotate(minutes=Sum("minutes"))
        .order_by("bucket")
    )

    # bucket_key -> topic_id -> minutes
    by_bucket = {}
    for row in qs:
        b = row["bucket"]
        if not b:
            continue
        key = b.date().isoformat() if hasattr(b, "date") else str(b)
        by_bucket.setdefault(key, {})[row["topic_id"]] = int(row["minutes"] or 0)

    # Build x-axis (full range, even if some buckets are 0)
    x = _bucket_keys(period, start, end)

    def series_for(topic: Topic):
        return [by_bucket.get(d, {}).get(topic.id, 0) for d in x]

    # Merge: add merged topics into tasks series and hide them from chart
    merged_ids = set()
    tasks_data = [0 for _ in x]
    if tasks_topic:
        tasks_data = series_for(tasks_topic)
    for t in topics:
        if t.id == (tasks_topic.id if tasks_topic else None):
            continue
        if t.merge_into_tasks and tasks_topic:
            merged_ids.add(t.id)
            td = series_for(t)
            tasks_data = [a + b for a, b in zip(tasks_data, td)]

    chart_series = []
    if tasks_topic:
        chart_series.append({"name": "任务（含合并）", "data": tasks_data})
    for t in topics:
        if tasks_topic and t.id == tasks_topic.id:
            continue
        if t.id in merged_ids:
            continue
        chart_series.append({"name": t.name, "data": series_for(t)})

    bucket_totals = []
    for d in x:
        day_total = 0
        for topic_minutes in by_bucket.get(d, {}).values():
            day_total += int(topic_minutes or 0)
        bucket_totals.append(day_total)

    total_minutes = sum(bucket_totals)
    active_days = sum(1 for v in bucket_totals if v > 0)
    peak_minutes = max(bucket_totals) if bucket_totals else 0
    peak_bucket = x[bucket_totals.index(peak_minutes)] if bucket_totals and peak_minutes > 0 else "-"

    today = timezone.localdate()
    today_qs = TimeEntry.objects.filter(user=request.user, entry_date=today)
    if not include_topics and tasks_topic:
        today_qs = today_qs.filter(topic=tasks_topic)
    today_minutes = int(today_qs.aggregate(total=Sum("minutes"))["total"] or 0)

    breakdown = []
    if tasks_topic:
        breakdown.append({"name": "任务（含合并）", "value": int(sum(tasks_data))})
    for t in topics:
        if tasks_topic and t.id == tasks_topic.id:
            continue
        if t.id in merged_ids:
            continue
        vals = series_for(t)
        breakdown.append({"name": t.name, "value": int(sum(vals))})
    breakdown = [r for r in breakdown if r["value"] > 0]

    add_form = TimeEntryForm(user=request.user, initial={"entry_date": timezone.localdate()})
    ctx = {
        "period": period,
        "include_topics": include_topics,
        "x": x,
        "series": chart_series,
        "breakdown": breakdown,
        "kpi_total_minutes": total_minutes,
        "kpi_today_minutes": today_minutes,
        "kpi_active_days": active_days,
        "kpi_peak_bucket": peak_bucket,
        "kpi_peak_minutes": peak_minutes,
        "topics": topics,
        "merged_topics": [t for t in topics if t.id in merged_ids],
        "add_form": add_form,
    }
    return render(request, "tasks/dashboard.html", ctx)


@login_required
@ensure_csrf_cookie
def topic_checklist(request, pk: int):
    _ensure_default_topics(request.user)
    topic = get_object_or_404(Topic, pk=pk, user=request.user)
    modules = list(TopicModule.objects.filter(topic=topic).order_by("sort_order", "id"))
    module_ids = [m.id for m in modules]
    items = list(TopicItem.objects.filter(module_id__in=module_ids).order_by("sort_order", "id"))
    item_ids = [i.id for i in items]
    prog_by_item = {
        p.item_id: p for p in TopicProgress.objects.filter(user=request.user, item_id__in=item_ids)
    }

    sections = []
    total = 0
    done = 0
    for m in modules:
        rows = []
        for it in items:
            if it.module_id != m.id:
                continue
            total += 1
            pr = prog_by_item.get(it.id)
            is_done = bool(pr and pr.is_done)
            if is_done:
                done += 1
            rows.append(
                {
                    "id": it.id,
                    "label": it.label,
                    "done": is_done,
                    "note": (pr.note or "").strip() if pr else "",
                    "can_delete": bool(it.owner_id == request.user.id),
                }
            )
        sections.append({"module": m, "items": rows})

    pct = round(100.0 * done / total, 1) if total else 0.0
    stats = {"overall": {"done": done, "total": total, "pct": pct}}
    add_form = TopicItemAddForm(topic=topic)
    return render(
        request,
        "tasks/topic_checklist.html",
        {"topic": topic, "sections": sections, "stats": stats, "add_form": add_form},
    )


@login_required
@require_POST
def topic_module_note(request, pk: int):
    mod = get_object_or_404(TopicModule, pk=pk, topic__user=request.user)
    note = (request.POST.get("note") or "").strip()
    mod.note = note
    mod.save(update_fields=["note"])
    messages.success(request, "章节备注已保存。")
    return redirect("tasks:topic_checklist", pk=mod.topic_id)


@login_required
@require_POST
def topic_item_add(request, pk: int):
    topic = get_object_or_404(Topic, pk=pk, user=request.user)
    form = TopicItemAddForm(request.POST, topic=topic)
    if not form.is_valid():
        # fall back rendering
        return topic_checklist(request, pk=topic.id)
    mod = form.cleaned_data.get("module")
    new_mod = form.cleaned_data.get("new_module") or ""
    if not mod and new_mod:
        # append module at end
        mx = TopicModule.objects.filter(topic=topic).aggregate(mx=Max("sort_order"))["mx"] or 0
        mod = TopicModule.objects.create(topic=topic, name=new_mod, sort_order=mx + 1, note="")
    if not mod or mod.topic_id != topic.id:
        return HttpResponseBadRequest("invalid module")
    label = form.cleaned_data["label"]
    mxi = TopicItem.objects.filter(module=mod, owner=request.user).aggregate(mx=Max("sort_order"))["mx"] or 10000
    TopicItem.objects.create(module=mod, label=label, sort_order=mxi + 1, owner=request.user)
    _log_activity(
        request.user,
        "topic_item_add",
        "topic",
        topic.id,
        topic.name,
        {"module": mod.name, "label": label},
    )
    messages.success(request, "已添加条目。")
    return redirect("tasks:topic_checklist", pk=topic.id)


@login_required
@require_POST
def topic_item_delete(request, pk: int):
    it = get_object_or_404(TopicItem, pk=pk, owner=request.user)
    topic_id = it.module.topic_id
    topic_name = it.module.topic.name
    label = it.label
    it.delete()
    _log_activity(
        request.user,
        "topic_item_delete",
        "topic",
        topic_id,
        topic_name,
        {"label": label},
    )
    messages.success(request, "已删除自定义条目。")
    return redirect("tasks:topic_checklist", pk=topic_id)


@login_required
@require_POST
def topic_toggle(request):
    try:
        body = json.loads(request.body.decode() or "{}")
    except json.JSONDecodeError:
        body = {}
    raw_id = body.get("item_id") if body.get("item_id") is not None else request.POST.get("item_id")
    if raw_id is None:
        return JsonResponse({"error": "missing item_id"}, status=400)
    try:
        item_id = int(raw_id)
    except (TypeError, ValueError):
        return JsonResponse({"error": "invalid item_id"}, status=400)
    item = get_object_or_404(TopicItem, pk=item_id, module__topic__user=request.user)
    prog, _ = TopicProgress.objects.get_or_create(
        user=request.user, item=item, defaults={"is_done": False, "note": ""}
    )
    prog.is_done = not prog.is_done
    prog.save(update_fields=["is_done", "updated_time"])
    _log_activity(
        request.user,
        "topic_item_toggle",
        "topic",
        item.module.topic_id,
        item.module.topic.name,
        {"item": item.label, "done": prog.is_done},
    )
    return JsonResponse({"done": prog.is_done}, json_dumps_params={"ensure_ascii": False})


_TOPIC_NOTE_MAX = 4000


@login_required
@require_POST
def topic_save_note(request):
    try:
        body = json.loads(request.body.decode() or "{}")
    except json.JSONDecodeError:
        body = {}
    raw_id = body.get("item_id") if body.get("item_id") is not None else request.POST.get("item_id")
    if raw_id is None:
        return JsonResponse({"error": "missing item_id"}, status=400)
    try:
        item_id = int(raw_id)
    except (TypeError, ValueError):
        return JsonResponse({"error": "invalid item_id"}, status=400)
    note = body.get("note")
    if note is None:
        note = request.POST.get("note", "")
    if not isinstance(note, str):
        return JsonResponse({"error": "invalid note"}, status=400)
    note = note.strip()
    if len(note) > _TOPIC_NOTE_MAX:
        return JsonResponse({"error": f"备注请控制在 {_TOPIC_NOTE_MAX} 字以内"}, status=400)
    item = get_object_or_404(TopicItem, pk=item_id, module__topic__user=request.user)
    prog, _ = TopicProgress.objects.get_or_create(
        user=request.user, item=item, defaults={"is_done": False, "note": ""}
    )
    prog.note = note
    prog.save(update_fields=["note", "updated_time"])
    _log_activity(
        request.user,
        "topic_item_note",
        "topic",
        item.module.topic_id,
        item.module.topic.name,
        {"item": item.label},
    )
    return JsonResponse({"ok": True, "note": note}, json_dumps_params={"ensure_ascii": False})


@login_required
def topic_list(request):
    _ensure_default_topics(request.user)
    topics = Topic.objects.filter(user=request.user).order_by("sort_order", "id")
    form = TopicForm()
    return render(request, "tasks/topic_list.html", {"topics": topics, "form": form})


@login_required
def topic_create(request):
    if request.method != "POST":
        return redirect("tasks:topic_list")
    form = TopicForm(request.POST)
    if not form.is_valid():
        topics = Topic.objects.filter(user=request.user).order_by("sort_order", "id")
        return render(request, "tasks/topic_list.html", {"topics": topics, "form": form})
    obj = form.save(commit=False)
    obj.user = request.user
    obj.is_builtin = False
    obj.sort_order = 1000
    obj.save()
    _log_activity(
        request.user,
        "topic_create",
        "topic",
        obj.id,
        obj.name,
        {"merge_into_tasks": obj.merge_into_tasks},
    )
    messages.success(request, "专题已创建。")
    return redirect("tasks:topic_list")


@login_required
@require_POST
def topic_toggle_merge(request, pk: int):
    t = get_object_or_404(Topic, pk=pk, user=request.user)
    if t.name == "任务":
        messages.error(request, "「任务」本身不支持合并开关。")
        return redirect("tasks:topic_list")
    t.merge_into_tasks = not t.merge_into_tasks
    t.save(update_fields=["merge_into_tasks"])
    _log_activity(
        request.user,
        "topic_toggle_merge",
        "topic",
        t.id,
        t.name,
        {"merge_into_tasks": t.merge_into_tasks},
    )
    return redirect("tasks:topic_list")


@login_required
@require_POST
def topic_delete(request, pk: int):
    t = get_object_or_404(Topic, pk=pk, user=request.user)
    if t.name == "任务" or t.is_builtin:
        messages.error(request, "内置专题不支持删除。")
        return redirect("tasks:topic_list")
    t_name = t.name
    t_id = t.id
    t.delete()
    _log_activity(request.user, "topic_delete", "topic", t_id, t_name)
    messages.success(request, "专题已删除。")
    return redirect("tasks:topic_list")


@login_required
def time_entry_create(request):
    if request.method != "POST":
        return redirect("tasks:dashboard")
    form = TimeEntryForm(request.POST, user=request.user)
    if not form.is_valid():
        period = (request.GET.get("period") or "day").strip().lower()
        if period not in {"day", "week", "month", "year"}:
            period = "day"
        start, end = _date_range(period)
        topics = list(Topic.objects.filter(user=request.user).order_by("sort_order", "id"))
        tasks_topic = next((t for t in topics if t.name == "任务"), None)
        ctx = {"period": period, "x": [], "series": [], "topics": topics, "merged_topics": [], "add_form": form}
        return render(request, "tasks/dashboard.html", ctx)
    obj = form.save(commit=False)
    obj.user = request.user
    # Safety: topic must belong to user
    if obj.topic.user_id != request.user.id:
        return HttpResponseBadRequest("invalid topic")
    obj.save()
    _log_activity(
        request.user,
        "time_entry_create",
        "time_entry",
        obj.id,
        obj.topic.name,
        {"entry_date": obj.entry_date.isoformat(), "minutes": obj.minutes},
    )
    messages.success(request, "已记录学习时间。")
    return redirect(reverse("tasks:dashboard") + "?period=" + (request.GET.get("period") or "day"))


@login_required
def activity_history(request):
    logs = ActivityLog.objects.filter(user=request.user).order_by("-created_time", "-id")[:300]
    return render(request, "tasks/history.html", {"logs": logs})


@require_POST
def set_theme(request):
    """通过 Cookie 持久化白天 / 夜间外观（一年）。"""
    theme = request.POST.get("theme", "")
    if theme not in ("light", "dark"):
        return HttpResponseBadRequest("invalid theme")
    next_url = request.POST.get("next") or reverse("tasks:home")
    if not next_url.startswith("/") or next_url.startswith("//"):
        next_url = reverse("tasks:home")
    resp = redirect(next_url)
    resp.set_cookie(
        "theme",
        theme,
        max_age=365 * 24 * 3600,
        httponly=False,
        samesite="Lax",
        path="/",
    )
    return resp


def _task_from_cet4_session(session: StudySession) -> Task:
    title = f"四级·{session.get_category_display()} ·{session.minutes}分钟"
    lines = [f"训练日期：{session.session_date}"]
    if session.remark:
        lines.append(session.remark)
    return Task(
        title=title[:200],
        description="\n".join(lines),
        status=Task.Status.COMPLETED,
        remark=session.remark,
    )


def _task_entry_date(task: Task):
    if task.time_accounting_basis == Task.TimeAccountingBasis.DEADLINE and task.deadline:
        return timezone.localtime(task.deadline).date()
    if task.completed_time:
        return timezone.localtime(task.completed_time).date()
    return timezone.localdate()


def _sync_task_time_entry(user, task: Task):
    # Only completed tasks with spent minutes should be counted.
    TimeEntry.objects.filter(user=user, source_task=task).delete()
    if task.status != Task.Status.COMPLETED or not task.spent_minutes:
        return
    _ensure_default_topics(user)
    tasks_topic = Topic.objects.filter(user=user, name="任务").first()
    if not tasks_topic:
        return
    TimeEntry.objects.create(
        user=user,
        topic=tasks_topic,
        source_task=task,
        entry_date=_task_entry_date(task),
        minutes=int(task.spent_minutes),
        note=f"任务：{task.title}"[:200],
    )


def _pick_export_date(request):
    raw = (request.GET.get("date") or "").strip()
    if not raw:
        return timezone.localdate()
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return timezone.localdate()


def _pick_export_scope(request) -> str:
    raw = (request.GET.get("scope") or "tasks").strip().lower()
    return "all" if raw == "all" else "tasks"


def _time_entries_on_day(user, target_day: date, scope: str):
    qs = TimeEntry.objects.filter(user=user, entry_date=target_day).select_related("topic", "source_task")
    if scope == "tasks":
        qs = qs.filter(topic__name="任务")
    rows = []
    for e in qs.order_by("-minutes", "-id"):
        rows.append(
            {
                "topic": e.topic.name,
                "title": (e.source_task.title if e.source_task else (e.note or "手动记录")),
                "minutes": int(e.minutes or 0),
                "from_task": bool(e.source_task_id),
                "note": e.note or "",
            }
        )
    return rows


def _patch_reportlab_usedforsecurity():
    import hashlib

    if getattr(hashlib, "_rl_usedforsecurity_compat", False):
        return

    _orig_md5 = hashlib.md5
    _orig_sha1 = hashlib.sha1

    def _md5_compat(*args, **kwargs):
        kwargs.pop("usedforsecurity", None)
        return _orig_md5(*args, **kwargs)

    def _sha1_compat(*args, **kwargs):
        kwargs.pop("usedforsecurity", None)
        return _orig_sha1(*args, **kwargs)

    hashlib.md5 = _md5_compat
    hashlib.sha1 = _sha1_compat
    hashlib._rl_usedforsecurity_compat = True

    # ReportLab modules that do "from hashlib import md5" keep local references.
    # Patch those module-level names too.
    try:
        import reportlab.pdfbase.pdfdoc as _rl_pdfdoc
        _rl_pdfdoc.md5 = _md5_compat
    except Exception:
        pass
    try:
        import reportlab.pdfbase.cidfonts as _rl_cidfonts
        _rl_cidfonts.md5 = _md5_compat
    except Exception:
        pass
    try:
        import reportlab.lib.utils as _rl_utils
        _rl_utils.md5 = _md5_compat
    except Exception:
        pass
    try:
        import reportlab.lib.fontfinder as _rl_fontfinder
        _rl_fontfinder.md5 = _md5_compat
    except Exception:
        pass


@login_required
def daily_success_pdf(request):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfgen import canvas

    _patch_reportlab_usedforsecurity()

    target_day = _pick_export_date(request)
    scope = _pick_export_scope(request)
    rows = _time_entries_on_day(request.user, target_day, scope)
    total_minutes = sum(r["minutes"] for r in rows)

    buf = BytesIO()
    p = canvas.Canvas(buf, pagesize=A4)
    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        font_name = "STSong-Light"
    except Exception:
        font_name = "Helvetica"

    width, height = A4
    y = height - 52
    p.setTitle(f"daily-success-{request.user.username}-{target_day.isoformat()}")
    p.setFont(font_name, 16)
    p.drawString(40, y, "每日完成任务时间报告")
    y -= 26
    p.setFont(font_name, 11)
    p.drawString(40, y, f"账号: {request.user.username}")
    y -= 18
    p.drawString(40, y, f"日期: {target_day.isoformat()} (GMT+8)")
    y -= 18
    p.drawString(40, y, f"导出范围: {'任务 + 专题' if scope == 'all' else '仅任务'}")
    y -= 18
    p.drawString(40, y, f"当日总耗时: {total_minutes} 分钟")
    y -= 28
    p.setFont(font_name, 10)
    p.drawString(40, y, "时间明细")
    y -= 16

    for idx, row in enumerate(rows, start=1):
        kind = "任务" if row["from_task"] else "专题"
        line = f"{idx:02d}. [{row['topic']}/{kind}] {row['title']} | {row['minutes']} 分钟"
        if y < 48:
            p.showPage()
            y = height - 52
            p.setFont(font_name, 10)
        p.drawString(40, y, line[:110])
        y -= 16

    if not rows:
        p.drawString(40, y, "当日没有可导出的时间记录。")

    p.showPage()
    p.save()
    pdf = buf.getvalue()
    buf.close()

    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = (
        f'attachment; filename="daily-success-{request.user.username}-{target_day.isoformat()}.pdf"'
    )
    return resp


@login_required
def task_list(request):
    status = request.GET.get("status", "").strip()
    q = request.GET.get("q", "").strip()

    qs = Task.objects.filter(user=request.user, is_deleted=False)
    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(remark__icontains=q))

    context = {
        "tasks": qs,
        "status": status,
        "q": q,
        "status_choices": Task.Status.choices,
        "now": timezone.localtime(),
    }
    return render(request, "tasks/task_list.html", context)


@login_required
def task_create(request):
    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            task.completed_time = (
                timezone.now() if task.status == Task.Status.COMPLETED else None
            )
            task.save()
            _sync_task_time_entry(request.user, task)
            _log_activity(
                request.user,
                "task_create",
                "task",
                task.id,
                task.title,
                {"status": task.status, "spent_minutes": task.spent_minutes},
            )
            return redirect("tasks:list")
    else:
        form = TaskForm()
    return render(request, "tasks/task_form.html", {"form": form, "mode": "create"})


@login_required
def task_update(request, pk: int):
    task = get_object_or_404(Task, pk=pk, user=request.user, is_deleted=False)
    prev_status = task.status
    if request.method == "POST":
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            updated = form.save(commit=False)
            if updated.status == Task.Status.COMPLETED and prev_status != Task.Status.COMPLETED:
                updated.completed_time = timezone.now()
            elif updated.status != Task.Status.COMPLETED:
                updated.completed_time = None
            updated.save()
            _sync_task_time_entry(request.user, updated)
            _log_activity(
                request.user,
                "task_update",
                "task",
                updated.id,
                updated.title,
                {"status": updated.status, "spent_minutes": updated.spent_minutes},
            )
            return redirect("tasks:list")
    else:
        form = TaskForm(instance=task)
    return render(
        request,
        "tasks/task_form.html",
        {"form": form, "mode": "update", "task": task},
    )


@login_required
def task_delete(request, pk: int):
    task = get_object_or_404(Task, pk=pk, user=request.user, is_deleted=False)
    if request.method == "POST":
        TimeEntry.objects.filter(user=request.user, source_task=task).delete()
        task.is_deleted = True
        task.deleted_time = timezone.now()
        task.save(update_fields=["is_deleted", "deleted_time"])
        _log_activity(request.user, "task_delete", "task", task.id, task.title)
        return redirect("tasks:list")
    return render(request, "tasks/task_confirm_delete.html", {"task": task})


@login_required
@require_POST
def task_complete(request, pk: int):
    task = get_object_or_404(Task, pk=pk, user=request.user, is_deleted=False)
    if task.status != Task.Status.COMPLETED:
        task.status = Task.Status.COMPLETED
        task.completed_time = timezone.now()
        task.save(update_fields=["status", "completed_time"])
        _sync_task_time_entry(request.user, task)
        _log_activity(
            request.user,
            "task_complete",
            "task",
            task.id,
            task.title,
            {"spent_minutes": task.spent_minutes},
        )
    return redirect("tasks:list")


_REMARK_MAX_LEN = 4000


def _task_list_redirect_from_remark_post(request):
    params = {}
    q = (request.POST.get("_q") or "").strip()
    if q:
        params["q"] = q[:200]
    st = (request.POST.get("_status") or "").strip()
    if st in {c[0] for c in Task.Status.choices}:
        params["status"] = st
    base = reverse("tasks:list")
    if params:
        return redirect(f"{base}?{urlencode(params)}")
    return redirect(base)


@login_required
@require_POST
def task_remark(request, pk: int):
    task = get_object_or_404(Task, pk=pk, user=request.user, is_deleted=False)
    text = (request.POST.get("remark") or "").strip()
    if len(text) > _REMARK_MAX_LEN:
        messages.error(request, f"备注过长，请控制在 {_REMARK_MAX_LEN} 字以内。")
        return _task_list_redirect_from_remark_post(request)
    task.remark = text
    task.save(update_fields=["remark"])
    _log_activity(request.user, "task_remark", "task", task.id, task.title)
    messages.success(request, "备注已保存。")
    return _task_list_redirect_from_remark_post(request)


@login_required
def cet4_list(request):
    sessions = StudySession.objects.filter(user=request.user)
    return render(
        request,
        "tasks/cet4_list.html",
        {"sessions": sessions, "category_choices": StudySession.Category.choices},
    )


@login_required
def cet4_create(request):
    if request.method == "POST":
        form = StudySessionForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                session = form.save(commit=False)
                session.user = request.user
                session.save()
                task = _task_from_cet4_session(session)
                task.user = request.user
                task.save()
                session.linked_task = task
                session.save(update_fields=["linked_task"])
            return redirect("tasks:cet4_list")
    else:
        form = StudySessionForm(initial={"session_date": timezone.localdate()})
    return render(request, "tasks/cet4_form.html", {"form": form})


@login_required
def cet4_delete(request, pk: int):
    session = get_object_or_404(StudySession, pk=pk, user=request.user)
    if request.method == "POST":
        if session.linked_task_id:
            linked = session.linked_task
            linked.is_deleted = True
            linked.deleted_time = timezone.now()
            linked.save(update_fields=["is_deleted", "deleted_time"])
            session.delete()
        else:
            session.delete()
        return redirect("tasks:cet4_list")
    return render(request, "tasks/cet4_confirm_delete.html", {"session": session})


@login_required
def cet4_stats_page(request):
    return render(
        request,
        "tasks/cet4_stats.html",
        {"cet4_stats_payload": _build_cet4_stats_payload(request.user)},
    )


def _build_cet4_stats_payload(user) -> dict:
    qs = (
        StudySession.objects.filter(user=user)
        .values("session_date", "category")
        .annotate(minutes=Sum("minutes"))
        .order_by("session_date", "category")
    )

    categories = list(StudySession.Category.values)
    cat_label = dict(StudySession.Category.choices)

    by_date = {}
    for row in qs:
        d = row["session_date"].isoformat()
        by_date.setdefault(d, {c: 0 for c in categories})
        by_date[d][row["category"]] = int(row["minutes"] or 0)

    dates = sorted(by_date.keys())
    series = [
        {
            "name": cat_label.get(cat, cat),
            "category": cat,
            "data": [by_date[d].get(cat, 0) for d in dates],
        }
        for cat in categories
    ]

    rows = []
    for d in dates:
        row = {"date": d}
        total = 0
        for c in categories:
            val = int(by_date[d].get(c, 0))
            row[c] = val
            total += val
        row["total"] = total
        rows.append(row)

    return {"dates": dates, "series": series, "rows": rows, "category_labels": cat_label}
