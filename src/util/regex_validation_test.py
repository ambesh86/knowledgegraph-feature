import logging
import re
import unittest


from util.regex_validation import sanitize_regex_pattern

logger = logging.getLogger(__name__)


class RegexSanitizeTest(unittest.TestCase):
    """Tests for _sanitize_regex_pattern function"""

    def test_simple_string_without_special_chars(self):
        """Test that simple strings pass through unchanged"""
        result = sanitize_regex_pattern("pfizer")
        assert result == "pfizer"

    def test_wildcard_asterisk_converts_to_regex(self):
        """Test that * wildcard converts to .* (match any characters)"""
        result = sanitize_regex_pattern("pfizer*")
        assert result == "pfizer.*"

    def test_wildcard_question_mark_converts_to_regex(self):
        """Test that ? wildcard converts to . (match single character)"""
        result = sanitize_regex_pattern("pf?zer")
        assert result == "pf.zer"

    def test_multiple_wildcards(self):
        """Test multiple wildcards in a pattern"""
        result = sanitize_regex_pattern("p*z?r")
        assert result == "p.*z.r"

    def test_escapes_dangerous_regex_chars(self):
        """Test that dangerous regex special characters are escaped"""
        # Test parentheses (grouping)
        result = sanitize_regex_pattern("pf(i|y)zer")
        assert result == r"pf\(i\|y\)zer"

        # Test square brackets (character classes)
        result = sanitize_regex_pattern("pfizer[abc]")
        assert result == r"pfizer\[abc\]"

        # Test curly braces (quantifiers)
        result = sanitize_regex_pattern("pfizer{2,5}")
        assert result == r"pfizer\{2,5\}"

    def test_escapes_anchors_and_boundaries(self):
        """Test that anchors and word boundaries are escaped"""
        result = sanitize_regex_pattern("^pfizer$")
        assert result == r"\^pfizer\$"

        result = sanitize_regex_pattern(r"\bpfizer\b")
        assert result == r"\\bpfizer\\b"

    def test_escapes_dot_metacharacter(self):
        """Test that . (any character) is escaped"""
        result = sanitize_regex_pattern("pfizer.com")
        assert result == r"pfizer\.com"

    def test_escapes_plus_and_star_operators(self):
        """Test that + operator is escaped (but * wildcard becomes .*)"""
        result = sanitize_regex_pattern("pfizer+")
        assert result == r"pfizer\+"

        # * should convert to .* not be escaped
        result = sanitize_regex_pattern("pfizer*")
        assert result == "pfizer.*"

    def test_complex_malicious_pattern(self):
        """Test a complex malicious regex pattern is fully escaped"""
        # This pattern could cause ReDoS if not escaped
        malicious = "pf(i|y)zer.*$$"
        result = sanitize_regex_pattern(malicious)
        # All special chars except the * wildcard should be escaped
        expected = r"pf\(i\|y\)zer\..*\$\$"
        assert result == expected

    def test_redos_pattern_is_neutralized(self):
        """Test that potential ReDoS patterns are neutralized"""
        # Pattern like (a+)+ can cause catastrophic backtracking
        redos_pattern = "(a+)+(b+)+"
        result = sanitize_regex_pattern(redos_pattern)
        assert result == r"\(a\+\)\+\(b\+\)\+"

    def test_empty_string(self):
        """Test empty string returns empty string"""
        result = sanitize_regex_pattern("")
        assert result == ""

    def test_only_wildcards(self):
        """Test string with only wildcards"""
        result = sanitize_regex_pattern("*?*")
        assert result == ".*..*"

    def test_special_chars_before_wildcards(self):
        """Test that special chars before wildcards are escaped"""
        result = sanitize_regex_pattern("pfizer.*test")
        assert result == r"pfizer\..*test"

    def test_backslash_escaping(self):
        """Test that backslashes are properly escaped"""
        result = sanitize_regex_pattern(r"pfizer\test")
        assert result == r"pfizer\\test"

    def test_sql_injection_like_pattern(self):
        """Test patterns that might be SQL injection attempts"""
        result = sanitize_regex_pattern("'; DROP TABLE companies; --")
        # All special chars should be escaped
        assert ";" in result
        assert "-" in result
        # Verify no unescaped dangerous characters remain
        assert result == r"';\ DROP\ TABLE\ companies;\ \-\-"

    def test_unicode_characters(self):
        """Test that unicode characters are preserved"""
        result = sanitize_regex_pattern("pfizer™")
        assert result == "pfizer™"

    def test_pattern_works_in_actual_regex(self):
        """Integration test: verify sanitized patterns work in actual regex"""
        # Test that sanitized patterns can be used safely
        pattern = sanitize_regex_pattern("pfizer*")
        regex = re.compile(f"(?i){pattern}")

        # Should match
        assert regex.match("pfizer")
        assert regex.match("pfizer inc")
        assert regex.match("Pfizer Corporation")

        # Should not match
        assert not regex.match("novartis")

    def test_question_mark_wildcard_in_regex(self):
        """Integration test: verify ? wildcard works correctly"""
        pattern = sanitize_regex_pattern("pf?zer")
        regex = re.compile(f"(?i){pattern}")

        # Should match (single character)
        assert regex.match("pfizer")
        assert regex.match("pfyzer")
        assert regex.match("pf1zer")

        # Should not match (missing character or multiple characters)
        assert not regex.match("pzer")
        assert not regex.match("pfiiizer")

    def test_escaped_special_chars_dont_have_regex_meaning(self):
        """Integration test: verify escaped chars are treated as literals"""
        pattern = sanitize_regex_pattern("price: $100+")
        regex = re.compile(pattern)

        # Should match literal string
        assert regex.search("price: $100+")

        # Should NOT match regex interpretation ($=end, +=one or more)
        assert not regex.match("price: 100")  # Missing $
        assert not regex.match("price: $1000")  # + doesn't mean one-or-more

    def test_nested_groups_are_escaped(self):
        """Test deeply nested grouping patterns are escaped"""
        result = sanitize_regex_pattern("((a|b)+)")
        assert result == r"\(\(a\|b\)\+\)"

    def test_lookahead_lookbehind_are_escaped(self):
        """Test that lookahead and lookbehind assertions are escaped

        Note: ? is converted to . (single char wildcard) as part of wildcard support,
        so (?=...) becomes (.=...) which prevents lookahead from working.
        """
        result = sanitize_regex_pattern("(?=pfizer)(?!novartis)")
        # Parentheses should be escaped
        assert "\\(" in result
        # ? is converted to . (wildcard), not escaped as \?
        assert "?" not in result
        assert ".=" in result
        assert ".!" in result
        # Verify the full pattern prevents lookahead/lookbehind from working
        assert result == r"\(.=pfizer\)\(.!novartis\)"
