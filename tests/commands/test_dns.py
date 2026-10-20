"""Tests for DNS commands."""

import json

import pytest
from unittest.mock import patch

from infomaniak_cli.commands.dns import (
    cmd_dns_add,
    cmd_dns_backup,
    cmd_dns_clone,
    cmd_dns_delete,
    cmd_dns_diff,
    cmd_dns_domains,
    cmd_dns_export,
    cmd_dns_import,
    cmd_dns_records,
    cmd_dns_search,
    cmd_dns_sync,
    cmd_dns_update,
)


_RECORD = {"id": 7, "type": "A", "source": "www", "target": "1.2.3.4", "ttl": 3600}


class TestDnsDomains:
    def test_displays_table(self, capsys, mock_token, mock_account_id, mock_api, fake_args):
        _, response = mock_api
        response.json.return_value = {
            "result": "success",
            "data": [
                {"id": 1, "customer_name": "example.com", "has_dnssec": True, "is_dns_managed_by_infomaniak": True},
                {"id": 2, "customer_name": "test.org", "has_dnssec": False, "is_dns_managed_by_infomaniak": False},
            ],
        }

        cmd_dns_domains(fake_args())
        captured = capsys.readouterr()
        assert "example.com" in captured.out
        assert "test.org" in captured.out
        assert "Domains (2)" in captured.out

    def test_json_output(self, capsys, mock_token, mock_account_id, mock_api, fake_args):
        _, response = mock_api
        response.json.return_value = {
            "result": "success",
            "data": [{"id": 1, "customer_name": "example.com"}],
        }

        with pytest.raises(SystemExit) as exc:
            cmd_dns_domains(fake_args(json=True))
        assert exc.value.code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data[0]["customer_name"] == "example.com"

    def test_empty(self, capsys, mock_token, mock_account_id, mock_api, fake_args):
        _, response = mock_api
        response.json.return_value = {"result": "success", "data": []}

        cmd_dns_domains(fake_args())
        captured = capsys.readouterr()
        assert "No domains" in captured.out


class TestDnsRecords:
    def test_lists_records(self, capsys, mock_token, mock_api, fake_args):
        _, response = mock_api
        response.json.return_value = {
            "result": "success",
            "data": [
                {"id": 100, "type": "A", "source": "www", "target": "1.2.3.4", "ttl": 3600},
                {"id": 101, "type": "CNAME", "source": "app", "target": "cdn.example.com", "ttl": 300},
            ],
        }

        cmd_dns_records(fake_args(domain="example.com", type=None))
        captured = capsys.readouterr()
        assert "1.2.3.4" in captured.out
        assert "cdn.example.com" in captured.out

    def test_filter_by_type(self, capsys, mock_token, mock_api, fake_args):
        _, response = mock_api
        response.json.return_value = {
            "result": "success",
            "data": [
                {"id": 100, "type": "A", "source": "www", "target": "1.2.3.4", "ttl": 3600},
                {"id": 101, "type": "CNAME", "source": "app", "target": "cdn.example.com", "ttl": 300},
            ],
        }

        cmd_dns_records(fake_args(domain="example.com", type="A"))
        captured = capsys.readouterr()
        assert "1.2.3.4" in captured.out
        assert "cdn.example.com" not in captured.out

    def test_dot_source_becomes_at(self, capsys, mock_token, mock_api, fake_args):
        _, response = mock_api
        response.json.return_value = {
            "result": "success",
            "data": [{"id": 100, "type": "A", "source": ".", "target": "1.2.3.4", "ttl": 3600}],
        }

        cmd_dns_records(fake_args(domain="example.com", type=None))
        captured = capsys.readouterr()
        assert "@" in captured.out


class TestDnsAdd:
    def test_sends_correct_payload(self, capsys, mock_token, mock_api, fake_args):
        mock_req, response = mock_api
        response.json.return_value = {"result": "success", "data": {"id": 999}}

        cmd_dns_add(fake_args(domain="example.com", type="A", source="www", target="1.2.3.4", ttl=3600))

        call_kwargs = mock_req.call_args[1]
        assert call_kwargs["json"]["type"] == "A"
        assert call_kwargs["json"]["source"] == "www"
        assert call_kwargs["json"]["target"] == "1.2.3.4"

    def test_at_source_becomes_empty(self, capsys, mock_token, mock_api, fake_args):
        mock_req, response = mock_api
        response.json.return_value = {"result": "success", "data": {"id": 999}}

        cmd_dns_add(fake_args(domain="example.com", type="A", source="@", target="1.2.3.4", ttl=3600))

        call_kwargs = mock_req.call_args[1]
        assert call_kwargs["json"]["source"] == ""

    def test_dry_run_sends_nothing(self, capsys, mock_token, mock_api, fake_args):
        mock_req, _ = mock_api

        cmd_dns_add(fake_args(domain="example.com", type="A", source="www", target="1.2.3.4",
                              ttl=3600, dry_run=True))

        mock_req.assert_not_called()
        assert "Would create" in capsys.readouterr().out


class TestDnsUpdate:
    def test_requires_target_or_ttl(self, fake_args, mock_token):
        with pytest.raises(SystemExit):
            cmd_dns_update(fake_args(domain="example.com", record_id="123", target=None, ttl=None))

    def test_shows_before_and_after(self, capsys, mock_token, mock_api, fake_args):
        mock_req, response = mock_api
        response.json.side_effect = [
            {"result": "success", "data": [_RECORD]},
            {"result": "success", "data": True},
        ]

        cmd_dns_update(fake_args(domain="example.com", record_id="7", target="5.6.7.8", ttl=300))

        out = capsys.readouterr().out
        assert "1.2.3.4 → 5.6.7.8" in out
        assert "3600 → 300" in out
        assert mock_req.call_args.args[0] == "PUT"

    def test_dry_run_does_not_write(self, capsys, mock_token, mock_api, fake_args):
        mock_req, response = mock_api
        response.json.return_value = {"result": "success", "data": [_RECORD]}

        cmd_dns_update(fake_args(domain="example.com", record_id="7", target="5.6.7.8",
                                 ttl=None, dry_run=True))

        assert [c.args[0] for c in mock_req.call_args_list] == ["GET"]
        assert "Dry run" in capsys.readouterr().out

    def test_unknown_record_id_exits_before_writing(self, capsys, mock_token, mock_api, fake_args):
        mock_req, response = mock_api
        response.json.return_value = {"result": "success", "data": [_RECORD]}

        with pytest.raises(SystemExit) as exc:
            cmd_dns_update(fake_args(domain="example.com", record_id="999", target="5.6.7.8", ttl=None))

        assert exc.value.code == 1
        assert "not found" in capsys.readouterr().out
        assert [c.args[0] for c in mock_req.call_args_list] == ["GET"]


class TestDnsDelete:
    def test_yes_deletes_and_prints_undo(self, capsys, mock_token, mock_api, fake_args):
        mock_req, response = mock_api
        txt = dict(_RECORD, type="TXT", source="_dmarc", target="v=DMARC1; p=none")
        response.json.side_effect = [
            {"result": "success", "data": [txt]},
            {"result": "success", "data": True},
        ]

        cmd_dns_delete(fake_args(domain="example.com", record_id="7", yes=True))

        assert mock_req.call_args.args[0] == "DELETE"
        out = capsys.readouterr().out
        assert "Undo: infomaniak dns add example.com TXT _dmarc 'v=DMARC1; p=none' --ttl 3600" in out

    def test_dry_run_does_not_delete(self, capsys, mock_token, mock_api, fake_args):
        mock_req, response = mock_api
        response.json.return_value = {"result": "success", "data": [_RECORD]}

        cmd_dns_delete(fake_args(domain="example.com", record_id="7", yes=False, dry_run=True))

        assert [c.args[0] for c in mock_req.call_args_list] == ["GET"]
        assert "Dry run" in capsys.readouterr().out

    def test_no_terminal_asks_for_yes(self, capsys, monkeypatch, mock_token, mock_api, fake_args):
        mock_req, response = mock_api
        response.json.return_value = {"result": "success", "data": [_RECORD]}
        monkeypatch.setattr("builtins.input", lambda *_: (_ for _ in ()).throw(EOFError()))

        with pytest.raises(SystemExit) as exc:
            cmd_dns_delete(fake_args(domain="example.com", record_id="7", yes=False))

        assert exc.value.code == 1
        assert "--yes" in capsys.readouterr().out
        assert [c.args[0] for c in mock_req.call_args_list] == ["GET"]


class TestDnsExport:
    def test_json_export(self, capsys, mock_token, mock_api, fake_args):
        _, response = mock_api
        response.json.return_value = {
            "result": "success",
            "data": [
                {"type": "A", "source": "www", "target": "1.2.3.4", "ttl": 3600},
            ],
        }

        cmd_dns_export(fake_args(domain="example.com", format="json", output=None))
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data[0]["type"] == "A"

    def test_export_to_file(self, tmp_path, mock_token, mock_api, fake_args, capsys):
        _, response = mock_api
        response.json.return_value = {
            "result": "success",
            "data": [{"type": "A", "source": "www", "target": "1.2.3.4", "ttl": 3600}],
        }

        outfile = str(tmp_path / "out.json")
        cmd_dns_export(fake_args(domain="example.com", format="json", output=outfile))

        content = (tmp_path / "out.json").read_text()
        data = json.loads(content)
        assert data[0]["target"] == "1.2.3.4"


class TestDnsImport:
    def test_imports_from_json(self, tmp_path, capsys, mock_token, mock_api, fake_args):
        mock_req, response = mock_api
        response.json.return_value = {"result": "success", "data": {"id": 1}}

        import_file = tmp_path / "records.json"
        import_file.write_text('[{"type":"A","source":"www","target":"1.2.3.4","ttl":3600}]')

        cmd_dns_import(fake_args(domain="example.com", file=str(import_file), yes=True))
        captured = capsys.readouterr()
        assert "1 created" in captured.out

    def test_missing_file_exits(self, fake_args, mock_token):
        with pytest.raises(SystemExit):
            cmd_dns_import(fake_args(domain="example.com", file="/nonexistent.json", yes=True))


class TestDnsDiff:
    def test_no_differences(self, tmp_path, capsys, mock_token, mock_api, fake_args, monkeypatch):
        from infomaniak_cli import output
        monkeypatch.setattr(output, "_COLOR", False)
        _, response = mock_api
        records = [
            {"type": "A", "source": "www", "target": "1.2.3.4", "ttl": 3600},
            {"type": "CNAME", "source": "app", "target": "cdn.example.com", "ttl": 300},
        ]
        response.json.return_value = {"result": "success", "data": records}

        diff_file = tmp_path / "records.json"
        diff_file.write_text(json.dumps(records))

        cmd_dns_diff(fake_args(domain="example.com", file=str(diff_file)))
        captured = capsys.readouterr()
        assert "No differences" in captured.out

    def test_shows_differences(self, tmp_path, capsys, mock_token, mock_api, fake_args, monkeypatch):
        from infomaniak_cli import output
        monkeypatch.setattr(output, "_COLOR", False)
        _, response = mock_api
        live_records = [
            {"type": "A", "source": "www", "target": "1.2.3.4", "ttl": 3600},
            {"type": "A", "source": "api", "target": "5.6.7.8", "ttl": 3600},
        ]
        file_records = [
            {"type": "A", "source": "www", "target": "1.2.3.4", "ttl": 3600},
            {"type": "A", "source": "new", "target": "9.9.9.9", "ttl": 300},
        ]
        response.json.return_value = {"result": "success", "data": live_records}

        diff_file = tmp_path / "records.json"
        diff_file.write_text(json.dumps(file_records))

        cmd_dns_diff(fake_args(domain="example.com", file=str(diff_file)))
        captured = capsys.readouterr()
        assert "In file but not live" in captured.out
        assert "Live but not in file" in captured.out
        assert "9.9.9.9" in captured.out
        assert "5.6.7.8" in captured.out

    def test_missing_file_exits(self, fake_args, mock_token):
        with pytest.raises(SystemExit):
            cmd_dns_diff(fake_args(domain="example.com", file="/nonexistent.json"))

    def test_json_output(self, tmp_path, capsys, mock_token, mock_api, fake_args):
        _, response = mock_api
        response.json.return_value = {
            "result": "success",
            "data": [{"type": "A", "source": "www", "target": "1.2.3.4", "ttl": 3600}],
        }
        diff_file = tmp_path / "records.json"
        diff_file.write_text('[{"type":"A","source":"new","target":"9.9.9.9","ttl":300}]')

        with pytest.raises(SystemExit) as exc:
            cmd_dns_diff(fake_args(domain="example.com", file=str(diff_file), json=True))
        assert exc.value.code == 0
        data = json.loads(capsys.readouterr().out)
        assert "only_in_file" in data
        assert "only_live" in data


class TestDnsClone:
    def test_clones_records(self, capsys, mock_token, mock_api, fake_args):
        mock_req, response = mock_api
        source_records = [
            {"type": "A", "source": "www", "target": "1.2.3.4", "ttl": 3600},
            {"type": "NS", "source": ".", "target": "ns1.example.com", "ttl": 3600},  # should be skipped
            {"type": "CNAME", "source": "app", "target": "cdn.example.com", "ttl": 300},
        ]
        # First call returns source records, subsequent calls are POST responses
        response.json.side_effect = [
            {"result": "success", "data": source_records},
            {"result": "success", "data": {"id": 1}},
            {"result": "success", "data": {"id": 2}},
        ]

        cmd_dns_clone(fake_args(source_domain="src.com", target_domain="dst.com", yes=True))
        captured = capsys.readouterr()
        assert "2 cloned" in captured.out
        # NS records should not appear in the cloned records list (only in the skip message)
        lines = [l.strip() for l in captured.out.split("\n") if "→" in l and "✓" in l]
        for line in lines:
            assert "ns1.example.com" not in line

    def test_skips_ns_and_soa(self, capsys, mock_token, mock_api, fake_args):
        _, response = mock_api
        response.json.side_effect = [
            {"result": "success", "data": [
                {"type": "NS", "source": ".", "target": "ns1.example.com", "ttl": 3600},
                {"type": "SOA", "source": ".", "target": "ns1.example.com admin.example.com", "ttl": 3600},
            ]},
        ]

        cmd_dns_clone(fake_args(source_domain="src.com", target_domain="dst.com", yes=True))
        captured = capsys.readouterr()
        assert "0 cloned" in captured.out


class TestDnsSearch:
    def test_finds_matches(self, capsys, mock_token, mock_account_id, mock_api, fake_args):
        _, response = mock_api
        response.json.side_effect = [
            # domains list
            {"result": "success", "data": [
                {"customer_name": "example.com"},
                {"customer_name": "test.org"},
            ]},
            # records for example.com
            {"result": "success", "data": [
                {"id": 1, "type": "A", "source": "www", "target": "1.2.3.4", "ttl": 3600},
                {"id": 2, "type": "A", "source": "api", "target": "5.6.7.8", "ttl": 3600},
            ]},
            # records for test.org
            {"result": "success", "data": [
                {"id": 3, "type": "A", "source": "www", "target": "9.9.9.9", "ttl": 3600},
            ]},
        ]

        cmd_dns_search(fake_args(query="www"))
        captured = capsys.readouterr()
        assert "2 matches" in captured.out
        assert "example.com" in captured.out
        assert "test.org" in captured.out

    def test_no_matches(self, capsys, mock_token, mock_account_id, mock_api, fake_args):
        _, response = mock_api
        response.json.side_effect = [
            {"result": "success", "data": [{"customer_name": "example.com"}]},
            {"result": "success", "data": [
                {"id": 1, "type": "A", "source": "www", "target": "1.2.3.4", "ttl": 3600},
            ]},
        ]

        cmd_dns_search(fake_args(query="nonexistent"))
        captured = capsys.readouterr()
        assert "No records matching" in captured.out


class TestDnsBackup:
    def test_backs_up_all_domains(self, tmp_path, capsys, mock_token, mock_account_id, mock_api, fake_args):
        _, response = mock_api
        response.json.side_effect = [
            # domains
            {"result": "success", "data": [
                {"customer_name": "a.com"},
                {"customer_name": "b.com"},
            ]},
            # records for a.com
            {"result": "success", "data": [
                {"type": "A", "source": "www", "target": "1.2.3.4", "ttl": 3600},
            ]},
            # records for b.com
            {"result": "success", "data": [
                {"type": "CNAME", "source": "app", "target": "cdn.b.com", "ttl": 300},
            ]},
        ]

        outdir = str(tmp_path / "backup")
        cmd_dns_backup(fake_args(output=outdir, format="json"))
        captured = capsys.readouterr()
        assert "a.com" in captured.out
        assert "b.com" in captured.out
        assert "Backed up 2 domains" in captured.out
        assert (tmp_path / "backup" / "a.com.json").exists()
        assert (tmp_path / "backup" / "b.com.json").exists()


class TestDnsSync:
    def test_already_in_sync(self, tmp_path, capsys, mock_token, mock_api, fake_args):
        _, response = mock_api
        records = [{"type": "A", "source": "www", "target": "1.2.3.4", "ttl": 3600}]
        response.json.return_value = {"result": "success", "data": records}

        sync_file = tmp_path / "records.json"
        sync_file.write_text(json.dumps(records))

        cmd_dns_sync(fake_args(domain="example.com", file=str(sync_file), dry_run=False, yes=True))
        captured = capsys.readouterr()
        assert "Already in sync" in captured.out

    def test_dry_run_shows_plan(self, tmp_path, capsys, mock_token, mock_api, fake_args, monkeypatch):
        from infomaniak_cli import output
        monkeypatch.setattr(output, "_COLOR", False)
        _, response = mock_api
        live = [
            {"id": 1, "type": "A", "source": "www", "target": "1.2.3.4", "ttl": 3600},
            {"id": 2, "type": "A", "source": "old", "target": "5.6.7.8", "ttl": 3600},
        ]
        desired = [
            {"type": "A", "source": "www", "target": "1.2.3.4", "ttl": 3600},
            {"type": "A", "source": "new", "target": "9.9.9.9", "ttl": 300},
        ]
        response.json.return_value = {"result": "success", "data": live}

        sync_file = tmp_path / "records.json"
        sync_file.write_text(json.dumps(desired))

        cmd_dns_sync(fake_args(domain="example.com", file=str(sync_file), dry_run=True, yes=False))
        captured = capsys.readouterr()
        assert "1 to create" in captured.out
        assert "1 to delete" in captured.out
        assert "1 unchanged" in captured.out
        assert "Dry run" in captured.out
        assert "9.9.9.9" in captured.out
        assert "5.6.7.8" in captured.out

    def test_skips_ns_soa_in_delete(self, tmp_path, capsys, mock_token, mock_api, fake_args):
        _, response = mock_api
        live = [
            {"id": 1, "type": "NS", "source": ".", "target": "ns1.example.com", "ttl": 3600},
            {"id": 2, "type": "A", "source": "www", "target": "1.2.3.4", "ttl": 3600},
        ]
        response.json.return_value = {"result": "success", "data": live}

        # File only has the A record — NS should NOT be deleted
        sync_file = tmp_path / "records.json"
        sync_file.write_text('[{"type":"A","source":"www","target":"1.2.3.4","ttl":3600}]')

        cmd_dns_sync(fake_args(domain="example.com", file=str(sync_file), dry_run=True, yes=False))
        captured = capsys.readouterr()
        assert "0 to delete" in captured.out

    def test_missing_file_exits(self, fake_args, mock_token):
        with pytest.raises(SystemExit):
            cmd_dns_sync(fake_args(domain="example.com", file="/nope.json", dry_run=False, yes=True))
