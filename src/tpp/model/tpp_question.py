from numpy import ndarray

from tpp.model.question_type_enum import QuestionTypeEnum


class TppQuestion:
    """
    target product profile (tpp) question
    """

    def __init__(
        self,
        question_type: QuestionTypeEnum,
        ideal: str,
        acceptable: str,
        excluded: str,
        embeddings: ndarray | None = None,
        node_index: str | None = None,
        node_id: str | None = None,
    ):
        self.question_type = question_type
        self.ideal = ideal
        self.acceptable = acceptable
        self.excluded = excluded
        self.embeddings = embeddings
        self.node_index = node_index
        self.node_id = node_id

    def __eq__(self, other):
        return self is other or (
            self.question_type == other.question_type
            and self.ideal == other.ideal
            and self.acceptable == other.acceptable
            and self.excluded == other.excluded
        )

    def __hash__(self):
        return hash(
            (
                self.question_type,
                self.ideal,
                self.acceptable,
                self.excluded,
            )
        )

    def __repr__(self):
        return "question={} ideal={} acceptable={} excluded={}".format(
            self.question_type,
            self.ideal,
            self.acceptable,
            self.excluded,
        )

    def __str__(self):
        return repr(self)
