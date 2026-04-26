from django.conf import settings
from django.db import models
from django.utils import timezone

class Task(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "未开始"
        IN_PROGRESS = "in_progress", "进行中"
        COMPLETED = "completed", "已完成"
    class TimeAccountingBasis(models.TextChoices):
        DEADLINE = "deadline", "按预定时间"
        COMPLETED_TIME = "completed_time", "按实际完成时间"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="tasks",
        verbose_name="用户",
        db_index=True,
    )
    title = models.CharField("任务标题", max_length=200)
    description = models.TextField("任务详情", blank=True)
    status = models.CharField(
        "状态",
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_STARTED,
        db_index=True,
    )
    created_time = models.DateTimeField("创建时间", auto_now_add=True, db_index=True)
    completed_time = models.DateTimeField("完成时间", null=True, blank=True, db_index=True)
    spent_minutes = models.PositiveIntegerField("耗时（分钟）", null=True, blank=True, db_index=True)
    time_accounting_basis = models.CharField(
        "计时口径",
        max_length=20,
        choices=TimeAccountingBasis.choices,
        default=TimeAccountingBasis.COMPLETED_TIME,
        db_index=True,
    )
    is_deleted = models.BooleanField("是否删除", default=False, db_index=True)
    deleted_time = models.DateTimeField("删除时间", null=True, blank=True, db_index=True)
    deadline = models.DateTimeField("截止时间", null=True, blank=True, db_index=True)
    remark = models.TextField("备注信息", blank=True)

    class Meta:
        ordering = ["-created_time"]
        verbose_name = "任务"
        verbose_name_plural = "任务"

    def __str__(self) -> str:
        return self.title


class StudySession(models.Model):
    class Category(models.TextChoices):
        LISTENING = "listening", "听力"
        READING = "reading", "阅读"
        TRANSLATION = "translation", "翻译"
        WRITING = "writing", "作文"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="study_sessions",
        verbose_name="用户",
        db_index=True,
    )
    category = models.CharField(
        "专项",
        max_length=20,
        choices=Category.choices,
        db_index=True,
    )
    minutes = models.PositiveIntegerField("训练时长（分钟）")
    session_date = models.DateField("训练日期", default=timezone.localdate, db_index=True)
    remark = models.CharField("备注", max_length=200, blank=True)
    created_time = models.DateTimeField("创建时间", auto_now_add=True, db_index=True)
    linked_task = models.OneToOneField(
        "Task",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="cet4_session",
        verbose_name="同步任务",
    )

    class Meta:
        ordering = ["-session_date", "-created_time"]
        verbose_name = "四级训练记录"
        verbose_name_plural = "四级训练记录"

    def __str__(self) -> str:
        return f"{self.get_category_display()} {self.minutes}min"


class Exam408Item(models.Model):
    """408 考纲知识点清单（内置 + 用户自定义）；不与 Task 同步。"""

    class Pillar(models.TextChoices):
        DS = "ds", "数据结构"
        OS = "os", "操作系统"
        CO = "co", "计算机组成原理"
        CN = "cn", "计算机网络"

    pillar = models.CharField("科目", max_length=2, choices=Pillar.choices, db_index=True)
    module = models.CharField("模块", max_length=64)
    label = models.CharField("知识点", max_length=200)
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="exam408_custom_items",
        verbose_name="创建者",
    )
    created_time = models.DateTimeField("创建时间", auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["pillar", "sort_order", "id"]
        verbose_name = "408知识点"
        verbose_name_plural = "408知识点"

    def __str__(self) -> str:
        return f"{self.get_pillar_display()}/{self.module}: {self.label}"


class Exam408Progress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="exam408_progress_rows",
    )
    item = models.ForeignKey(
        Exam408Item,
        on_delete=models.CASCADE,
        related_name="progress_rows",
    )
    is_done = models.BooleanField("已完成", default=False, db_index=True)
    note = models.TextField("知识点备注", blank=True)
    updated_time = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "item"], name="uniq_exam408_progress_user_item"),
        ]
        verbose_name = "408勾选进度"
        verbose_name_plural = "408勾选进度"

    def __str__(self) -> str:
        return f"{self.user_id}:{self.item_id}:{self.is_done}"


class ExamMathUserPreference(models.Model):
    """每个账号选择的考研数学卷种（一/二），可修改。"""

    class Track(models.TextChoices):
        M1 = "m1", "数学一"
        M2 = "m2", "数学二"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="exam_math_pref",
        verbose_name="用户",
    )
    track = models.CharField(
        "卷种",
        max_length=2,
        choices=Track.choices,
        db_index=True,
    )
    updated_time = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "考研数学卷种偏好"
        verbose_name_plural = "考研数学卷种偏好"

    def __str__(self) -> str:
        return f"{self.user_id}:{self.track}"


class ExamMathItem(models.Model):
    """考研数学一/二知识点清单（参考全国统考大纲结构）；不与 Task 同步。"""

    class Track(models.TextChoices):
        M1 = "m1", "数学一"
        M2 = "m2", "数学二"

    class Subject(models.TextChoices):
        CALC = "calc", "高等数学"
        LA = "la", "线性代数"
        PROB = "prob", "概率论与数理统计"

    track = models.CharField("卷种", max_length=2, choices=Track.choices, db_index=True)
    subject = models.CharField("科目", max_length=4, choices=Subject.choices, db_index=True)
    module = models.CharField("章节", max_length=64)
    label = models.CharField("知识点", max_length=200)
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="exam_math_custom_items",
        verbose_name="创建者",
    )
    created_time = models.DateTimeField("创建时间", auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["track", "subject", "sort_order", "id"]
        verbose_name = "考研数学知识点"
        verbose_name_plural = "考研数学知识点"

    def __str__(self) -> str:
        return f"{self.get_track_display()}/{self.get_subject_display()}/{self.module}: {self.label}"


class ExamMathProgress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="exam_math_progress_rows",
    )
    item = models.ForeignKey(
        ExamMathItem,
        on_delete=models.CASCADE,
        related_name="progress_rows",
    )
    is_done = models.BooleanField("已完成", default=False, db_index=True)
    note = models.TextField("知识点备注", blank=True)
    updated_time = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "item"], name="uniq_exam_math_progress_user_item"
            ),
        ]
        verbose_name = "考研数学勾选进度"
        verbose_name_plural = "考研数学勾选进度"

    def __str__(self) -> str:
        return f"{self.user_id}:{self.item_id}:{self.is_done}"


class UserProfile(models.Model):
    """注册补充信息：手机号等用户联系信息。"""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="用户",
    )
    phone = models.CharField("手机号", max_length=20)
    created_time = models.DateTimeField("创建时间", auto_now_add=True)
    updated_time = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "用户资料"
        verbose_name_plural = "用户资料"

    def __str__(self) -> str:
        return f"{self.user_id}:{self.phone}"


class UserSessionBinding(models.Model):
    """记录账号当前有效会话，用于单账号单设备登录控制。"""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="session_binding",
        verbose_name="用户",
    )
    session_key = models.CharField("当前会话Key", max_length=64, default="")
    updated_time = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "用户会话绑定"
        verbose_name_plural = "用户会话绑定"

    def __str__(self) -> str:
        return f"{self.user_id}:{self.session_key}"


class Topic(models.Model):
    """专题（每个账号自己的专题列表）。"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="topics",
        verbose_name="用户",
    )
    name = models.CharField("专题名称", max_length=50)
    is_builtin = models.BooleanField("内置专题", default=False, db_index=True)
    merge_into_tasks = models.BooleanField("合并到任务时间", default=False, db_index=True)
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    created_time = models.DateTimeField("创建时间", auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="uniq_topic_user_name"),
        ]
        verbose_name = "专题"
        verbose_name_plural = "专题"

    def __str__(self) -> str:
        return f"{self.user_id}:{self.name}"


class TimeEntry(models.Model):
    """每天专题学习时长记录（分钟）。"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="time_entries",
        verbose_name="用户",
    )
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name="time_entries",
        verbose_name="专题",
    )
    source_task = models.ForeignKey(
        Task,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="time_entries",
        verbose_name="来源任务",
    )
    entry_date = models.DateField("日期", default=timezone.localdate, db_index=True)
    minutes = models.PositiveIntegerField("分钟数")
    note = models.CharField("备注", max_length=200, blank=True)
    created_time = models.DateTimeField("创建时间", auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-entry_date", "-created_time"]
        indexes = [
            models.Index(fields=["user", "entry_date"]),
            models.Index(fields=["user", "topic", "entry_date"]),
        ]
        verbose_name = "学习时间记录"
        verbose_name_plural = "学习时间记录"

    def __str__(self) -> str:
        return f"{self.user_id}:{self.topic_id}:{self.entry_date}:{self.minutes}"


class TopicModule(models.Model):
    """专题下的章节/模块（可写章节备注）。"""

    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name="modules",
        verbose_name="专题",
    )
    name = models.CharField("章节", max_length=64)
    note = models.TextField("章节备注", blank=True)
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    created_time = models.DateTimeField("创建时间", auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["topic", "name"], name="uniq_topic_module_topic_name"),
        ]
        verbose_name = "专题章节"
        verbose_name_plural = "专题章节"

    def __str__(self) -> str:
        return f"{self.topic_id}:{self.name}"


class TopicItem(models.Model):
    """章节下的条目（类似 408/数学 的知识点条目）。"""

    module = models.ForeignKey(
        TopicModule,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="章节",
    )
    label = models.CharField("条目", max_length=200)
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="custom_topic_items",
        verbose_name="创建者",
    )
    created_time = models.DateTimeField("创建时间", auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "专题条目"
        verbose_name_plural = "专题条目"

    def __str__(self) -> str:
        return f"{self.module_id}:{self.label}"


class TopicProgress(models.Model):
    """每个账号对每个条目的勾选与备注（仅自己可见）。"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="topic_progress_rows",
        verbose_name="用户",
    )
    item = models.ForeignKey(
        TopicItem,
        on_delete=models.CASCADE,
        related_name="progress_rows",
        verbose_name="条目",
    )
    is_done = models.BooleanField("已完成", default=False, db_index=True)
    note = models.TextField("条目备注", blank=True)
    updated_time = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "item"], name="uniq_topic_progress_user_item"),
        ]
        verbose_name = "专题勾选进度"
        verbose_name_plural = "专题勾选进度"

    def __str__(self) -> str:
        return f"{self.user_id}:{self.item_id}:{self.is_done}"


class ActivityLog(models.Model):
    """用户操作历史记录。"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="activity_logs",
        verbose_name="用户",
    )
    action = models.CharField("动作", max_length=64, db_index=True)
    target_type = models.CharField("对象类型", max_length=32, db_index=True)
    target_id = models.PositiveIntegerField("对象ID", null=True, blank=True, db_index=True)
    target_name = models.CharField("对象名称", max_length=200, blank=True)
    detail = models.JSONField("详情", default=dict, blank=True)
    created_time = models.DateTimeField("创建时间", auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_time", "-id"]
        verbose_name = "操作历史"
        verbose_name_plural = "操作历史"

    def __str__(self) -> str:
        return f"{self.user_id}:{self.action}:{self.target_type}:{self.target_id or '-'}"
