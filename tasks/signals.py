from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from .models import Topic, UserSessionBinding


def _ensure_default_topics(user):
    defaults = [
        {"name": "任务", "is_builtin": True, "merge_into_tasks": False, "sort_order": 10},
        {"name": "408", "is_builtin": True, "merge_into_tasks": False, "sort_order": 20},
        {"name": "四六级", "is_builtin": True, "merge_into_tasks": False, "sort_order": 30},
        {"name": "数学", "is_builtin": True, "merge_into_tasks": False, "sort_order": 40},
    ]
    for row in defaults:
        Topic.objects.get_or_create(
            user=user,
            name=row["name"],
            defaults=row,
        )


@receiver(user_logged_in)
def bind_active_session(sender, request, user, **kwargs):
    if request is None:
        return
    if request.session.session_key is None:
        request.session.save()
    session_key = request.session.session_key or ""
    UserSessionBinding.objects.update_or_create(
        user=user,
        defaults={"session_key": session_key},
    )
    _ensure_default_topics(user)


@receiver(user_logged_out)
def clear_active_session(sender, request, user, **kwargs):
    if user is None:
        return
    session_key = ""
    if request is not None:
        session_key = request.session.session_key or ""
    if not session_key:
        UserSessionBinding.objects.filter(user=user).update(session_key="")
        return
    UserSessionBinding.objects.filter(user=user, session_key=session_key).update(
        session_key=""
    )
