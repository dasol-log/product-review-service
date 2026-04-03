from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.crawling.models import CrawlTarget
from apps.crawling.services.target_selector import get_due_targets


class TargetSelectorTest(TestCase):
    def setUp(self):
        now = timezone.now()

        self.t1 = CrawlTarget.objects.create(
            site="danawa",
            target_type="search",
            keyword="수분크림",
            title="다나와 1",
            url="https://example.com/d1",
            is_active=True,
            crawl_interval_minutes=60,
            priority=3,
            last_crawled_at=None,   # 아직 안 돌림
        )

        self.t2 = CrawlTarget.objects.create(
            site="hwahae",
            target_type="search",
            keyword="수분크림",
            title="화해 1",
            url="https://example.com/h1",
            is_active=True,
            crawl_interval_minutes=60,
            priority=2,
            last_crawled_at=now - timedelta(hours=2),   # due
        )

        self.t3 = CrawlTarget.objects.create(
            site="glowpick",
            target_type="search",
            keyword="수분크림",
            title="글로우픽 1",
            url="https://example.com/g1",
            is_active=True,
            crawl_interval_minutes=60,
            priority=1,
            last_crawled_at=now - timedelta(minutes=10),   # 아직 due 아님
        )

    def test_never_crawled_target_selected_first(self):
        targets = list(get_due_targets(limit=1))
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0].id, self.t1.id)

    def test_due_targets_only(self):
        targets = list(get_due_targets(limit=3))
        target_ids = [t.id for t in targets]

        self.assertIn(self.t1.id, target_ids)
        self.assertIn(self.t2.id, target_ids)
        self.assertNotIn(self.t3.id, target_ids)

    def test_limit_works(self):
        targets = list(get_due_targets(limit=1))
        self.assertEqual(len(targets), 1)