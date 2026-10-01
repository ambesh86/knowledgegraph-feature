from enum import Enum


class QuestionTypeEnum(Enum):
    UNKNOWN = 0, "Unknown".lower()
    INDICATION = 1, "Indication".lower()
    CONTRAINDICATION = 2, "Contraindication".lower()
    MECHANISM_OF_ACTION = 3, "MoA & modality".lower()
    ROUTE_OF_ADMINISTRATION = 4, "RoA & dosing".lower()
    EFFICACY = 5, "Efficacy".lower()
    SAFTEY_AND_TOLERABILITY = 6, "Safety & tolerability".lower()
    COST_OF_GOODS_SOLD = 7, "COGs".lower()
