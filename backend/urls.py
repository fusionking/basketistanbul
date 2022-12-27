from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from rest_framework import routers
from rest_framework_simplejwt.views import (TokenObtainPairView,
                                            TokenRefreshView)

from preferences.views import PreferenceViewSet
from reservations.views import (ReservationJobViewSet, ReservationViewSet,
                                ShowSlotsView)
from selections.views import (SelectionViewSet, SlotViewSet,
                              SportSelectionViewSet)
from users.views import RegisterView, TestTokenView

router = routers.DefaultRouter(trailing_slash=False)

router.register(r"selections", SelectionViewSet)
router.register(r"slots", SlotViewSet)
router.register(r"sport-selections", SportSelectionViewSet)
router.register(r"preferences", PreferenceViewSet)
router.register(r"reservations", ReservationViewSet)
router.register(r"reservation-jobs", ReservationJobViewSet)


urlpatterns = [
    path("", include(router.urls)),
    path("admin/", admin.site.urls),
    # Auth
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # Slots
    path("show-slots/", ShowSlotsView.as_view(), name="show-slots"),
    # Register
    path("register/", RegisterView.as_view(), name="register"),
    # test
    path("test", TestTokenView.as_view(), name="test-token"),
    re_path(".*", TemplateView.as_view(template_name="index.html")),
]
