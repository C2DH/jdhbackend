import base64
import json
import logging
import marko
import re
import requests
import os
import subprocess

from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from django.utils.html import strip_tags

from jdhapi.utils.doi import get_doi_url_formatted_jdh
from jdhapi.models import Author, Tag

from jdhseo.utils import getReferencesFromJupyterNotebook
from requests.exceptions import HTTPError

logger = logging.getLogger(__name__)

METADATA_TAGS = [
    "title",
    "abstract",
    "contributor",
    "disclaimer",
    "keywords",
    "copyright",
]


def get_notebook_from_raw_github(raw_url):
    try:
        logger.info(f"get_notebook_from_raw_github - parsing url: {raw_url}")
        r = requests.get(raw_url)
        r.raise_for_status()  # Raise an error if the request is not successful (e.g., 404)
        return r.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Request to {raw_url} failed with exception: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"JSON decoding failed with exception: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")


def get_notebook_from_github(repository_url, host="https://raw.githubusercontent.com"):
    logger.info(f"get_notebook_from_github - parsing repository_url: {repository_url}")
    result = re.search(
        r"github\.com\/([^\/]+)\/([^\/]+)\/(blob\/)?(.*\.ipynb$)", repository_url
    )
    github_user = result.group(1)
    github_repo = result.group(2)
    github_filepath = result.group(4)
    raw_url = f"{host}/{github_user}/{github_repo}/{github_filepath}"
    # https://raw.githubusercontent.com/jdh-observer/jdh001-WBqfZzfi7nHK/blob/8315a108416f4a5e9e6da0c5e9f18b5e583ed825/scripts/Digital_epigraphy_cite2c_biblio.ipynb
    # Match github.com/<github_user abc>/<github_filepath XXX/yyy/zzz.ipynb>
    # and exclude the `/blob/` part of the url if any.
    # then extract the gighub username nd the filepath to download
    # conveniently from githubusercontent server.
    logger.info(f"get_notebook_from_github - requesting raw_url: {raw_url}...")
    return get_notebook_from_raw_github(raw_url)


# Method to use to generate the fingerprint datas
def get_notebook_stats(raw_url):
    notebook = get_notebook_from_raw_github(raw_url=raw_url)
    logger.info(f"get_notebook_stats - notebook loaded: {raw_url}")
    try:
        cells = notebook.get("cells")
        # output
        cells_stats = []
        countContributors = 0
        # loop through cells and save relevant informations
        for cell in cells:
            c = {"type": cell["cell_type"]}
            # just skip if it's empty
            source = cell.get("source", [])
            if not source:
                continue
            contents = "".join(cell.get("source"))
            # check cell metadata
            tags = cell.get("metadata").get("tags", [])
            if "hidden" in tags:
                continue
            if "contributor" in tags:
                countContributors += 1
            c["countChars"] = len("".join(source))
            if cell["cell_type"] == "markdown":
                initialWords = " ".join(
                    source[0].split()[: int(settings.NUM_CHARS_FINGERPRINT)]
                )
                initialWordsEscape = strip_tags(
                    "".join(marko.convert((initialWords)))
                ).rstrip()
            # for code cell - don't use markdown parser and gettwo first line of code
            else:
                initialWords = " ".join(source[:2])
                initialWordsEscape = initialWords
            c["firstWords"] = initialWordsEscape
            c["isMetadata"] = any(tag in METADATA_TAGS for tag in tags)
            c["tags"] = tags
            c["isHermeneutic"] = any(
                tag in ["hermeneutics", "hermeneutics-step"] for tag in tags
            )
            c["isFigure"] = any(tag.startswith("figure-") for tag in tags)
            c["isTable"] = any(tag.startswith("table-") for tag in tags)
            c["isHeading"] = (
                cell["cell_type"] == "markdown"
                and re.match(r"\s*#+\s", contents) is not None
            )
            cells_stats.append(c)
            # does it contains a cite2c marker?
            markers = re.findall(r'data-cite=[\'"][^\'"]+[\'"]', contents)
            c["countRefs"] = len(markers)

        result = {
            "stats": {
                "countRefs": sum([c["countRefs"] for c in cells_stats]),
                # 'countLines': sum([c['countLines'] for c in cells_stats]),
                "countChars": sum([c["countChars"] for c in cells_stats]),
                "countContributors": countContributors,
                "countHeadings": sum([c["isHeading"] for c in cells_stats]),
                "countHermeneuticCells": sum([c["isHermeneutic"] for c in cells_stats]),
                "countCodeCells": sum([c["type"] == "code" for c in cells_stats]),
                "countCells": len(cells_stats),
                "extentChars": [
                    min([c["countChars"] for c in cells_stats]),
                    max([c["countChars"] for c in cells_stats]),
                ],
                "extentRefs": [
                    min([c["countRefs"] for c in cells_stats]),
                    max([c["countRefs"] for c in cells_stats]),
                ],
            },
            "cells": cells_stats,
        }
    except Exception as err:
        logger.error(f"Error occurred by generating fingerprint for {raw_url}: {err}")
    return result


def get_notebook_specifics_tags(article, raw_url):
    selected_tags = ["title", "abstract", "contributor", "keywords", "collaborators"]
    countTagsFound = 0
    notebook = get_notebook_from_raw_github(raw_url=raw_url)
    logger.info(f"get_notebook_specifics_tags - notebook loaded: {raw_url}")
    cells = notebook.get("cells")
    # output
    result = {}
    # loop through cells and save relevant informations
    for cell in cells:
        # check cell metadata
        tags = cell.get("metadata").get("tags", [])
        for tag in tags:
            if tag in selected_tags:
                countTagsFound += 1
                source = cell.get("source", [])
                logger.info(f"number element {len(source)}")
                if not source:
                    continue
                sourceStr = " ".join([str(elem) for elem in source])
                logger.info(f"celltagged {tag} : {sourceStr}")
                if tag in result:
                    logger.info(f"already one {tag} in {result}")
                    result[tag].append(sourceStr)
                else:
                    result[tag] = [sourceStr]
    if countTagsFound < len(selected_tags):
        logger.error(
            f"get_notebook_specifics_tags - MISSING TAG in notebook: {raw_url}"
        )
        try:
            # logger.info("HOST" + settings.EMAIL_HOST + " PORT " + settings.EMAIL_PORT)
            body = (
                "One or more than one tag are missing, look at for tags '%s' in the following notebook %s."
                % (" ".join(selected_tags), raw_url)
            )
            send_mail(
                "Missing tags in notebooks",
                body,
                "jdh.admin@uni.lu",
                ["jdh.admin@uni.lu"],
                fail_silently=False,
            )
        except Exception as e:  # catch *all* exceptions
            logger.error(f"send_confirmation exception:{e}")
    return result


def get_citation(raw_url, article):
    # output
    # logger.info("title marko" + marko.convert(article.data["title"]))
    titleEscape = strip_tags(
        "".join(marko.convert((article.data["title"][0])))
    ).rstrip()
    authors = []
    authorIds = article.abstract.authors.all()
    for contrib in authorIds:
        contributor = get_object_or_404(Author, lastname=contrib)
        contrib = {"given": contributor.firstname, "family": contributor.lastname}
        authors.append(contrib)
    url = get_doi_url_formatted_jdh(article.doi)
    logger.info(f"url CITATION:{url}")
    return {
        # DO NOT DISPLAYED THE DOI FOR THE MOMENT
        # "DOI": article.doi,
        "URL": url,
        "type": "article-journal",
        "issue": article.issue.issue,
        "title": titleEscape,
        "author": authors,
        "issued": {"year": article.issue.publication_date.strftime("%Y")},
        "volume": article.issue.volume,
        "container-title": "Journal of Digital History",
        "container-title-short": "JDH",
    }


def get_raw_from_github(
    repository_url, file_type, host="https://raw.githubusercontent.com"
):
    logger.info(f"get_raw_from_github - parsing repository_url: {repository_url}")
    result = re.search(
        r"github\.com\/([^\/]+)\/([^\/]+)\/(blob\/)?(.*\." + file_type + "$)",
        repository_url,
    )
    github_user = result.group(1)
    github_repo = result.group(2)
    github_filepath = result.group(4)
    raw_url = f"{host}/{github_user}/{github_repo}/{github_filepath}"
    # https://raw.githubusercontent.com/jdh-observer/jdh001-WBqfZzfi7nHK/blob/8315a108416f4a5e9e6da0c5e9f18b5e583ed825/scripts/Digital_epigraphy_cite2c_biblio.ipynb
    # Match github.com/<github_user abc>/<github_filepath XXX/yyy/zzz.ipynb>
    # and exclude the `/blob/` part of the url if any.
    # then extract the gighub username nd the filepath to download
    # conveniently from githubusercontent server.
    logger.info(f"get_raw_from_github - requesting raw_url: {raw_url}")
    return raw_url


def get_pypi_info(package_name):
    # we go to use the JSON information about packages https://wiki.python.org/moin/PyPIJSON https://pypi.python.org/pypi/<package_name>/json
    URL = "https://pypi.org/pypi/"
    JSON = "/json"
    data = {
        "language": "python",
        "info": {
            "summary": "",
            "url": "",
        },
    }
    try:
        response = requests.get(URL + package_name + JSON)
        response.raise_for_status()
        # access JSON content
        jsonResponse = response.json()
        data["info"]["summary"] = jsonResponse["info"]["summary"]
        data["info"]["package_url"] = jsonResponse["info"]["package_url"]
    except HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err}")
    except Exception as err:
        logger.error(f"Other error occurred: {err}")
    return data


def read_libraries(article):
    # check for requirements.txt
    py_raw_url = get_raw_from_github(
        article.repository_url + "/blob/main/requirements.txt", "txt"
    )
    r = requests.get(py_raw_url)
    if r.status_code == 200:
        reqs = r.text.split()
        if len(reqs) != 0:
            i = 0
            for req in reqs:
                package_name = req.split("==")[0]
                if package_name != "jupyter-contrib-nbextensions":
                    pypi_data = get_pypi_info(package_name)
                    tag, created = Tag.objects.get_or_create(
                        name=package_name, category=Tag.TOOL
                    )
                    tag.data = pypi_data
                    tag.save()
                    article.tags.add(tag)
                    i = i + 1
            return str(i) + " libraries Python tags created"
        else:
            return "0 libraries defined"
    elif r.status_code == 404:
        try:
            # check for install.R
            r_raw_url = get_raw_from_github(
                article.repository_url + "/blob/main/install.R", "R"
            )
            response = requests.get(r_raw_url)
            if response.status_code == 200:
                reqs = response.text
                if len(reqs) != 0:
                    founds = re.findall(r"\"(.*?)\"", reqs)
                    i = 0
                    for found in founds:
                        tag, created = Tag.objects.get_or_create(
                            name=found, category=Tag.TOOL
                        )
                        tag.data = {
                            "language": "R",
                        }
                        tag.save()
                        article.tags.add(tag)
                        i = i + 1
                    return str(i) + " libraries R tags created"
            else:
                return f"no requiremnts.txt - no install.R"
        except HTTPError as http_err:
            logger.error(f"HTTP error occurred: {http_err}")
        except Exception as err:
            logger.error(f"Other error occurred: {err}")


def generate_narrative_tags(article):
    # GENERATE TAGS NARRATIVE FROM KEYWORDS
    # remove existing tags TOOL if exist
    initial_set = article.tags.all()
    if initial_set:
        for initial in initial_set:
            if initial.category == Tag.NARRATIVE:
                article.tags.remove(initial)
    if "keywords" in article.data:
        array_keys = article.data["keywords"][0].replace(";", ",").split(",")
        for key in array_keys:
            tag, created = Tag.objects.get_or_create(
                name=key.lower().strip(), category=Tag.NARRATIVE
            )
            tag.data = {
                "language": "",
            }
            tag.save()
            article.tags.add(tag)
        return str(len(array_keys)) + " narrative tags created"
    else:
        return f"generate task preload information for keywords first: {article.abstract.title}"


def generate_tags(article):
    # remove existing tags TOOL if exist
    initial_set = article.tags.all()
    if initial_set:
        for initial in initial_set:
            if initial.category == Tag.TOOL:
                article.tags.remove(initial)
    # parse requirements.txt or install.R
    return read_libraries(article)


def get_notebook_references_fulltext(article_id, raw_url):
    notebook = get_notebook_from_raw_github(raw_url=raw_url)
    cells = notebook.get("cells")
    logger.debug(f"get_notebook_references_fulltext - notebook loaded: {raw_url}")
    try:
        references, bibliography, refs = getReferencesFromJupyterNotebook(notebook)

        def formatInlineCitations(m):
            parsed_ref = refs.get(m[1], None)
            if parsed_ref is None:
                return f"{m[1]}"
            return parsed_ref

        num = 0
        for cell in cells:
            # check cell metadata
            source = "".join(cell.get("source", ""))
            # check if the cell is tagged as hermeneutics
            tags = cell.get("metadata").get("tags", [])
            # Remove markdown image
            # if (https://orcid.org/sites/default/files/images/orcid_16x16.png) remove it
            # if(https://licensebuttons.net/*)
            if re.search(
                r"https://orcid.org/sites/default/files/images/orcid_16x16.png", source
            ):
                updated_source = re.sub(
                    r"!\[.*\]\(https://orcid.org/sites/default/files/images/orcid_16x16.png\)",
                    "",
                    source,
                )
                cell["source"] = updated_source
            if re.search(r"https://licensebuttons.net/", source):
                updated_source = re.sub(
                    r"!\[.*\]\(https://licensebuttons.net/.*\)", "", source
                )
                cell["source"] = updated_source
            if "hermeneutics" in tags:
                if cell["cell_type"] == "markdown":
                    # Concatenate the strings in the 'source' array to form a single string
                    source_text = "".join(source)
                    # insert start hermeneutics at the beginning of the cell
                    hermeneutics_source = "START HERMENEUTICS\n\n" + source_text
                    # insert end hermeneutics at the end of the cell
                    hermeneutics_source += "\n\nEND HERMENEUTICS\n\n "
                    cell["source"] = [hermeneutics_source]
                else:
                    source_code = "".join(source)
                    hermeneutics_source = "#START HERMENEUTICS\n\n" + source_code
                    # insert end hermeneutics at the end of the cell
                    hermeneutics_source += "\n\n#END HERMENEUTICS\n\n "
                    cell["source"] = [hermeneutics_source]
            # check if the cell contains <cite data-cite="..."></cite>
            if re.search(r"<cite\s+data-cite=.([/\dA-Z]+).>([^<]*)</cite>", source):
                updated_source = re.sub(
                    r"<cite\s+data-cite=.([/\dA-Z]+).>([^<]*)</cite>",
                    formatInlineCitations,
                    source,
                )
                cell["source"] = updated_source

            # Check if the cell contains <div class="cite2c-biblio"></div>
            if "cite2c-biblio" in source:
                logger.info(
                    'Replaced <div class="cite2c-biblio"></div> in cell with bibliography content.'
                )
                # Convert the array to a string with each element on a separate line
                bibliography_lines = "\n\n".join(bibliography)
                cell["source"] = bibliography_lines
            if "cite2c-biblio" in source:
                # Log the replacement
                logger.info(
                    'Replaced <div class="cite2c-biblio"></div> in cell with bibliography content.'
                )
                # Convert the array to a string with each element on a separate line
                bibliography_lines = "\n\n".join(bibliography)
                cell["source"] = bibliography_lines
        generate_output_file(notebook, f"{article_id}.ipynb")
        return {"references": references, "bibliography": bibliography, "refs": refs}
    except Exception as err:
        logger.error(f"Other error occurred: {err}")


def generate_output_file(notebook, output_file):
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)
    output_file_path = os.path.join(output_dir, output_file)
    with open(output_file_path, "w") as outfile:
        json.dump(notebook, outfile)

    logger.info("Output file generated successfully: %s", output_file_path)
    convert_notebook(output_file_path, output_format="pdf")


def convert_notebook(notebook_file, output_format="pdf"):
    try:
        # Run the nbconvert command to generate the output file
        command = f"jupyter nbconvert --to {output_format} {notebook_file}"
        # subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        subprocess.check_output(
            command, shell=True, stderr=subprocess.STDOUT, text=True
        )

        logger.info("Conversion successful!")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error during conversion: {e}")
        logger.error("Command output:\n", e.output)


def convert_string_to_base64(string):
    string_bytes = string.encode("utf-8")
    base64_bytes = base64.b64encode(string_bytes)
    base64_string = base64_bytes.decode("utf-8")

    return base64_string
