import requests

from django.core.exceptions import ValidationError
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from jdhapi.models import Article
from jdhapi.utils.articleUtils import convert_string_to_base64


@receiver(post_save, sender=Article)
def send_email_for_peer_review_article(sender, instance, created, **kwargs):
    if (
        not created
        and instance.tracker.has_changed("status")
        and instance.status == Article.Status.PEER_REVIEW
    ):
        instance.send_email_if_peer_review()


@receiver(pre_save, sender=Article)
def validate_urls_for_article_submission(sender, instance, **kwargs):
    def check_github_url(url):
        if url:
            response = requests.get(url)
            if response.status_code == 200:
                return False
        return True

    def check_notebook_url(notebook_url, repository_url):
        substring_to_remove = "https://github.com/jdh-observer/"
        prefix_to_add = "%2Fproxy-githubusercontent%2Fjdh-observer%2F"
        suffix_to_add = f"%2Fmain%2F{instance.notebook_path}"

        converted_string = (
            repository_url.replace(substring_to_remove, prefix_to_add) + suffix_to_add
        )

        if notebook_url == convert_string_to_base64(converted_string):
            return False
        else:
            return True

    if instance.notebook_url and check_github_url(instance.repository_url):
        raise ValidationError("Repository url is not correct")

    if instance.notebook_url and check_notebook_url(
        instance.notebook_url, instance.repository_url
    ):

        raise ValidationError("Notebook url is not correct")
