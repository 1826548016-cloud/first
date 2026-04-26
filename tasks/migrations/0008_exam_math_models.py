import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tasks", "0007_exam408progress_note"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExamMathUserPreference",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "track",
                    models.CharField(
                        choices=[("m1", "数学一"), ("m2", "数学二")],
                        db_index=True,
                        max_length=2,
                        verbose_name="卷种",
                    ),
                ),
                ("updated_time", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="exam_math_pref",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="用户",
                    ),
                ),
            ],
            options={
                "verbose_name": "考研数学卷种偏好",
                "verbose_name_plural": "考研数学卷种偏好",
            },
        ),
        migrations.CreateModel(
            name="ExamMathItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "track",
                    models.CharField(
                        choices=[("m1", "数学一"), ("m2", "数学二")],
                        db_index=True,
                        max_length=2,
                        verbose_name="卷种",
                    ),
                ),
                (
                    "subject",
                    models.CharField(
                        choices=[
                            ("calc", "高等数学"),
                            ("la", "线性代数"),
                            ("prob", "概率论与数理统计"),
                        ],
                        db_index=True,
                        max_length=4,
                        verbose_name="科目",
                    ),
                ),
                ("module", models.CharField(max_length=64, verbose_name="章节")),
                ("label", models.CharField(max_length=200, verbose_name="知识点")),
                ("sort_order", models.PositiveIntegerField(db_index=True, default=0)),
                ("created_time", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="创建时间")),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="exam_math_custom_items",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="创建者",
                    ),
                ),
            ],
            options={
                "verbose_name": "考研数学知识点",
                "verbose_name_plural": "考研数学知识点",
                "ordering": ["track", "subject", "sort_order", "id"],
            },
        ),
        migrations.CreateModel(
            name="ExamMathProgress",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_done", models.BooleanField(db_index=True, default=False, verbose_name="已完成")),
                ("note", models.TextField(blank=True, verbose_name="知识点备注")),
                ("updated_time", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                (
                    "item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="progress_rows",
                        to="tasks.exammathitem",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="exam_math_progress_rows",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "考研数学勾选进度",
                "verbose_name_plural": "考研数学勾选进度",
            },
        ),
        migrations.AddConstraint(
            model_name="exammathprogress",
            constraint=models.UniqueConstraint(fields=("user", "item"), name="uniq_exam_math_progress_user_item"),
        ),
    ]
