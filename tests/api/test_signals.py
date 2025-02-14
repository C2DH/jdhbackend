from django.core.exceptions import ValidationError
from django.test import TestCase
from jdhapi.models import Article, Abstract, Issue
from .fixtures.fixture_signals import (
    date,
    repository_url,
    notebook_url,
    notebook_url_skim,
    false_repository_url,
    false_notebook_url,
)
from unittest.mock import patch, Mock


class TestSignal(TestCase):

    def setUp(self):
        self.abstract = Abstract.objects.create(
            title="Test Abstract",
            abstract="This is a test abstract",
            contact_orcid="0000-0000-0000-0000",
            contact_affiliation="Test Affiliation",
            contact_email="test@example.com",
            contact_lastname="Doe",
            contact_firstname="John",
        )
        self.issue = Issue.objects.create(
            name="Test Issue",
            publication_date=date,
        )

    def create_article(self, notebook_url, repository_url, notebook_path):
        return Article.objects.create(
            status=Article.Status.DRAFT,
            notebook_url=notebook_url,
            repository_url=repository_url,
            notebook_path=notebook_path,
            publication_date=date,
            abstract=self.abstract,
            issue=self.issue,
        )

    def test_validate_urls_for_article_submission(self):

        with patch("jdhapi.signals.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            article = self.create_article(
                notebook_url,
                repository_url,
                "article.ipynb",
            )
            article.save()

            self.assertEqual(article.notebook_url, notebook_url)
            self.assertEqual(article.repository_url, repository_url)

    def test_validate_urls_for_skim_article_submission(self):

        with patch("jdhapi.signals.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            article = self.create_article(
                notebook_url_skim,
                repository_url,
                "skim-article.ipynb",
            )
            article.save()

            self.assertEqual(article.notebook_url, notebook_url_skim)
            self.assertEqual(article.repository_url, repository_url)

    def test_false_repository_url_for_article_submission(self):

        with patch("jdhapi.signals.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response

            with self.assertRaises(ValidationError):
                article = self.create_article(
                    notebook_url,
                    false_repository_url,
                    "article.ipynb",
                )
                article.save()

    def test_false_notebook_url_for_article_submission(self):

        with patch("jdhapi.signals.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response

            with self.assertRaises(ValidationError):
                article = self.create_article(
                    false_notebook_url,
                    repository_url,
                    "article.ipynb",
                )
                article.save()
