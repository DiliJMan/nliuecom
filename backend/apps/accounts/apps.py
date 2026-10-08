from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "apps.accounts"
    label = "accounts"

    def ready(self):
        from apps.core import registry

        from .models import User, UserGroup

        registry.register(
            registry.ObjectType(
                key="accounts.user",
                model=User,
                label="User",
                domain_of=lambda obj: None,
                audit_exclude=("password", "last_login"),
            )
        )
        registry.register(
            registry.ObjectType(
                key="accounts.usergroup",
                model=UserGroup,
                label="User group",
                domain_of=lambda obj: None,
            )
        )
