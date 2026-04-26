from django.db import migrations, models


def backfill_completed_time(apps, schema_editor):
    Task = apps.get_model("tasks", "Task")
    Task.objects.filter(status="completed", completed_time__isnull=True).update(
        completed_time=models.F("created_time")
    )


class Migration(migrations.Migration):
    dependencies = [
        ("tasks", "0010_userprofile"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="completed_time",
            field=models.DateTimeField(
                blank=True, db_index=True, null=True, verbose_name="完成时间"
            ),
        ),
        migrations.RunPython(backfill_completed_time, migrations.RunPython.noop),
    ]
