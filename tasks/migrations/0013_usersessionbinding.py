import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tasks", "0012_task_soft_delete"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserSessionBinding",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("session_key", models.CharField(default="", max_length=64, verbose_name="当前会话Key")),
                ("updated_time", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="session_binding",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="用户",
                    ),
                ),
            ],
            options={
                "verbose_name": "用户会话绑定",
                "verbose_name_plural": "用户会话绑定",
            },
        ),
    ]
