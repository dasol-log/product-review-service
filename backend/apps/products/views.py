from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import Product
from .serializers import ProductSerializer
from .paginations import ProductPageNumberPagination


class ProductViewSet(ViewSet):
    """
    Product CRUD API

    - list     : 상품 목록 조회 (GET /products/)
    - retrieve : 상품 상세 조회 (GET /products/{id}/)
    - create   : 상품 생성 (POST /products/)
    - update   : 상품 수정 (PUT /products/{id}/)
    - destroy  : 상품 삭제 (DELETE /products/{id}/)
    """
    
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def list(self, request):
        """
        상품 목록 조회 API

        흐름:
        1. DB에서 전체 상품 조회 (최신순)
        2. 페이지네이션 적용
        3. Serializer로 JSON 변환
        4. 페이지네이션 응답 반환
        """
        queryset = Product.objects.all().order_by("-id")

        paginator = ProductPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)

        serializer = ProductSerializer(page, many=True, context={"request": request})

        return paginator.get_paginated_response(serializer.data)


    def retrieve(self, request, pk=None):
        """
        상품 상세 조회 API

        흐름:
        1. pk(id)로 상품 조회
        2. 없으면 404 에러
        3. Serializer 변환
        4. Response 반환
        """
        product = get_object_or_404(Product, pk=pk)

        serializer = ProductSerializer(product, context={"request": request})

        return Response(serializer.data, status=status.HTTP_200_OK)


    def create(self, request):
        """
        상품 생성 API

        흐름:
        1. 요청 데이터(request.data) 받기
        2. Serializer로 검증
        3. 유효하면 DB 저장
        4. 생성된 데이터 반환
        """
        serializer = ProductSerializer(data=request.data, context={"request": request})

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        # ❌ 유효성 실패 시 에러 반환
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    def update(self, request, pk=None):
        """
        상품 수정 API

        흐름:
        1. 기존 상품 조회
        2. 요청 데이터로 덮어쓰기
        3. 검증 후 저장
        4. 수정된 데이터 반환
        """
        product = get_object_or_404(Product, pk=pk)

        serializer = ProductSerializer(product, data=request.data, partial=True, context={"request": request})

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

    def partial_update(self, request, pk=None):
        product = get_object_or_404(Product, pk=pk)

        serializer = ProductSerializer(
            product,
            data=request.data,
            partial=True,
            context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    def destroy(self, request, pk=None):
        """
        상품 삭제 API

        흐름:
        1. 삭제 대상 조회
        2. DB에서 삭제
        3. 성공 메시지 반환
        """
        product = get_object_or_404(Product, pk=pk)
        product.delete()
        return Response({"message": "deleted"}, status=status.HTTP_204_NO_CONTENT)
    

class ProductListPageView(TemplateView):
    template_name = "products/product_list.html"


class ProductDetailPageView(TemplateView):
    template_name = "products/product_detail.html"


class ProductCreatePageView(TemplateView):
    template_name = "products/product_create.html"

    
class ProductUpdatePageView(TemplateView):
    template_name = "products/product_update.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pk"] = self.kwargs.get("pk")
        return context
