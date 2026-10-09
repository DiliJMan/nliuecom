from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.core.api import ScopedModelViewSet

from . import service
from .models import Task
from .serializers import TaskSerializer


class TaskViewSet(ScopedModelViewSet):
    object_type = "tasks.task"
    queryset = Task.objects.select_related("domain", "assignee")
    serializer_class = TaskSerializer
    filter_fields = ("domain", "status", "priority", "linked_object_type", "linked_object_id")
    search_fields = ("title", "description")
    ordering_fields = ("due_date", "priority", "title", "created_at")
    action_permissions = {"complete": "change"}

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        assignee = params.get("assignee")
        if assignee == "me":
            queryset = queryset.filter(assignee=self.request.user)
        elif assignee:
            queryset = queryset.filter(assignee=assignee)
        if params.get("open") in ("1", "true"):
            queryset = queryset.filter(status__in=Task.OPEN)
        if params.get("due_before"):
            queryset = queryset.filter(Q(due_date__lte=params["due_before"]))
        return queryset

    @extend_schema(request=None, responses=TaskSerializer)
    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        task = self.get_object()
        if task.status in (Task.Status.DONE, Task.Status.CANCELLED):
            raise ValidationError("This task is already closed.")
        service.complete(task)
        return Response(
            TaskSerializer(self.get_queryset().get(pk=task.pk), context={"request": request}).data
        )
