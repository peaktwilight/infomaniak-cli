"""Tests for account command."""

import json

import pytest

from infomaniak_cli.commands.account import cmd_account


class TestAccount:
    def test_shows_product_summary(self, capsys, mock_token, mock_account_id, mock_api, fake_args):
        _, response = mock_api
        response.json.side_effect = [
            # accounts call (may fail, that's ok)
            {"result": "success", "data": [{"id": 12345, "name": "Test Account"}]},
            # products call
            {"result": "success", "data": [
                {"service_name": "domain", "customer_name": "a.com",
                 "has_maintenance": False, "is_locked": False, "has_operation_in_progress": False},
                {"service_name": "domain", "customer_name": "b.com",
                 "has_maintenance": False, "is_locked": False, "has_operation_in_progress": False},
                {"service_name": "email_hosting", "customer_name": "a.com",
                 "has_maintenance": False, "is_locked": False, "has_operation_in_progress": False},
            ], "pages": 1},
        ]

        cmd_account(fake_args())
        captured = capsys.readouterr()
        assert "Test Account" in captured.out
        assert "3 products" in captured.out
        assert "domain" in captured.out
        assert "email_hosting" in captured.out

    def test_json_output(self, capsys, mock_token, mock_account_id, mock_api, fake_args):
        _, response = mock_api
        response.json.side_effect = [
            {"result": "success", "data": [{"id": 12345, "name": "Test"}]},
            {"result": "success", "data": [{"service_name": "domain", "customer_name": "a.com"}], "pages": 1},
        ]

        with pytest.raises(SystemExit) as exc:
            cmd_account(fake_args(json=True))
        assert exc.value.code == 0
        data = json.loads(capsys.readouterr().out)
        assert "account" in data
        assert "summary" in data
