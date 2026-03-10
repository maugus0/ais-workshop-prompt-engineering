"""Unit tests for cafe_order_processor (no API key required; mocks OpenAI)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cafe_order_processor import load_prompt_config, process_order, strip_json_fences  # noqa: E402


def test_load_prompt_config_structure():
    """load_prompt_config returns dict with meta and system_prompt."""
    config = load_prompt_config()
    assert "meta" in config
    assert "system_prompt" in config
    assert config["meta"]["model"]
    assert "temperature" in config["meta"]
    assert len(config["system_prompt"]) > 100


def test_strip_json_fences_plain():
    """Plain JSON is unchanged."""
    text = '{"items": [], "total_items": 0}'
    assert strip_json_fences(text) == text


def test_strip_json_fences_with_backticks():
    """Markdown code fence is removed."""
    wrapped = '```json\n{"a": 1}\n```'
    assert strip_json_fences(wrapped) == '{"a": 1}'


def test_strip_json_fences_only_opening():
    """Only opening ``` is stripped."""
    text = '```\n{"a": 1}'
    result = strip_json_fences(text)
    assert result == '{"a": 1}'


def test_process_order_success():
    """process_order returns validated dict when API returns valid JSON."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content='{"items":[{"name":"Americano","quantity":2,"size":"regular","modifiers":[]}],'
                '"special_instructions":"","total_items":2}'
            )
        )
    ]
    with patch("cafe_order_processor.client") as mock_client:
        mock_client.chat.completions.create.return_value = mock_response
        result = process_order("2 Americanos")
    assert "error" not in result
    assert result["total_items"] == 2
    assert len(result["items"]) == 1
    assert result["items"][0]["name"] == "Americano"
    assert result["items"][0]["quantity"] == 2


def test_process_order_fixes_total_items():
    """total_items is recomputed from item quantities."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content='{"items":[{"name":"Coffee","quantity":3,"size":"regular","modifiers":[]}],'
                '"special_instructions":"","total_items":99}'
            )
        )
    ]
    with patch("cafe_order_processor.client") as mock_client:
        mock_client.chat.completions.create.return_value = mock_response
        result = process_order("3 coffees")
    assert result["total_items"] == 3


def test_process_order_handles_fenced_response():
    """Response wrapped in ```json ... ``` is parsed correctly."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content='```json\n{"items":[{"name":"Tea","quantity":1,"size":"regular","modifiers":[]}],'
                '"special_instructions":"","total_items":1}\n```'
            )
        )
    ]
    with patch("cafe_order_processor.client") as mock_client:
        mock_client.chat.completions.create.return_value = mock_response
        result = process_order("one tea")
    assert "error" not in result
    assert result["total_items"] == 1
    assert result["items"][0]["name"] == "Tea"


def test_process_order_returns_error_on_invalid_json():
    """When API returns non-JSON, process_order returns error dict."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Not valid JSON at all"))]
    with patch("cafe_order_processor.client") as mock_client:
        mock_client.chat.completions.create.return_value = mock_response
        result = process_order("something")
    assert "error" in result
    assert "raw_response" in result
