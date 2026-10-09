from rest_framework import serializers

from apps.accounts.models import User
from apps.core import registry
from apps.core.linking import check_links
from apps.core.serializers import DomainObjectSerializer

from .models import Task


class TaskSerializer(DomainObjectSerializer):
    custom_fields_object_type = "tasks.task"
    custom_fields = serializers.DictField(required=False)
    assignee = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True), required=False, allow_null=True
    )
    assignee_email = serializers.CharField(source="assignee.email", read_only=True, default=None)
    overdue = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id",
            "domain",
            "title",
            "description",
            "assignee",
            "assignee_email",
            "status",
            "priority",
            "due_date",
            "overdue",
            "recurrence",
            "recurrence_interval",
            "reminder_days_before",
            "completed_at",
            "next_task",
            "linked_object_type",
            "linked_object_id",
            "custom_fields",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "completed_at", "next_task", "created_at", "updated_at"]

    def get_overdue(self, task) -> bool:
        from datetime import date

        return bool(task.due_date and task.status in Task.OPEN and task.due_date < date.today())

    def validate(self, attrs):
        attrs = super().validate(attrs)
        merged = {
            f: attrs.get(f, getattr(self.instance, f, None))
            for f in ("recurrence", "due_date", "linked_object_type", "linked_object_id")
        }
        if merged["recurrence"] not in (None, Task.Recurrence.NONE) and merged["due_date"] is None:
            raise serializers.ValidationError({"due_date": "A repeating task needs a due date."})
        kind, ident = merged["linked_object_type"] or "", merged["linked_object_id"] or ""
        if bool(kind) != bool(ident):
            raise serializers.ValidationError("Give both linked_object_type and linked_object_id.")
        if kind:
            info = registry.find(kind)
            target = info.model.objects.filter(pk=ident).first() if info else None
            if target is None:
                raise serializers.ValidationError(
                    {"linked_object_id": "The linked object does not exist."}
                )
            request = self.context.get("request")
            domain = self.object_domain(attrs)
            if request is not None and domain is not None:
                check_links(request.user, domain, {"linked_object_id": (kind, [target])})
        return attrs
