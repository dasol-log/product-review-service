from rest_framework import serializers
from .models import Product


class ProductSerializer(serializers.ModelSerializer):

    image = serializers.ImageField(required=False, allow_null=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "description",
            "price",
            "image",
            "image_url",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
        ]

    
    def get_image_url(self, obj):
        request = self.context.get("request")

        if not obj.image:
            return None

        try:
            image_url = obj.image.url
        except Exception:
            # 파일 접근 중 예외가 나면 안전하게 None 반환
            return None

        # request가 있으면 절대 URL 생성
        if request:
            return request.build_absolute_uri(image_url)
        
        # request가 없으면 상대 URL 반환
        return image_url