"""
Tests for LLM response parsing (agents/graph.py).
"""

from agents.graph import _adapt_response_to_schema, _normalize_to_string_list, parse_json_response
from models.schemas import CodeReview, FixedCode


class TestParseJsonResponse:
    """Tests for parse_json_response function."""

    def test_parses_valid_json(self):
        """Should parse well-formed JSON response."""
        response = '''
{
    "issues": ["Line 5: potential IndexError"],
    "suggestions": ["Add bounds checking"],
    "severity": "high",
    "summary": "Found potential crash bug"
}
'''
        result = parse_json_response(response, CodeReview)
        
        assert result is not None
        assert result["severity"] == "high"
        assert len(result["issues"]) == 1
        assert "IndexError" in result["issues"][0]

    def test_extracts_json_from_markdown(self):
        """Should extract JSON from markdown code blocks."""
        response = '''
Here's my analysis:

```json
{
    "issues": ["Bug found"],
    "suggestions": ["Fix it"],
    "severity": "medium",
    "summary": "Review complete"
}
```

Let me know if you need more details.
'''
        result = parse_json_response(response, CodeReview)
        
        assert result is not None
        assert result["summary"] == "Review complete"

    def test_handles_thinking_tags(self):
        """Should remove thinking tags before parsing."""
        response = '''
<think>
Let me analyze this code carefully...
The user wants me to find bugs.
</think>
{
    "issues": [],
    "suggestions": ["Code looks good"],
    "severity": "low",
    "summary": "No issues found"
}
'''
        result = parse_json_response(response, CodeReview)
        
        assert result is not None
        assert result["severity"] == "low"

    def test_handles_empty_lists(self):
        """Should handle empty issue/suggestion lists."""
        response = '''
{
    "issues": [],
    "suggestions": [],
    "severity": "low",
    "summary": "Perfect code"
}
'''
        result = parse_json_response(response, CodeReview)
        
        assert result is not None
        assert result["issues"] == []
        assert result["suggestions"] == []

    def test_parses_fixed_code_response(self):
        """Should parse FixedCode schema."""
        response = '''
{
    "code": "print('fixed')",
    "explanation": "Fixed the bug",
    "changes_made": ["Changed X to Y"]
}
'''
        result = parse_json_response(response, FixedCode)
        
        assert result is not None
        assert result["code"] == "print('fixed')"
        assert "Fixed" in result["explanation"]

    def test_returns_none_for_invalid_json(self):
        """Should return None for completely invalid responses."""
        response = "This is not JSON at all, just plain text."
        result = parse_json_response(response, CodeReview)
        
        assert result is None

    def test_extracts_json_with_surrounding_text(self):
        """Should extract JSON even with surrounding prose."""
        response = '''
After analyzing the code, here are my findings:
{"issues": ["test"], "suggestions": [], "severity": "low", "summary": "done"}
That's all I found.
'''
        result = parse_json_response(response, CodeReview)
        
        assert result is not None
        assert result["issues"] == ["test"]


class TestNormalizeToStringList:
    """Tests for _normalize_to_string_list helper."""

    def test_preserves_string_list(self):
        """Should preserve a list of strings unchanged."""
        items = ["issue 1", "issue 2", "issue 3"]
        result = _normalize_to_string_list(items)
        
        assert result == items

    def test_converts_dict_with_description(self):
        """Should extract description from dict items."""
        items = [
            {"line": 5, "description": "IndexError possible"},
            {"line": 10, "description": "Missing return"}
        ]
        result = _normalize_to_string_list(items)
        
        assert len(result) == 2
        assert "Line 5" in result[0]
        assert "IndexError" in result[0]

    def test_handles_mixed_types(self):
        """Should handle mixed strings and dicts."""
        items = [
            "plain string issue",
            {"description": "dict issue"},
            123  # number
        ]
        result = _normalize_to_string_list(items)
        
        assert len(result) == 3
        assert result[0] == "plain string issue"
        assert result[1] == "dict issue"
        assert result[2] == "123"


class TestAdaptResponseToSchema:
    """Tests for _adapt_response_to_schema helper."""

    def test_normalizes_severity(self):
        """Should normalize severity to lowercase."""
        data = {
            "issues": [],
            "suggestions": [],
            "severity": "HIGH",
            "summary": "test"
        }
        result = _adapt_response_to_schema(data, CodeReview)
        
        assert result["severity"] == "high"

    def test_fixes_invalid_severity(self):
        """Should default invalid severity to medium."""
        data = {
            "issues": [],
            "suggestions": [],
            "severity": "critical",  # not a valid option
            "summary": "test"
        }
        result = _adapt_response_to_schema(data, CodeReview)
        
        assert result["severity"] == "medium"

    def test_normalizes_issues_list(self):
        """Should normalize issues from dicts to strings."""
        data = {
            "issues": [{"line": 1, "description": "bug"}],
            "suggestions": [],
            "severity": "high",
            "summary": "test"
        }
        result = _adapt_response_to_schema(data, CodeReview)
        
        assert isinstance(result["issues"][0], str)
        assert "Line 1" in result["issues"][0]
