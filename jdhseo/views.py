import base64
import datetime
import logging
import requests
import os
import urllib.parse
import marko
import io, zipfile
from urllib.parse import urlparse
from django.http import Http404
from django.shortcuts import render
from jdhapi.models import Article, Issue, Author
from django.conf import settings
from .utils import parseJupyterNotebook, generate_qrcode
from .utils import getPlainMetadataFromArticle
from django.http import HttpResponse
from jdhapi.utils.article_xml import ArticleXml
from jdhapi.utils.doi import get_publisher_id, get_doi_url_formatted_jdh
from jdhapi.utils.copyright import CopyrightJDH
from jdhapi.utils.affiliation import get_affiliation_json
from lxml import html
from django.http import FileResponse
from django.template.response import TemplateResponse
from django.http import HttpResponse


logger = logging.getLogger(__name__)


def ArticleDetail(request, pid):
    published_date = ""
    # get ONLY published article matching the pid
    try:
        article = Article.objects.get(
            abstract__pid=pid)
            #status=Article.Status.PUBLISHED)
    except Article.DoesNotExist:
        raise Http404("Article does not exist")
    # generate qrcode
    qrCodebase64 = generate_qrcode(pid)
    # get doi url format for DG
    doi_url = get_doi_url_formatted_jdh(article.doi)
    # Publish online
    if (article.publication_date):
        published_date = article.publication_date.date()
    # decode notebook url
    notebook_url = urllib.parse.unquote(
        base64.b64decode(article.notebook_url).decode('utf-8'))
    # contact_orcid
    ORCID_URL = "https://orcid.org/"
    contact_orcid = article.abstract.contact_orcid.partition(ORCID_URL)[2]
    if 'keywords' in article.data:
        array_keys = "<b>Keywords: </b>" + article.data['keywords'][0].replace(';', ',')
    logger.info(f"keywords {array_keys}")
    # fill the context for the template file.
    context = {
        'article': article,
        'article_absolute_url':
            f"https://journalofdigitalhistory.org/en/article/"
            f"{article.abstract.pid}",
        'qr_code': qrCodebase64,
        'media_url': settings.MEDIA_URL,
        'doi_url': doi_url,
        'published_date': published_date,
        'keywords': array_keys
    }
    # check if it is a github url

    context.update({'proxy': 'github', 'host': settings.JDHSEO_PROXY_HOST})
    if notebook_url.startswith(settings.JDHSEO_PROXY_PATH_GITHUB):
        # load contents from remote link (it uses nginx cache if availeble.
        # this can be improved using local cacle mechanism
        # Cf. https://docs.djangoproject.com/en/3.2/topics/cache/
        remote_url = urllib.parse.urljoin(
            settings.JDHSEO_PROXY_HOST, notebook_url)
        try:
            res = requests.get(remote_url)
            # add NB paragraphs to context
            context.update({'nb': parseJupyterNotebook(res.json(), contact_orcid)})
        except Exception as e:
            logger.error(
                f'Error occurred on article pk={article.pk}'
                f' notebook remote_url={remote_url}')
            logger.exception(e)
            raise Http404("Article Notebook file not found (or not valid)")
    else:
        logger.error(
            f'Article(pid={pid}).notebook_url is BAD:"{notebook_url}"')
        raise Http404("Article does not exist")
    # get content from notebook_url using our proxy
    # r = requests.get('https://api.github.com/user')
    return render(request, 'jdhseo/article_detail.html', context)


def IssueDetail(request, pid):
    try:
        issue = Issue.objects.get(
            pid=pid,
            status=Issue.Status.PUBLISHED)
    except Article.DoesNotExist:
        raise Http404("Issue does not exist")

    articles = Article.objects.filter(
        issue__pid=pid,
        status=Article.Status.PUBLISHED)
    context = {
        'site_base_url': 'https://journalofdigitalhistory.org',
        'issue': issue,
        'count_articles': articles.count(),
        'plain_articles': [
            getPlainMetadataFromArticle(article=a)
            for a in articles
        ]
    }
    return render(request, 'jdhseo/issue_detail.html', context)


def IssueXmlDG(request, pid):
    context = {
        'journal_publisher_id': 'jdh',
        'journal_code': 'jdh',
        'doi_code': 'jdh',
        'issn': '2747-5271',
    }
    return render(request, 'jdhseo/issue_dg.xml', context, content_type='text/xml; charset=utf-8')


def ArticleXmlDG(request, pid):
    try:
        article = Article.objects.get(
            abstract__pid=pid,
            status=Article.Status.PUBLISHED)

        nbauthors = article.abstract.authors.count()
        logger.debug(f'Nb Authors(count={nbauthors}) for article {pid}')
        logger.debug(f'Belongs to issue {article.issue}')
        keywords = []
        if 'keywords' in article.data:
            array_keys = article.data['keywords'][0].replace(';', ',').split(',')
            for item in array_keys:
                keyword = {
                    "keyword": item,
                }
                keywords.append(keyword)
        if 'title' in article.data:
            articleTitle = html.fromstring(marko.convert(article.data['title'][0])).text_content()
        context = {
            'articleXml': ArticleXml(article.abstract.authors.all(), articleTitle, article.doi, keywords, article.publication_date, article.copyright_type, article.issue, pid),
            'journal_publisher_id': 'jdh',
            'journal_code': 'jdh',
            'doi_code': 'jdh',
            'issn': '2747-5271',
        }
    except Article.DoesNotExist:
        raise Http404("Article does not exist")
    return render(request, 'jdhseo/article_dg.xml', context, content_type='text/xml; charset=utf-8')


def ArticleXmlDG(request, pid):
    try:
        article = Article.objects.get(
            abstract__pid=pid,
            status=Article.Status.PUBLISHED)

        nbauthors = article.abstract.authors.count()
        logger.debug(f'Nb Authors(count={nbauthors}) for article {pid}')
        logger.debug(f'Belongs to issue {article.issue}')
        keywords = []
        if 'keywords' in article.data:
            array_keys = article.data['keywords'][0].replace(';', ',').split(',')
            for item in array_keys:
                keyword = {
                    "keyword": item,
                }
                keywords.append(keyword)
        if 'title' in article.data:
            articleTitle = html.fromstring(marko.convert(article.data['title'][0])).text_content()
        context = {
            'articleXml': ArticleXml(article.abstract.authors.all(), articleTitle, article.doi, keywords, article.publication_date, article.copyright_type, article.issue, pid),
            'journal_publisher_id': 'jdh',
            'journal_code': 'jdh',
            'doi_code': 'jdh',
            'issn': '2747-5271',
        }
    except Article.DoesNotExist:
        raise Http404("Article does not exist")
    return render(request, 'jdhseo/article_dg.xml', context, content_type='text/xml; charset=utf-8')


def GetArticleContent_from_url(url, pid):
    response = requests.get(url)
    # Get filename from doi
    try:
        article = Article.objects.get(
            abstract__pid=pid,
            status=Article.Status.PUBLISHED)
    except Article.DoesNotExist:
        raise Http404("Article does not exist")
    filename = get_publisher_id(article.doi).lower()
    path = urlparse(url).path
    ext = os.path.splitext(path)[1]
    if ext == '.pdf':
        filename = f"/{filename}/{filename}.pdf"
    else:
        filename = f"/{filename}/{filename}.xml"
    return response.content, filename


def GetIssueContent_from_url(url, pid):
    response = requests.get(url)
    # Get filename from doi
    try:
        article = Article.objects.get(
            abstract__pid=pid,
            status=Article.Status.PUBLISHED)
    except Article.DoesNotExist:
        raise Http404("Article does not exist")
    filename = get_publisher_id(article.doi).lower()
    logger.debug(f"filename {filename}")
    filename_issue = "/issue-files/jdh.2022.2.issue-1.xml"
    # filename_zip: jdh_{filename}_oi_YYYY-MM-DD--HH-MM-SS.zip
    today = datetime.datetime.now()
    filename_zip = f"jdh_{filename}_oi_{today.strftime('%Y-%m-%d--%H-%M-%S')}.zip"
    logger.debug(f"filename_zip {filename_zip}")
    return response.content, filename_issue, filename_zip


def Generate_zip(request, pid):
    logger.info(f"{request.build_absolute_uri()}")
    # The article's package for DG contains : XML and pdf
    # issue xml
    url_issue = f'http://127.0.0.1:8000/en/issue/dg/{pid}'
    # url_issue = f'https://journalofdigitalhistory.org/prerendered/en/article/dg/{pid}'
    url_xml = f'https://journalofdigitalhistory.org/prerendered/en/article/dg/{pid}'
    url_pdf = f'https://journalofdigitalhistory.org/en/article/{pid}.pdf'
    response_issue, filename_issue, filename_zip = GetIssueContent_from_url(url_issue, pid)
    # Create zip
    buffer = io.BytesIO()
    zip_file = zipfile.ZipFile(buffer, 'w')
    for url in [url_xml, url_pdf]:
        response, filename = GetArticleContent_from_url(url, pid)
        zip_file.writestr(filename, response)
    zip_file.writestr(filename_issue, response_issue)
    zip_file.close()
    # Return zip
    response = HttpResponse(buffer.getvalue())
    response['Content-Type'] = 'application/x-zip-compressed'
    response['Content-Disposition'] = f'attachment; filename={filename_zip}'
    return response


