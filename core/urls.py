from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("documents", views.DocumentViewSet, basename="document")
router.register("products", views.ProductViewSet, basename="product")
router.register("conversations", views.ConversationViewSet, basename="conversation")
router.register("eval-logs", views.EvalLogViewSet, basename="evallog")

urlpatterns = [
    path("health", views.health, name="health"),
    path("api/auth/token", obtain_auth_token, name="api-token-auth"),
    path("api/", include(router.urls)),
]
