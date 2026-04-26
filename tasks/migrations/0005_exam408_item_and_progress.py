import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tasks", "0004_studysession_linked_task"),
    ]

    operations = [
        migrations.CreateModel(
            name="Exam408Item",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("pillar", models.CharField(choices=[("ds", "数据结构"), ("os", "操作系统"), ("co", "计算机组成原理"), ("cn", "计算机网络")], db_index=True, max_length=2, verbose_name="科目")),
                ("module", models.CharField(max_length=64, verbose_name="模块")),
                ("label", models.CharField(max_length=200, verbose_name="知识点")),
                ("sort_order", models.PositiveIntegerField(db_index=True, default=0)),
                ("created_time", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="创建时间")),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="exam408_custom_items",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="创建者",
                    ),
                ),
            ],
            options={
                "verbose_name": "408知识点",
                "verbose_name_plural": "408知识点",
                "ordering": ["pillar", "sort_order", "id"],
            },
        ),
        migrations.CreateModel(
            name="Exam408Progress",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_done", models.BooleanField(db_index=True, default=False, verbose_name="已完成")),
                ("updated_time", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                (
                    "item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="progress_rows",
                        to="tasks.exam408item",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="exam408_progress_rows",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "408勾选进度",
                "verbose_name_plural": "408勾选进度",
            },
        ),
        migrations.AddConstraint(
            model_name="exam408progress",
            constraint=models.UniqueConstraint(fields=("user", "item"), name="uniq_exam408_progress_user_item"),
        ),
    ]
