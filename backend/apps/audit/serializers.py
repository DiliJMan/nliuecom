from rest_framework import serializers

from .models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    changes = serializers.DictField(read_only=True)

    class Meta:
        model = AuditEvent
        fields = [
            "id",
            "timestamp",
            "actor_id",
            "actor_email",
            "ip_address",
            "action",
            "object_type",
            "object_id",
            "object_repr",
            "domain_id",
            "changes",
            "prev_hash",
            "hash",
        ]
        read_only_fields = fields
