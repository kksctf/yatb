import pytest
import uuid
from . import client as client_cl, app, test_auth, TestClient
from .. import schema

client = client_cl


def test_read_main(client: TestClient):
    resp = client.get("/")
    assert resp.status_code == 200
