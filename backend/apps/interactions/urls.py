from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ReviewLikeViewSet,
    ReviewBookmarkViewSet,
    ReviewCommentViewSet,
    ReviewReportViewSet,
)


router = DefaultRouter()

router.register("likes", ReviewLikeViewSet, basename="review-like")
router.register("bookmarks", ReviewBookmarkViewSet, basename="review-bookmark")
router.register("comments", ReviewCommentViewSet, basename="review-comment")
router.register("reports", ReviewReportViewSet, basename="review-report")


urlpatterns = [
    path("", include(router.urls)),
]