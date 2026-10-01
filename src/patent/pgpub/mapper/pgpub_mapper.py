import logging
from typing import Any
from lxml import etree

from patent.pgpub.model.pgpub import Pgpub
from patent.pgpub.model.pgpub_metadata import PgpubMetadata

logger = logging.getLogger(__name__)


class PgpubMapper:
    """
    map responses from listing pgpub associated documents
    https://data.uspto.gov/apis/patent-file-wrapper/associated-documents
    """

    def map(self, pgpub_metadata: PgpubMetadata, xml_response: bytes) -> Pgpub:
        """
        Parses XML content and extracts relevant pgpub information.
        """
        root = etree.fromstring(xml_response)
        abstract = self._map_abstract_paragraph(root)
        description = self._map_descriptions(root)
        organizations = self._map_organizations(root)
        claims = self._map_claims(root)
        return Pgpub(
            application_number_text=pgpub_metadata.application_number_text,
            pgpub_metadata=pgpub_metadata,
            abstract=abstract,
            organizations=organizations,
            description=description,
            claims=claims,
        )

    def _map_organizations(self, root: etree._Element) -> set[str]:
        self._ensure_root(root)
        # e.g.
        # <assignees>
        #     <assignee>
        #         <addressbook>
        #             <orgname>Pacific Biosciences of California, Inc.</orgname>
        tree = etree.ElementTree(root)
        path = tree.getpath(root)
        logger.debug(f"{path}")
        orgs = set()
        for organization in root.xpath(
            "//assignees/assignee/addressbook/orgname/text()"
        ):
            logger.debug(f"org: {organization}")
            orgs.add(organization)
        return orgs

    def _map_abstract_paragraph(self, root: etree._Element) -> str:
        self._ensure_root(root)
        abstracts = root.xpath("//abstract//text()")
        if abstracts is None:
            logger.warning("Doc is missing abstract. Moving on...")
            return ""
        return "".join(abstracts).strip()

    def _map_descriptions(self, root: etree._Element) -> list[str]:
        self._ensure_root(root)
        description_paths = root.xpath("//description")
        return self._map_paragraph_subelements(description_paths)

    def _map_claims(self, root: etree._Element) -> list[str]:
        self._ensure_root(root)
        # e.g.
        # <claims id="claims">
        #   <claim id="CLM-00051" num="00051">
        #         <claim-text><b>51</b>. A labeled nucleotide analog comprising: <claim-text>a first
        #             avidin protein having four subunits, each subunit comprising one biotin binding
        return self._map_paragraph_subelements(root.xpath("//claims/claim/claim-text"))

    def _map_paragraph_subelements(self, elements: list[Any]) -> list[str]:
        paragraphs = []
        for paragraph_el in elements:
            logger.debug(f"paragraph: {paragraph_el}")
            for paragraph in paragraph_el.itertext():
                paragraph = paragraph.strip()
                if not paragraph == "":
                    paragraphs.append(paragraph)

        return paragraphs

    def _ensure_root(self, root: etree._Element) -> None:
        if root is None:
            raise ValueError("root is None!")
