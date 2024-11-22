from django.contrib.syndication.views import Feed

from .models import Article


class LatestArticleFeed(Feed):
    title = "Journal of Digital History"
    link = "https://journalofdigitalhistory.org"
    description = "International, academic, peer-reviewed and diamond open-access Journal of digital History"

    def items(self):
        # latest 50 PUBLISHED articles
        return Article.objects.filter(status=Article.Status.PUBLISHED).order_by(
            "-publication_date"
        )[:50]

    def item_title(self, item):
        title_parts = item.data.get("title", [])
        # if is string, return it
        if isinstance(title_parts, str):
            return title_parts
        # if is array, join all elements
        elif isinstance(title_parts, list):
            return " ".join(title_parts)
        return ""

    def item_description(self, item):
        abstract_parts = item.data.get("abstract", [])
        # if is string, return it
        if isinstance(abstract_parts, str):
            return abstract_parts
        # if is array, join all elements
        elif isinstance(abstract_parts, list):
            return " ".join(abstract_parts)
        return ""

    # item_link is only needed if NewsItem has no get_absolute_url method.
    def item_link(self, item):
        return f"{self.link}/en/article/{item.abstract.pid}"
