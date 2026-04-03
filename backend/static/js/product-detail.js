document.addEventListener("DOMContentLoaded", function () {
    const productDetailBox = document.getElementById("productDetailBox");

    const productId = window.PRODUCT_ID;

    const editBtn = document.getElementById("editBtn");
    const deleteBtn = document.getElementById("deleteProductBtn");

    const reviewForm = document.getElementById("reviewCreateForm");
    const contentInput = document.getElementById("content");
    const ratingInput = document.getElementById("rating");
    const imageInput = document.getElementById("images");
    const previewBox = document.getElementById("previewBox");
    const reviewList = document.getElementById("reviewList");

    const api = window.api || axios;

    function getAuthHeaders(extraHeaders = {}) {
        const token =
            localStorage.getItem("access") ||
            localStorage.getItem("access_token") ||
            localStorage.getItem("token");

        const headers = { ...extraHeaders };

        if (token) {
            headers.Authorization = `Bearer ${token}`;
        }

        return headers;
    }

    async function loadProductDetail() {
        try {
            const response = await api.get(`/products/api/${productId}/`);
            const product = response.data;

            productDetailBox.innerHTML = `
                <img src="${product.image_url || ""}" alt="${product.name}" class="thumb">
                <h1>${product.name}</h1>
                <p>${product.description || ""}</p>
                <p><strong>${Number(product.price).toLocaleString()}원</strong></p>
                <p class="muted">등록일: ${product.created_at || "-"}</p>
            `;
        } catch (error) {
            productDetailBox.innerHTML = `<p>상품 상세 정보를 불러오지 못했습니다.</p>`;
        }
    }

    async function loadReviews() {
        try {
            const response = await api.get(`/reviews/?product=${productId}`);
            const data = response.data;
            const reviews = data.results || data;

            reviewList.innerHTML = "";

            if (!reviews || reviews.length === 0) {
                reviewList.innerHTML = "<p>아직 등록된 리뷰가 없습니다.</p>";
                return;
            }

            // [수정] 안내 문구를 "비동기 처리" 기준으로 변경
            const guideBox = document.createElement("div");
            guideBox.innerHTML = `
                <p>
                    비슷한 후기를 비동기로 찾아 보여줍니다.
                </p>
            `;
            reviewList.appendChild(guideBox);

            reviews.forEach((review) => {
                const card = document.createElement("div");

                card.innerHTML = `
                    <p>${review.content}</p>

                    <!-- [수정] 버튼 스타일 제거 (UI 분리) -->
                    <button class="ai-analyze-btn" data-review-id="${review.id}">
                        비슷한 후기 보기
                    </button>

                    <!-- [수정] 결과 영역 스타일 최소화 -->
                    <div id="ai-result-${review.id}" style="display:none;"></div>
                `;

                reviewList.appendChild(card);
            });

            bindAnalyzeButtons();

        } catch (error) {
            reviewList.innerHTML = "<p>리뷰 목록을 불러오지 못했습니다.</p>";
        }
    }

    // =========================================================
    // [추가] Celery 상태 polling 함수
    // 기존 코드에는 없음
    // =========================================================
    async function pollTaskStatus(taskId, reviewId, button, resultBox) {
        const intervalId = setInterval(async () => {
            try {
                // [추가] 상태 조회 API 호출
                const response = await api.get(`/ai/tasks/${taskId}/status/`);
                const data = response.data;

                // [추가] 작업 완료 시 결과 렌더링
                if (data.status === "SUCCESS") {
                    clearInterval(intervalId);

                    const result = data.result || {};

                    resultBox.innerHTML = `
                        <p>결과 개수: ${result.similar_reviews?.length || 0}</p>
                    `;

                    button.disabled = false;
                    button.textContent = "비슷한 후기 보기";
                    return;
                }

                // [추가] 진행 중 상태 표시
                resultBox.innerHTML = `<p>분석 중... (${data.status})</p>`;

            } catch (error) {
                clearInterval(intervalId);
            }
        }, 1500);
    }

    // =========================================================
    // [핵심 수정] 버튼 클릭 로직 변경
    // 기존: GET → 즉시 결과 반환
    // 변경: POST → 작업 등록 → polling
    // =========================================================
    function bindAnalyzeButtons() {
        const buttons = document.querySelectorAll(".ai-analyze-btn");

        buttons.forEach((button) => {
            button.addEventListener("click", async () => {
                const reviewId = button.dataset.reviewId;
                const resultBox = document.getElementById(`ai-result-${reviewId}`);

                button.disabled = true;

                // [수정] 문구 변경 (즉시 분석 → 작업 등록)
                button.textContent = "작업 등록 중...";

                resultBox.style.display = "block";
                resultBox.innerHTML = "<p>작업 등록 중...</p>";

                try {
                    // [핵심 수정]
                    // 기존: GET /ai/reviews/{id}/analyze/
                    // 변경: POST → Celery 작업 등록
                    const response = await api.post(
                        `/ai/reviews/${reviewId}/analyze/`,
                        {},
                        { headers: getAuthHeaders() }
                    );

                    const taskId = response.data.task_id;

                    // [추가] task_id 기반 polling 시작
                    button.textContent = "분석 진행 중...";
                    pollTaskStatus(taskId, reviewId, button, resultBox);

                } catch (error) {
                    button.disabled = false;
                    button.textContent = "비슷한 후기 보기";
                }
            });
        });
    }

    // [유지] 이미지 미리보기
    if (imageInput && previewBox) {
        imageInput.addEventListener("change", function () {
            previewBox.innerHTML = "";

            Array.from(imageInput.files).forEach((file) => {
                if (!file.type.startsWith("image/")) return;

                const reader = new FileReader();

                reader.onload = function (e) {
                    const img = document.createElement("img");
                    img.src = e.target.result;
                    img.className = "preview-image";
                    img.style.width = "120px";
                    img.style.height = "120px";
                    img.style.objectFit = "cover";
                    img.style.marginRight = "10px";
                    img.style.marginTop = "10px";
                    img.style.borderRadius = "8px";
                    previewBox.appendChild(img);
                };

                reader.readAsDataURL(file);
            });
        });
    }

    // [유지] 리뷰 작성 기능
    if (reviewForm) {
        reviewForm.addEventListener("submit", async function (e) {
            e.preventDefault();

            const content = contentInput.value.trim();
            const rating = ratingInput.value.trim();

            if (!content || !rating) {
                alert("리뷰 내용과 평점을 입력해주세요.");
                return;
            }

            try {
                const formData = new FormData();
                formData.append("product", productId);
                formData.append("content", content);
                formData.append("rating", rating);

                if (imageInput && imageInput.files.length > 0) {
                    for (let i = 0; i < imageInput.files.length; i++) {
                        formData.append("uploaded_images", imageInput.files[i]);
                    }
                }

                const response = await api.post("/reviews/", formData, {
                    headers: getAuthHeaders({
                        "Content-Type": "multipart/form-data",
                    }),
                });

                console.log("리뷰 등록 성공:", response.data);

                alert("리뷰가 등록되었습니다.");

                reviewForm.reset();
                previewBox.innerHTML = "";

                await loadReviews();
            } catch (error) {
                console.error("리뷰 등록 실패:", error.response?.data || error);

                if (error.response?.status === 401) {
                    alert("리뷰 작성은 로그인 후 가능합니다.");
                    return;
                }

                alert("리뷰 등록 실패: " + JSON.stringify(error.response?.data || {}));
            }
        });
    }

    // [유지] 상품 수정 이동
    if (editBtn) {
        editBtn.addEventListener("click", function () {
            window.location.href = `/products/${productId}/update/`;
        });
    }

    // [유지] 상품 삭제
    if (deleteBtn) {
        deleteBtn.addEventListener("click", async function () {
            const confirmDelete = confirm("정말 이 상품을 삭제하시겠습니까?");
            if (!confirmDelete) return;

            try {
                await api.delete(`/products/api/${productId}/`, {
                    headers: getAuthHeaders(),
                });

                alert("상품이 삭제되었습니다.");
                window.location.href = "/products/";
            } catch (error) {
                console.error("상품 삭제 실패:", error.response?.data || error);

                if (error.response?.status === 401) {
                    alert("상품 삭제는 로그인 후 가능합니다.");
                    return;
                }

                alert("상품 삭제에 실패했습니다.");
            }
        });
    }

    // [유지] 페이지 시작 시 실행
    loadProductDetail();
    loadReviews();
});