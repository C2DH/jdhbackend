from django.http import Http404

from jdhapi.utils.copyright import CopyrightJDH
from jdhapi.utils.doi import get_doi, get_publisher_id, get_elocation_id
from jdhapi.utils.affiliation import (
    get_authors,
    get_affiliation_json,
    is_default_affiliation,
)
from jdhapi.utils.publication_date import get_order_publication
from jdhapi.models import Issue

import logging

logger = logging.getLogger(__name__)


class ArticleXml:

    def _raise_for_default_affiliations(self, article_authors):
        if is_default_affiliation(self.affiliations):
            error_message = (
                "Warning: Please fill the country and city in the affiliation"
            )
            authors = [
                f"{author.lastname} {author.firstname}" for author in article_authors
            ]
            authors_str = ", ".join(authors)

            raise Http404(
                f"Default affiliation \n{error_message}.\nAuthors: {authors_str}"
            )

    def __init__(
        self,
        article_authors,
        title,
        article_doi,
        keywords,
        publication_date,
        copyright,
        issue_pid,
        pid,
    ):

        self.publisher_id = get_publisher_id(article_doi).lower()
        self.affiliations = get_affiliation_json(article_authors, self.publisher_id)
        self._raise_for_default_affiliations(article_authors)
        self.authors = get_authors(article_authors, self.affiliations)
        self.authors_concat = CopyrightJDH.getAuthorList(self.authors)
        self.title = title
        self.doi = get_doi(article_doi).lower()
        self.keywords = keywords
        self.epub = publication_date
        self.copyright_desc = CopyrightJDH.getCopyrightDesc(copyright)
        self.copyright_url = CopyrightJDH.getCopyrightUrl(copyright)
        # To look at here http://www.wiki.degruyter.de/production/files/dg_variables_and_id.xhtml#elocation-id
        self.elocation_id = get_elocation_id(self.publisher_id)
        # seq reflect the sequence of articles within an issue.
        self.seq = get_order_publication(pid, issue_pid)

        try:
            issue = Issue.objects.get(pid=issue_pid)
            self.volume = issue.volume
            self.issue = issue.issue
            self.cover_date = issue.cover_date
            self.issue_date = issue.publication_date
        except Issue.DoesNotExist:
            raise Http404("Issue does not exist")

    @property
    def seq(self):
        return self._seq

    @property
    def issue_date(self):
        return self._issue_date

    @property
    def elocation_id(self):
        return self._elocation_id

    @property
    def issue(self):
        return self._issue

    @property
    def volume(self):
        return self._volume

    @property
    def cover_date(self):
        return self._cover_date

    @property
    def copyright_desc(self):
        return self._copyright_desc

    @property
    def copyright_url(self):
        return self._copyright_url

    @property
    def epub(self):
        return self._epub

    @property
    def keywords(self):
        return self._keywords

    @property
    def publisher_id(self):
        return self._publisher_id

    @property
    def doi(self):
        return self._doi

    @property
    def authors(self):
        return self._authors

    @property
    def authors_concat(self):
        return self._authors_concat

    @property
    def title(self):
        return self._title

    @copyright_url.setter
    def copyright_url(self, value):
        self._copyright_url = value

    @copyright_desc.setter
    def copyright_desc(self, value):
        self._copyright_desc = value

    @cover_date.setter
    def cover_date(self, value):
        self._cover_date = value

    @epub.setter
    def epub(self, value):
        self._epub = value

    @keywords.setter
    def keywords(self, value):
        self._keywords = value

    @doi.setter
    def doi(self, value):
        self._doi = value

    @publisher_id.setter
    def publisher_id(self, value):
        self._publisher_id = value

    @authors.setter
    def authors(self, value):
        self._authors = value

    @title.setter
    def title(self, value):
        self._title = value

    @authors_concat.setter
    def authors_concat(self, value):
        self._authors_concat = value

    @issue.setter
    def issue(self, value):
        self._issue = value

    @volume.setter
    def volume(self, value):
        self._volume = value

    @elocation_id.setter
    def elocation_id(self, value):
        self._elocation_id = value

    @seq.setter
    def seq(self, value):
        self._seq = value

    @issue_date.setter
    def issue_date(self, value):
        self._issue_date = value
