"""Tests for DNS propagation command."""

import json
from unittest.mock import patch

import dns.exception
import dns.resolver
import pytest

from infomaniak_cli import output
from infomaniak_cli.commands.propagation import RESOLVERS, _resolve, cmd_dns_propagation


class TestDnsPropagation:
    def test_all_agree(self, capsys, fake_args, monkeypatch):
        monkeypatch.setattr(output, "_COLOR", False)

        with patch("infomaniak_cli.commands.propagation._resolve") as mock_resolve:
            mock_resolve.return_value = ["1.2.3.4"]

            cmd_dns_propagation(fake_args(domain="example.com", name="@", type="A"))
            captured = capsys.readouterr()
            assert "All queried resolvers agree" in captured.out
            assert "fully propagated" not in captured.out
            assert "1.2.3.4" in captured.out

    def test_inconsistent(self, capsys, fake_args, monkeypatch):
        monkeypatch.setattr(output, "_COLOR", False)

        call_count = [0]
        def mock_resolve(domain, rtype, resolver_ip):
            call_count[0] += 1
            if call_count[0] <= 3:
                return ["1.2.3.4"]
            return ["5.6.7.8"]

        with patch("infomaniak_cli.commands.propagation._resolve", side_effect=mock_resolve):
            with pytest.raises(SystemExit) as exc:
                cmd_dns_propagation(fake_args(domain="example.com", name="@", type="A"))
            assert exc.value.code == 1
            captured = capsys.readouterr()
            assert "Inconsistent" in captured.out

    def test_with_subdomain(self, capsys, fake_args, monkeypatch):
        monkeypatch.setattr(output, "_COLOR", False)

        with patch("infomaniak_cli.commands.propagation._resolve") as mock_resolve:
            mock_resolve.return_value = ["1.2.3.4"]

            cmd_dns_propagation(fake_args(domain="example.com", name="www", type="A"))
            captured = capsys.readouterr()
            assert "www.example.com" in captured.out

    @pytest.mark.parametrize("error, message", [
        (dns.resolver.NXDOMAIN(), "NXDOMAIN"),
        (dns.resolver.NoAnswer(), "no answer"),
        (dns.resolver.NoNameservers(), "no nameservers"),
        (dns.exception.Timeout(), "timed out"),
        (dns.exception.DNSException("invalid response"), "invalid response"),
        (OSError("network unreachable"), "network unreachable"),
    ])
    def test_matching_errors_are_not_success(self, error, message, capsys, fake_args):
        with patch("dns.resolver.Resolver") as resolver:
            resolver.return_value.resolve.side_effect = error
            with pytest.raises(SystemExit) as exc:
                cmd_dns_propagation(fake_args(domain="example.com", name="@", type="A"))

        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert message in out
        assert "could not be verified" in out
        assert "fully propagated" not in out
        assert "All queried resolvers agree" not in out

    def test_one_failed_resolver_is_not_success(self, capsys, fake_args):
        with patch("dns.resolver.Resolver") as resolver:
            resolver.return_value.resolve.side_effect = [
                ["192.0.2.1"], dns.exception.Timeout(),
                ["192.0.2.1"], ["192.0.2.1"], ["192.0.2.1"],
            ]
            with pytest.raises(SystemExit) as exc:
                cmd_dns_propagation(fake_args(domain="example.com", name="@", type="A"))

        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert "1 resolver(s) failed" in out
        assert "192.0.2.1" in out

    def test_empty_answers_are_not_success(self, capsys, fake_args):
        with patch("dns.resolver.Resolver") as resolver:
            resolver.return_value.resolve.return_value = []
            with pytest.raises(SystemExit) as exc:
                cmd_dns_propagation(fake_args(domain="example.com", name="@", type="A"))
        assert exc.value.code == 1
        assert "could not be verified" in capsys.readouterr().out

    @pytest.mark.parametrize("failure", [False, True])
    def test_json_is_parseable_and_preserves_failure_status(self, failure, capsys, fake_args):
        with patch("dns.resolver.Resolver") as resolver:
            if failure:
                resolver.return_value.resolve.side_effect = dns.resolver.NXDOMAIN()
            else:
                resolver.return_value.resolve.return_value = ["192.0.2.1"]
            with pytest.raises(SystemExit) as exc:
                cmd_dns_propagation(fake_args(domain="example.com", name="@", type="A", json=True))

        assert exc.value.code == int(failure)
        results = json.loads(capsys.readouterr().out)
        assert len(results) == len(RESOLVERS)
        assert [r["ip"] for r in results] == [ip for _, ip in RESOLVERS]
        if failure:
            assert all(r["error"] == "NXDOMAIN" and r["answers"] == [] for r in results)
        else:
            assert all(r["answers"] == ["192.0.2.1"] for r in results)


@pytest.mark.parametrize("record_type, answers", [
    ("TXT", ['"v=spf1 -all"']),
    ("MX", ["10 mail.example.com."]),
    ("AAAA", ["2001:db8::2", "2001:db8::1"]),
])
def test_resolve_queries_requested_server_and_record_type(record_type, answers):
    with patch("dns.resolver.Resolver") as resolver:
        resolver.return_value.resolve.return_value = answers
        result = _resolve("example.com", record_type, "9.9.9.9")
        resolver.assert_called_once_with(configure=False)
        assert resolver.return_value.nameservers == ["9.9.9.9"]
        resolver.return_value.resolve.assert_called_once_with("example.com", record_type)
        assert result == sorted(answers)
