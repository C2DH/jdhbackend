from django.db import models
from django.utils import timezone
from .callofpaper import CallOfPaper
import shortuuid


def create_short_url():
    return shortuuid.uuid()[:12]  # es => "IRVaY2b3VI89"


class Abstract(models.Model):

    class Status(models.TextChoices):
        SUBMITTED = (
            "SUBMITTED",
            "Submitted",
        )
        ACCEPTED = (
            "ACCEPTED",
            "Accepted",
        )
        DECLINED = (
            "DECLINED",
            "Declined",
        )
        ABANDONED = (
            "ABANDONED",
            "Abandoned",
        )
        SUSPENDED = (
            "SUSPENDED",
            "Suspended",
        )
        PUBLISHED = "PUBLISHED", "Published"

    id = models.AutoField(primary_key=True, db_column="id")
    pid = models.CharField(
        max_length=255, default=create_short_url, db_index=True, unique=True
    )
    title = models.CharField(max_length=250)
    callpaper = models.ForeignKey(
        CallOfPaper, blank=True, null=True, on_delete=models.CASCADE
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.SUBMITTED,
    )
    submitted_date = models.DateTimeField(default=timezone.now)
    validation_date = models.DateTimeField(blank=True, null=True)
    abstract = models.TextField()
    contact_orcid = models.CharField(max_length=50)
    contact_affiliation = models.CharField(max_length=250)
    contact_email = models.EmailField(max_length=254)
    contact_lastname = models.CharField(max_length=50)
    contact_firstname = models.CharField(max_length=50)

    authors = models.ManyToManyField(
        "jdhapi.Author", related_name="abstracts", blank=True
    )
    datasets = models.ManyToManyField(
        "jdhapi.Dataset", related_name="abstracts", blank=True
    )
    consented = models.BooleanField(default=False)
    comment = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["submitted_date"]

    def accepted(self):
        self.validation_date = timezone.now()
        self.status = Abstract.Status.ACCEPTED
        self.save()

    def declined(self):
        self.validation_date = timezone.now()
        self.status = Abstract.Status.DECLINED
        self.save()

    def abandoned(self):
        self.validation_date = timezone.now()
        self.status = Abstract.Status.ABANDONED
        self.save()

    def suspended(self):
        self.validation_date = timezone.now()
        self.status = Abstract.Status.SUSPENDED
        self.save()

    def __str__(self):
        return self.title
