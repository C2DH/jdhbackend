from django.db import models


class Dataset(models.Model):
    id = models.AutoField(primary_key=True, db_column="id")
    url = models.URLField(max_length=254, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.url
