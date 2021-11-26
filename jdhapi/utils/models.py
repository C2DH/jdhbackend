# function that can be used in models live here
import json
import requests
from django.core.mail import send_mail
import re
import logging
from django.conf import settings  # import the settings file
from django.utils.html import strip_tags
import marko
from django.shortcuts import render, get_object_or_404
from jdhapi.models import Author

logger = logging.getLogger(__name__)


def get_notebook_from_raw_github(raw_url):
    logger.info(
        f'get_notebook_from_raw_github - parsing url: {raw_url}')
    r = requests.get(raw_url)
    return r.json()


def get_notebook_from_github(
    repository_url, host='https://raw.githubusercontent.com'
):
    logger.info(
        f'get_notebook_from_github - parsing repository_url: {repository_url}')
    result = re.search(
        r'github\.com\/([^\/]+)\/([^\/]+)\/(blob\/)?(.*\.ipynb$)',
        repository_url
    )
    github_user = result.group(1)
    github_repo = result.group(2)
    github_filepath = result.group(4)
    raw_url = f'{host}/{github_user}/{github_repo}/{github_filepath}'
    # https://raw.githubusercontent.com/jdh-observer/jdh001-WBqfZzfi7nHK/blob/8315a108416f4a5e9e6da0c5e9f18b5e583ed825/scripts/Digital_epigraphy_cite2c_biblio.ipynb
    # Match github.com/<github_user abc>/<github_filepath XXX/yyy/zzz.ipynb>
    # and exclude the `/blob/` part of the url if any.
    # then extract the gighub username nd the filepath to download
    # conveniently from githubusercontent server.
    logger.info(f'get_notebook_from_github - requesting raw_url: {raw_url}...')
    return get_notebook_from_raw_github(raw_url)


def get_notebook_stats(raw_url):
    notebook = get_notebook_from_raw_github(raw_url=raw_url)
    logger.info(f'get_notebook_stats - notebook loaded: {raw_url}')

    cells = notebook.get('cells')
    # output
    cells_stats = []
    countContributors = 0
    # loop through cells and save relevant informations
    for cell in cells:
        c = {'type': cell['cell_type']}
        # just skip if it's empty
        source = cell.get('source', [])
        if not source:
            continue
        contents = ''.join(cell.get('source'))
        # check cell metadata
        tags = cell.get('metadata').get('tags', [])
        if 'hidden' in tags:
            continue
        if 'contributor' in tags:
            countContributors += 1
        c['countChars'] = len(''.join(source))
        c['firstWords'] = ' '.join(source[0].split()[:5])
        c['isMetadata'] = any(tag in [
            'title', 'abstract', 'contributor', 'disclaimer', 'keywords'
        ] for tag in tags)
        c['isHermeneutic'] = any(tag in [
            'hermeneutics', 'hermeneutics-step'
        ] for tag in tags)
        c['isFigure'] = any(tag.startswith('figure-') for tag in tags)
        c['isTable'] = any(tag.startswith('table-') for tag in tags)
        c['isHeading'] = cell['cell_type'] == 'markdown' and re.match(
            r'\s*#+\s', contents) is not None
        cells_stats.append(c)
        # does it contains a cite2c marker?
        markers = re.findall(r'data-cite=[\'"][^\'"]+[\'"]', contents)
        c['countRefs'] = len(markers)

    result = {
        'stats': {
            'countRefs': sum([
                c['countRefs'] for c in cells_stats]),
            # 'countLines': sum([c['countLines'] for c in cells_stats]),
            'countChars': sum([
                c['countChars'] for c in cells_stats]),
            'countContributors': countContributors,
            'countHeadings': sum([
                c['isHeading'] for c in cells_stats]),
            'countHermeneuticCells': sum([
                c['isHermeneutic'] for c in cells_stats]),
            'countCodeCells': sum([
                c['type'] == 'code' for c in cells_stats]),
            'countCells': len(cells_stats),
            'extentChars': [
                min([c['countChars'] for c in cells_stats]),
                max([c['countChars'] for c in cells_stats])],
            'extentRefs': [
                min([c['countRefs'] for c in cells_stats]),
                max([c['countRefs'] for c in cells_stats])]
        },
        'cells': cells_stats
    }

    return result


def get_notebook_specifics_tags(raw_url):
    selected_tags = ['title', 'abstract', 'contributor', 'keywords', 'collaborators']
    countTagsFound = 0
    notebook = get_notebook_from_raw_github(raw_url=raw_url)
    logger.info(f'get_notebook_specifics_tags - notebook loaded: {raw_url}')
    cells = notebook.get('cells')
    # output
    result = {}
    # loop through cells and save relevant informations
    for cell in cells:
        # check cell metadata
        tags = cell.get('metadata').get('tags', [])
        for tag in tags:
            if tag in selected_tags:
                countTagsFound += 1
                source = cell.get('source', [])
                logger.info(f'number element {len(source)}')
                if not source:
                    continue
                sourceStr = ' '.join([str(elem) for elem in source])
                logger.info(
                    f'celltagged {tag} : {sourceStr}'
                )
                if tag in result:
                    logger.info(
                        f'already one {tag} in {result}'
                    )
                    result[tag].append(sourceStr)
                else:
                    result[tag] = [sourceStr]
    if countTagsFound < len(selected_tags):
        logger.error(f'get_notebook_specifics_tags - MISSING TAG in notebook: {raw_url}')
        try:
            # logger.info("HOST" + settings.EMAIL_HOST + " PORT " + settings.EMAIL_PORT)
            body = "One or more than one tag are missing, look at for tags '%s' in the following notebook %s." % (" ".join(selected_tags), raw_url)
            send_mail("Missing tags in notebooks", body, 'jdh.admin@uni.lu', ['jdh.admin@uni.lu'], fail_silently=False,)
        except Exception as e:  # catch *all* exceptions
            logger.error(f'send_confirmation exception:{e}')
    return result


def get_citation(raw_url, article):
    # output
    # logger.info("title marko" + marko.convert(article.data["title"]))
    titleEscape = strip_tags(''.join(marko.convert((article.data["title"][0])))).rstrip()
    authors = []
    """ mainAuthor = {
        "given": article.abstract.contact_firstname,
        "family": article.abstract.contact_lastname
    }
    authors.append(mainAuthor) """
    authorIds = article.abstract.authors.all()
    for contrib in authorIds:
        contributor = get_object_or_404(Author, lastname=contrib)
        contrib = {
            "given": contributor.firstname,
            "family": contributor.lastname
        }
        authors.append(contrib)
    return ({
        # DO NOT DISPLAYED THE DOI FOR THE MOMENT
        # "DOI": article.doi,
        "URL": "https://journalofdigitalhistory.org/en/article/" + article.abstract.pid,
        "type": "article-journal",
        "issue": article.issue.pid,
        "title": titleEscape,
        "author": authors,
        "issued": {
            "year": article.issue.creation_date.strftime("%Y")
        },
        # "volume": "1",
        "container-title": "Journal of Digital History",
        "container-title-short": "JDH"
    })
