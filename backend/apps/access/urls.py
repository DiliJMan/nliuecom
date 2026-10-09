from rest_framework.routers import DefaultRouter

from .views import RoleAssignmentViewSet, RoleViewSet

router = DefaultRouter()
router.register("roles", RoleViewSet, basename="role")
router.register("role-assignments", RoleAssignmentViewSet, basename="roleassignment")
urlpatterns = router.urls
