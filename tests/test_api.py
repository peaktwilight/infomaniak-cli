"""Tests for API client."""

import pytest
from unittest.mock import MagicMock, patch

from infomaniak_cli.api import api_request, api_request_paginated


class TestApiRequest:
    def test_get_success(self, mock_api):
        mock_req, response = mock_api
        response.json.return_value = {"result": "success", "data": [{"id": 1}]}

        result = api_request("GET", "/1/test", "token123")

        mock_req.assert_called_once()
        call_kwargs = mock_req.call_args
        assert call_kwargs[1]["headers"]["Authorization"] == "Bearer token123"
        assert result["data"] == [{"id": 1}]

    def test_post_with_json_body(self, mock_api):
        mock_req, response = mock_api
        response.json.return_value = {"result": "success", "data": {"id": 99}}

        api_request("POST", "/2/zones/test.com/records", "tok", json_data={"type": "A"})

        assert mock_req.call_args[1]["json"] == {"type": "A"}

    def test_204_returns_success(self, mock_api):
        mock_req, response = mock_api
        response.status_code = 204

        result = api_request("DELETE", "/test", "tok")
        assert result == {"result": "success", "data": None}

    def test_api_error_exits(self, mock_api):
        mock_req, response = mock_api
        response.json.return_value = {
            "result": "error",
            "error": {"code": "forbidden", "description": "No access"},
        }

        with pytest.raises(SystemExit):
            api_request("GET", "/test", "tok")

    def test_non_json_response_exits(self, mock_api):
        mock_req, response = mock_api
        response.json.side_effect = ValueError("No JSON")
        response.text = "Bad Gateway"

        with pytest.raises(SystemExit):
            api_request("GET", "/test", "tok")

    def test_http_error_exits(self, mock_api):
        mock_req, response = mock_api
        response.status_code = 500
        response.json.return_value = {"result": "success", "data": None}
        response.text = "Internal Server Error"

        with pytest.raises(SystemExit):
            api_request("GET", "/test", "tok")


class TestApiRequestPaginated:
    def test_single_page(self, mock_api):
        mock_req, response = mock_api
        response.json.return_value = {
            "result": "success",
            "data": [{"id": 1}, {"id": 2}],
            "pages": 1,
            "page": 1,
        }

        result = api_request_paginated("/1/products", "tok")
        assert len(result) == 2

    def test_multiple_pages(self, mock_api):
        mock_req, response = mock_api
        page_data = [
            {"result": "success", "data": [{"id": 1}], "pages": 3, "page": 1},
            {"result": "success", "data": [{"id": 2}], "pages": 3, "page": 2},
            {"result": "success", "data": [{"id": 3}], "pages": 3, "page": 3},
        ]
        response.json.side_effect = page_data

        result = api_request_paginated("/1/products", "tok")
        assert len(result) == 3
        assert [r["id"] for r in result] == [1, 2, 3]


class TestReadOnlyMode:
    @pytest.mark.parametrize("method", ["POST", "PUT", "DELETE"])
    def test_blocks_writes(self, method, monkeypatch, capsys, mock_api):
        mock_req, _ = mock_api
        monkeypatch.setenv("INFOMANIAK_READ_ONLY", "1")

        with pytest.raises(SystemExit) as exc:
            api_request(method, "/2/zones/test.com/records", "tok", json_data={"type": "A"})

        assert exc.value.code == 1
        assert "was not sent" in capsys.readouterr().out
        mock_req.assert_not_called()

    def test_allows_reads(self, monkeypatch, mock_api):
        mock_req, response = mock_api
        response.json.return_value = {"result": "success", "data": []}
        monkeypatch.setenv("INFOMANIAK_READ_ONLY", "1")

        api_request("GET", "/1/products", "tok")

        mock_req.assert_called_once()
