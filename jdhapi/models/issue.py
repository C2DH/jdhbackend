from django.db import models

from django.utils import timezone


class Issue(models.Model):
    """
    Represents an issue in the journal of digital history.

    Attributes:
        id (AutoField): Primary key for the issue.
        pid (CharField): Unique identifier for the issue, default is "jdh001".
        name (CharField): Name of the issue.
        description (TextField): Description of the issue, can be null or blank.
        creation_date (DateTimeField): Date and time when the issue was created, defaults to the current time.
        publication_date (DateTimeField): Date and time when the issue was published, can be null or blank.
        cover_date (DateTimeField): Date and time for the cover date of the issue, can be null or blank.
        data (JSONField): JSON formatted data contents, defaults to an empty dictionary.
        is_open_ended (BooleanField): Indicates if the issue is open-ended, defaults to True.
        volume (PositiveSmallIntegerField): Volume number of the issue, can be null.
        issue (PositiveSmallIntegerField): Issue number within the volume, can be null.
        status (CharField): Status of the issue, choices are 'DRAFT' or 'PUBLISHED', defaults to 'DRAFT'.

    Methods:
        __str__(): Returns the unique identifier (pid) of the issue as its string representation.
    """

    class Status(models.TextChoices):
        DRAFT = (
            "DRAFT",
            "Draft",
        )
        PUBLISHED = "PUBLISHED", "Published"

    id = models.AutoField(primary_key=True, db_column="id")
    pid = models.CharField(max_length=10, unique=True, default="jdh001")
    name = models.CharField(max_length=250)
    description = models.TextField(null=True, blank=True)
    creation_date = models.DateTimeField(default=timezone.now)
    publication_date = models.DateTimeField(blank=True, null=True)
    cover_date = models.DateTimeField(blank=True, null=True)
    data = models.JSONField(
        verbose_name="data contents", help_text="JSON format", default=dict, blank=True
    )
    is_open_ended = models.BooleanField(default=True)
    # YEAR OF PUBLICATION
    # 2021 - volume 1
    # 2022 -  volume 2
    volume = models.PositiveSmallIntegerField(null=True)
    # ISSUE
    # first issue - issue 1
    issue = models.PositiveSmallIntegerField(null=True)
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    def __str__(self):
        return self.pid
