from django.db import migrations

from tasks.exam_math_seed_data import bulk_items_for_migration, unseed_builtin


def apply_seed(apps, schema_editor):
    ExamMathItem = apps.get_model("tasks", "ExamMathItem")
    ExamMathItem.objects.bulk_create(bulk_items_for_migration(ExamMathItem))


def reverse_seed(apps, schema_editor):
    ExamMathItem = apps.get_model("tasks", "ExamMathItem")
    unseed_builtin(ExamMathItem)


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0008_exam_math_models"),
    ]

    operations = [
        migrations.RunPython(apply_seed, reverse_seed),
    ]
