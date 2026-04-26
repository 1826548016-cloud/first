from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0003_studysession"),
    ]

    operations = [
        migrations.AddField(
            model_name="studysession",
            name="linked_task",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="cet4_session",
                to="tasks.task",
                verbose_name="同步任务",
            ),
        ),
    ]
