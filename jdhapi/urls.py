from django.urls import path, include
from jdhapi import views
from rest_framework.urlpatterns import format_suffix_patterns

urlpatterns = [
    path("api/", views.api_root),
    path("api/me", views.api_me, name="me"),
    path("api-auth/", include("rest_framework.urls")),
    path("api/authors/", views.AuthorList.as_view(), name="author-list"),
    path("api/authors/<int:pk>/", views.AuthorDetail.as_view(), name="author-detail"),
    path("api/datasets/", views.DatasetList.as_view(), name="dataset-list"),
    path(
        "api/datasets/<int:pk>/", views.DatasetDetail.as_view(), name="dataset-detail"
    ),
    path("api/abstracts/", views.AbstractList.as_view(), name="abstract-list"),
    path(
        "api/abstracts/<str:pid>/",
        views.AbstractDetail.as_view(),
        name="abstract-detail",
    ),
    path("api/articles/", views.ArticleList.as_view(), name="article-list"),
    path(
        "api/articles/<str:abstract__pid>/",
        views.ArticleDetail.as_view(),
        name="article-detail",
    ),
    path("api/issues/", views.IssueList.as_view(), name="issue-list"),
    path("api/issues/<str:pid>/", views.IssueDetail.as_view(), name="issue-detail"),
    path("api/submit-abstract/", views.SubmitAbstract),
    path("api/generate-notebook/<str:pid>", views.GenerateNotebook),
    path("api/tags/", views.TagList.as_view(), name="tag-list"),
    path("api/tags/<int:pk>/", views.TagDetail.as_view(), name="tag-detail"),
    path("api/callofpaper/", views.CallOfPaperList.as_view(), name="callofpaper-list"),
    path(
        "api/callofpaper/<str:folder_name>/",
        views.CallOfPaperDetail.as_view(),
        name="callofpaper-detail",
    ),
]
urlpatterns = format_suffix_patterns(urlpatterns)
