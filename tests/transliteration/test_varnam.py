"""Tests for the Varnam API client (Manglish → Malayalam transliteration)."""

from unittest.mock import MagicMock, patch

import httpx

from linguaalayam.transliteration.varnam import manglish_to_malayalam


def _mock_client(
    response: MagicMock | None = None, raise_exc: Exception | None = None
) -> MagicMock:
    """Build a mock httpx.Client whose context-managed get() returns response or raises."""
    client = MagicMock()
    if raise_exc is not None:
        client.__enter__.return_value.get.side_effect = raise_exc
    else:
        client.__enter__.return_value.get.return_value = response
    return client


def _response(json_body: object, status_code: int = 200) -> MagicMock:
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_body
    if status_code >= 400:
        r.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=r
        )
    return r


def test_manglish_to_malayalam_returns_candidates():
    body = {"success": True, "result": ["ഓടുക", "ഓട്ടുക"]}
    with patch(
        "linguaalayam.transliteration.varnam.httpx.Client",
        return_value=_mock_client(_response(body)),
    ):
        result = manglish_to_malayalam("oduka")
    assert result == ["ഓടുക", "ഓട്ടുക"]


def test_manglish_to_malayalam_deduplicates_preserving_order():
    body = {"success": True, "result": ["ഓടുക", "ഓട്ടുക", "ഓടുക"]}
    with patch(
        "linguaalayam.transliteration.varnam.httpx.Client",
        return_value=_mock_client(_response(body)),
    ):
        result = manglish_to_malayalam("oduka")
    assert result == ["ഓടുക", "ഓട്ടുക"]


def test_manglish_to_malayalam_filters_non_malayalam_tokens():
    body = {"success": True, "result": ["ഓടുക", "not-malayalam", "123"]}
    with patch(
        "linguaalayam.transliteration.varnam.httpx.Client",
        return_value=_mock_client(_response(body)),
    ):
        result = manglish_to_malayalam("oduka")
    assert result == ["ഓടുക"]


def test_manglish_to_malayalam_unsuccessful_response_returns_empty():
    body = {"success": False, "error": "no match"}
    with patch(
        "linguaalayam.transliteration.varnam.httpx.Client",
        return_value=_mock_client(_response(body)),
    ):
        result = manglish_to_malayalam("xyzzy")
    assert result == []


def test_manglish_to_malayalam_non_list_result_returns_empty():
    body = {"success": True, "result": "not-a-list"}
    with patch(
        "linguaalayam.transliteration.varnam.httpx.Client",
        return_value=_mock_client(_response(body)),
    ):
        result = manglish_to_malayalam("oduka")
    assert result == []


def test_manglish_to_malayalam_non_dict_body_returns_empty():
    with patch(
        "linguaalayam.transliteration.varnam.httpx.Client",
        return_value=_mock_client(_response(["oops"])),
    ):
        result = manglish_to_malayalam("oduka")
    assert result == []


def test_manglish_to_malayalam_timeout_returns_empty():
    with patch(
        "linguaalayam.transliteration.varnam.httpx.Client",
        return_value=_mock_client(raise_exc=httpx.TimeoutException("timed out")),
    ):
        result = manglish_to_malayalam("oduka")
    assert result == []


def test_manglish_to_malayalam_request_error_returns_empty():
    with patch(
        "linguaalayam.transliteration.varnam.httpx.Client",
        return_value=_mock_client(raise_exc=httpx.RequestError("boom")),
    ):
        result = manglish_to_malayalam("oduka")
    assert result == []


def test_manglish_to_malayalam_http_error_status_returns_empty():
    with patch(
        "linguaalayam.transliteration.varnam.httpx.Client",
        return_value=_mock_client(_response({}, status_code=500)),
    ):
        result = manglish_to_malayalam("oduka")
    assert result == []


def test_manglish_to_malayalam_non_json_response_returns_empty():
    r = _response({})
    r.json.side_effect = ValueError("not json")
    with patch("linguaalayam.transliteration.varnam.httpx.Client", return_value=_mock_client(r)):
        result = manglish_to_malayalam("oduka")
    assert result == []


def test_manglish_to_malayalam_non_string_items_skipped():
    body = {"success": True, "result": ["ഓടുക", 123, None]}
    with patch(
        "linguaalayam.transliteration.varnam.httpx.Client",
        return_value=_mock_client(_response(body)),
    ):
        result = manglish_to_malayalam("oduka")
    assert result == ["ഓടുക"]
