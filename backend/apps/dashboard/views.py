from collections import Counter
from datetime import date, timedelta

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.policy import scope_queryset
from apps.assets.models import Asset
from apps.compliance.models import ComplianceAssessment
from apps.controls.models import AppliedControl
from apps.frameworks.models import Framework
from apps.frameworks.scope import framework_scope
from apps.risk.models import RiskScenario
from apps.tasks.models import Task

MAX_SCENARIOS = 5000


@extend_schema(
    responses=inline_serializer(
        "Dashboard",
        {
            "assets": serializers.IntegerField(),
            "frameworks": serializers.IntegerField(),
            "controls": serializers.DictField(),
            "risk": serializers.DictField(),
            "compliance": serializers.ListField(child=serializers.DictField()),
            "tasks": serializers.DictField(),
        },
    )
)
class DashboardView(APIView):
    """Headline numbers, limited to the domains the caller can see."""

    def get(self, request):
        user = request.user
        assets = scope_queryset(user, Asset.objects.all(), "assets.asset:view")
        controls = scope_queryset(
            user, AppliedControl.objects.all(), "controls.appliedcontrol:view"
        )
        scenarios = scope_queryset(
            user,
            RiskScenario.objects.select_related("risk_assessment__matrix"),
            "risk.riskscenario:view",
            "risk_assessment__domain",
        )
        assessments = scope_queryset(
            user,
            ComplianceAssessment.objects.select_related("domain", "framework"),
            "compliance.complianceassessment:view",
        )
        tasks = scope_queryset(
            user, Task.objects.filter(assignee=user, status__in=Task.OPEN), "tasks.task:view"
        )

        by_level: Counter = Counter()
        colours: dict[str, str] = {}
        unrated = 0
        total_scenarios = scenarios.count()
        for scenario in scenarios[:MAX_SCENARIOS]:
            level = scenario.residual_level() or scenario.current_level()
            if level is None:
                unrated += 1
                continue
            by_level[level["name"]] += 1
            colours[level["name"]] = level["colour"]

        today = date.today()
        return Response(
            {
                "assets": assets.count(),
                "frameworks": Framework.objects.filter(framework_scope(user)).count(),
                "controls": {
                    "total": controls.count(),
                    "by_status": dict(Counter(controls.values_list("status", flat=True))),
                },
                "risk": {
                    "scenarios": total_scenarios,
                    "unrated": unrated,
                    "by_level": [
                        {"name": name, "colour": colours[name], "count": count}
                        for name, count in by_level.most_common()
                    ],
                },
                "compliance": [
                    {
                        "id": str(a.pk),
                        "name": a.name,
                        "framework": a.framework.name,
                        "domain": a.domain.name,
                        "summary": a.summary(),
                    }
                    for a in assessments.order_by("name")[:12]
                ],
                "tasks": {
                    "open": tasks.count(),
                    "overdue": tasks.filter(due_date__lt=today).count(),
                    "due_this_week": tasks.filter(
                        due_date__gte=today, due_date__lte=today + timedelta(days=7)
                    ).count(),
                },
            }
        )
