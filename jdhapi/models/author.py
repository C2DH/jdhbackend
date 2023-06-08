from django.db import models
from django.conf import settings
from django.utils import timezone
import shortuuid


class Author(models.Model):
    id = models.AutoField(primary_key=True, db_column="id")
    email = models.EmailField(max_length=254, null=True, blank=True)
    lastname = models.CharField(max_length=50)
    firstname = models.CharField(max_length=50)
    orcid = models.CharField(max_length=50, null=True, blank=True)
    affiliation = models.CharField(max_length=250)
    # a flag for the main author of the publication
    main_author = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['lastname']

    def __str__(self):
        return self.lastname

