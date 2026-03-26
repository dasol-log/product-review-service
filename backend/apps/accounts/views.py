from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from rest_framework import generics, permissions, status
# API 응답을 반환하기 위한 객체 (JSON 형태로 반환됨)
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from .models import User
# User 데이터를 JSON으로 변환해주는 Serializer
from .serializers import UserSerializer, SignupSerializer


class UserViewSet(ViewSet):
    """
    사용자 조회용 ViewSet
    """

    permission_classes = [permissions.AllowAny]

    def list(self, request):
        """
        전체 사용자 조회 API

        흐름:
        1. DB에서 모든 User 조회
        2. Serializer로 JSON 변환
        3. Response로 반환
        """
        users = User.objects.all().order_by("-id")
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)


    def retrieve(self, request, pk=None):
        """
        특정 사용자 상세 조회 API

        흐름:
        4. pk(id)를 기준으로 User 조회
        5. 없으면 404 에러 발생
        6. Serializer로 JSON 변환
        7. Response 반환
        """
        user = get_object_or_404(User, pk=pk)
        serializer = UserSerializer(user)
        return Response(serializer.data)
    

class SignupAPIView(generics.CreateAPIView):
    """
    회원가입 API
    POST /accounts/api/signup/
    """

    serializer_class = SignupSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "created_at": user.created_at,
            },
            status=status.HTTP_201_CREATED,
        )


class MeAPIView(generics.RetrieveAPIView):
    """
    현재 로그인한 사용자 정보 조회 API
    GET /accounts/api/me/
    """

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
    

# -------------------------------------------------
# Template Views
# -------------------------------------------------
class SignupPageView(TemplateView):
    template_name = "accounts/signup.html"


class LoginPageView(TemplateView):
    template_name = "accounts/login.html"


class MyPageView(TemplateView):
    template_name = "accounts/mypage.html"