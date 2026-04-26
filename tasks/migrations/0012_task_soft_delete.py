from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tasks", "0011_task_completed_time"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="deleted_time",
            field=models.DateTimeField(
                blank=True, db_index=True, null=True, verbose_name="删除时间"
            ),
        ),
        migrations.AddField(
            model_name="task",
            name="is_deleted",
            field=models.BooleanField(
                db_index=True, default=False, verbose_name="是否删除"
            ),
        ),
    ]
