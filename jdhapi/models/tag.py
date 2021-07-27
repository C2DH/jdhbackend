from django.conf import settings
from django.db import models


class Tag(models.Model):
    KEYWORD = 'keyword'  # i.e, no special category at all
    TOOL = 'tool'
    CATEGORY_CHOICES = (
        (KEYWORD, 'keyword'),
        (TOOL, 'tool'),
    )
    data = models.JSONField(verbose_name=u'data contents', help_text='JSON format', default=dict, blank=True)
    # e.g. 'Mr. E. Smith'
    name = models.CharField(max_length=100)
    # e.g. 'actor' or 'institution'
    category = models.CharField(
        max_length=32, choices=CATEGORY_CHOICES, default=KEYWORD)

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ('name', 'category')

    def __unicode__(self):
        return f'{self.name}({self.category})'
