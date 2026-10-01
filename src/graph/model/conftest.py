import pytest
from graph.model.entity import Entity
from graph.model.relationship import Relationship


@pytest.fixture(scope="class")
def sample_entity() -> Entity:
    return Entity("PolQ", "Protein")


@pytest.fixture(scope="class")
def sample_entities() -> set[Entity]:
    return {Entity("53BP1", "Protein"), Entity("AZD7648", "Molecule")}


@pytest.fixture(scope="class")
def sample_relationship() -> Relationship:
    source = Entity("i53 mRNA", "mRNA")
    target = Entity("CYBB locus", "Genomic Locus")
    relation = "Enhancement"
    return Relationship(source, target, relation)
