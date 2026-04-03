from requests import RequestException

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from django.shortcuts import get_object_or_404   
# [추가] review_id로 기준 리뷰 1개를 안전하게 조회하기 위해 추가

from apps.reviews.models import Review          
# [추가] DB에서 리뷰를 조회하기 위해 추가

from .services import FastAPIClient

# [추가] AI 추론 결과 저장 모델 import
from .models import ReviewSimilarityResult


# ============================
# [추가] 유사도 점수 → 사용자용 문구 변환 함수
# ============================
def get_similarity_label(score: float) -> str:
    if score > 0.7:
        return "매우 비슷"
    if score > 0.5:
        return "비슷"
    if score > 0.3:
        return "약간 비슷"
    return "관련 있음"


class EmbeddingAPIView(APIView):
    def post(self, request):
        serializer = EmbeddingRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        texts = serializer.validated_data["texts"]

        try:
            # 현재 구조 유지: 한 문장씩 보내서 리스트로 반환
            embeddings = [FastAPIClient.get_embedding(text) for text in texts]
            return Response({"embeddings": embeddings}, status=status.HTTP_200_OK)
        except RequestException as e:
            return Response(
                {"detail": f"FastAPI 호출 실패: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class SimilarityAPIView(APIView):
    def post(self, request):
        serializer = SimilarityRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        text1 = serializer.validated_data["text1"]
        text2 = serializer.validated_data["text2"]

        try:
            result = FastAPIClient.get_similarity(text1, text2)
            return Response(result, status=status.HTTP_200_OK)
        except RequestException as e:
            return Response(
                {"detail": f"FastAPI 호출 실패: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        

class ReviewAnalyzeAPIView(APIView):
    """
    [기능]
    특정 리뷰 1개를 기준으로
    같은 상품의 다른 리뷰들과 유사도를 비교하는 API

    GET /ai/reviews/<review_id>/analyze/

    -------------------------------------------------
    [이전 코드]
    - 사용자가 text1, text2를 직접 입력해서 비교
    - 결과는 {"similarity": 점수} 정도의 단순 응답

    [현재 코드]
    - review_id만 받음
    - Django가 DB에서 기준 리뷰와 후보 리뷰들을 조회
    - FastAPI로 여러 리뷰를 반복 비교
    - 점수 기준(threshold) 이상만 남김
    - 화면에서 바로 쓸 수 있는 형태로 반환
    -------------------------------------------------
    """

    # [유지] 로그인 없이도 결과 조회 가능
    permission_classes = [AllowAny]

    # [현재 코드에서 추가]
    # 이전 코드에는 없었고,
    # 너무 낮은 유사도 결과는 화면에 안 보여주기 위한 기준값
    SIMILARITY_THRESHOLD = 0.45

    def get(self, request, review_id):
        # =========================================================
        # [흐름 1] 기준 리뷰 1개 조회
        # ---------------------------------------------------------
        # [이전 코드]
        # - 사용자가 text1, text2를 직접 body로 보냈음
        #
        # [현재 코드]
        # - review_id를 받아 DB에서 기준 리뷰를 직접 조회함
        # =========================================================
        source_review = get_object_or_404(
            Review.objects.select_related("user", "product"),
            id=review_id,
            is_public=True,
        )

        # =========================================================
        # [흐름 2] 같은 상품의 다른 리뷰들을 비교 후보로 조회
        # ---------------------------------------------------------
        # [이전 코드]
        # - 비교할 문장이 2개뿐이라 후보 조회 자체가 없었음
        #
        # [현재 코드]
        # - 같은 product의 다른 리뷰들을 DB에서 가져옴
        # - 자기 자신은 제외
        # - 최신순 정렬
        # - 최대 20개까지만 비교
        # =========================================================
        candidate_reviews = (
            Review.objects
            .select_related("user")
            .filter(
                product=source_review.product,
                is_public=True
            )
            .exclude(id=source_review.id)
            .order_by("-created_at")[:20]
        )

        # =========================================================
        # [흐름 3] 기준 리뷰 내용 검사
        # ---------------------------------------------------------
        # [이전 코드]
        # - 사용자가 text1, text2를 직접 입력했기 때문에
        #   serializer가 비어 있는 값 검증을 담당했음
        #
        # [현재 코드]
        # - serializer 대신 DB에서 가져온 content를 직접 검사
        # =========================================================
        if not source_review.content.strip():
            return Response(
                {"detail": "분석할 리뷰 내용이 없습니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # [유지] 최종 비교 결과를 담을 리스트
        results = []

        try:
            # =====================================================
            # [흐름 4] 후보 리뷰들을 하나씩 FastAPI에 보내 유사도 비교
            # -----------------------------------------------------
            # [이전 코드]
            # - text1, text2 한 번만 비교
            #
            # [현재 코드]
            # - 기준 리뷰 1개 vs 후보 리뷰 여러 개를 반복 비교
            # =====================================================
            for candidate in candidate_reviews:

                # [유지] 후보 리뷰 내용이 비어 있으면 비교하지 않음
                if not candidate.content.strip():
                    continue

                # -------------------------------------------------
                # [유지] FastAPI에 실제 유사도 계산 요청
                # - Django는 계산하지 않고 FastAPI에 위임
                # -------------------------------------------------
                similarity_result = FastAPIClient.get_similarity(
                    source_review.content,
                    candidate.content
                )

                # [현재 코드에서 분리]
                # 이전 코드에서는 결과를 바로 append 했다면,
                # 지금은 먼저 score 변수로 꺼내서 threshold 비교에 사용
                score = round(similarity_result["similarity"], 4)

                # =================================================
                # [흐름 5] threshold 기준 적용
                # -------------------------------------------------
                # [이전 코드]
                # - 점수와 상관없이 결과를 모두 담았음
                #
                # [현재 코드]
                # - 기준 점수(0.45) 이상인 결과만 포함
                # - 너무 낮은 관련 리뷰가 노출되는 것을 방지
                # =================================================
                if score >= self.SIMILARITY_THRESHOLD:
                    results.append({
                        "review_id": candidate.id,
                        "username": candidate.user.username,
                        "content": candidate.content,
                        "score": score,
                        "created_at": candidate.created_at.strftime("%Y-%m-%d %H:%M"),
                    })

        except RequestException as e:
            # [유지] FastAPI 호출 실패 시 502 반환
            return Response(
                {"detail": f"FastAPI 호출 실패: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY
            )

        # =========================================================
        # [흐름 6] 점수 높은 순으로 정렬
        # ---------------------------------------------------------
        # [이전 코드]
        # - 정렬은 있었음
        #
        # [현재 코드]
        # - threshold를 통과한 결과들만 정렬
        # =========================================================
        results.sort(key=lambda x: x["score"], reverse=True)

        # =========================================================
        # [흐름 7] 상위 3개만 최종 선택
        # ---------------------------------------------------------
        # [유지]
        # - 너무 많은 결과를 보내지 않고 화면용으로 Top 3만 반환
        # =========================================================
        top_results = results[:3]

        # =========================================================
        # [흐름 8] 프론트에서 바로 쓸 수 있는 JSON 구조로 반환
        # ---------------------------------------------------------
        # [이전 코드]
        # - {"similarity": 점수} 같은 단순 구조
        #
        # [현재 코드]
        # - 기준 리뷰 정보(source_review)
        # - 최종 유사 리뷰 목록(similar_reviews)
        # - 비교 후보 수(candidate_count)
        # - 기준 점수(similarity_threshold)
        # 를 함께 반환
        # =========================================================
        return Response(
            {
                # [유지] 기준 리뷰 정보
                "source_review": {
                    "review_id": source_review.id,
                    "username": source_review.user.username,
                    "content": source_review.content,
                },

                # [유지] threshold 적용 + 정렬 후 Top 3 결과
                "similar_reviews": top_results,

                # [현재 코드에서 추가]
                # 프론트에서 "비교할 리뷰가 몇 개 있었는지" 안내 문구에 활용 가능
                "candidate_count": candidate_reviews.count(),

                # [현재 코드에서 추가]
                # 프론트/디버깅 시 현재 기준값 확인용
                "similarity_threshold": self.SIMILARITY_THRESHOLD,
            },
            status=status.HTTP_200_OK
        )