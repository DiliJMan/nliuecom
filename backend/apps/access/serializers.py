from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from apps.access import policy

from .models import Role, RoleAssignment


class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.ListField(child=serializers.CharField(), required=False)

    class Meta:
        model = Role
        fields = ["id", "name", "description", "permissions", "builtin", "created_at", "updated_at"]
        read_only_fields = ["id", "builtin", "created_at", "updated_at"]


class RoleAssignmentSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True, default=None)
    group_name = serializers.CharField(source="group.name", read_only=True, default=None)
    role_name = serializers.CharField(source="role.name", read_only=True)
    domain_name = serializers.CharField(source="domain.name", read_only=True)

    class Meta:
        model = RoleAssignment
        fields = [
            "id",
            "user",
            "user_email",
            "group",
            "group_name",
            "role",
            "role_name",
            "domain",
            "domain_name",
            "recursive",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        if bool(attrs.get("user")) == bool(attrs.get("group")):
            raise serializers.ValidationError("Give exactly one of user or group.")
        actor = self.context["request"].user
        if not policy.has_permission(actor, "access.roleassignment:add", attrs["domain"]):
            raise PermissionDenied()
        # No one can hand out more than they hold at that domain.
        held = policy.effective_permissions(actor, attrs["domain"])
        excess = sorted(set(attrs["role"].permissions) - held)
        if excess:
            raise serializers.ValidationError(
                {"role": f"This role carries permissions you do not hold here: {', '.join(excess)}"}
            )
        return attrs
