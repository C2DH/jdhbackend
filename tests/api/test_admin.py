from django.test import TestCase
from django.contrib.admin.sites import site
from jdhapi.models import Article


class ArticleAdminTest(TestCase):
    def test_list_display_headers(self):
        article_admin = site._registry[Article]

        expected_headers = [
            "abstract_pid",
            "issue_name",
            "issue",
            "abstract_title",
            "status",
            "publication_date",
            "clickable_dataverse_url",
        ]

        for header in expected_headers:
            self.assertIn(header, article_admin.list_display)
