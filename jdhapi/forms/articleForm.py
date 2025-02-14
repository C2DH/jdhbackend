# import marko
from django import forms
from jdhapi.models import Article, Abstract
from jdhapi.utils.gitup_repository import is_socialmediacover_exist
import logging
import datetime
from django.http import Http404

# from django.conf import settings


logger = logging.getLogger(__name__)


class ArticleForm(forms.ModelForm):

    class Meta:
        model = Article
        fields = "__all__"

    def clean(self):
        # Get the article data
        doi = self.cleaned_data["doi"]
        status = self.cleaned_data["status"]
        repository_url = self.cleaned_data["repository_url"]
        notebook_url = self.cleaned_data["notebook_url"]
        notebook_path = self.cleaned_data["notebook_path"]

        if self.has_changed():
            logger.info(
                "The following fields changed: %s" % ", ".join(self.changed_data)
            )
            if "status" in self.changed_data:
                # IF PUBLISHED
                if status == Article.Status.PUBLISHED:
                    if not doi:
                        raise forms.ValidationError(
                            {"doi": "Doi is mandatory if published"}
                        )
                    if not is_socialmediacover_exist(repository_url):
                        raise forms.ValidationError(
                            {
                                "repository_url": (
                                    "No social media cover uploaded in the GitHub repository"
                                )
                            }
                        )
                    else:
                        self.cleaned_data["publication_date"] = datetime.datetime.now()
                        logger.info(f"primary key {self.instance.pk}")
                        try:
                            abstract = Abstract.objects.get(id=self.instance.pk)
                            abstract.status = Abstract.Status.PUBLISHED
                            # This prevents triggering any undesired signals
                            abstract.save(update_fields=["status"])
                        except Article.DoesNotExist:
                            # do something in case not
                            logger.error("No abstract found")
                            # Abstract.objects.filter(pid=self.instance.pk).update(status=Abstract.Status.PUBLISHED)
                            raise Http404(
                                "Abstract linked to the article does not exist"
                            )
            if status == Article.Status.PEER_REVIEW:
                if not repository_url:
                    raise forms.ValidationError(
                        {"repository_url": "Repository_url is mandatory if published"}
                    )
                if not notebook_url:
                    raise forms.ValidationError(
                        {"notebook_url": "Notebook_url is mandatory if published"}
                    )
                if not notebook_path:
                    raise forms.ValidationError(
                        {"notebook_path": "Notebook_url is mandatory if published"}
                    )
        else:
            logger.info("no changed fields")
