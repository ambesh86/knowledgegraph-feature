import json
import datetime
from typing import Any

import numpy as np

from patent.pgpub.model.pgpub import Pgpub


class PgpubJsonEncoder(json.JSONEncoder):

    def default(self, o: Pgpub):
        # application_number_text: str,
        # pgpub_metadata: PgpubMetadata,
        # abstract: str,
        # description: list[str] | None,
        # claims: list[str] | None,
        # organizations: set[str] | None,
        # chemical_compound_synonyms: set[str] | None = None,
        # embeddings: ndarray | None = None,
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
