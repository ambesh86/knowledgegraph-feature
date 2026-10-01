from dataclasses import asdict
import json
from typing import Any

from organization.model.organization_resolution import OrganizationResolution


class ListOfOrganizationResolutionJsonEncoder(json.JSONEncoder):

    def default(self, o: list[OrganizationResolution]):
        dict_list = [self._remove_none(asdict(obj)) for obj in o]
        json_string = json.dumps(dict_list, indent=4)
        return json_string
        # if isinstance(o, list) or isinstance(o, set):
        # else:
        #     return super().default(o)

    def _remove_none(self, obj: dict[str, Any]) -> dict[str, Any]:
        for key in list(obj.keys()):
            if obj[key] is None:
                del obj[key]
        return obj
