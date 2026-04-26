from django.utils import timezone


def theme(request):
    t = request.COOKIES.get("theme", "light")
    if t not in ("light", "dark"):
        t = "light"
    return {"theme": t}


def beijing_clock(request):
    now = timezone.localtime()
    return {
        "beijing_now_text": now.strftime("%Y-%m-%d %H:%M"),
    }
