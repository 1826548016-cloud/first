from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

app_name = "tasks"

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("history/", views.activity_history, name="history"),
    path("topics/", views.topic_list, name="topic_list"),
    path("topics/new/", views.topic_create, name="topic_create"),
    path("topics/<int:pk>/toggle-merge/", views.topic_toggle_merge, name="topic_toggle_merge"),
    path("topics/<int:pk>/delete/", views.topic_delete, name="topic_delete"),
    path("topics/<int:pk>/", views.topic_checklist, name="topic_checklist"),
    path("topics/<int:pk>/add-item/", views.topic_item_add, name="topic_item_add"),
    path("topics/item/<int:pk>/delete/", views.topic_item_delete, name="topic_item_delete"),
    path("topics/module/<int:pk>/note/", views.topic_module_note, name="topic_module_note"),
    path("api/topic/toggle/", views.topic_toggle, name="topic_toggle"),
    path("api/topic/note/", views.topic_save_note, name="topic_save_note"),
    path("time/new/", views.time_entry_create, name="time_entry_create"),
    path("theme/", views.set_theme, name="set_theme"),
    path("tasks/new/", views.task_create, name="create"),
    path("tasks/<int:pk>/edit/", views.task_update, name="update"),
    path("tasks/<int:pk>/delete/", views.task_delete, name="delete"),
    path("tasks/<int:pk>/complete/", views.task_complete, name="complete"),
    path("tasks/<int:pk>/remark/", views.task_remark, name="remark"),
    path("tasks/export/daily-pdf/", views.daily_success_pdf, name="daily_success_pdf"),
    path("tasks/", views.task_list, name="list"),
    path("cet4/", views.cet4_list, name="cet4_list"),
    path("cet4/new/", views.cet4_create, name="cet4_create"),
    path("cet4/<int:pk>/delete/", views.cet4_delete, name="cet4_delete"),
    path("cet4/stats/", views.cet4_stats_page, name="cet4_stats"),
    # 旧备考专项入口已取消（统一到专题区）；保留旧功能代码但不暴露路由。
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("register/", views.register, name="register"),
    path("logout/", auth_views.LogoutView.as_view(next_page="tasks:home"), name="logout"),
]
