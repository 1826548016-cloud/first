from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone

from .models import UserSessionBinding


class SingleSessionMiddleware:
    """同账号仅允许一个有效会话，后登录会顶掉先登录。"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 强制当前请求使用中国时区，避免页面显示/统计分桶出现跨天偏差。
        timezone.activate("Asia/Shanghai")

        # 退出/登录等认证入口不做单会话拦截，避免与 Django 自带视图交叉触发导致跳转异常。
        try:
            path = getattr(request, "path", "") or ""
            if path in {
                reverse("tasks:login"),
                reverse("tasks:logout"),
                reverse("tasks:register"),
            }:
                return self.get_response(request)
        except Exception:
            # reverse 失败等情况不影响主流程
            pass

        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            if request.session.session_key is None:
                request.session.save()
            current_key = request.session.session_key or ""
            binding = UserSessionBinding.objects.filter(user=user).first()
            if binding is None:
                UserSessionBinding.objects.create(user=user, session_key=current_key)
            elif binding.session_key and binding.session_key != current_key:
                logout(request)
                messages.warning(request, "该账号已在其他设备登录，当前设备已下线。")
                return redirect(reverse("tasks:login"))
            elif not binding.session_key and current_key:
                binding.session_key = current_key
                binding.save(update_fields=["session_key", "updated_time"])
        return self.get_response(request)
