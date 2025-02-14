import os
from django.contrib import admin
from django.utils.safestring import mark_safe

from jdhapi.filter.issuenamepidfilter import IssueNamePIDFilter

from .forms import articleForm
from .models import Author, Abstract, Dataset, Article, Issue, Tag, Role, CallOfPaper
from .filter.languagetagfilter import LanguageTagFilter
from .filter.dataverseurlfilter import EmptyDataverseURLFilter
from .tasks import (
    save_article_fingerprint,
    save_article_specific_content,
    save_citation,
    save_libraries,
    save_references,
)
from import_export.admin import ExportActionMixin
from .forms import articleForm
from django.utils.html import format_html


def save_notebook_fingerprint(modeladmin, request, queryset):
    for article in queryset:
        save_article_fingerprint.delay(article_id=article.pk)


save_notebook_fingerprint.short_description = "1: Generate fingerprint"


def save_notebook_specific_cell(modeladmin, request, queryset):
    for article in queryset:
        save_article_specific_content.delay(article_id=article.pk)


save_notebook_specific_cell.short_description = "2: Generate preload information"


def save_article_citation(modeladmin, request, queryset):
    for article in queryset:
        save_citation.delay(article_id=article.pk)


save_article_citation.short_description = "3: Generate citation"


def save_article_package(modeladmin, request, queryset):
    for article in queryset:
        save_libraries.delay(article_id=article.pk)


save_article_package.short_description = "4: Generate tags TOOL/NARRATIVE"


def save_article_references(modeladmin, request, queryset):
    for article in queryset:
        save_references.delay(article_id=article.pk)


save_article_references.short_description = "5: Generate pdf"


@admin.register(Abstract)
class AbstractAdmin(ExportActionMixin, admin.ModelAdmin):
    search_fields = ("title", "pid")
    list_display = [
        "pid",
        "title",
        "callpaper",
        "contact_email",
        "submitted_date",
        "status",
    ]
    list_filter = ("status", "callpaper")
    fieldsets = (
        (
            "Information related to the abstract",
            {
                "fields": (
                    "pid",
                    "title",
                    "callpaper",
                    "status",
                    "abstract",
                    "submitted_date",
                    "validation_date",
                ),
            },
        ),
        (
            "Information related to the contact point",
            {
                "fields": (
                    ("contact_firstname", "contact_lastname"),
                    "contact_email",
                    "contact_affiliation",
                    "contact_orcid",
                )
            },
        ),
        (
            "Information related to the authors - datasets and others",
            {"fields": ("authors", "datasets", "consented", "comment")},
        ),
    )


@admin.register(CallOfPaper)
class CallOfPaperAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ["title", "deadline_abstract", "deadline_article"]


@admin.register(Author)
class AuthorAdmin(ExportActionMixin, admin.ModelAdmin):
    search_fields = ("lastname", "firstname", "affiliation", "orcid", "email")
    list_display = [
        "lastname",
        "firstname",
        "affiliation",
        "city",
        "country",
        "clickable_orcid",
        "email",
    ]

    def clickable_orcid(self, obj):
        if obj.orcid:
            return format_html(
                '<a href="{}" target="_blank">{}</a>', obj.orcid, obj.orcid
            )
        return ""

    clickable_orcid.short_description = "Orcid URL"


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "pid",
        "volume",
        "issue",
        "status",
        "publication_date",
        "is_open_ended",
    ]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["name", "category"]
    list_filter = (
        "category",
        LanguageTagFilter,
    )


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    form = articleForm.ArticleForm
    exclude = ["notebook_commit_hash"]
    search_fields = ("abstract__title", "abstract__pid")
    list_display = [
        "abstract_pid",
        "issue_name",
        "issue",
        "abstract_title",
        "status",
        "publication_date",
        "clickable_dataverse_url",
    ]
    list_filter = (
        IssueNamePIDFilter,
        "status",
        "copyright_type",
        EmptyDataverseURLFilter,
    )
    actions = [
        save_notebook_fingerprint,
        save_notebook_specific_cell,
        save_article_citation,
        save_article_package,
        save_article_references,
    ]
    fieldsets = (
        (
            "Information related to the article",
            {
                # Section Description
                # "description" : "Enter the vehicle information",
                # Group Make and Model
                "fields": (
                    "abstract",
                    "status",
                    "doi",
                    "publication_date",
                    "issue",
                    "copyright_type",
                ),
            },
        ),
        (
            "Information related to the GitHub repository",
            {
                # Section Description
                # "description" : "Enter the vehicle information",
                # Group Make and Model
                "fields": (
                    ("repository_type", "repository_url"),
                    "notebook_url",
                    "notebook_path",
                    "binder_url",
                    "notebook_ipython_url",
                    "dataverse_url",
                )
            },
        ),
        (
            "Information related to the publication: citation - preaload - fingerprint - tags",
            {
                # Section Description
                # "description" : "Enter any additional information",
                # Enable a Collapsible Section
                "classes": ("collapse",),
                "fields": ("citation", "fingerprint", "data", "tags"),
            },
        ),
    )

    def clickable_dataverse_url(self, obj):
        if obj.dataverse_url:
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                obj.dataverse_url,
                obj.dataverse_url,
            )
        return ""

    clickable_dataverse_url.short_description = "Dataverse URL"

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is None:
            # Limit abstract choices when creating new article instance
            form.base_fields["abstract"].queryset = Abstract.objects.filter(
                article__isnull=True
            ).order_by("title")
        return form

    def issue_name(self, obj):
        return obj.issue.name

    issue_name.short_description = "Issue name"

    def abstract_pid(self, obj):
        return obj.abstract.pid

    abstract_pid.short_description = "Pid"

    def abstract_title(self, obj):
        return obj.abstract.title

    abstract_title.short_description = "Title"


# Register your models here.
admin.site.register(Dataset)
admin.site.register(Role)
admin.site.site_url = "/dashboard"
admin.site.site_header = mark_safe(
    '<b style="color:white">JDH admin</b>'
    f'({os.environ.get("GIT_BRANCH")}/{os.environ.get("GIT_REVISION")})'
)
