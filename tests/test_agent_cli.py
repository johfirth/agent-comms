import argparse

import httpx
import pytest

import agent_cli


def test_find_workspace_connect_error_exits_with_structured_message(monkeypatch, capsys):
    def fake_get(*args, **kwargs):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(agent_cli.httpx, "get", fake_get)
    monkeypatch.setattr(agent_cli, "BASE_URL", "http://example.invalid")

    with pytest.raises(SystemExit) as exc:
        agent_cli._find_workspace("demo")

    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.strip() == '{"error": "Cannot connect to agent-comms server at http://example.invalid"}'


def test_find_workspace_http_error_exits_with_structured_message(monkeypatch, capsys):
    request = httpx.Request("GET", "http://example.invalid/workspaces")
    response = httpx.Response(status_code=503, text="service unavailable", request=request)

    class DummyResponse:
        def raise_for_status(self):
            raise httpx.HTTPStatusError("bad status", request=request, response=response)

    monkeypatch.setattr(agent_cli.httpx, "get", lambda *args, **kwargs: DummyResponse())

    with pytest.raises(SystemExit) as exc:
        agent_cli._find_workspace("demo")

    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.strip() == '{"error": "HTTP 503: service unavailable"}'


def test_cmd_threads_connection_error_uses_structured_json(monkeypatch, capsys):
    monkeypatch.setattr(agent_cli, "_find_workspace", lambda _: {"id": "workspace-1", "name": "demo"})
    monkeypatch.setattr(agent_cli, "BASE_URL", "http://example.invalid")

    def fake_get(*args, **kwargs):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(agent_cli.httpx, "get", fake_get)
    args = argparse.Namespace(workspace_name="demo")

    with pytest.raises(SystemExit) as exc:
        agent_cli.cmd_threads(args)

    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.strip() == '{"error": "Cannot connect to agent-comms server at http://example.invalid"}'

