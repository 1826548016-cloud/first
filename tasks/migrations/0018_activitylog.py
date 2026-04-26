import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tasks", "0017_task_spent_minutes_and_migrate_old_checklists"),
    ]

    operations = [
        migrations.CreateModel(
            name="ActivityLog",
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
                ("action", models.CharField(db_index=True, max_length=64, verbose_name="动作")),
                ("target_type", models.CharField(db_index=True, max_length=32, verbose_name="对象类型")),
                ("target_id", models.PositiveIntegerField(blank=True, db_index=True, null=True, verbose_name="对象ID")),
                ("target_name", models.CharField(blank=True, max_length=200, verbose_name="对象名称")),
                ("detail", models.JSONField(blank=True, default=dict, verbose_name="详情")),
                ("created_time", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="创建时间")),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="activity_logs",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="用户",
                    ),
                ),
            ],
            options={
                "verbose_name": "操作历史",
                "verbose_name_plural": "操作历史",
                "ordering": ["-created_time", "-id"],
            },
        ),
    ]

