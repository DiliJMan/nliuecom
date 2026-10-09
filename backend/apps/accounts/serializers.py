from django.contrib.auth.password_validation import validate_password
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.access.models import RoleAssignment

from .models import User, UserGroup


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=False, style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_superuser",
            "password",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        password = attrs.get("password")
        if self.instance is None and not password:
            raise serializers.ValidationError({"password": "A password is required."})
        if password:
            candidate = self.instance or User(
                email=attrs.get("email", ""),
                first_name=attrs.get("first_name", ""),
                last_name=attrs.get("last_name", ""),
            )
            validate_password(password, candidate)
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

    def validate_email(self, value):
        value = value.lower()
        clash = User.objects.filter(email__iexact=value).exclude(
            pk=getattr(self.instance, "pk", None)
        )
        if clash.exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value


class UserGroupSerializer(serializers.ModelSerializer):
    members = serializers.PrimaryKeyRelatedField(
        many=True, queryset=User.objects.all(), required=False
    )

    class Meta:
        model = UserGroup
        fields = ["id", "name", "description", "members", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class GrantSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source="role.name", read_only=True)
    domain_name = serializers.CharField(source="domain.name", read_only=True)

    class Meta:
        model = RoleAssignment
        fields = ["id", "role", "role_name", "domain", "domain_name", "recursive"]


class MeSerializer(serializers.ModelSerializer):
    grants = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "is_superuser", "grants"]

    @extend_schema_field(GrantSerializer(many=True))
    def get_grants(self, user):
        from django.db.models import Q

        assignments = (
            RoleAssignment.objects.filter(Q(user=user) | Q(group__members=user))
            .select_related("role", "domain")
            .distinct()
        )
        return GrantSerializer(assignments, many=True).data
