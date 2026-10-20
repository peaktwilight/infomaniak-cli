"""Tests for hosting commands."""

import json

import pytest

from infomaniak_cli.commands.hosting import cmd_hosting_list


class TestHostingList:
    def test_displays_table(self, capsys, mock_token, mock_account_id, mock_api, fake_args):
        _, response = mock_api
        response.json.return_value = {
            "result": "success",
            "data": [
                {"id": 1, "customer_name": "mysite.com", "service_name": "web_hosting",
                 "has_maintenance": False, "is_locked": False, "has_operation_in_progress": False},
            ],
            "pages": 1,
        }

        cmd_hosting_list(fake_args())
        captured = capsys.readouterr()
        assert "mysite.com" in captured.out
        assert "Web Hostings (1)" in captured.out

    def test_empty(self, capsys, mock_token, mock_account_id, mock_api, fake_args):
        _, response = mock_api
        response.json.return_value = {"result": "success", "data": [], "pages": 1}

        cmd_hosting_list(fake_args())
        captured = capsys.readouterr()
        assert "No web hostings" in captured.out

    def test_includes_hosting_and_web_hosting(
            self, capsys, mock_token, mock_account_id, mock_api, fake_args):
        _, response = mock_api
        expected = [
            {"id": 1, "service_name": "hosting", "customer_name": "one.example"},
            {"id": 2, "service_name": "web_hosting", "customer_name": "two.example"},
        ]
        response.json.return_value = {
            "result": "success",
            "data": expected + [{"id": 3, "service_name": "email_hosting"}],
            "pages": 1,
        }

        with pytest.raises(SystemExit) as exc:
            cmd_hosting_list(fake_args(json=True))
        assert exc.value.code == 0
        assert json.loads(capsys.readouterr().out) == expected
