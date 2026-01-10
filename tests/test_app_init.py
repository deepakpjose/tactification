import pytest


def test_create_app_registers_blueprints(app_instance):
    # The fixture already calls create_app; ensure blueprints exist.
    assert "main" in app_instance.blueprints
    assert "auth" in app_instance.blueprints


#def test_external_url_handler_returns_lookup(monkeypatch, app_instance):
#    from app import external_url_handler
#
#    monkeypatch.setattr("app.lookup_url", lambda endpoint, **values: "http://example.com/result")
#    url = external_url_handler(Exception("err"), "external", {"id": 1})
#    assert url == "http://example.com/result"
