from django.urls import path

# interactions 앱에서 사용하는 APIView import
from .views import (
    ReviewLikeToggleAPIView,        # 리뷰 좋아요 토글 API
    ReviewBookmarkToggleAPIView,    # 리뷰 북마크 토글 API
    ReviewCommentCreateAPIView,     # 리뷰 댓글 생성 API
    ReviewCommentListAPIView,       # 리뷰 댓글 목록 조회 API
    ReviewCommentDetailAPIView,     # 리뷰 댓글 수정 / 삭제 API
    ReviewReportCreateAPIView,      # 리뷰 신고 생성 API
    ReviewReportListAPIView,        # 리뷰 신고 목록 조회 API
)

urlpatterns = [
    path(
        "like/<int:review_id>/",
        ReviewLikeToggleAPIView.as_view(),
        name="review-like-toggle"
    ),

    path(
        "bookmark/<int:review_id>/",
        ReviewBookmarkToggleAPIView.as_view(),
        name="review-bookmark-toggle"
    ),

    path(
        "comment/<int:review_id>/",
        ReviewCommentCreateAPIView.as_view(),
        name="review-comment-create"
    ),

    path(
        "comments/<int:review_id>/",
        ReviewCommentListAPIView.as_view(),
        name="review-comment-list"
    ),

    path(
        "comment/detail/<int:comment_id>/",
        ReviewCommentDetailAPIView.as_view(),
        name="review-comment-detail"
    ),

    path(
        "report/<int:review_id>/",
        ReviewReportCreateAPIView.as_view(),
        name="review-report-create"
    ),

    path(
        "reports/<int:review_id>/",
        ReviewReportListAPIView.as_view(),
        name="review-report-list"
    ),
]