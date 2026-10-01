from dataclasses import dataclass


@dataclass
class TherapeuticArea:
    primary_id: str
    primary_label: str
    synonyms: list[str]

    def as_list(self) -> list[str]:
        arr = [self.primary_label]
        if self.synonyms is not None:
            arr.extend(self.synonyms)
        return arr
