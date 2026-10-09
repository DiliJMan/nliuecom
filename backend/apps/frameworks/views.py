import json
import tempfile
from pathlib import Path

from django.db.models import Count, Q
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.core.api import ScopedModelViewSet
from apps.domains.models import Domain

from . import loader
from .importers import PARSERS, projectjson
from .importers.spec import ImportProblem
from .models import Framework, RequirementMapping, RequirementNode
from .scope import framework_scope
from .serializers import (
    DeriveSerializer,
    FrameworkSerializer,
    ImportSerializer,
    RequirementMappingSerializer,
    RequirementNodeSerializer,
    slugify_name,
)

MAX_UPLOAD = 60 * 1024 * 1024


class FrameworkViewSet(ScopedModelViewSet):
    object_type = "frameworks.framework"
    queryset = Framework.objects.all()
    serializer_class = FrameworkSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    action_permissions = {"nodes": "view", "derive": "view", "export": "view"}

    def get_queryset(self):
        return (
            Framework.objects.filter(framework_scope(self.request.user))
            .annotate(
                node_count=Count("nodes"),
                assessable_count=Count("nodes", filter=Q(nodes__assessable=True)),
            )
            .order_by("name", "version")
        )

    def perform_update(self, serializer):
        if serializer.instance.locked:
            raise ValidationError(
                "Imported frameworks are read-only. Derive a copy to customise it."
            )
        serializer.save()

    @extend_schema(responses=RequirementNodeSerializer(many=True))
    @action(detail=True, methods=["get"], pagination_class=None)
    def nodes(self, request, pk=None):
        framework = self.get_object()
        nodes = framework.nodes.order_by("order")
        return Response(RequirementNodeSerializer(nodes, many=True).data)

    @extend_schema(request=DeriveSerializer, responses=FrameworkSerializer)
    @action(detail=True, methods=["post"])
    def derive(self, request, pk=None):
        source = self.get_object()
        data = DeriveSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        domain = Domain.objects.filter(pk=data.validated_data["domain"]).first()
        if domain is None:
            raise ValidationError({"domain": "Domain not found."})
        self.require("add", domain)
        slug = data.validated_data.get("slug") or slugify_name(data.validated_data["name"])
        if Framework.objects.filter(slug=slug, domain=domain).exists():
            raise ValidationError(
                {"slug": "This domain already has a framework with that identifier."}
            )
        copy = loader.derive(source, domain=domain, name=data.validated_data["name"], slug=slug)
        copy = self.get_queryset().get(pk=copy.pk)
        return Response(FrameworkSerializer(copy).data, status=status.HTTP_201_CREATED)

    @extend_schema(responses=None)
    @action(detail=True, methods=["get"])
    def export(self, request, pk=None):
        framework = self.get_object()
        if not framework.redistributable:
            raise PermissionDenied(
                "This framework contains licensed or no-derivatives material and cannot be exported."
            )
        body = json.dumps(projectjson.to_dict(framework), indent=2, ensure_ascii=False)
        response = HttpResponse(body, content_type="application/json")
        response["Content-Disposition"] = f'attachment; filename="{framework.slug}.json"'
        return response

    @extend_schema(request=ImportSerializer, responses=FrameworkSerializer)
    @action(detail=False, methods=["post"], url_path="import")
    def import_file(self, request):
        data = ImportSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        kind, upload = data.validated_data["kind"], data.validated_data["file"]
        domain = None
        if data.validated_data.get("domain"):
            domain = Domain.objects.filter(pk=data.validated_data["domain"]).first()
            if domain is None:
                raise ValidationError({"domain": "Domain not found."})
            if kind != "project":
                raise ValidationError(
                    {"domain": "Only project files can be imported into a domain."}
                )
        # Instance-wide imports (and licensed sources) are for instance administrators only.
        self.require("add", domain)
        parse, suffix = PARSERS[kind]
        if upload.size > MAX_UPLOAD:
            raise ValidationError({"file": "The file is too large."})
        if Path(upload.name).suffix.lower() != suffix:
            raise ValidationError({"file": f"Expected a {suffix} file."})
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / f"upload{suffix}"
            with open(target, "wb") as handle:
                for chunk in upload.chunks():
                    handle.write(chunk)
            try:
                spec = parse(target)
                spec.source = (
                    f"{spec.source.split(' ')[0]} {Path(upload.name).name}".strip()
                    if kind != "project"
                    else f"Project file {Path(upload.name).name}"
                )
                framework = loader.load(spec, replace=data.validated_data["replace"], domain=domain)
            except ImportProblem as exc:
                raise ValidationError({"file": str(exc)}) from None
        framework = self.get_queryset().get(pk=framework.pk)
        body = FrameworkSerializer(framework).data
        body["notes"] = spec.notes
        return Response(body, status=status.HTTP_201_CREATED)


class RequirementNodeViewSet(ScopedModelViewSet):
    object_type = "frameworks.requirementnode"
    domain_lookup = "framework__domain"
    queryset = RequirementNode.objects.select_related("framework")
    serializer_class = RequirementNodeSerializer
    action_permissions = {"mappings": "view"}

    def get_queryset(self):
        queryset = RequirementNode.objects.select_related("framework").filter(
            framework_scope(self.request.user, "framework__")
        )
        framework = self.request.query_params.get("framework")
        return queryset.filter(framework=framework) if framework else queryset

    def creation_domain(self, serializer):
        return serializer.validated_data["framework"].domain

    def perform_update(self, serializer):
        serializer.save()

    @extend_schema(responses=RequirementMappingSerializer(many=True))
    @action(detail=True, methods=["get"], pagination_class=None)
    def mappings(self, request, pk=None):
        node = self.get_object()
        links = RequirementMapping.objects.filter(Q(source=node) | Q(target=node)).select_related(
            "source__framework", "target__framework"
        )
        visible = framework_scope(request.user, "")
        allowed = set(Framework.objects.filter(visible).values_list("pk", flat=True))
        links = [
            link
            for link in links
            if link.source.framework_id in allowed and link.target.framework_id in allowed
        ]
        return Response(RequirementMappingSerializer(links, many=True).data)


class RequirementMappingViewSet(ScopedModelViewSet):
    object_type = "frameworks.requirementmapping"
    domain_lookup = None
    queryset = RequirementMapping.objects.select_related("source__framework", "target__framework")
    serializer_class = RequirementMappingSerializer
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        queryset = super().get_queryset().order_by("source__ref_id", "target__ref_id", "id")
        framework = self.request.query_params.get("framework")
        if framework:
            queryset = queryset.filter(
                Q(source__framework=framework) | Q(target__framework=framework)
            )
        return queryset
