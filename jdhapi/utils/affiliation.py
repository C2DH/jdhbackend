import logging
from re import I
import pycountry
from jdhseo.utils import get_affiliation
from jdhapi.models import Author

logger = logging.getLogger(__name__)


def get_authors(article_authors, affiliations):
    """
    Extracts and returns a list of authors with their respective affiliations.

    Args:
        article_authors (list): A list of author objects, where each object contains
                                attributes like 'firstname', 'lastname', and 'orcid'.
        affiliations (list): A list of affiliation dictionaries, where each dictionary
                             contains 'aff_id', 'aff_pub_id', and 'authors_link' which
                             is a list of author last names linked to the affiliation.

    Returns:
        list: A list of dictionaries, where each dictionary represents an author with
              their 'given_names', 'surname', 'orcid', 'aff_id', and 'aff_pub_id'.
    """
    authors = []
    for author in article_authors:
        for affiliation in affiliations:
            for author_aff in affiliation["authors_link"]:
                if author.lastname == author_aff:
                    # logger.debug(f'author found {author} in affiliation {affiliation["aff_id"]}  ')
                    contrib = {
                        "given_names": author.firstname,
                        "surname": author.lastname,
                        "orcid": author.orcid,
                        "aff_id": affiliation["aff_id"],
                        "aff_pub_id": affiliation["aff_pub_id"],
                    }
        authors.append(contrib)
        # logger.debug(f'authors {authors}')
    return authors


def get_affiliation_from_orcid(orcid_url, affiliation):
    """
    Retrieve the affiliation details from ORCID.

    Args:
        orcid_url (str): The ORCID URL of the author.
        affiliation (str): The institution affiliation of the author.

    Returns:
        dict or None: A dictionary containing the affiliation details if found, otherwise None.
    """
    ORCID_URL = "https://orcid.org/"
    logger.debug(f"ORCID URL: {orcid_url}")
    orcid = orcid_url.partition(ORCID_URL)[2]
    city_country = get_affiliation(orcid)
    if city_country:
        city = city_country.partition("-")[0].strip()
        country = city_country.partition("-")[2].strip()
        country_name = pycountry.countries.get(alpha_2=country).name
        affiliation = {
            "institution": affiliation,
            "city": city,
            "country": country,
            "country_name": country_name,
        }
        logger.debug(f"Affiliation found in ORCID for author {orcid}")
        return affiliation
    logger.debug(f"No affiliation found in ORCID for author {orcid}")
    return None


def check_database_for_affiliation(author_id):
    """
    Check the database for an affiliation for the given author ID.

    Args:
        author_id (int): The ID of the author.

    Returns:
        dict or None: A dictionary containing the affiliation details if found, otherwise None.
    """
    try:
        author = Author.objects.get(id=author_id)
        if author.city and author.country:
            logger.debug(f"Affiliation found in DB for author {author.lastname}")
            affiliation = {
                "institution": author.affiliation,
                "city": author.city,
                "country": author.country,
                "country_name": author.country.name,
            }
            return affiliation
        else:
            logger.debug(
                f"City and country not found in DB for author {author.lastname}"
            )
            return None
    except Author.DoesNotExist:
        logger.debug(f"Author with ID {author_id} does not exist in the database.")
        return None


def get_affiliation_json_one(author_id, orcid_url, affiliation):
    """
    Retrieve the affiliation details for an author based on ORCID URL or database information.

    Args:
        author_id (int): The ID of the author in the database.
        orcid_url (str): The ORCID URL of the author.
        affiliation (str): The institution affiliation of the author.

    Returns:
        dict: A dictionary containing the affiliation details.
    """
    logger.debug("START get_affiliation_json_one")

    # Check in the database if there is an affiliation
    db_affiliation = check_database_for_affiliation(author_id)
    if db_affiliation:
        return db_affiliation

    # Call ORCID URL if no affiliation in the database
    orcid_affiliation = get_affiliation_from_orcid(orcid_url, affiliation)
    if orcid_affiliation:
        return orcid_affiliation

    # Return default affiliation if no answer from ORCID URL
    default_affiliation = {
        "institution": affiliation,
        "city": "not available",
        "country": "not available",
        "country_name": "not available",
    }
    return default_affiliation


def get_aff_pub_id(publisher_id, aff_id):
    """
    Generate a formatted affiliation publisher ID.

    Args:
        publisher_id (str): The ID of the publisher.
        aff_id (int): The affiliation ID.

    Returns:
        str: A string in the format "j_<publisher_id>_aff_00<aff_id>".
    """
    return "j_" + publisher_id.lower() + "_aff_00" + str(aff_id)


def get_affiliation_json(authors, publisher_id):
    """
    Generate a list of affiliation JSON objects for a given list of authors and a publisher ID.

    Args:
        authors (list): A list of author objects. Each author object should have the attributes 'id', 'orcid', 'affiliation', and 'lastname'.
        publisher_id (str): The ID of the publisher.

    Returns:
        list: A list of dictionaries, each representing an affiliation. Each dictionary contains the following keys:
            - aff_id (int): The affiliation ID.
            - authors_link (list): A list of author last names associated with the affiliation.
            - aff_pub_id (str): The formatted affiliation publisher ID.
            - institution (str): The institution name (from the author's affiliation).
    """
    affiliations = []
    i = 1
    for author in authors:
        affiliation_one = get_affiliation_json_one(
            author.id, author.orcid, author.affiliation
        )
        if len(affiliations) == 0:
            affiliation_one["aff_id"] = i
            affiliation_one["authors_link"] = [author.lastname]
            # format j_publisherId_aff_00sup Ex: j_jdh-2021-1006_aff_001
            affiliation_one["aff_pub_id"] = get_aff_pub_id(
                publisher_id, affiliation_one["aff_id"]
            )
            affiliations.append(affiliation_one)
        else:
            # need to check if already exist
            result = next(
                (
                    item
                    for item in affiliations
                    if item["institution"] == affiliation_one["institution"]
                ),
                {},
            )
            if result:
                # need to add author
                result["authors_link"].append(author.lastname)
            else:
                i += 1
                affiliation_one["aff_id"] = i
                affiliation_one["authors_link"] = [author.lastname]
                affiliation_one["aff_pub_id"] = get_aff_pub_id(
                    publisher_id, affiliation_one["aff_id"]
                )
                affiliations.append(affiliation_one)
    # logger.info(f"affiliations: {affiliations}")
    return affiliations


def is_default_affiliation(affiliations):
    """
    Checks if any affiliation in the list has default values.

    This function iterates through a list of affiliations and checks if any
    affiliation has "not available" as the value for the keys "institution", "city", "country",
    or "country_name". If any of these keys have the value "not available", the
    function returns True, indicating that the affiliation has default values.

    Args:
        affiliations (list of dict): A list of affiliation dictionaries, where
                                     each dictionary contains keys "institution", "city",
                                     "country", and "country_name".

    Returns:
        bool: True if any affiliation has "not available" as the value for "institution", "city",
              "country", or "country_name". False otherwise.
    """
    for affiliation in affiliations:

        if affiliation["institution"] == "not available" and (
            affiliation["city"] == "not available"
            or affiliation["country"] == "not available"
            or affiliation["country_name"] == "not available"
        ):
            return True
    return False
