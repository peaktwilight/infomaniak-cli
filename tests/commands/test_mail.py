"""Tests for mail commands."""

import json

import pytest

from infomaniak_cli.commands.mail import (
    cmd_mail_aliases, cmd_mail_forwarding, cmd_mail_list, cmd_mail_show,
)


class TestMailList:
    def test_displays_table(self, capsys, mock_token, mock_account_id, mock_api, fake_args):
        _, response = mock_api
        response.json.return_value = {
            "result": "success",
            "data": [
                {"id": 1, "customer_name": "example.com", "service_name": "email_hosting",
                 "has_maintenance": False, "is_locked": False, "has_operation_in_progress": False},
            ],
            "pages": 1,
        }

        cmd_mail_list(fake_args())
        captured = capsys.readouterr()
        assert "example.com" in captured.out
        assert "Mail Hostings (1)" in captured.out

    def test_empty(self, capsys, mock_token, mock_account_id, mock_api, fake_args):
        _, response = mock_api
        response.json.return_value = {"result": "success", "data": [], "pages": 1}

        cmd_mail_list(fake_args())
        captured = capsys.readouterr()
        assert "No mail hostings" in captured.out

    def test_json_output(self, capsys, mock_token, mock_account_id, mock_api, fake_args):
        _, response = mock_api
        response.json.return_value = {
            "result": "success",
            "data": [{"id": 1, "customer_name": "test.com"}],
            "pages": 1,
        }

        with pytest.raises(SystemExit) as exc:
            cmd_mail_list(fake_args(json=True))
        assert exc.value.code == 0
        data = json.loads(capsys.readouterr().out)
        assert data[0]["customer_name"] == "test.com"


DETAILS = {"mailbox": "hello@example.com", "mailbox_name": "hello",
           "is_free_mail": False, "is_limited": True, "note": "Support"}
ALIASES = {"enabled_alias": 1, "aliases": ["support@example.com", "help@example.com"]}
FORWARDING = {"is_enabled": "1", "has_dont_deliver": "0", "has_forward_spam": "0",
              "redirect_adresses": [{"email": "other@example.net"}]}


@pytest.mark.parametrize("handler, suffix, payload", [
    (cmd_mail_show, "", DETAILS),
    (cmd_mail_aliases, "/aliases", ALIASES),
    (cmd_mail_forwarding, "/forwarding_addresses", FORWARDING),
])
class TestMailboxDetails:
    def test_requests_mailbox_endpoint(
            self, handler, suffix, payload, mock_token, mock_api, fake_args):
        request, response = mock_api
        response.json.return_value = {"result": "success", "data": payload}

        handler(fake_args(mail_hosting_id="123", mailbox_name="hello+tag"))
        assert request.call_args.args[1].endswith(f"/mail_hostings/123/mailboxes/hello%2Btag{suffix}")

    def test_json_output(self, handler, suffix, payload, capsys, mock_token, mock_api, fake_args):
        _, response = mock_api
        response.json.return_value = {"result": "success", "data": payload}

        with pytest.raises(SystemExit) as exc:
            handler(fake_args(mail_hosting_id="123", mailbox_name="hello", json=True))
        assert exc.value.code == 0
        assert json.loads(capsys.readouterr().out) == payload


def test_show_displays_details(capsys, mock_token, mock_api, fake_args):
    _, response = mock_api
    response.json.return_value = {"result": "success", "data": DETAILS}

    cmd_mail_show(fake_args(mail_hosting_id="123", mailbox_name="hello"))
    out = capsys.readouterr().out
    assert "hello@example.com" in out
    assert "Support" in out


def test_aliases_lists_each_alias(capsys, mock_token, mock_api, fake_args):
    _, response = mock_api
    response.json.return_value = {"result": "success", "data": ALIASES}

    cmd_mail_aliases(fake_args(mail_hosting_id="123", mailbox_name="hello"))
    out = capsys.readouterr().out
    assert "support@example.com" in out
    assert "help@example.com" in out


def test_forwarding_treats_string_zero_as_no(capsys, mock_token, mock_api, fake_args):
    _, response = mock_api
    response.json.return_value = {"result": "success", "data": FORWARDING}

    cmd_mail_forwarding(fake_args(mail_hosting_id="123", mailbox_name="hello"))
    lines = capsys.readouterr().out.splitlines()
    assert next(l for l in lines if "Enabled" in l).rstrip().endswith("yes")
    assert next(l for l in lines if "Forward spam" in l).rstrip().endswith("no")
    assert any("other@example.net" in l for l in lines)
