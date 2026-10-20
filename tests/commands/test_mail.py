"""Tests for mail commands."""

import json

import pytest

from infomaniak_cli.commands.mail import (
    cmd_mail_alias_add, cmd_mail_alias_delete, cmd_mail_aliases, cmd_mail_forward_add,
    cmd_mail_forward_delete, cmd_mail_forwarding, cmd_mail_list, cmd_mail_show,
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


def _writes(mock_req):
    return [(c.args[0], c.args[1].split("/1/")[1], c.kwargs["json"]) for c in mock_req.call_args_list]


class TestMailWrites:
    def test_alias_add(self, capsys, mock_token, mock_api, fake_args):
        mock_req, response = mock_api
        response.json.return_value = {"result": "success", "data": True}

        cmd_mail_alias_add(fake_args(mail_hosting_id="123", mailbox_name="hello", alias="support"))

        assert _writes(mock_req) == [
            ("POST", "mail_hostings/123/mailboxes/hello/aliases", {"alias": "support"})]
        assert "Add alias support" in capsys.readouterr().out

    def test_alias_rejects_domain_part(self, capsys, mock_token, mock_api, fake_args):
        mock_req, _ = mock_api

        with pytest.raises(SystemExit) as exc:
            cmd_mail_alias_add(fake_args(mail_hosting_id="123", mailbox_name="hello",
                                         alias="support@example.com"))

        assert exc.value.code == 1
        mock_req.assert_not_called()

    def test_alias_delete_with_yes(self, mock_token, mock_api, fake_args):
        mock_req, response = mock_api
        response.json.return_value = {"result": "success", "data": True}

        cmd_mail_alias_delete(fake_args(mail_hosting_id="123", mailbox_name="hello",
                                        alias="support", yes=True))

        assert _writes(mock_req) == [
            ("DELETE", "mail_hostings/123/mailboxes/hello/aliases/support", None)]

    def test_forward_add_sends_redirect_address(self, mock_token, mock_api, fake_args):
        mock_req, response = mock_api
        response.json.return_value = {"result": "success", "data": {"email": "a@example.net"}}

        cmd_mail_forward_add(fake_args(mail_hosting_id="123", mailbox_name="hello",
                                       address="a@example.net", yes=True))

        assert _writes(mock_req) == [
            ("POST", "mail_hostings/123/mailboxes/hello/forwarding_addresses",
             {"redirect_address": "a@example.net"})]

    def test_forward_add_rejects_non_address(self, mock_token, mock_api, fake_args):
        mock_req, _ = mock_api

        with pytest.raises(SystemExit):
            cmd_mail_forward_add(fake_args(mail_hosting_id="123", mailbox_name="hello",
                                           address="nobody", yes=True))

        mock_req.assert_not_called()

    def test_forward_delete_encodes_address(self, mock_token, mock_api, fake_args):
        mock_req, response = mock_api
        response.json.return_value = {"result": "success", "data": True}

        cmd_mail_forward_delete(fake_args(mail_hosting_id="123", mailbox_name="hello",
                                          address="a+b@example.net", yes=True))

        assert _writes(mock_req)[0][1].endswith("/forwarding_addresses/a%2Bb%40example.net")

    @pytest.mark.parametrize("handler, extra", [
        (cmd_mail_alias_add, {"alias": "support"}),
        (cmd_mail_alias_delete, {"alias": "support"}),
        (cmd_mail_forward_add, {"address": "a@example.net"}),
        (cmd_mail_forward_delete, {"address": "a@example.net"}),
    ])
    def test_dry_run_sends_nothing(self, handler, extra, capsys, mock_token, mock_api, fake_args):
        mock_req, _ = mock_api

        handler(fake_args(mail_hosting_id="123", mailbox_name="hello", dry_run=True, **extra))

        mock_req.assert_not_called()
        assert "Would" in capsys.readouterr().out

    @pytest.mark.parametrize("answer, sent", [("n", False), ("y", True)])
    def test_confirmation_controls_the_write(
            self, answer, sent, monkeypatch, mock_token, mock_api, fake_args):
        mock_req, response = mock_api
        response.json.return_value = {"result": "success", "data": True}
        monkeypatch.setattr("builtins.input", lambda *_: answer)

        cmd_mail_forward_delete(fake_args(mail_hosting_id="123", mailbox_name="hello",
                                          address="a@example.net"))

        assert mock_req.called is sent

    def test_no_terminal_asks_for_yes(self, capsys, monkeypatch, mock_token, mock_api, fake_args):
        mock_req, _ = mock_api
        monkeypatch.setattr("builtins.input", lambda *_: (_ for _ in ()).throw(EOFError()))

        with pytest.raises(SystemExit) as exc:
            cmd_mail_forward_add(fake_args(mail_hosting_id="123", mailbox_name="hello",
                                           address="a@example.net"))

        assert exc.value.code == 1
        assert "--yes" in capsys.readouterr().out
        mock_req.assert_not_called()
