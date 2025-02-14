import logging
import marko

from django.conf import settings

from django.core.mail import EmailMessage
from django.db import models
from django.template.loader import render_to_string

from lxml import html
from model_utils import FieldTracker
from weasyprint import HTML

logger = logging.getLogger(__name__)


class Article(models.Model):
    """
    Represents an article in the Journal of Digital History.

    Attributes:
        abstract (OneToOneField): A one-to-one relationship with the Abstract model.
        status (CharField): The current status of the article, with choices defined in the Status inner class.
        tracker (FieldTracker): Tracks changes to the status field.
        issue (ForeignKey): A foreign key relationship to the Issue model.
        repository_url (URLField): The URL of the article's repository (e.g., GitHub).
        repository_type (CharField): The type of repository, with choices defined in the RepositoryType inner class.
        notebook_url (CharField): The URL of the article's preview.
        notebook_ipython_url (URLField): The URL of the raw GitHub ipynb file.
        notebook_commit_hash (CharField): The git commit hash of the notebook.
        notebook_path (CharField): The file name of the notebook with .ipynb extension.
        binder_url (URLField): The URL for Binder.
        doi (CharField): The DOI received from ScholarOne.
        dataverse_url (URLField): The URL for Dataverse.
        publication_date (DateTimeField): The publication date of the article.
        copyright_type (CharField): The type of copyright, with choices defined in the CopyrightType inner class.
        data (JSONField): JSON data contents of the article.
        fingerprint (JSONField): JSON fingerprint contents of the article.
        citation (JSONField): JSON citation contents of the article.
        tags (ManyToManyField): Tags associated with the article.
        authors (ManyToManyField): Authors of the article, through the Role model.

    Methods:
        get_kernel_language(): Returns the kernel language based on the 'tool' tag.
        __str__(): Returns the title of the abstract.
        send_email_if_peer_review(): Sends an email with a PDF attachment if the article is in peer review status.
    """

    class Status(models.TextChoices):
        DRAFT = (
            "DRAFT",
            "Draft",
        )
        TECHNICAL_REVIEW = (
            "TECHNICAL_REVIEW",
            "Technical review",
        )
        PEER_REVIEW = (
            "PEER_REVIEW",
            "Peer review",
        )
        DESIGN_REVIEW = (
            "DESIGN_REVIEW",
            "Design review",
        )
        PUBLISHED = "PUBLISHED", "Published"

    class CopyrightType(models.TextChoices):
        DRAFT = (
            "DRAFT",
            "Draft",
        )
        CC_BY = (
            "CC_BY",
            "CC-BY",
        )
        CC_BY_NC_ND = "CC_BY_NC_ND", "CC-BY-NC-ND"

    class RepositoryType(models.TextChoices):
        GITHUB = (
            "GITHUB",
            "Github",
        )
        GITLAB = (
            "GITLAB",
            "Gitlab",
        )

    abstract = models.OneToOneField(
        "jdhapi.Abstract",
        on_delete=models.CASCADE,
        primary_key=True,
    )
    status = models.CharField(
        max_length=25,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    tracker = FieldTracker(fields=["status"])
    issue = models.ForeignKey("jdhapi.Issue", on_delete=models.CASCADE)
    repository_url = models.URLField(
        max_length=254, null=True, blank=True, help_text="GitHub's repository URL "
    )
    repository_type = models.CharField(
        max_length=15,
        choices=RepositoryType.choices,
        default=RepositoryType.GITHUB,
    )
    # Url of the article in the front
    notebook_url = models.CharField(
        max_length=254,
        null=True,
        blank=True,
        help_text="Article's preview URL - All the caracters after the url : https://journalofdigitalhistory.org/en/notebook-viewer/",
    )
    # Json source from raw.github
    notebook_ipython_url = models.URLField(
        max_length=254, null=True, blank=True, help_text="Raw GitHub ipynb URL"
    )
    notebook_commit_hash = models.CharField(
        max_length=22, default="", help_text="store the git hash", blank=True
    )
    notebook_path = models.CharField(
        max_length=254,
        null=True,
        blank=True,
        help_text="Notebook file name with .ipynb",
    )
    binder_url = models.URLField(max_length=254, null=True, blank=True)
    doi = models.CharField(
        max_length=254,
        null=True,
        blank=True,
        help_text="Doi received from ScholarOne -  10.1515/JDH.YYYY.XXXX.RX",
    )
    dataverse_url = models.URLField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Url to find here https://data.journalofdigitalhistory.org/",
    )  # New field for Dataverse URL
    publication_date = models.DateTimeField(blank=True, null=True)
    copyright_type = models.CharField(
        max_length=15,
        choices=CopyrightType.choices,
        default=CopyrightType.DRAFT,
    )
    data = models.JSONField(
        verbose_name="data contents", help_text="JSON format", default=dict, blank=True
    )
    fingerprint = models.JSONField(
        verbose_name="fingerprint contents",
        help_text="JSON format",
        default=dict,
        blank=True,
    )
    citation = models.JSONField(
        verbose_name="citation contents",
        help_text="JSON format",
        default=dict,
        blank=True,
    )
    tags = models.ManyToManyField("jdhapi.Tag", blank=True)
    authors = models.ManyToManyField("jdhapi.Author", through="Role")

    def get_kernel_language(self):
        tool_tags = self.tags.filter(category="tool")
        if tool_tags.exists():
            first_tool_tag = tool_tags.first()
            return first_tool_tag.data.get("language", "")
        # Default language if no 'tool' tag or
        # language field present
        return ""

    def __str__(self):
        return self.abstract.title

    def send_email_if_peer_review(self):
        if self.status == self.Status.PEER_REVIEW:
            # Render the PDF template
            template = "jdhseo/peer_review.html"
            if "title" in self.data:
                articleTitle = html.fromstring(
                    marko.convert(self.data["title"][0])
                ).text_content()
                context = {"article": self, "articleTitle": articleTitle}
                html_string = render_to_string(template, context)

                # Generate the PDF
                pdf_file = HTML(string=html_string).write_pdf()
                logger.info("Pdf generated")
                filename = "peer_review_" + self.abstract.pid + ".pdf"
                # Save the PDF to a file
                # with open(filename, 'wb') as f:
                #    f.write(pdf_file)
                # logger.info("Pdf saved")
                # Create an email message with the PDF attachment
                subject = f"{articleTitle} can been sent to peer review!"
                body = "Please find attached the links useful for the peer review."
                from_email = settings.DEFAULT_FROM_EMAIL
                to_email = settings.DEFAULT_TO_EMAIL
                email = EmailMessage(subject, body, from_email, [to_email])
                email.attach(filename, pdf_file, "application/pdf")

                # Send the email
                try:
                    email.send()
                    logger.info("Email sent")
                except Exception as e:
                    print(f"Error sending email: {str(e)}")
