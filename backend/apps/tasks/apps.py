from django.apps import AppConfig


class TasksConfig(AppConfig):
    name = "apps.tasks"
    label = "tasks"

    def ready(self):
        from apps.core import registry

        from .models import Task

        registry.register(
            registry.ObjectType(
                key="tasks.task", model=Task, label="Task", supports_custom_fields=True
            )
        )
