"""The exact-name lookup's Lucene query construction.

These pin the property the whole optimisation rests on: the phrase text handed to the
fulltext index must reach the *same analyzer* that indexed the node name, so that a
name equal to the query analyses to the same tokens and cannot be missed. Anything that
rewrites the characters — stripping punctuation, collapsing separators — breaks that
parity, and the breakage is silent: the lookup simply stops finding a node it used to.
"""

from foundation.infra.db.adapter.neo4j_foundational_node_adapter import (
    _to_fulltext_fuzzy_query,
    _to_fulltext_phrase_query,
)


class TestPhraseQuery:
    def test_a_simple_name_is_quoted(self):
        assert _to_fulltext_phrase_query("hemophilia") == '"hemophilia"'

    def test_a_multi_word_name_stays_one_phrase(self):
        """The point of the change: quoted, this is a phrase; unquoted, Lucene reads it
        as an OR and the index returns every node matching any single word."""
        assert (
            _to_fulltext_phrase_query("superficial multifocal basal cell carcinoma")
            == '"superficial multifocal basal cell carcinoma"'
        )

    def test_punctuation_is_preserved_verbatim(self):
        """THE regression test.

        This name analyses into a token that keeps the colon. An earlier version of
        this function stripped Lucene's reserved characters — as the fuzzy path does —
        which searched for `oxoglutarate` and `oxygen` separately. Neither token exists
        in the index, so the node stopped resolving, and no amount of phrase slop
        recovered it because the tokens differed in identity, not position.
        """
        name = "gibberellin A19, 2-oxoglutarate:oxygen oxidoreductase activity"
        assert _to_fulltext_phrase_query(name) == f'"{name}"'

    def test_bracketed_chemical_names_are_not_syntax(self):
        """Names like this made the old raw query raise a Lucene ParseException — a
        500 from the endpoint, not a miss. Inside a phrase they are literal text."""
        name = "3-[4-AMINO-1-(1-METHYLETHYL)-1H-PYRAZOLO[3,4-D]PYRIMIDIN-3-YL]PHENOL"
        assert _to_fulltext_phrase_query(name) == f'"{name}"'

    def test_embedded_quote_is_escaped(self):
        assert _to_fulltext_phrase_query('alpha "1" antitrypsin') == '"alpha \\"1\\" antitrypsin"'

    def test_embedded_backslash_is_escaped_before_the_quote_is_added(self):
        """Order matters: escaping the backslash after wrapping would escape the quote
        we just added and unbalance the phrase."""
        assert _to_fulltext_phrase_query("a\\b") == '"a\\\\b"'

    def test_empty_input_produces_no_query(self):
        assert _to_fulltext_phrase_query("") == ""
        assert _to_fulltext_phrase_query(None) == ""  # type: ignore[arg-type]

    def test_the_phrase_is_always_balanced(self):
        """Whatever goes in, what comes out must parse — an unbalanced quote is a 500."""
        for value in [
            'a"b',
            "a\\b",
            'trailing\\',
            '"',
            "\\",
            'mixed "quote\\ and slash',
            "(+)-camphor biosynthetic process",
        ]:
            out = _to_fulltext_phrase_query(value)
            assert out.startswith('"') and out.endswith('"')
            body = out[1:-1]
            # Every quote inside the body is escaped, and every escape is deliberate.
            i, escaped = 0, 0
            while i < len(body):
                if body[i] == "\\":
                    assert i + 1 < len(body), f"dangling escape in {out!r}"
                    assert body[i + 1] in ('"', "\\"), f"stray escape in {out!r}"
                    escaped += 1
                    i += 2
                    continue
                assert body[i] != '"', f"unescaped quote in {out!r}"
                i += 1


class TestFuzzyQueryIsUnchanged:
    """The fuzzy path deliberately still sanitises: it is matching approximately, so
    token identity is not load-bearing there the way it is for an exact lookup."""

    def test_tokens_get_an_edit_distance_marker(self):
        assert _to_fulltext_fuzzy_query("folic acid deficiency") == "folic~ acid~ deficiency~"

    def test_reserved_characters_are_stripped(self):
        assert _to_fulltext_fuzzy_query("tonic-clonic") == "tonic~ clonic~"
