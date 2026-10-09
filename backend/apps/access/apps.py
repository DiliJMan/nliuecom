from django.apps import AppConfig


class AccessConfig(AppConfig):
    name = "apps.access"
    label = "access"

    def ready(self):
        from django.db.models.signals import post_migrate

        from apps.core import registry

        from .builtin import sync_builtin_roles

        post_migrate.connect(sync_builtin_roles, sender=self, dispatch_uid="sync_builtin_roles")

        from .models import Role, RoleAssignment

        registry.register(
            registry.ObjectType(
                key="access.role", model=Role, label="Role", domain_of=lambda obj: None
            )
        )
        registry.register(
            registry.ObjectType(
                key="access.roleassignment",
                model=RoleAssignment,
                label="Role assignment",
                actions=("view", "add", "delete"),
                domain_of=lambda obj: obj.domain,
            )
        )
