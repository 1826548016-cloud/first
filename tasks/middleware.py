from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone

# region agent log
import json as _agent_json
import os as _agent_os
import time as _agent_time
# endregion

from .models import UserSessionBinding


class SingleSessionMiddleware:
    """同账号仅允许一个有效会话，后登录会顶掉先登录。"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 强制当前请求使用中国时区，避免页面显示/统计分桶出现跨天偏差。
        timezone.activate("Asia/Shanghai")

        # region agent log
        try:
            payload = {
                "sessionId": "c97c4e",
                "runId": "pre-fix",
                "hypothesisId": "H1",
                "location": "tasks/middleware.py:__call__",
                "message": "request seen",
                "data": {
                    "path": getattr(request, "path", ""),
                    "method": getattr(request, "method", ""),
                    "user_authenticated": bool(getattr(getattr(request, "user", None), "is_authenticated", False)),
                },
                "timestamp": int(_agent_time.time() * 1000),
            }
            with open("debug-c97c4e.log", "a", encoding="utf-8") as f:
                f.write(_agent_json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # endregion
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            if request.session.session_key is None:
                request.session.save()
            current_key = request.session.session_key or ""
            binding = UserSessionBinding.objects.filter(user=user).first()
            if binding is None:
                UserSessionBinding.objects.create(user=user, session_key=current_key)
            elif binding.session_key and binding.session_key != current_key:
                # region agent log
                try:
                    payload = {
                        "sessionId": "c97c4e",
                        "runId": "pre-fix",
                        "hypothesisId": "H2",
                        "location": "tasks/middleware.py:__call__",
                        "message": "kicked due to other session",
                        "data": {"path": getattr(request, "path", ""), "session_key_present": bool(current_key)},
                        "timestamp": int(_agent_time.time() * 1000),
                    }
                    with open("debug-c97c4e.log", "a", encoding="utf-8") as f:
                        f.write(_agent_json.dumps(payload, ensure_ascii=False) + "\n")
                except Exception:
                    pass
                # endregion
                logout(request)
                messages.warning(request, "该账号已在其他设备登录，当前设备已下线。")
                return redirect(reverse("tasks:login"))
            elif not binding.session_key and current_key:
                binding.session_key = current_key
                binding.save(update_fields=["session_key", "updated_time"])
        return self.get_response(request)
