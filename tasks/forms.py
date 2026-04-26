import random
import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core import signing
from django.utils import timezone

from .models import StudySession, Task, TimeEntry, Topic, TopicModule


class RegisterForm(UserCreationForm):
    """用户自注册（样式由模板类名配合 style.css 的 .auth-* 控制）。"""

    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=True)
    captcha_token = forms.CharField(widget=forms.HiddenInput())
    captcha_answer = forms.IntegerField(min_value=0)

    class Meta:
        model = get_user_model()
        fields = ("username", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        u = self.fields["username"]
        u.label = "账户名称"
        u.help_text = None
        u.widget.attrs.update(
            {
                "class": "auth-input",
                "autocomplete": "username",
                "placeholder": "用户名",
                "autocapitalize": "off",
                "spellcheck": "false",
            }
        )
        p1 = self.fields["password1"]
        p1.label = "密码"
        p1.help_text = None
        p1.widget.attrs.update(
            {
                "class": "auth-input",
                "autocomplete": "new-password",
                "placeholder": "至少 8 个字符",
            }
        )
        p2 = self.fields["password2"]
        p2.label = "确认密码"
        p2.help_text = None
        p2.widget.attrs.update(
            {
                "class": "auth-input",
                "autocomplete": "new-password",
                "placeholder": "再次输入密码",
            }
        )
        e = self.fields["email"]
        e.label = "邮箱"
        e.help_text = None
        e.widget.attrs.update(
            {
                "class": "auth-input",
                "autocomplete": "email",
                "placeholder": "name@example.com",
            }
        )
        ph = self.fields["phone"]
        ph.label = "手机号"
        ph.help_text = "仅用于账户识别与后续找回。"
        ph.widget.attrs.update(
            {
                "class": "auth-input",
                "autocomplete": "tel",
                "placeholder": "11位手机号",
                "inputmode": "numeric",
            }
        )
        c = self.fields["captcha_answer"]
        c.label = "人机验证"
        c.help_text = "请完成上面的加法计算。"
        c.widget.attrs.update({"class": "auth-input", "placeholder": "请输入结果"})
        self.order_fields(["username", "email", "phone", "password1", "password2", "captcha_answer", "captcha_token"])

        token = ""
        pair = None
        if self.is_bound:
            token = (self.data.get("captcha_token") or "").strip()
            pair = self._read_captcha(token)
        if pair is None:
            pair = self._new_captcha_pair()
            token = self._sign_captcha(pair)
            self.initial["captcha_token"] = token
        self.fields["captcha_answer"].label = f"人机验证：{pair['a']} + {pair['b']} = ?"

    @staticmethod
    def _new_captcha_pair():
        return {"a": random.randint(2, 12), "b": random.randint(2, 12)}

    @staticmethod
    def _sign_captcha(payload):
        return signing.dumps(payload, salt="register-captcha")

    @staticmethod
    def _read_captcha(token):
        if not token:
            return None
        try:
            payload = signing.loads(token, salt="register-captcha", max_age=600)
        except signing.BadSignature:
            return None
        if not isinstance(payload, dict):
            return None
        if "a" not in payload or "b" not in payload:
            return None
        return payload

    def clean(self):
        cleaned = super().clean()
        token = (cleaned.get("captcha_token") or "").strip()
        pair = self._read_captcha(token)
        if not pair:
            self.add_error("captcha_answer", "验证已过期，请刷新后重试。")
            return cleaned
        answer = cleaned.get("captcha_answer")
        if answer is None:
            return cleaned
        if answer != pair["a"] + pair["b"]:
            self.add_error("captcha_answer", "答案不正确，请再试一次。")
        return cleaned

    def clean_phone(self):
        phone = re.sub(r"\s+", "", (self.cleaned_data.get("phone") or ""))
        if not re.fullmatch(r"1\d{10}", phone):
            raise forms.ValidationError("请输入有效的 11 位手机号。")
        return phone

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = (self.cleaned_data.get("email") or "").strip()
        if commit:
            user.save()
        return user


class TaskForm(forms.ModelForm):
    deadline_choice = forms.ChoiceField(required=False)
    deadline_custom = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local", "step": "1"},
            format="%Y-%m-%dT%H:%M:%S",
        ),
    )

    class Meta:
        model = Task
        fields = ["title", "description", "status", "time_accounting_basis", "spent_minutes", "remark"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "例如：完成周报"}),
            "description": forms.Textarea(attrs={"rows": 4, "placeholder": "任务详情（可选）"}),
            "remark": forms.Textarea(attrs={"rows": 3, "placeholder": "备注（可选）"}),
            "spent_minutes": forms.NumberInput(attrs={"min": "1", "placeholder": "例如：45"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_class = "input"
        self.fields["title"].widget.attrs.setdefault("class", base_class)
        self.fields["status"].widget.attrs.setdefault("class", "select")
        self.fields["time_accounting_basis"].widget.attrs.setdefault("class", "select")
        self.fields["description"].widget.attrs.setdefault("class", base_class)
        self.fields["spent_minutes"].widget.attrs.setdefault("class", base_class)
        self.fields["remark"].widget.attrs.setdefault("class", base_class)

        self.fields["deadline_choice"].widget.attrs.setdefault("class", "select")
        self.fields["deadline_choice"].label = "截止时间"

        self.fields["deadline_custom"].widget.attrs.setdefault("class", base_class)
        self.fields["deadline_custom"].label = "自定义截止时间"

        now = timezone.localtime()
        today_18 = now.replace(hour=18, minute=0, second=0, microsecond=0)
        if today_18 <= now:
            today_18 = today_18 + timezone.timedelta(days=1)

        def iso(dt):
            return dt.isoformat()

        choices = [
            ("", "无截止时间"),
            (iso(today_18), "今天/最近的 18:00"),
            (iso(now + timezone.timedelta(days=1)), "明天（当前时间）"),
            (iso(now + timezone.timedelta(days=3)), "3 天后（当前时间）"),
            (iso(now + timezone.timedelta(days=7)), "7 天后（当前时间）"),
            (iso(now + timezone.timedelta(days=30)), "30 天后（当前时间）"),
            ("__custom__", "自定义…（精确到秒）"),
        ]

        if self.instance and self.instance.deadline:
            current = timezone.localtime(self.instance.deadline)
            current_key = iso(current)
            choices.insert(1, (current_key, f"保持当前：{current.strftime('%Y-%m-%d %H:%M')}"))
            self.initial["deadline_choice"] = current_key
            self.initial["deadline_custom"] = current.strftime("%Y-%m-%dT%H:%M:%S")

        self.fields["deadline_choice"].choices = choices

    def clean(self):
        cleaned = super().clean()
        choice = cleaned.get("deadline_choice") or ""
        custom = cleaned.get("deadline_custom")

        if choice == "__custom__":
            if not custom:
                raise forms.ValidationError("请选择自定义截止时间（精确到秒）。")
            cleaned["deadline"] = timezone.localtime(custom)
            if timezone.is_naive(cleaned["deadline"]):
                cleaned["deadline"] = timezone.make_aware(
                    cleaned["deadline"], timezone.get_current_timezone()
                )
            return cleaned

        if choice == "":
            cleaned["deadline"] = None
            return cleaned

        try:
            cleaned["deadline"] = timezone.datetime.fromisoformat(choice)
        except ValueError:
            raise forms.ValidationError("截止时间选项无效，请重新选择。")

        if timezone.is_naive(cleaned["deadline"]):
            cleaned["deadline"] = timezone.make_aware(cleaned["deadline"], timezone.get_current_timezone())
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.deadline = self.cleaned_data.get("deadline")
        if commit:
            instance.save()
        return instance


class StudySessionForm(forms.ModelForm):
    class Meta:
        model = StudySession
        fields = ["category", "minutes", "session_date", "remark"]
        widgets = {
            "remark": forms.TextInput(attrs={"placeholder": "可选：例如 听力真题第1套"}),
            "session_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].widget.attrs.setdefault("class", "select")
        self.fields["minutes"].widget.attrs.setdefault("class", "input")
        self.fields["session_date"].widget.attrs.setdefault("class", "input")
        self.fields["remark"].widget.attrs.setdefault("class", "input")
        self.fields["minutes"].widget.attrs.setdefault("min", "1")


class TopicForm(forms.ModelForm):
    class Meta:
        model = Topic
        fields = ["name", "merge_into_tasks"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].widget.attrs.setdefault("class", "input")
        self.fields["name"].widget.attrs.setdefault("maxlength", "50")
        self.fields["merge_into_tasks"].widget.attrs.setdefault("class", "checkbox")

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("请输入专题名称。")
        return name


class TimeEntryForm(forms.ModelForm):
    class Meta:
        model = TimeEntry
        fields = ["topic", "entry_date", "minutes", "note"]
        widgets = {
            "entry_date": forms.DateInput(attrs={"type": "date"}),
            "note": forms.TextInput(attrs={"placeholder": "可选：例如 真题/章节/番茄钟…"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["topic"].widget.attrs.setdefault("class", "select")
        self.fields["entry_date"].widget.attrs.setdefault("class", "input")
        self.fields["minutes"].widget.attrs.setdefault("class", "input")
        self.fields["note"].widget.attrs.setdefault("class", "input")
        self.fields["minutes"].widget.attrs.setdefault("min", "1")
        if user is not None:
            self.fields["topic"].queryset = Topic.objects.filter(user=user).order_by(
                "sort_order", "id"
            )


class TopicItemAddForm(forms.Form):
    module = forms.ModelChoiceField(queryset=TopicModule.objects.none(), required=False)
    new_module = forms.CharField(max_length=64, required=False)
    label = forms.CharField(max_length=200)

    def __init__(self, *args, **kwargs):
        topic = kwargs.pop("topic", None)
        super().__init__(*args, **kwargs)
        self.fields["label"].widget.attrs.setdefault("class", "input")
        self.fields["new_module"].widget.attrs.setdefault("class", "input")
        self.fields["module"].widget.attrs.setdefault("class", "select")
        if topic is not None:
            self.fields["module"].queryset = TopicModule.objects.filter(topic=topic).order_by(
                "sort_order", "id"
            )

    def clean(self):
        cleaned = super().clean()
        if not cleaned:
            return cleaned
        label = (cleaned.get("label") or "").strip()
        if not label:
            raise forms.ValidationError("请输入条目内容。")
        cleaned["label"] = label

        mod = cleaned.get("module")
        new_mod = (cleaned.get("new_module") or "").strip()
        if not mod and not new_mod:
            raise forms.ValidationError("请选择章节或输入新章节名称。")
        cleaned["new_module"] = new_mod
        return cleaned
