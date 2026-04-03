import hashlib

from django.db import transaction
from django.utils import timezone

from apps.crawling.services.repository import upsert_raw_data


# [4단계 수정]
# 기존에는 unique_key에 URL 전체를 그대로 넣어서
# 다나와처럼 긴 URL에서 varchar(255) 초과 문제가 발생했습니다.
# 그래서 이제는 원문 문자열을 sha256 해시로 변환해서
# 항상 고정 길이 unique_key를 저장하도록 수정합니다.


def make_hash(value: str) -> str:
    """
    문자열을 SHA256 해시값(64자리 고정 길이)으로 변환합니다.
    """
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_page_info_unique_key(target) -> str:
    raw = f"{target.site}:page_info:{target.url}"
    return make_hash(raw)


def build_candidate_unique_key(target, item_url: str) -> str:
    raw = f"{target.site}:candidate_link:{item_url}"
    return make_hash(raw)


def build_page_info_defaults(target, result: dict) -> dict:
    """
    page_info 레코드 저장용 defaults 조립
    """
    page_info = result["page_info"]
    html = result["html"]

    return {
        "target": target,
        "source_url": target.url,
        "page_title": page_info["title"][:500],   # 방어적 슬라이싱
        "item_title": "",
        "item_url": "",
        "raw_text": page_info["text_preview"],
        "raw_html": html[:5000],
        "record_type": "page_info",
        "extra_data": {
            "a_count": page_info["a_count"],
            "contains_review_word": page_info["contains_review_word"],
            "contains_keyword": page_info["contains_keyword"],
        },
    }


def build_candidate_defaults(target, page_title: str, item: dict) -> dict:
    """
    candidate_link 레코드 저장용 defaults 조립
    """
    return {
        "target": target,
        "source_url": target.url,
        "page_title": page_title[:500],      # 방어적 슬라이싱
        "item_title": item["title"][:500],   # 방어적 슬라이싱
        "item_url": item["url"],
        "raw_text": "",
        "raw_html": "",
        "record_type": "candidate_link",
        "extra_data": {},
    }


@transaction.atomic
def save_search_result(target, result: dict) -> dict:
    """
    검색 결과를 DB에 저장하되,
    - page_info는 unique_key로 1건 유지
    - candidate_link는 item_url 기준으로 중복 저장 방지
    - 새 데이터는 create
    - 기존 데이터는 update
    """
    created_count = 0
    updated_count = 0

    page_info = result["page_info"]
    candidate_links = result["candidate_links"]

    # 1. 페이지 정보 upsert
    page_info_key = build_page_info_unique_key(target)
    _, created = upsert_raw_data(
        unique_key=page_info_key,
        defaults={
            **build_page_info_defaults(target, result),
            "unique_key": page_info_key,
        }
    )
    if created:
        created_count += 1
    else:
        updated_count += 1

    # 2. 후보 링크 upsert
    for item in candidate_links:
        candidate_key = build_candidate_unique_key(target, item["url"])

        # 필요하면 한 번만 디버깅
        print("candidate title len =", len(item["title"]))
        print("candidate url len =", len(item["url"]))
        print("candidate unique_key len =", len(candidate_key))
        print("page title len =", len(page_info["title"]))

        _, created = upsert_raw_data(
            unique_key=candidate_key,
            defaults={
                **build_candidate_defaults(target, page_info["title"], item),
                "unique_key": candidate_key,
            }
        )

        if created:
            created_count += 1
        else:
            updated_count += 1

    # 3. 마지막 크롤링 시간 갱신
    target.last_crawled_at = timezone.now()
    target.save(update_fields=["last_crawled_at"])

    return {
        "page_title": page_info["title"],
        "candidate_count": len(candidate_links),
        "created_count": created_count,
        "updated_count": updated_count,
    }