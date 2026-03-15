"""Tests for drive commands."""

from infomaniak_cli.commands.drive import cmd_drive_list


class TestDriveList:
    def test_displays_table(self, capsys, mock_token, mock_account_id, mock_api, fake_args):
        _, response = mock_api
        response.json.return_value = {
            "result": "success",
            "data": [
                {"id": 1, "customer_name": "mysite.com", "service_name": "drive",
                 "is_free": True, "is_zero_price": False,
                 "has_maintenance": False, "is_locked": False, "has_operation_in_progress": False},
            ],
            "pages": 1,
        }

        cmd_drive_list(fake_args())
        captured = capsys.readouterr()
        assert "mysite.com" in captured.out
        assert "kDrive (1)" in captured.out

    def test_empty(self, capsys, mock_token, mock_account_id, mock_api, fake_args):
        _, response = mock_api
        response.json.return_value = {"result": "success", "data": [], "pages": 1}

        cmd_drive_list(fake_args())
        captured = capsys.readouterr()
        assert "No kDrive" in captured.out
