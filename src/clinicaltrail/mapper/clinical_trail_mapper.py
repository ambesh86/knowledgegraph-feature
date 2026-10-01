import json
from lxml import etree


class ClinicalTrailMapper:
    """
    Class responsible for parsing the XML response from ClinicalTrials.gov API.
    """

    def map_studies_xml(self, xml_response: etree._Element) -> list[dict]:
        """
        Parses XML content and extracts relevant study information.
        Returns a list of dictionaries containing study details.
        """
        studies = []

        for study in xml_response.xpath("//Study"):
            study_data = {
                "NCTId": study.find("NCTId").text,
                "BriefTitle": study.find("BriefTitle").text,
                "Condition": [
                    c.text for c in study.find("Conditions").findall("Condition")
                ],
                "InterventionName": [
                    i.text
                    for i in study.find("Interventions").findall("InterventionName")
                ],
                "OutcomeMeasure": [
                    (om.text, om.find("Type").text)
                    for om in study.find("OutcomeMeasures").findall("OutcomeMeasure")
                ],
            }
            studies.append(study_data)

        return studies

    def map_studies_json(self, json_payload: str) -> list[dict]:
        """
        Parses JSON content and extracts fields we care about
        Return list of dictionaries
        """
        payload = json.loads(json_payload)
        return payload["studies"]
