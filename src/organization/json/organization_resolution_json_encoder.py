from dataclasses import asdict
import json
import logging

from organization.model.organization_resolution import OrganizationResolution

logger = logging.getLogger(__name__)


class OrganizationResolutionJsonEncoder(json.JSONEncoder):

    def default(self, o: OrganizationResolution):
        logger.info(f"{type(o)} {o}")
        if isinstance(o, OrganizationResolution):
            logger.info(f"found organization resolution {type(o)}")
            d = asdict(o)
            logger.info(d)
            return d
            # json_string = json.dumps(dict, cls=OrganizationResolutionJsonEncoder, indent=4)
            # return json_string
        elif isinstance(o, set):
            l = list(o).sort()
            return l
        elif isinstance(o, list):
            l = o.sort()
            return l
        elif hasattr(o, "__dict__"):
            d = o.__dict__
            return d
        else:
            return super().default(o)

    # def _remove_none(self, obj: dict[str, Any]) -> dict[str, Any]:
    #     for key in list(obj.keys()):
    #         if obj[key] is None:
    #             del obj[key]
    #     return obj
