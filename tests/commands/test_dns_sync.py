"""Regression tests for safe DNS sync updates and partial failures."""

import json
from unittest.mock import patch

import pytest
import requests

from infomaniak_cli.commands.dns import cmd_dns_sync


@pytest.fixture
def run_sync(tmp_path, mock_token, fake_args):
    def run(live, desired, *, fail_method=None, error=None, dry_run=False):
        path = tmp_path / "desired.json"
        path.write_text(json.dumps(desired))
        calls = []

        def api(method, endpoint, token, **kwargs):
            calls.append((method, endpoint, kwargs.get("json_data")))
            if method == "GET":
                return {"data": live}
            if method == fail_method:
                raise error if error is not None else SystemExit(1)
            return {"result": "success", "data": {}}

        with patch("infomaniak_cli.commands.dns.api_request", side_effect=api):
            try:
                cmd_dns_sync(fake_args(domain="example.com", file=str(path), dry_run=dry_run, yes=True))
            except SystemExit as exc:
                return calls, exc.code
        return calls, 0

    return run


def record(record_id=1, source="www", target="192.0.2.1", ttl=3600, rtype="A"):
    return {"id": record_id, "type": rtype, "source": source, "target": target, "ttl": ttl}


@pytest.mark.parametrize("rtype,old,new", [
    ("A", "192.0.2.1", "192.0.2.2"),
    ("CNAME", "old.example.net.", "new.example.net."),
])
def test_replacement_updates_existing_id_without_deleting(run_sync, rtype, old, new):
    calls, code = run_sync([record(target=old, rtype=rtype)], [record(target=new, rtype=rtype)])
    assert code == 0
    assert [c[0] for c in calls] == ["GET", "PUT"]
    assert calls[1][1].endswith("/records/1")
    assert calls[1][2] == {"target": new, "ttl": 3600}


@pytest.mark.parametrize("live_source,desired_source", [("www", "www"), ("", "@"), (".", "")])
def test_ttl_only_change_is_applied(run_sync, live_source, desired_source):
    calls, code = run_sync([record(source=live_source)], [record(source=desired_source, ttl=300)])
    assert code == 0
    assert [c[0] for c in calls] == ["GET", "PUT"]
    assert calls[1][2] == {"ttl": 300}


def test_failed_replacement_leaves_old_record_in_place(run_sync, capsys):
    calls, code = run_sync([record()], [record(target="192.0.2.2")], fail_method="PUT")
    assert code == 1
    assert [c[0] for c in calls] == ["GET", "PUT"]
    assert "Sync complete" not in capsys.readouterr().out


@pytest.mark.parametrize("error", [SystemExit(1), requests.Timeout("request timed out")])
def test_failed_creation_prevents_deletions(run_sync, capsys, error):
    calls, code = run_sync([record(source="old")], [record(source="new")], fail_method="POST", error=error)
    assert code == 1
    assert [c[0] for c in calls] == ["GET", "POST"]
    out = capsys.readouterr().out
    assert "Sync incomplete" in out
    assert "Sync complete" not in out


def test_new_records_are_created_before_old_records_are_deleted(run_sync):
    calls, code = run_sync([record(source="old")], [record(source="new")])
    assert code == 0
    assert [c[0] for c in calls] == ["GET", "POST", "DELETE"]


def test_failed_delete_stops_remaining_deletions(run_sync, capsys):
    calls, code = run_sync([record(source="a"), record(record_id=2, source="b")], [], fail_method="DELETE")
    assert code == 1
    assert [c[0] for c in calls] == ["GET", "DELETE"]
    assert "Sync incomplete" in capsys.readouterr().out


def test_dry_run_previews_target_and_ttl_updates(run_sync, capsys):
    calls, code = run_sync([record()], [record(target="192.0.2.2", ttl=300)], dry_run=True)
    assert code == 0
    assert [c[0] for c in calls] == ["GET"]
    out = capsys.readouterr().out
    assert "1 to update" in out
    assert "192.0.2.1" in out and "192.0.2.2" in out
    assert "300" in out


def test_multi_value_record_set_keeps_matching_record(run_sync):
    live = [record(), record(record_id=2, target="192.0.2.2")]
    desired = [record(), record(record_id=2, target="192.0.2.3")]
    calls, code = run_sync(live, desired)
    assert code == 0
    assert [c[0] for c in calls] == ["GET", "PUT"]
    assert calls[1][1].endswith("/records/2")


def test_failed_update_prevents_obsolete_record_deletion(run_sync):
    calls, code = run_sync(
        [record(), record(record_id=2, source="old")],
        [record(ttl=300)], fail_method="PUT",
    )
    assert code == 1
    assert [c[0] for c in calls] == ["GET", "PUT"]


def test_ambiguous_replacements_create_before_deleting(run_sync):
    calls, code = run_sync(
        [record(), record(record_id=2, target="192.0.2.2")],
        [record(target="192.0.2.3"), record(target="192.0.2.4")],
    )
    assert code == 0
    assert [c[0] for c in calls] == ["GET", "POST", "POST", "DELETE", "DELETE"]


def test_conflicting_record_type_creation_does_not_remove_working_record(run_sync):
    calls, code = run_sync(
        [record()], [record(rtype="CNAME", target="new.example.net.")], fail_method="POST",
    )
    assert code == 1
    assert [c[0] for c in calls] == ["GET", "POST"]


def test_ns_and_soa_are_not_deleted_during_apply(run_sync):
    calls, code = run_sync(
        [record(rtype="NS", source="@", target="ns.example.net."),
         record(record_id=2, rtype="SOA", source="@", target="soa.example.net.")],
        [],
    )
    assert code == 0
    assert [c[0] for c in calls] == ["GET"]
