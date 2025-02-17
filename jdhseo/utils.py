import marko
import re
import logging
import base64
import qrcode
import requests

from io import BytesIO
from citeproc import formatter
from citeproc import Citation
from citeproc import CitationItem
from citeproc import CitationStylesStyle
from citeproc import CitationStylesBibliography
from citeproc.source.json import CiteProcJSON
from django.utils.html import strip_tags
from requests.exceptions import HTTPError
from requests.structures import CaseInsensitiveDict
from django.conf import settings  # import the settings file

logger = logging.getLogger(__name__)


def getAuthorDateFromReference(ref):
    year = ""
    author = None
    editor = None
    if ref.get("issued", None) is not None:
        if ref.get("issued").get("year", None) is not None:
            year = ref["issued"]["year"]
        elif ref.get("issued").get("literal", None) is not None:
            year = ref["issued"]["literal"]
    elif ref.get("accessed", None) is not None:
        if ref.get("accessed").get("year", None) is not None:
            year = ref["accessed"]["year"]
    if isinstance(ref.get("author", None), list):
        authors = [x["family"] for x in ref["author"]]
        # TODO
        # it is possible to limit the number of authors, add "et al."
        author = ", ".join(authors)
    if isinstance(ref.get("editor", None), list):
        editors = [x["family"] for x in ref["editor"]]
        editor = ", ".join(editors)
    if author is None and editor is not None:
        return f"*{editor} {year}*"
    if editor is None and author is not None:
        return f"*{author} {year}*"
    if editor is not None and author is not None:
        return f"*{author} {year}*"
    else:
        if ref.get("container-title", None) is not None:
            container = ref["container-title"]
            return f"*{container} {year}*"


def getReferencesFromJupyterNotebook(notebook):
    metadata = notebook.get("metadata")
    references = []
    bibliography = []
    inline_references_table = dict()
    try:
        cite2c = metadata.get("cite2c", {})
        references = cite2c.get("citations", {})
        # logger.info("Loging references ---> {0}".format(references))
        bib_source = CiteProcJSON(references.values())
        bib_style = CitationStylesStyle(
            "jdhseo/styles/modern-language-association.csl", validate=False
        )
        bib = CitationStylesBibliography(bib_style, bib_source, formatter.html)
        # register citation
        for key, entry in bib_source.items():
            # exclude  "undefined" due to bug cite2c
            if key != "undefined":
                bib.register(Citation([CitationItem(key)]))
        for item in bib.bibliography():
            bibliography.append(str(item))
        for k, entry in references.items():
            inline_references_table[k] = getAuthorDateFromReference(entry)
    except Exception as e:
        logger.exception(e)
        pass
    # caseless matching
    # return references, sorted(bibliography, key=str.casefold), inline_references_table
    return (
        references,
        sorted(bibliography, key=lambda x: re.sub("[^A-Za-z]+", "", x).lower()),
        inline_references_table,
    )


def parseJupyterNotebook(notebook, merged_authors_affiliations):
    cells = notebook.get("cells")
    title = []
    abstract = []
    disclaimer = []
    paragraphs = []
    collaborators = []
    keywords = []
    references, bibliography, refs = getReferencesFromJupyterNotebook(notebook)

    def formatInlineCitations(m):
        parsed_ref = refs.get(m[1], None)
        if parsed_ref is None:
            return f"{m[1]}"
        return parsed_ref

    # Build contributor array based on merged_authors_affiliations
    contributor = []
    for author in merged_authors_affiliations:
        contributor_html = (
            f'<h3>{author["given_names"]} {author["surname"]} '
            f'<a href="{author["orcid"]}">'
            f'<img src="https://orcid.org/sites/default/files/images/orcid_16x16.png" alt="orcid" /></a></h3>\n'
            f'<p>{author["institution"]}, {author["city"]}, {author["country_name"]}</p>\n'
        )
        contributor.append(contributor_html)

    num = 0
    for cell in cells:
        # check cell metadata
        tags = cell.get("metadata", {}).get("tags", [])
        source = "".join(cell.get("source", ""))
        source = re.sub(
            r"<cite\s+data-cite=.([/\dA-Z]+).>([^<]*)</cite>",
            formatInlineCitations,
            source,
        )
        if "hidden" in tags or "contributor" in tags:
            continue
        if "title" in tags:
            title.append(marko.convert(source))
        elif "abstract" in tags:
            abstract.append(marko.convert(source))
        elif "disclaimer" in tags:
            disclaimer.append(marko.convert(source))
        elif "collaborators" in tags:
            collaborators.append(marko.convert(source))
        elif "keywords" in tags:
            keywords.append(marko.convert(source))
        else:
            if cell.get("cell_type") == "markdown":
                num = num + 1
                paragraphs.append({"num": num, "source": marko.convert(source)})
            elif cell.get("cell_type") == "code":
                num = num + 1
                paragraphs.append({"numCode": num, "code": marko.convert(source)})
    # logger.info(f"contributors {contributor}")
    return {
        "title": title,
        "title_plain": strip_tags("".join(title)).strip(),
        "abstract": abstract,
        "abstract_plain": strip_tags("".join(abstract)).strip(),
        "contributor": contributor,
        "disclaimer": disclaimer,
        "paragraphs": paragraphs,
        "collaborators": collaborators,
        "keywords": keywords,
        "references": references,
        "bibliography": bibliography,
    }


def getPlainMetadataFromArticle(article):
    # Given an `Article` instance,
    # get a dict cotaining flatten down metadata for the
    # article: title, contributors etc.
    title = marko.convert("".join(article.data.get("title", "")))
    abstract = marko.convert("".join(article.data.get("abstract", "")))
    contributor = marko.convert("".join(article.data.get("contributor", "")))
    return {
        "pid": article.abstract.pid,
        "contributor": strip_tags(contributor).strip(),
        "title": strip_tags(title).strip(),
        "abstract": strip_tags(abstract).strip(),
        "keywords": article.data.get("keywords", []),
        "data": article.data,
    }


def generate_qrcode(pid):
    buffer = BytesIO()
    input_data = "https://journalofdigitalhistory.org/en/article/"
    qr = qrcode.QRCode(version=1, box_size=10, border=5)

    qr.add_data(input_data + pid)
    qr.make(fit=True)
    # code hex 00F5D4
    img = qr.make_image(back_color=(255, 255, 255), fill_color=(0, 245, 212))
    img.save(buffer, format="PNG")
    typeEncode = "data:image/png;base64,"
    # base64Encode = "iVBORw0KGgoAAAANSUhEUgAAAZoAAAGaAQAAAAAefbjOAAAC3UlEQVR4nO2cQYrjMBBFX40NvVSgD9BHsa82R+ob2EfpAwzIy4BMzUIlRUkPDA09SUYuL4wT+xEZf0r1S+WI8uVt/fF1BhxyyCGHHHLIoT4hsW0ENhHYRmRmF5nZBbZywfyQ4Tl0RwhVVWVSVdU4qKommDQBDJp3Uz5Rrlue/J4c+g5oswAg8/aiumwvyqQJXcJZdAEsgjxoeA7dDRo/f7WLEhIK+8j0MSLT+6OG59ATQCEh8yYi8zaiP98SuvybX3LoGaESI4ICG7Ceosr6pgCKEIZcw2orWU9+Tw59A7SKiMgJmD7GvJN5q0fs2Wo8angO3TtGtAEgnEUh2af1hFgEecTwHLo7VNxnBGAwC7owqC4hoRqHq7PuPnuHsIccEkyqCkGzIkwHWRZYeun1iO4hU4RGq0ZlbQDoEtQqVBSBeIzoH2pmjSKGoYaMVK8yw+Exon/IFAFgxeoIRSAWPyAk8s4V0T3UzBoWI8quLGSUPCJLxRXRO9TECHvwda6YLq4DMG24InqHykOm5BGt00y36aUron+ozBqaclCwdCFCazyrN/VZo3uozSNqFpkjwxShySNyjcIV0TtUZw2zGY0YyEe1iyZ6PeIIUMksg00Jtos1Z2iqVh4jjgA1VWxrgwjamAtyUun1iONAV+7zEi3ipUiZKBbUY8QRIOuYmRaQ6f2U18V1fTuLAgjbq8oUX4HwS/Tew3Po7tBVaTLPH/bRStl1hdxrlseAGkVAYzgSOaPQ2C5yuSL6h2qFyrYrw4Gll9V/uCL6h3IeURooh6RrPt5HYChLHNtrPvI8on/o9p2usr51sR61uQqvUB0J2upLneEs2YLaiRdlFcnf2SX/yT059D1QfQlYTrvk1mxbAN29O/8AUNuLXdc+SyNVsR51wcNnjf6hP7wbriWPiOZDS1nT+yOOALV9lvWfASy9bKKFNVe5IvqHRP9+ze3m/0zmkEMOOeSQQw4B/AbOLPLhVmPyigAAAABJRU5ErkJggg=="
    base64Encode = base64.b64encode(buffer.getvalue()).decode("utf-8")
    srcImage = typeEncode + base64Encode
    return srcImage


def get_affiliation(orcid):
    logger.debug("START get_affiliation- call API ORCID")
    TOKEN_ID = settings.JDH_ORCID_API_TOKEN
    API_URL = "https://pub.orcid.org/v3.0"
    headers = CaseInsensitiveDict()
    headers["Content-Type"] = "application/orcid+json"
    headers["Authorization"] = f"Bearer {TOKEN_ID}"
    try:
        affiliation = get_employment_affiliation(orcid, API_URL, headers)
        if affiliation is None:
            affiliation = get_education_affiliation(orcid, API_URL, headers)
        logger.debug("END get_affiliation- call API ORCID")
        return affiliation
    except HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err}")
    except Exception as err:
        logger.error(f"Other error occurred: {err}")


def get_employment_affiliation(orcid, api_url, headers):
    url = f"{api_url}/{orcid}/employments"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    json_response = resp.json()
    if json_response["affiliation-group"]:
        for summaries in json_response["affiliation-group"]:
            for summary in summaries["summaries"]:
                if summary["employment-summary"]["end-date"] is None:
                    last = summary["employment-summary"]["organization"]
                    return f"{last['address']['city']} - {last['address']['country']}"
    return None


def get_education_affiliation(orcid, api_url, headers):
    url = f"{api_url}/{orcid}/educations"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    json_response = resp.json()
    if json_response["affiliation-group"]:
        for summaries in json_response["affiliation-group"]:
            for summary in summaries["summaries"]:
                if summary["education-summary"]["end-date"] is None:
                    last = summary["education-summary"]["organization"]
                    return f"{last['address']['city']} - {last['address']['country']}"
    return None


def merge_authors_affiliations(authors, affiliations):
    """
    Merge authors and affiliations information into a single structure.

    Args:
        authors (list): A list of author dictionaries.
        affiliations (list): A list of affiliation dictionaries.

    Returns:
        list: A list of dictionaries, each containing merged author and affiliation information.
    """
    merged_list = []
    for author in authors:
        for affiliation in affiliations:
            if author["aff_id"] == affiliation["aff_id"]:
                merged_info = {
                    "given_names": author["given_names"],
                    "surname": author["surname"],
                    "orcid": author["orcid"],
                    "institution": affiliation["institution"],
                    "city": affiliation["city"],
                    "country": affiliation["country"],
                    "country_name": affiliation["country_name"],
                }
                merged_list.append(merged_info)
                break
    return merged_list
