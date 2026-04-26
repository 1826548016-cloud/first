import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tasks", "0015_rename_tasks_timeentry_user_date_idx_tasks_timee_user_id_27a2e3_idx_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="TopicModule",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("name", models.CharField(max_length=64, verbose_name="章节")),
                ("note", models.TextField(blank=True, verbose_name="章节备注")),
                ("sort_order", models.PositiveIntegerField(db_index=True, default=0)),
                ("created_time", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="创建时间")),
                (
                    "topic",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="modules",
                        to="tasks.topic",
                        verbose_name="专题",
                    ),
                ),
            ],
            options={
                "verbose_name": "专题章节",
                "verbose_name_plural": "专题章节",
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.CreateModel(
            name="TopicItem",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("label", models.CharField(max_length=200, verbose_name="条目")),
                ("sort_order", models.PositiveIntegerField(db_index=True, default=0)),
                ("created_time", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="创建时间")),
                (
                    "module",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="tasks.topicmodule",
                        verbose_name="章节",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="custom_topic_items",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="创建者",
                    ),
                ),
            ],
            options={
                "verbose_name": "专题条目",
                "verbose_name_plural": "专题条目",
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.CreateModel(
            name="TopicProgress",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("is_done", models.BooleanField(db_index=True, default=False, verbose_name="已完成")),
                ("note", models.TextField(blank=True, verbose_name="条目备注")),
                ("updated_time", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                (
                    "item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="progress_rows",
                        to="tasks.topicitem",
                        verbose_name="条目",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="topic_progress_rows",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="用户",
                    ),
                ),
            ],
            options={
                "verbose_name": "专题勾选进度",
                "verbose_name_plural": "专题勾选进度",
            },
        ),
        migrations.AddConstraint(
            model_name="topicmodule",
            constraint=models.UniqueConstraint(
                fields=("topic", "name"), name="uniq_topic_module_topic_name"
            ),
        ),
        migrations.AddConstraint(
            model_name="topicprogress",
            constraint=models.UniqueConstraint(
                fields=("user", "item"), name="uniq_topic_progress_user_item"
            ),
        ),
    ]

