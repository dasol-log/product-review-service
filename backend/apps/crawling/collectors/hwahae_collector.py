import re
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup


class HwahaeReviewCollector:
    """
    화해 상품 상세 페이지에서 리뷰 데이터를 수집합니다.
    - 리뷰 탭 클릭
    - 페이지 스크롤
    - 리뷰 작성자/피부타입/작성일 + 리뷰 본문 추출
    """

    def _build_driver(self):
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--start-maximized")
        options.add_argument("--window-size=1400,1200")
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/145.0.0.0 Safari/537.36"
        )

        driver = uc.Chrome(
            options=options,
            version_main=145,
            headless=False,   # 나중에 안정화되면 True 검토
            use_subprocess=True,
        )
        return driver

    def _is_author_line(self, text: str) -> bool:
        """
        작성자/피부타입/날짜 줄인지 판별
        예:
        dmslek 20대/수부지/여드름 2026.03.12
        nkiihu 20대/복합성 2026.03.12
        """
        age_keywords = ["10대", "20대", "30대", "40대", "50대", "60대"]
        has_age = any(k in text for k in age_keywords)
        has_date = bool(re.search(r"\d{4}\.\d{2}\.\d{2}", text))
        return has_age and has_date

    def _is_stop_line(self, text: str) -> bool:
        """
        리뷰 본문이 끝났다고 판단할 키워드들
        """
        stop_keywords = [
            "전체 성분",
            "좋아요",
            "아쉬워요",
            "목적별 성분",
            "피부 보습",
            "피부 보호",
            "수분 증발 차단",
            "피부 미백",
            "주름 개선",
            "구매 전에",
            "화해 정보를 허가없이",
            "상품이 장바구니에 담겼습니다",
            "지금 확인하시겠습니까",
            "사업자정보확인",
            "이용약관",
            "개인정보 처리방침",
            "화해 비즈니스",
            "광고/제휴문의",
            "모든 손해",
            "All Rights Reserved",
            "새로운 뷰티의 발견",
            "리뷰 확인부터 무료 체험 신청",
        ]
        return any(k in text for k in stop_keywords)

    def _clean_review_text(self, text: str) -> str:
        """
        불필요한 공백/줄바꿈 정리
        """
        text = text.replace("\n", " ")
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def collect_reviews(self, product_url: str, limit: int = 20) -> list[dict]:
        driver = None
        results = []

        try:
            driver = self._build_driver()

            driver.get("https://www.hwahae.co.kr/")
            time.sleep(3)

            driver.get(product_url)
            time.sleep(5)

            for _ in range(5):
                driver.execute_script("window.scrollBy(0, 1000);")
                time.sleep(1.5)

            buttons = driver.find_elements(By.XPATH, "//*[contains(text(),'리뷰')]")
            for b in buttons:
                try:
                    if "리뷰" in b.text:
                        driver.execute_script("arguments[0].click();", b)
                        time.sleep(5)
                        break
                except Exception:
                    continue

            html = driver.page_source
            soup = BeautifulSoup(html, "lxml")

            texts = []
            for tag in soup.find_all(["p", "span", "div"]):
                text = tag.get_text(" ", strip=True)
                if 2 <= len(text) <= 200:
                    texts.append(text)

            unique_texts = []
            seen = set()
            for t in texts:
                if t not in seen:
                    seen.add(t)
                    unique_texts.append(t)

            i = 0
            while i < len(unique_texts):
                line = unique_texts[i]

                if self._is_author_line(line):
                    author_info = line
                    review_parts = []
                    j = i + 1

                    while j < len(unique_texts):
                        next_line = unique_texts[j]

                        # 다음 작성자 나오면 현재 리뷰 종료
                        if self._is_author_line(next_line):
                            break

                        # 성분/푸터/장바구니 등 나오면 종료
                        if self._is_stop_line(next_line):
                            break

                        # 너무 짧은 라인은 제외
                        if len(next_line) >= 8:
                            review_parts.append(next_line)

                        # 리뷰는 보통 1~3문장 정도만 가져오도록 제한
                        if len(review_parts) >= 3:
                            break

                        j += 1

                    review_text = self._clean_review_text(" ".join(review_parts))

                    # 최종 필터
                    if review_text and 10 <= len(review_text) <= 300:
                        results.append({
                            "source": "hwahae",
                            "url": product_url,
                            "author_info": author_info,
                            "review": review_text,
                        })

                    i = j
                else:
                    i += 1

            return results[:limit]

        except Exception as e:
            print(f"hwahae 리뷰 수집 실패: {e}")
            return []

        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass