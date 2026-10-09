from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.core.api import ScopedModelViewSet

from .models import User, UserGroup
from .serializers import GrantSerializer, MeSerializer, UserGroupSerializer, UserSerializer


@extend_schema(
    responses=inline_serializer("Csrf", {"csrfToken": serializers.CharField()}),
)
class CsrfView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(style={"input_type": "password"})


@method_decorator(csrf_protect, name="dispatch")
@extend_schema(
    request=LoginSerializer,
    responses={
        200: inline_serializer(
            "LoginResult",
            {
                "id": serializers.UUIDField(),
                "email": serializers.EmailField(),
                "first_name": serializers.CharField(),
                "last_name": serializers.CharField(),
                "is_superuser": serializers.BooleanField(),
                "grants": GrantSerializer(many=True),
                "csrfToken": serializers.CharField(),
            },
        ),
        401: OpenApiResponse(description="Invalid email or password."),
    },
)
class LoginView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        data = LoginSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        user = authenticate(
            request._request,
            username=data.validated_data["email"],
            password=data.validated_data["password"],
        )
        if user is None:
            # One message for unknown address, wrong password, inactive and locked accounts.
            return Response(
                {"detail": "Invalid email or password."}, status=status.HTTP_401_UNAUTHORIZED
            )
        login(request._request, user)
        # Django rotates the CSRF token at sign-in, so the client needs the new one.
        return Response({**MeSerializer(user).data, "csrfToken": get_token(request._request)})


@extend_schema(request=None, responses={204: None})
class LogoutView(APIView):
    def post(self, request):
        logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(responses=MeSerializer)
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(MeSerializer(request.user).data)


class PasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField()
    new_password = serializers.CharField()


@extend_schema(request=PasswordSerializer, responses={204: None})
class PasswordChangeView(APIView):
    def post(self, request):
        data = PasswordSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(data.validated_data["current_password"]):
            raise serializers.ValidationError(
                {"current_password": "The current password is wrong."}
            )
        validate_password(data.validated_data["new_password"], user)
        user.set_password(data.validated_data["new_password"])
        user.save()
        # Keep this session, end every other one.
        from django.contrib.auth import update_session_auth_hash

        update_session_auth_hash(request._request, user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserViewSet(ScopedModelViewSet):
    object_type = "accounts.user"
    domain_lookup = None
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_queryset(self):
        return super().get_queryset().order_by("email")


class UserGroupViewSet(ScopedModelViewSet):
    object_type = "accounts.usergroup"
    domain_lookup = None
    queryset = UserGroup.objects.prefetch_related("members")
    serializer_class = UserGroupSerializer


class DirectoryView(APIView):
    """Names and addresses of active users, for owner and assignee pickers.

    Open to anyone who holds a role (or is an administrator), so a person with no access yet
    cannot enumerate colleagues.
    """

    @extend_schema(
        responses=inline_serializer(
            "DirectoryEntry",
            {
                "id": serializers.UUIDField(),
                "email": serializers.EmailField(),
                "name": serializers.CharField(),
            },
            many=True,
        )
    )
    def get(self, request):
        from django.db.models import Q

        from apps.access.models import RoleAssignment

        user = request.user
        allowed = (
            user.is_superuser
            or RoleAssignment.objects.filter(Q(user=user) | Q(group__members=user)).exists()
        )
        if not allowed:
            return Response([], status=status.HTTP_403_FORBIDDEN)
        rows = User.objects.filter(is_active=True).order_by("email")
        return Response([{"id": u.pk, "email": u.email, "name": u.display_name} for u in rows])
