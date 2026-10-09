from rest_framework.routers import DefaultRouter

from apps.accounts.views import UserGroupViewSet, UserViewSet
from apps.customfields.views import CustomFieldDefinitionViewSet

from .views import DomainViewSet

router = DefaultRouter()
router.register("domains", DomainViewSet, basename="domain")
router.register("users", UserViewSet, basename="user")
router.register("user-groups", UserGroupViewSet, basename="usergroup")
router.register("custom-fields", CustomFieldDefinitionViewSet, basename="customfield")
urlpatterns = router.urls
