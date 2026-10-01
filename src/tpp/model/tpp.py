from numpy import ndarray

from tpp.model.tpp_question import TppQuestion
from tpp.model.theraputic_area_enum import TheraputicAreaEnum


class Tpp:
    """
    target product profile (tpp)
    an array of questions developed by business development in a different theraputic areas
    """

    def __init__(
        self,
        questions: set[TppQuestion] | None,
        threaputic_area: TheraputicAreaEnum | None = None,
        product_description: str | None = None,
        embeddings: ndarray | None = None,
        node_index: str | None = None,
        node_id: str | None = None,
    ):
        self.threaputic_area = threaputic_area
        self.product_description = product_description
        self.questions = questions
        self.embeddings = embeddings
        self.node_index = node_index
        self.node_id = node_id

    def __eq__(self, other):
        return self is other or (
            self.threaputic_area == other.threaputic_area
            and self.product_description == other.product_description
            and self.questions == other.questions
        )

    def __hash__(self):
        questions = frozenset(self.questions) if self.questions is not None else set()
        return hash((self.threaputic_area, self.product_description, questions))

    def __repr__(self):
        return "threaputic_area={} product_description={} questions={} embeddings={}".format(
            self.threaputic_area,
            self.product_description,
            self.questions,
            self.embeddings,
        )

    def __str__(self):
        return repr(self)
