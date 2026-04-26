from django.conf import settings
from django.db import migrations, models


def migrate_old_checklists(apps, schema_editor):
    Topic = apps.get_model("tasks", "Topic")
    TopicModule = apps.get_model("tasks", "TopicModule")
    TopicItem = apps.get_model("tasks", "TopicItem")
    TopicProgress = apps.get_model("tasks", "TopicProgress")
    Exam408Item = apps.get_model("tasks", "Exam408Item")
    Exam408Progress = apps.get_model("tasks", "Exam408Progress")
    ExamMathItem = apps.get_model("tasks", "ExamMathItem")
    ExamMathProgress = apps.get_model("tasks", "ExamMathProgress")

    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))

    def ensure_topic(user, name, sort_order):
        obj, _ = Topic.objects.get_or_create(
            user=user,
            name=name,
            defaults={
                "is_builtin": True,
                "merge_into_tasks": False,
                "sort_order": sort_order,
            },
        )
        return obj

    def get_or_create_module(topic, module_name, sort_order=0):
        obj, _ = TopicModule.objects.get_or_create(
            topic=topic,
            name=module_name,
            defaults={"note": "", "sort_order": sort_order},
        )
        return obj

    # --- 408 -> Topic("408")
    pillar_label = {
        "ds": "数据结构",
        "os": "操作系统",
        "co": "计算机组成原理",
        "cn": "计算机网络",
    }

    # For each user that has any 408 progress/custom items, migrate their visible items
    users_408 = set(
        list(Exam408Progress.objects.values_list("user_id", flat=True).distinct())
        + list(
            Exam408Item.objects.exclude(owner_id=None)
            .values_list("owner_id", flat=True)
            .distinct()
        )
    )
    for uid in users_408:
        user = User.objects.filter(id=uid).first()
        if not user:
            continue
        topic = ensure_topic(user, "408", 20)
        # visible items: builtin + owned
        items = list(
            Exam408Item.objects.filter(models.Q(owner_id=None) | models.Q(owner_id=uid)).order_by(
                "pillar", "sort_order", "id"
            )
        )
        # create modules and items, keep mapping
        id_map = {}
        for it in items:
            mod_name = f"{pillar_label.get(it.pillar, it.pillar)} · {it.module}"
            mod = get_or_create_module(topic, mod_name, sort_order=it.sort_order)
            ti = TopicItem.objects.create(
                module=mod,
                label=it.label,
                sort_order=it.sort_order,
                owner=it.owner_id and user or None,
            )
            id_map[it.id] = ti.id
        # migrate progress
        for pr in Exam408Progress.objects.filter(user_id=uid):
            new_item_id = id_map.get(pr.item_id)
            if not new_item_id:
                continue
            TopicProgress.objects.update_or_create(
                user_id=uid,
                item_id=new_item_id,
                defaults={"is_done": pr.is_done, "note": pr.note or ""},
            )

    # --- Math -> Topic("数学")
    subj_label = {"calc": "高等数学", "la": "线性代数", "prob": "概率论与数理统计"}
    track_label = {"m1": "数一", "m2": "数二"}

    users_math = set(
        list(ExamMathProgress.objects.values_list("user_id", flat=True).distinct())
        + list(
            ExamMathItem.objects.exclude(owner_id=None)
            .values_list("owner_id", flat=True)
            .distinct()
        )
    )
    for uid in users_math:
        user = User.objects.filter(id=uid).first()
        if not user:
            continue
        topic = ensure_topic(user, "数学", 40)
        items = list(
            ExamMathItem.objects.filter(models.Q(owner_id=None) | models.Q(owner_id=uid)).order_by(
                "track", "subject", "sort_order", "id"
            )
        )
        id_map = {}
        for it in items:
            mod_name = f"{track_label.get(it.track, it.track)} · {subj_label.get(it.subject, it.subject)} · {it.module}"
            mod = get_or_create_module(topic, mod_name, sort_order=it.sort_order)
            ti = TopicItem.objects.create(
                module=mod,
                label=it.label,
                sort_order=it.sort_order,
                owner=it.owner_id and user or None,
            )
            id_map[it.id] = ti.id
        for pr in ExamMathProgress.objects.filter(user_id=uid):
            new_item_id = id_map.get(pr.item_id)
            if not new_item_id:
                continue
            TopicProgress.objects.update_or_create(
                user_id=uid,
                item_id=new_item_id,
                defaults={"is_done": pr.is_done, "note": pr.note or ""},
            )


class Migration(migrations.Migration):
    dependencies = [
        ("tasks", "0016_topic_modules_items_progress"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="spent_minutes",
            field=models.PositiveIntegerField(
                blank=True, db_index=True, null=True, verbose_name="耗时（分钟）"
            ),
        ),
        migrations.RunPython(migrate_old_checklists, migrations.RunPython.noop),
    ]

