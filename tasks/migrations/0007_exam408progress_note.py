from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0006_exam408_seed_builtin"),
    ]

    operations = [
        migrations.AddField(
            model_name="exam408progress",
            name="note",
            field=models.TextField(blank=True, verbose_name="知识点备注"),
        ),
    ]
