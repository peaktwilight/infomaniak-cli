"""Tests for DNS audit command."""

import json

import pytest
import requests

from infomaniak_cli import output
from infomaniak_cli.commands.audit import cmd_dns_audit


class TestDnsAudit:
    def _make_records(self, has_spf=True, has_dmarc=True, has_dkim=True, has_mx=True):
        """Helper to build a record set with optional features."""
        records = [
            {"type": "A", "source": ".", "target": "1.2.3.4", "ttl": 3600},
            {"type": "NS", "source": ".", "target": "ns1.example.com", "ttl": 3600},
        ]
        if has_spf:
            records.append({"type": "TXT", "source": ".", "target": '"v=spf1 include:example.com ~all"', "ttl": 3600})
        if has_dmarc:
            records.append({"type": "TXT", "source": "_dmarc", "target": '"v=DMARC1; p=reject"', "ttl": 3600})
        if has_dkim:
            records.append({"type": "CNAME", "source": "default._domainkey", "target": "dkim.example.com", "ttl": 3600})
        if has_mx:
            records.append({"type": "MX", "source": ".", "target": "10 mail.example.com", "ttl": 3600})
        return records

    def test_clean_domain(self, capsys, mock_token, mock_account_id, mock_api, fake_args, monkeypatch):
        monkeypatch.setattr(output, "_COLOR", False)
        _, response = mock_api
        response.json.side_effect = [
            {"result": "success", "data": [{"customer_name": "clean.com"}]},
            {"result": "success", "data": self._make_records()},
        ]

        cmd_dns_audit(fake_args(domain="clean.com"))
        captured = capsys.readouterr()
        assert "1 clean" in captured.out

    def test_missing_spf(self, capsys, mock_token, mock_account_id, mock_api, fake_args, monkeypatch):
        monkeypatch.setattr(output, "_COLOR", False)
        _, response = mock_api
        response.json.side_effect = [
            {"result": "success", "data": [{"customer_name": "nospf.com"}]},
            {"result": "success", "data": self._make_records(has_spf=False)},
        ]

        cmd_dns_audit(fake_args(domain="nospf.com"))
        captured = capsys.readouterr()
        assert "No SPF" in captured.out

    def test_missing_dmarc(self, capsys, mock_token, mock_account_id, mock_api, fake_args, monkeypatch):
        monkeypatch.setattr(output, "_COLOR", False)
        _, response = mock_api
        response.json.side_effect = [
            {"result": "success", "data": [{"customer_name": "nodmarc.com"}]},
            {"result": "success", "data": self._make_records(has_dmarc=False)},
        ]

        cmd_dns_audit(fake_args(domain="nodmarc.com"))
        captured = capsys.readouterr()
        assert "No DMARC" in captured.out

    def test_missing_dkim(self, capsys, mock_token, mock_account_id, mock_api, fake_args, monkeypatch):
        monkeypatch.setattr(output, "_COLOR", False)
        _, response = mock_api
        response.json.side_effect = [
            {"result": "success", "data": [{"customer_name": "nodkim.com"}]},
            {"result": "success", "data": self._make_records(has_dkim=False)},
        ]

        cmd_dns_audit(fake_args(domain="nodkim.com"))
        captured = capsys.readouterr()
        assert "No DKIM" in captured.out

    def test_multiple_issues(self, capsys, mock_token, mock_account_id, mock_api, fake_args, monkeypatch):
        monkeypatch.setattr(output, "_COLOR", False)
        _, response = mock_api
        response.json.side_effect = [
            {"result": "success", "data": [{"customer_name": "bad.com"}]},
            {"result": "success", "data": self._make_records(has_spf=False, has_dmarc=False, has_mx=False)},
        ]

        cmd_dns_audit(fake_args(domain="bad.com"))
        captured = capsys.readouterr()
        assert "No SPF" in captured.out
        assert "No DMARC" in captured.out

    @pytest.mark.parametrize("json_mode", [False, True])
    @pytest.mark.parametrize("failure", ["api_error", "timeout"])
    def test_unreadable_zone_is_not_reported_as_clean(
            self, json_mode, failure, capsys, mock_token, mock_account_id, mock_api, fake_args):
        request, response = mock_api
        domains = {"result": "success",
                   "data": [{"customer_name": "ok.example"}, {"customer_name": "bad.example"}]}
        zone = {"result": "success", "data": self._make_records()}
        if failure == "api_error":
            response.json.side_effect = [
                domains, zone,
                {"result": "error", "error": {"code": "forbidden", "description": "denied"}},
            ]
            response.status_code = 200
        else:
            response.json.side_effect = [domains, zone]
            request.side_effect = [response, response, requests.Timeout()]

        with pytest.raises(SystemExit) as exc:
            cmd_dns_audit(fake_args(json=json_mode))
        assert exc.value.code == 1
        captured = capsys.readouterr()
        assert "All domains passed" not in captured.out
        if json_mode:
            results = json.loads(captured.out)
            assert results[1] == {"domain": "bad.example", "issues": [], "error": "could not read records"}
            if failure == "api_error":
                assert "forbidden" in captured.err
        else:
            assert "1 could not be scanned" in captured.out

    def test_json_has_no_headings(self, capsys, mock_token, mock_account_id, mock_api, fake_args):
        _, response = mock_api
        response.json.side_effect = [
            {"result": "success", "data": [{"customer_name": "ok.example"}]},
            {"result": "success", "data": self._make_records()},
        ]
        with pytest.raises(SystemExit) as exc:
            cmd_dns_audit(fake_args(json=True))
        assert exc.value.code == 0
        assert json.loads(capsys.readouterr().out)[0]["domain"] == "ok.example"
