"""Tests for hosting commands."""

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
