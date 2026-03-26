from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (ProductViewSet, ProductListPageView, ProductDetailPageView, ProductCreatePageView, ProductUpdatePageView)


router = DefaultRouter()
router.register("", ProductViewSet, basename="product")

urlpatterns = [
    # =================================================
    # Template Page URLs
    # =================================================

    # -----------------------------------
    # [추가] 상품 목록 페이지
    # 실제 최종 URL: /products/
    # -----------------------------------
    path("", ProductListPageView.as_view(), name="product-page-list"),
    path("create/", ProductCreatePageView.as_view(), name="product-page-create"),
    path("<int:pk>/update/", ProductUpdatePageView.as_view(), name="product-page-edit"),

    # -----------------------------------
    # [추가] 상품 상세 페이지
    # 실제 최종 URL: /products/1/
    # -----------------------------------
    path("<int:pk>/", ProductDetailPageView.as_view(), name="product-page-detail"),


    # =================================================
    # API URLs
    # =================================================

    # -----------------------------------
    # [추가] API는 api/ 하위로 분리
    # 실제 최종 URL:
    # /products/api/
    # /products/api/1/
    # -----------------------------------
    path("api/", include(router.urls)),
]