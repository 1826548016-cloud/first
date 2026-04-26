import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tasks", "0013_usersessionbinding"),
    ]

    operations = [
        migrations.CreateModel(
            name="Topic",
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
                ("name", models.CharField(max_length=50, verbose_name="专题名称")),
                ("is_builtin", models.BooleanField(db_index=True, default=False, verbose_name="内置专题")),
                (
                    "merge_into_tasks",
                    models.BooleanField(db_index=True, default=False, verbose_name="合并到任务时间"),
                ),
                ("sort_order", models.PositiveIntegerField(db_index=True, default=0)),
                ("created_time", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="创建时间")),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="topics",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="用户",
                    ),
                ),
            ],
            options={
                "verbose_name": "专题",
                "verbose_name_plural": "专题",
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.CreateModel(
            name="TimeEntry",
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
                ("entry_date", models.DateField(db_index=True, default=timezone.localdate, verbose_name="日期")),
                ("minutes", models.PositiveIntegerField(verbose_name="分钟数")),
                ("note", models.CharField(blank=True, max_length=200, verbose_name="备注")),
                ("created_time", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="创建时间")),
                (
                    "topic",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="time_entries",
                        to="tasks.topic",
                        verbose_name="专题",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="time_entries",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="用户",
                    ),
                ),
            ],
            options={
                "verbose_name": "学习时间记录",
                "verbose_name_plural": "学习时间记录",
                "ordering": ["-entry_date", "-created_time"],
            },
        ),
        migrations.AddIndex(
            model_name="timeentry",
            index=models.Index(fields=["user", "entry_date"], name="tasks_timeentry_user_date_idx"),
        ),
        migrations.AddIndex(
            model_name="timeentry",
            index=models.Index(fields=["user", "topic", "entry_date"], name="tasks_timeentry_user_topic_date_idx"),
        ),
        migrations.AddConstraint(
            model_name="topic",
            constraint=models.UniqueConstraint(fields=("user", "name"), name="uniq_topic_user_name"),
        ),
    ]
