import json
import datetime
from typing import Any

import numpy as np

from patent.application.model.application import Application


class ApplicationJsonEncoder(json.JSONEncoder):

    def default(self, o: Application):
        # application_number_text: str | None,
        # invention_title: str,
        # first_applicant_name: str | None,
        # applicants: set[str] | None,
        # application_status_description_text: str,
        # application_status_code: int,
        # customer_number: int | None,
        # application_type_code: str,
        # application_type_label_name: str,
        # cpc_classifications: set[str],
        # application_status_date: datetime.date,
        # effective_filing_date: datetime.date | None,
        # filing_date: datetime.date,
        # patent_number: int | None,
        # grant_date: datetime.date | None,
        if isinstance(o, set):
            l = list(o).sort()
            return l
        if isinstance(o, list):
            l = o.sort()
            return l
        elif isinstance(o, datetime.date):
            return o.isoformat()
        elif isinstance(o, np.ndarray):
            return np.array2string(
                o,
                suppress_small=True,
                precision=6,
                separator=", ",
                prefix="",
                suffix="",
            )
        elif hasattr(o, "__dict__"):
            d = o.__dict__
            return self._remove_none(d)
        else:
            return super().default(o)

    def _remove_none(self, obj: dict[str, Any]) -> dict[str, Any]:
        for key in list(obj.keys()):
            if obj[key] is None:
                del obj[key]
        return obj
